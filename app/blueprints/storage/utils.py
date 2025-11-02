import os
from app.blueprints.storage import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from app import db
from app.models.storage import File, Directory 

SONG_DATA_FOLDER = os.path.abspath(os.path.normpath(os.path.join(UPLOAD_FOLDER, 'song_data')))
os.makedirs(SONG_DATA_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def file_icon(filename):
    """Determine appropriate file icon based on extension"""
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    
    icons = {
        'json': 'fa-file-code',
        'pdf': 'fa-file-pdf',
        'doc': 'fa-file-word', 'docx': 'fa-file-word',
        'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel',
        'ppt': 'fa-file-powerpoint', 'pptx': 'fa-file-powerpoint',
        'jpg': 'fa-file-image', 'jpeg': 'fa-file-image', 'png': 'fa-file-image', 
        'gif': 'fa-file-image', 'bmp': 'fa-file-image',
        'mp3': 'fa-file-audio', 'wav': 'fa-file-audio',
        'mp4': 'fa-file-video', 'avi': 'fa-file-video', 'mov': 'fa-file-video',
        'zip': 'fa-file-archive', 'rar': 'fa-file-archive', 'tar': 'fa-file-archive',
        'txt': 'fa-file-alt',
        'html': 'fa-file-code', 'css': 'fa-file-code', 'js': 'fa-file-code',
        'py': 'fa-file-code', 'java': 'fa-file-code'
    }
    
    return icons.get(extension, 'fa-file')

def format_size(size_in_bytes):
    """Format file size in readable units"""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes/1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_in_bytes/(1024*1024*1024):.1f} GB"

import os
from app import db
from app.blueprints.storage import UPLOAD_FOLDER

# Add this constant at the top
SONG_DATA_FOLDER = os.path.abspath(os.path.normpath(os.path.join(UPLOAD_FOLDER, 'song_data')))

def delete_directory_recursive(directory):
    """Recursively delete a directory and all its contents"""
    from app.models.storage import Directory, File
    
    # Delete all files in this directory
    files = File.query.filter_by(directory_id=directory.id).all()
    for file in files:
        try:
            # Use SONG_DATA_FOLDER instead of UPLOAD_FOLDER
            file_path = os.path.join(SONG_DATA_FOLDER, file.path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except (OSError, FileNotFoundError):
            pass
        db.session.delete(file)
    
    # Recursively delete all subdirectories
    subdirectories = Directory.query.filter_by(parent_id=directory.id).all()
    for subdir in subdirectories:
        delete_directory_recursive(subdir)
    
    # Delete the directory itself
    db.session.delete(directory)
    db.session.commit()

def is_descendant(potential_descendant, potential_ancestor):
    """
    Checks if potential_descendant is a descendant of potential_ancestor.
    """
    if not potential_descendant.parent_id:
        return False # Root directory cannot be a descendant
    if potential_descendant.parent_id == potential_ancestor.id:
        return True
    
    parent = Directory.query.get(potential_descendant.parent_id)
    if parent:
        return is_descendant(parent, potential_ancestor)
    return False