import math
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from mutagen.mp3 import MP3
from mutagen.id3 import TIT2, TPE1, TALB, TPE2, COMM, TDRC, TRCK, TCON, TCOP, TYER, TLEN

from app.workables.config.manager import get_config
from app.workables.predigt_upload.ffmpeg_setup import get_ffmpeg_path  
import ffmpeg

def compress_audio(file_name):
    config = get_config()

    try:
        ffmpeg_location = get_ffmpeg_path()
        print(f"FFmpeg location: {ffmpeg_location}")
    except FileNotFoundError as e:
        raise Exception(f"FFmpeg setup failed: {e}")

    threshold_db = config.get('threshold_db', -12) 
    ratio = config.get('ratio', 4)        
    attack = config.get('attack', 20)  
    release = config.get('release', 250)
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)

    try:
        ffmpeg_cmd = ffmpeg.input(file_name)
        
        # Use custom FFmpeg path if available - ADD THIS
        if ffmpeg_location:
            ffmpeg_executable = str(Path(ffmpeg_location) / 'ffmpeg.exe')
            (
                ffmpeg_cmd
                .output(temp_file.name, acodec='libmp3lame', audio_bitrate='128k',
                        af=f'acompressor=threshold={threshold_db}dB:ratio={ratio}:attack={attack}:release={release}')
                .overwrite_output()
                .run(cmd=ffmpeg_executable, capture_stdout=True, capture_stderr=True)
            )
        else:
            # Use system FFmpeg
            (
                ffmpeg_cmd
                .output(temp_file.name, acodec='libmp3lame', audio_bitrate='128k',
                        af=f'acompressor=threshold={threshold_db}dB:ratio={ratio}:attack={attack}:release={release}')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        
        # Rest of your existing code...
        original_temp_name = temp_file.name
        temp_file.close()
        os.replace(original_temp_name, file_name)
        return file_name

    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"FFmpeg Error: {error_msg}")
        # Cleanup and raise
        if os.path.exists(temp_file.name):
            try:
                temp_file.close()
                os.unlink(temp_file.name)
            except:
                pass
        raise Exception(f"FFmpeg error: {error_msg}")
    except Exception as e:
        print(f"Unexpected error in audio compression: {e}")
        if os.path.exists(temp_file.name):
            try:
                temp_file.close()
                os.unlink(temp_file.name)
            except:
                pass
        raise


def generate_id3_tags(file_path: str, metadata: Dict[str, str]) -> Generator[Dict[str, Any], None, None]:
    """Generates and applies ID3 tags to an MP3 file."""
    yield {
        "step": "Tagging",
        "status": "in_progress",
        "message": "Generating and applying ID3 tags..."
    }
    try:
        audio = MP3(file_path)
        
        audio['TIT2'] = TIT2(encoding=3, text=metadata.get("title", ""))
        audio['TPE1'] = TPE1(encoding=3, text=metadata.get("speaker", ""))
        audio['TDRC'] = TDRC(encoding=3, text=metadata.get("date", "")) # YYYY-MM-DD
        audio['TYER'] = TYER(encoding=3, text=metadata.get("year", ""))

        # Set static tags
        audio['TALB'] = TALB(encoding=3, text=metadata.get("album", "Predigten aus Treffpunkt Leben Karlsruhe"))
        audio['TCON'] = TCON(encoding=3, text=metadata.get("genre", "Predigt Online"))
        audio['TCOP'] = TCOP(encoding=3, text=metadata.get("copyright", "Treffpunkt Leben Karlsruhe - alle Rechte vorbehalten"))

        # Calculate and set duration
        duration_ms = int(audio.info.length * 1000)
        audio['TLEN'] = TLEN(encoding=3, text=str(duration_ms))
        
        audio.save()
        yield {
            "step": "Tagging",
            "status": "completed",
            "message": "ID3 tags applied successfully."
        }
    except Exception as e:
        logging.error(f"Error applying ID3 tags: {e}")
        yield {
            "step": "Tagging",
            "status": "failed",
            "message": f"Error applying ID3 tags: {e}"
        }
        raise