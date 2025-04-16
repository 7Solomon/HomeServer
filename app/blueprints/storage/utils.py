import os
from app.blueprints.storage import UPLOAD_FOLDER, ALLOWED_EXTENSIONS

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