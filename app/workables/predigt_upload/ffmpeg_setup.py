import os
import requests
import zipfile
import shutil
import json
from pathlib import Path
import logging

def get_ffmpeg_path():
    """Get the path to bundled FFmpeg or system FFmpeg."""
    project_root = Path(__file__).parent.parent.parent.parent  # Go to project root
    bundled_ffmpeg = project_root / 'instance' / 'ffmpeg' / 'ffmpeg.exe'
    bundled_ffprobe = project_root / 'instance' / 'ffmpeg' / 'ffprobe.exe'
    
    # Check if bundled FFmpeg exists
    if bundled_ffmpeg.exists() and bundled_ffprobe.exists():
        return str(project_root / 'instance' / 'ffmpeg')
    
    # Check if system FFmpeg exists
    if shutil.which('ffmpeg') and shutil.which('ffprobe'):
        return None  # Use system PATH
    
    # FFmpeg not found - try to download it automatically
    logging.info("FFmpeg not found. Attempting to download...")
    try:
        download_ffmpeg()
        
        # Check again after download
        if bundled_ffmpeg.exists() and bundled_ffprobe.exists():
            return str(project_root / 'instance' / 'ffmpeg')
    except Exception as e:
        logging.error(f"Failed to auto-download FFmpeg: {e}")
    
    raise FileNotFoundError(
        "FFmpeg not found. Please install FFmpeg or place ffmpeg.exe and ffprobe.exe in the instance/ffmpeg/ directory."
    )

def download_ffmpeg():
    """Download and extract FFmpeg for Windows."""
    project_root = Path(__file__).parent.parent.parent.parent
    ffmpeg_dir = project_root / 'instance' / 'ffmpeg'
    
    # Check if FFmpeg already exists
    if ffmpeg_dir.exists() and (ffmpeg_dir / 'ffmpeg.exe').exists():
        print("FFmpeg already exists.")
        return
    
    try:
        # Use stable GitHub release
        download_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        print(f"Downloading FFmpeg from: {download_url}")
        
        response = requests.get(download_url, stream=True, allow_redirects=True, timeout=30)
        response.raise_for_status()
        
        zip_path = project_root / 'instance' / 'ffmpeg_download.zip'
        
        # Create instance directory if it doesn't exist
        (project_root / 'instance').mkdir(exist_ok=True)
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print("Extracting FFmpeg...")
        
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(project_root / 'instance' / 'ffmpeg_temp')
        
        # Find and move executables
        ffmpeg_dir.mkdir(exist_ok=True)
        temp_dir = project_root / 'instance' / 'ffmpeg_temp'
        
        # Look for ffmpeg.exe and ffprobe.exe in extracted folders
        executables_found = False
        for root, dirs, files in os.walk(temp_dir):
            ffmpeg_path = None
            ffprobe_path = None
            
            for file in files:
                if file == 'ffmpeg.exe':
                    ffmpeg_path = Path(root) / file
                elif file == 'ffprobe.exe':
                    ffprobe_path = Path(root) / file
            
            # If we found both, copy them
            if ffmpeg_path and ffprobe_path:
                shutil.copy2(ffmpeg_path, ffmpeg_dir)
                shutil.copy2(ffprobe_path, ffmpeg_dir)
                print(f"Found and copied FFmpeg executables from: {root}")
                executables_found = True
                break
        
        if not executables_found:
            raise Exception("Could not find ffmpeg.exe and ffprobe.exe in the downloaded archive")
        
        # Cleanup
        shutil.rmtree(temp_dir)
        zip_path.unlink()
        
        print("FFmpeg setup complete!")
        
    except Exception as e:
        print(f"Error setting up FFmpeg: {e}")
        # Cleanup on failure
        try:
            if (project_root / 'instance' / 'ffmpeg_download.zip').exists():
                (project_root / 'instance' / 'ffmpeg_download.zip').unlink()
            if (project_root / 'instance' / 'ffmpeg_temp').exists():
                shutil.rmtree(project_root / 'instance' / 'ffmpeg_temp')
        except:
            pass
        raise

if __name__ == "__main__":
    download_ffmpeg()