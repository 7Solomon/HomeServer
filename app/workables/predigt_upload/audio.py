import math
import os
import tempfile
from app.workables.config.manager import get_config
import ffmpeg


def compress_audio(file_name):
    config = get_config() # Load the configuration

    # Get data from config, providing defaults if keys are missing
    threshold_db = config.get('predigt_upload_audio_compression', {}).get('threshold_db', -12) 
    ratio = config.get('predigt_upload_audio_compression', {}).get('ratio', 4)        
    attack = config.get('predigt_upload_audio_compression', {}).get('attack', 20)  
    release = config.get('predigt_upload_audio_compression', {}).get('release', 250)

    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
    
    # Convert threshold_db dB to amplitude ratio if it's a number
    threshold_amplitude = 0.25 # Default amplitude if conversion fails
    if isinstance(threshold_db, (int, float)):
        try:
            threshold_amplitude = math.pow(10, threshold_db / 20)
        except OverflowError:
            print(f"Warning: OverflowError converting threshold_db ({threshold_db}) to amplitude. Using default.")
    else:
        print(f"Warning: threshold_db ({threshold_db}) is not a number. Using default amplitude.")


    try:
        result = (
            ffmpeg
            .input(file_name)
            .audio
            .filter('acompressor', threshold=threshold_amplitude, ratio=ratio, attack=attack, release=release)
            .output(temp_file.name, acodec='libmp3lame', q=0) # Using -q:a 0 for VBR best quality with libmp3lame
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        # ffmpeg output is often on stderr, even for success
        if result[1]: # Check if there's any stderr output
            print("FFmpeg stderr:", result[1].decode())
        
        # It's safer to close the temp file before trying to replace the original
        original_temp_name = temp_file.name
        temp_file.close() 

        # Replace original file with compressed file
        os.replace(original_temp_name, file_name) # Replaces the original file_name with temp_file.name
        
        return file_name # Return the original file name, now pointing to the compressed version

    except ffmpeg.Error as e:
        print("FFmpeg execution error:", e.stderr.decode() if e.stderr else "No stderr")
        # Clean up temp file if it still exists and ffmpeg failed
        if os.path.exists(temp_file.name):
            try:
                temp_file.close() # Ensure it's closed before unlinking
                os.unlink(temp_file.name)
            except Exception as cleanup_e:
                print(f"Error cleaning up temp file {temp_file.name}: {cleanup_e}")
        # Do not delete the original input file if compression failed
        raise
    except Exception as e:
        print(f"An unexpected error occurred during compression: {e}")
        if os.path.exists(temp_file.name):
            try:
                temp_file.close()
                os.unlink(temp_file.name)
            except Exception as cleanup_e:
                print(f"Error cleaning up temp file {temp_file.name} on general error: {cleanup_e}")
        raise