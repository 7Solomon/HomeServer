

import pathlib
import re
import asyncio

import logging
import shutil
import tempfile
from typing import AsyncGenerator

from flask import json
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.blueprints.storage import storage_bp
from app.utils.auth import admin_required
from app.workables.predigt_upload.audio import compress_audio
from app.workables.predigt_upload.youtube import get_last_livestream_data, download_youtube_audio_from_url
from app.workables.predigt_upload.ftp_handler import list_ftp_files

@storage_bp.route('/admin/list_predigt_upload/')
@admin_required
async def list_predigt_upload(limit: int = 10):
    """
    Returns last livestreams with title, date (YYYY-MM-DD), and whether a file with
    the same date exists on the FTP server.
    """
    try:
        # Get livestreams (now includes "date")
        livestreams = await asyncio.to_thread(list, get_last_livestream_data(limit))
        livestreams = livestreams or []

        # Get files from server and extract dates found in filenames
        files = await asyncio.to_thread(list_ftp_files)
        files = files or []

        date_rx = re.compile(r'(\d{4}-\d{2}-\d{2})')
        server_dates = set()
        for fname in files:
            m = date_rx.search(fname)
            if m:
                server_dates.add(m.group(1))

        items = []
        for v in livestreams:
            date_str = v.get("date")
            items.append({
                "id": v.get("id"),
                "title": v.get("title"),
                "date": date_str,
                "on_server": (date_str in server_dates) if date_str else False
            })

        return {
            "status": "success",
            "items": items
        }
    except Exception as e:
        logging.error(f"Error in /action: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    
class ProcessAudioRequest(BaseModel):
    id: str # Video ID
    prediger: str
    titel: str
    datum: dt.date

@storage_bp.route('/admin/streamline_predigt/')
async def process_audio_stream(req: ProcessAudioRequest):
    """
    Processes an audio stream from a YouTube URL.
    This endpoint streams progress updates for each step.
    """

    logging.info(f"Received processing request: {req}")
    logging.info(f"Video ID: {req.id}, Prediger: {req.prediger}, Titel: {req.titel}, Datum: {req.datum}")
    
    video_url = f"https://www.youtube.com/watch?v={req.id}"
    
    async def processing_generator() -> AsyncGenerator[str, None]:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # 1. Download
                yield json.dumps({"step": "download", "status": "in_progress", "progress": "05", "message": "Starte Download..."}) + "\n"
                downloaded_path = await asyncio.to_thread(download_youtube_audio_from_url, video_url, temp_dir)
                yield json.dumps({"step": "download", "status": "completed", "progress": "15", "message": "Download abgeschlossen."}) + "\n"

                # 2. Compress
                compressed_path = pathlib.Path(temp_dir) / "compressed.mp3"
                async for update in run_sync_generator(compress_audio(downloaded_path, str(compressed_path))):
                    update['step'] = 'compress'
                    update['progress'] = "60"
                    yield json.dumps(update) + "\n"

                # 3. Tag
                metadata = {
                    "title": req.titel,
                    "speaker": req.prediger,
                    "date": req.datum.strftime("%Y-%m-%d"),
                    "year": req.datum.strftime("%Y"),
                    "album": download.CONFIG.get("album_name", "Predigten aus Treffpunkt Leben Karlsruhe"),
                    "copyright": download.CONFIG.get("copyright_notice", "Treffpunkt Leben Karlsruhe - alle Rechte vorbehalten"),
                    "genre": "Predigt Online"
                }
                async for update in run_sync_generator(generate_id3_tags(str(compressed_path), metadata)):
                    update['step'] = 'tags'
                    update['progress'] = "80"
                    yield json.dumps(update) + "\n"

                # 4. Rename
                final_name = f"predigt-{req.datum.strftime('%Y-%m-%d')}_Treffpunkt_Leben_Karlsruhe.mp3"
                yield json.dumps({"step": "finalize", "status": "in_progress", "progress": "90", "message": f"Renaming file to {final_name}..."}) + "\n"
                final_path = await asyncio.to_thread(rename_file, str(compressed_path), final_name)

                # Move file to persistent location so it still exists for /server/upload
                persistent_dir = pathlib.Path(__file__).parent / "processed_files"
                persistent_dir.mkdir(exist_ok=True)
                persistent_final_path = persistent_dir / final_name
                await asyncio.to_thread(shutil.move, final_path, persistent_final_path)

                yield json.dumps({
                    "step": "complete",
                    "status": "completed",
                    "progress": "100",
                    "message": "Verarbeitung abgeschlossen!",
                    "final_path": str(persistent_final_path)  # return persistent path
                }) + "\n"
            except Exception as e:
                logging.error(f"Error in processing stream: {e}", exc_info=True)
                yield json.dumps({"step": "error", "status": "failed", "message": f"Ein Fehler ist aufgetreten: {e}"}) + "\n"
    return StreamingResponse(processing_generator(), media_type="application/x-ndjson")