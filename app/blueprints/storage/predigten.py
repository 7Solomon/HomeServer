import re  # ADD THIS at top
import asyncio
import json
import logging
import shutil
import pathlib
import tempfile
from datetime import datetime

from flask import jsonify, render_template, request, Response, stream_with_context

from app.workables.predigt_upload.youtube import get_last_livestream_data, download_youtube_audio_from_url
from app.workables.predigt_upload.ftp_handler import list_ftp_files, refresh_website, upload_file_ftp
from app.workables.predigt_upload.audio import compress_audio, generate_id3_tags
        
from app.utils.auth import admin_token, admin_required
from app.blueprints.storage import storage_bp


@storage_bp.route('/admin/predigt_upload/page')
@admin_required
def predigt_upload():
    """List page for predigt upload management."""
    return render_template('storage/predigt_upload/list.html')
@storage_bp.route('/admin/predigt_upload/item/<string:video_id>', methods=['GET'])
@admin_required
def predigt_upload_item(video_id):
    """Detail page for a single video to process/upload."""
    return render_template('storage/predigt_upload/action.html', video_id=video_id)


@admin_token
@storage_bp.route('/api/predigt_upload/action/<int:limit>', methods=['GET'])
def get_action_data(limit):
    """
    Returns last livestreams with title, date (YYYY-MM-DD), and whether a file with
    the same date exists on the FTP server. Returns partial data with warnings on errors.
    """
    warnings = []
    try:
        # Livestreams (never raise to client)
        try:
            livestreams = get_last_livestream_data(limit) or []
        except Exception as e:
            logging.exception("get_last_livestream_data failed")
            warnings.append(f"YouTube list error: {e}")
            livestreams = []

        # FTP listing (optional; mark as unchecked if it fails)
        server_checked = True
        server_dates = set()
        try:
            status_code, files = list_ftp_files()
            files = files or []
            date_rx = re.compile(r'(\d{4}-\d{2}-\d{2})')
            for fname in files:
                m = date_rx.search(fname)
                if m:
                    server_dates.add(m.group(1))
        except Exception as e:
            logging.exception("list_ftp_files failed")
            warnings.append(f"FTP list error: {e}")
            server_checked = False

        items = []
        for v in livestreams:
            date_str = v.get("date")
            on_server = (date_str in server_dates) if (server_checked and date_str) else False
            items.append({
                "id": v.get("id"),
                "title": v.get("title"),
                "date": date_str,
                "on_server": on_server,
                "server_checked": server_checked,
                "thumbnail_url": v.get("thumbnail_url"),
                "duration_seconds": v.get("duration_seconds"),
                "duration_string": v.get("duration_string"),
            })

        return jsonify({
            "status": "success",
            "warnings": warnings,
            "items": items
        }), 200
    except Exception as e:
        logging.exception("Error in /action")
        return jsonify({"status": "error", "message": str(e)}), 500

@admin_required
@storage_bp.route('/predigt_upload/audio/process', methods=['POST'])
def process_audio_stream():
    """
    Processes an audio stream from a YouTube URL and streams NDJSON progress.
    Expects JSON: { "id": "...", "prediger": "...", "titel": "...", "datum": "YYYY-MM-DD" }
    """
    data = request.get_json(silent=True) or {}
    vid = data.get("id")
    prediger = data.get("prediger") or ""
    titel = data.get("titel") or ""
    datum_str = data.get("datum") or ""

    if not vid or not datum_str:
        return jsonify({"status": "error", "message": "Missing required fields: id, datum"}), 400

    # Parse date
    try:
        try:
            datum_dt = datetime.fromisoformat(datum_str)
        except ValueError:
            datum_dt = datetime.strptime(datum_str, "%Y-%m-%d")
    except Exception:
        return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD"}), 400

    video_url = f"https://www.youtube.com/watch?v={vid}"

    def gen():
        def nd(step, status, progress=None, message=None, **extra):
            payload = {"step": step, "status": status}
            if progress is not None:
                payload["progress"] = f"{int(progress):02d}"
            if message is not None:
                payload["message"] = message
            payload.update(extra)
            return json.dumps(payload) + "\n"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_p = pathlib.Path(temp_dir)
            try:
                # 1) Download
                yield nd("download", "in_progress", 5, "Starte Download…")
                downloaded_path = download_youtube_audio_from_url(video_url)  # temp .mp3 path
                downloaded_p = pathlib.Path(downloaded_path)
                staged_p = temp_dir_p / downloaded_p.name
                shutil.move(str(downloaded_p), staged_p)
                yield nd("download", "completed", 15, "Download abgeschlossen.")

                # 2) Compress
                yield nd("compress", "in_progress", 30, "Starte Kompression…")
                compressed_p = compress_audio(str(staged_p))
                yield nd("compress", "completed", 60, "Kompression abgeschlossen.")

                # 3) Tagging (stream sub-steps if your tagger yields events)
                meta = {
                    "title": titel,
                    "speaker": prediger,
                    "date": datum_dt.strftime("%Y-%m-%d"),
                    "year": datum_dt.strftime("%Y"),
                    "album": "Predigten aus Treffpunkt Leben Karlsruhe",
                    "genre": "Predigt Online",
                }
                try:
                    # If generate_id3_tags is a generator of dicts {step,status,message,...}
                    for evt in generate_id3_tags(str(compressed_p), meta):
                        yield json.dumps(evt) + "\n"
                    yield nd("tags", "completed", 80, "ID3-Tags gesetzt.")
                except TypeError:
                    # If it returns bool
                    ok = generate_id3_tags(str(compressed_p), meta)
                    yield nd("tags", "completed" if ok else "skipped", 80,
                             "ID3-Tags gesetzt." if ok else "ID3-Tags übersprungen.")

                # 4) Finalize
                final_name = f"predigt-{datum_dt.strftime('%Y-%m-%d')}_Treffpunkt_Leben_Karlsruhe.mp3"
                yield nd("finalize", "in_progress", 90, f"Benennen in {final_name}…")
                persistent_dir = pathlib.Path(__file__).parent / "processed_files"
                persistent_dir.mkdir(exist_ok=True)
                final_p = persistent_dir / final_name
                if final_p.exists():
                    final_p.unlink()
                shutil.move(str(compressed_p), final_p)

                yield nd("complete", "completed", 100, "Verarbeitung abgeschlossen!", final_path=str(final_p))
            except Exception as e:
                logging.exception("Error in processing stream")
                yield nd("error", "failed", 0, f"Ein Fehler ist aufgetreten: {e}")

    return Response(
        stream_with_context(gen()),
        mimetype="application/x-ndjson",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@admin_required
@storage_bp.route('/api/predigt_upload/ftp/upload', methods=['POST'])
def ftp_upload():
    data = request.get_json(silent=True) or {}
    local_path = data.get('local_path')
    remote_name = data.get('remote_name')  # optional override
    if not local_path:
        return jsonify({"status": "error", "message": "local_path fehlt"}), 400
    try:
        upload_success = upload_file_ftp(local_path, remote_name)
        refresh_success = refresh_website()
        if not upload_success:
            return jsonify({"status": "error", "message": "FTP upload failed"}), 500
        if not refresh_success:
            return jsonify({"status": "error", "message": "Website refresh failed"}), 500
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.exception("FTP upload failed")
        return jsonify({"status": "error", "message": str(e)}), 500