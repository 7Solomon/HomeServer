from __future__ import annotations
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import tempfile
import os
import isodate

from app.workables.config.manager import get_config
from app.workables.predigt_upload.ffmpeg_setup import get_ffmpeg_path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import yt_dlp

youtube_service = None

def _get_youtube_service():
    global youtube_service
    if youtube_service is not None:
        return youtube_service
    cfg = get_config() or {}
    api_key = cfg.get("YOUTUBE_API_KEY")
    if not api_key:
        logging.error("ERROR: YOUTUBE_API_KEY not found in configuration for Google API Client.")
        youtube_service = None
        return None
    try:
        youtube_service = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
    except Exception as e:
        logging.error(f"ERROR: YouTube service could not be initialized: {e}")
        youtube_service = None
    return youtube_service

def _iso8601_to_seconds(iso: str | None) -> int | None:
    if not iso:
        return None
    # PT#H#M#S
    import re
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", iso)
    if not m:
        return None
    h = int(m.group(1) or 0)
    m_ = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h * 3600 + m_ * 60 + s

def _format_duration(sec: int | None) -> str | None:
    if sec is None:
        return None
    sec = max(0, int(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def get_last_livestream_data(limit=7):
    """
    Returns ONLY completed livestreams as a list of dicts:
    { id, title, date, thumbnail_url, duration_seconds, duration_string }
    """
    cfg = get_config() or {}
    channel_id = cfg.get("channel_id")
    yt = _get_youtube_service()
    if not yt:
        return []

    if not channel_id:
        logging.error("channel_id missing in config")
        return []

    try:
        # 1) Find completed livestreams (no Shorts, no uploads, no upcoming/live)
        search_res = yt.search().list(
            part="id",
            channelId=channel_id,
            type="video",
            eventType="completed",   # ONLY previous livestreams
            order="date",
            maxResults=min(int(limit or 7), 50)
        ).execute()

        items = search_res.get("items", [])
        ids = [it.get("id", {}).get("videoId") for it in items if it.get("id", {}).get("videoId")]
        if not ids:
            return []

        # 2) Fetch details (duration, thumbnails, title, actual times)
        vres = yt.videos().list(
            part="snippet,contentDetails,liveStreamingDetails",
            id=",".join(ids)
        ).execute()
        details_by_id = {v["id"]: v for v in vres.get("items", [])}

        # Preserve order from search
        out = []
        for vid in ids:
            v = details_by_id.get(vid, {})
            snip = v.get("snippet", {}) or {}
            thumbs = snip.get("thumbnails") or {}
            lsd = v.get("liveStreamingDetails", {}) or {}
            cd = v.get("contentDetails", {}) or {}

            # Prefer actualStartTime (fallback to publishedAt)
            actual_start = (lsd.get("actualStartTime") or snip.get("publishedAt") or "")
            date = actual_start[:10] if len(actual_start) >= 10 else None

            # Best available thumbnail
            t = thumbs.get("maxres") or thumbs.get("standard") or thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}
            thumb_url = t.get("url")

            iso = cd.get("duration")
            dur_sec = _iso8601_to_seconds(iso)
            dur_str = _format_duration(dur_sec)

            out.append({
                "id": vid,
                "title": snip.get("title") or "",
                "date": date,
                "thumbnail_url": thumb_url,
                "duration_seconds": dur_sec,
                "duration_string": dur_str,
            })
        return out[: int(limit or 7)]
    except HttpError as e:
        logging.error(f"YouTube API error: {e}")
        return []
    except Exception as e:
        logging.exception("get_last_livestream_data failed")
        return []

def _update_yt_dlp():
    """Update yt-dlp to the latest version in the current Python environment"""
    try:
        logging.info("Attempting to update yt-dlp...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logging.info("yt-dlp updated successfully")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update yt-dlp: {e}")
        return False
    except Exception as e:
        logging.exception(f"Unexpected error updating yt-dlp: {e}")
        return False

def download_youtube_audio_from_url(URL: str, retry_with_update: bool = True) -> str:
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    base = temp_file.name
    temp_file.close()

    # Tell yt-dlp where ffmpeg/ffprobe live (if bundled)
    ffdir = None
    try:
        ffdir = get_ffmpeg_path()
    except Exception:
        pass

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{base}.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "keepvideo": False,
        "overwrites": True,
        "verbose": False,
        "ffmpeg_location": ffdir or None,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(URL, download=True)

        mp3 = Path(f"{base}.mp3")
        if mp3.exists():
            return str(mp3)
        # Fallback: best-effort find something
        for ext in (".m4a", ".webm", ".opus"):
            p = Path(f"{base}{ext}")
            if p.exists():
                return str(p)
        raise FileNotFoundError("Downloaded audio file not found")
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        # Check if it's a format error
        if "Requested format is not available" in error_msg or "not available" in error_msg.lower():
            if retry_with_update:
                logging.warning(f"Format error encountered: {error_msg}. Attempting to update yt-dlp...")
                if _update_yt_dlp():
                    logging.info("Retrying download after yt-dlp update...")
                    # Retry once without update flag to prevent infinite loop
                    return download_youtube_audio_from_url(URL, retry_with_update=False)
                else:
                    logging.error("yt-dlp update failed, cannot retry download")
            raise
        else:
            # Other download errors, just raise
            raise
    except Exception as e:
        logging.exception(f"Unexpected error downloading from {URL}")
        raise

def get_video_info(video_id_or_url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': 'discard_in_playlist',
        # 'dump_single_json': True,  # not needed; extract_info returns dict
    }
    # Let yt-dlp find ffmpeg if needed (not strictly required for metadata)
    try:
        ffdir = get_ffmpeg_path()
        if ffdir:
            ydl_opts['ffmpeg_location'] = ffdir
    except Exception:
        pass

    video_url = video_id_or_url if video_id_or_url.startswith('http') else f"https://www.youtube.com/watch?v={video_id_or_url}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            description = info.get('description') or ''
            return {
                'id': info.get('id'),
                'title': info.get('title', 'No Title'),
                'description': description,
                'duration_seconds': info.get('duration'),
                'duration_string': info.get('duration_string'),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'thumbnail_url': info.get('thumbnail'),
                'webpage_url': info.get('webpage_url')
            }
    except yt_dlp.utils.DownloadError as e:
        # Upcoming live or restricted => let caller fall back to API snippet
        print(f"INFO (yt-dlp): metadata fallback for {video_url}: {e}")
        return None
    except Exception as e:
        print(f"ERROR (get_video_info): {e}")
        return None

def get_video_duration(video_id):
    service = _get_youtube_service()
    if not service:
        print("ERROR: YouTube service could not be initialized for get_video_duration.")
        return None

    try:
        video_response = service.videos().list(
            part='contentDetails',
            id=video_id
        ).execute()

        if 'items' in video_response and len(video_response['items']) > 0:
            content_details = video_response['items'][0]['contentDetails']
            duration_iso = content_details['duration'] # Renamed for clarity
            duration_seconds = isodate.parse_duration(duration_iso).total_seconds()
            return duration_seconds * 1000 # Return milliseconds
        else:
            return None
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred while fetching video duration: {e.content}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_video_duration: {e}")
        return None


