import os
import isodate
import tempfile # For sanitizing filenames
from app.workables.config.manager import get_config
import yt_dlp 

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

youtube_service = None

def _get_youtube_service():
    """Initializes and returns the YouTube API service client."""
    global youtube_service
    if youtube_service is None:
        config = get_config()
        api_key = config.get('YOUTUBE_API_KEY')
        if not api_key:
            print("ERROR: YOUTUBE_API_KEY not found in configuration for Google API Client.")
            return None
        try:
            youtube_service = build('youtube', 'v3', developerKey=api_key)
        except Exception as e:
            print(f"ERROR: Could not build YouTube service: {e}")
            return None
    return youtube_service


def get_video_info(video_id_or_url):
    """
    Fetches detailed video information using yt-dlp without downloading the video.

    Args:
        video_id_or_url (str): The YouTube video ID or full URL.

    Returns:
        dict: A dictionary containing video metadata (title, description, duration_seconds, etc.)
              or None if an error occurs.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True, # Do not download the video
        # 'forcejson': True, # Deprecated, extract_info returns a dict
        'extract_flat': 'discard_in_playlist', # Speeds up if URL is a playlist by mistake
        'dumpingle_json': True # Get info as JSON, alternative to forcejson
    }
    video_url = video_id_or_url if video_id_or_url.startswith('http') else f"https://www.youtube.com/watch?v={video_id_or_url}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            description = info.get('description', 'No Description')
            if description is None: 
                description = ''

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
        print(f"ERROR (yt-dlp): Could not extract info for {video_url}: {e}")
        return None
    except Exception as e:
        print(f"ERROR (get_video_info): An unexpected error occurred for {video_url}: {e}")
        return None

def get_last_livestream_data(limit=20):
    """
    Fetches data for the latest livestreams from a configured YouTube channel.
    Now uses get_video_info for more detailed information.
    """
    config = get_config() # Still need config for channel_id
    # api_key is handled by _get_youtube_service
    channel_id = config.get('channel_id')

    youtube = _get_youtube_service()
    if not youtube:
        print("ERROR: YouTube service could not be initialized.")
        return []

    # if not api_key: # Handled by _get_youtube_service
    #     print("ERROR: YOUTUBE_API_KEY not found in configuration.")
    #     return []
    if not channel_id:
        print("ERROR: channel_id not found in configuration.")
        return []

    try:
        # youtube = build('youtube', 'v3', developerKey=api_key) # Handled by _get_youtube_service
        channel_response = youtube.channels().list(
            id=channel_id,
            part="contentDetails"
        ).execute()

        if not channel_response.get('items'):
            print(f"ERROR: Could not retrieve channel details for channel ID: {channel_id}")
            return []

        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        playlist_response = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part='contentDetails',
            maxResults=limit
        ).execute()

        last_livestreams = []
        if 'items' in playlist_response and playlist_response['items']:
            for item in playlist_response['items']:
                video_id = item['contentDetails']['videoId']
                video_response = youtube.videos().list(
                    id=video_id,
                    part='snippet,liveStreamingDetails' # Keep snippet for fallback if yt-dlp fails
                ).execute()

                if video_response.get('items'):
                    video_item_api = video_response['items'][0]
                    if 'liveStreamingDetails' in video_item_api: # Check if it was a livestream
                        video_details_yt_dlp = get_video_info(video_id)
                        
                        if video_details_yt_dlp:
                            last_livestreams.append({
                                "id": video_id,
                                "title": video_details_yt_dlp.get('title', 'No Title'),
                                "description": video_details_yt_dlp.get('description', 'No Description'),
                                "URL": video_details_yt_dlp.get('webpage_url', f"https://www.youtube.com/watch?v={video_id}"),
                                'length_seconds': video_details_yt_dlp.get('duration_seconds'),
                                'length_string': video_details_yt_dlp.get('duration_string', 'N/A'),
                                'upload_date': video_details_yt_dlp.get('upload_date')
                            })
                        else:
                            # Fallback to API snippet if get_video_info fails
                            snippet = video_item_api['snippet']
                            last_livestreams.append({
                                "id": video_id,
                                "title": snippet.get('title', 'No Title'),
                                "description": snippet.get('description', 'No Description'),
                                "URL": f"https://www.youtube.com/watch?v={video_id}",
                                'length_seconds': None,
                                'length_string': 'Error fetching duration via yt-dlp',
                                'upload_date': snippet.get('publishedAt') # Format: YYYY-MM-DDTHH:MM:SSZ
                            })
                else:
                    print(f"Could not retrieve details for video ID: {video_id} via YouTube API")
        else:
            print("No videos found in the uploads playlist.")
            
        return last_livestreams

    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred: {e.content}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred in get_last_livestream_data: {e}")
        return []


def download_youtube_audio_from_url(URL): # Renamed from dowload_youtube
    # global youtube # Not needed for yt_dlp
    # config = get_config() # Not needed for yt_dlp specific part
    # if not youtube: # Not needed
    #     api_key = config.get('YOUTUBE_API_KEY', None)
    #     youtube = build('youtube', 'v3', developerKey=api_key)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file_name = f'{temp_file.name}.mp3'
    temp_file.close() 
    
    download_options = {
        'format': 'bestaudio/best',
        'outtmpl': f'{temp_file.name}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        
        'verbose': True, # FOR DEBUGGING
        'keepvideo': False,
        'overwrites': True,
        'ffmpeg_location': None 
    }

    try:
        with yt_dlp.YoutubeDL(download_options) as ydl:
            print(f"Downloading to: {temp_file_name}")
            ydl.download([URL])
            return temp_file_name
    except Exception as e:
        print(f"Download error: {str(e)}")
        # Cleanup any temporary files
        for ext in ['.mp3', '.webm', '.m4a', '.part']:
            possible_file = f"{temp_file_name}{ext}"
            if os.path.exists(possible_file):
                os.unlink(possible_file)
        raise

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


