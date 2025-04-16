from flask import Blueprint, request, jsonify, g, send_from_directory, render_template
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from app import db
from app.models.storage import File, Directory
from app.utils.auth import token_required
import os
import time

# Define the upload folder and allowed file types
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create blueprint
storage_bp = Blueprint('storage', __name__)

@storage_bp.route('/api/files')
@token_required
def api_list_files():
    """API endpoint to list files for the authenticated user"""
    user = g.current_user
    
    # Get root files
    root_files = File.query.filter_by(user_id=user.id, directory_id=None).all()
    
    # Format file data
    files_data = [{
        'id': file.id,
        'name': file.name,
        'size': file.size,
        'created_at': file.created_at.isoformat()
    } for file in root_files]
    
    return jsonify({'files': files_data})

@storage_bp.route('/api/upload', methods=['POST'])
@token_required
def api_upload_file():
    """API endpoint to upload files"""
    user = g.current_user
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    directory_id = request.form.get('directory_id')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Create a unique filename using timestamp
        unique_filename = f"{user.id}_{int(time.time())}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Store file information in database
        new_file = File(
            name=filename,
            path=unique_filename,
            size=os.path.getsize(file_path),
            user_id=user.id,
            directory_id=directory_id
        )
        db.session.add(new_file)
        db.session.commit()
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file': {
                'id': new_file.id,
                'name': new_file.name,
                'size': new_file.size
            }
        })
    
    return jsonify({'error': 'File type not allowed'}), 400

@storage_bp.route('/api/download/<int:file_id>')
@token_required
def api_download_file(file_id):
    """API endpoint to download files"""
    user = g.current_user
    file = File.query.get_or_404(file_id)
    
    # Check if user has permission
    if file.user_id != user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    return send_from_directory(UPLOAD_FOLDER, file.path, as_attachment=True, download_name=file.name)

# Template-Hilfsfunktionen
def file_icon(filename):
    """Bestimmt das passende Dateisymbol basierend auf Dateiendung"""
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    
    icons = {
        'json': 'fa-file-code',
        #'pdf': 'fa-file-pdf',
        #'doc': 'fa-file-word', 'docx': 'fa-file-word',
        #'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel',
        #'ppt': 'fa-file-powerpoint', 'pptx': 'fa-file-powerpoint',
        #'jpg': 'fa-file-image', 'jpeg': 'fa-file-image', 'png': 'fa-file-image', 
        #'gif': 'fa-file-image', 'bmp': 'fa-file-image',
        #'mp3': 'fa-file-audio', 'wav': 'fa-file-audio',
        #'mp4': 'fa-file-video', 'avi': 'fa-file-video', 'mov': 'fa-file-video',
        #'zip': 'fa-file-archive', 'rar': 'fa-file-archive', 'tar': 'fa-file-archive',
        #'txt': 'fa-file-alt',
        #'html': 'fa-file-code', 'css': 'fa-file-code', 'js': 'fa-file-code',
        #'py': 'fa-file-code', 'java': 'fa-file-code'
    }
    
    return icons.get(extension, 'fa-file')

def format_size(size_in_bytes):
    """Formatiert die Dateigröße in lesbare Einheiten"""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes/1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_in_bytes/(1024*1024*1024):.1f} GB"

# Web-Interface-Routen
@storage_bp.route('/files')
@login_required
def files():
    """Zeigt die Root-Dateien und -Ordner des Benutzers an"""
    directories = Directory.query.filter_by(user_id=current_user.id, parent_id=None).all()
    files = File.query.filter_by(user_id=current_user.id, directory_id=None).all()
    
    return render_template(
        'storage/files.html', 
        files=files, 
        directories=directories,
        path=[],
        current_dir=None,
        parent_dir=None,
        file_icon=file_icon,
        format_size=format_size
    )

@storage_bp.route('/directory/<int:dir_id>')
@login_required
def directory(dir_id):
    """Zeigt Dateien und Ordner innerhalb eines bestimmten Verzeichnisses an"""
    current_dir = Directory.query.filter_by(id=dir_id, user_id=current_user.id).first_or_404()
    
    # Verzeichnispfad berechnen
    path = []
    parent = current_dir
    while parent:
        path.insert(0, parent)
        parent = parent.parent
    
    # Unterverzeichnisse und Dateien abrufen
    directories = Directory.query.filter_by(user_id=current_user.id, parent_id=dir_id).all()
    files = File.query.filter_by(user_id=current_user.id, directory_id=dir_id).all()
    
    return render_template(
        'storage/files.html', 
        files=files, 
        directories=directories,
        path=path[:-1],  # Aktuelles Verzeichnis nicht im Pfad anzeigen
        current_dir=current_dir,
        parent_dir=current_dir.parent,
        file_icon=file_icon,
        format_size=format_size
    )

@storage_bp.route('/download/<int:file_id>')
@login_required
def download(file_id):
    """Web-Route zum Herunterladen von Dateien"""
    file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
    return send_from_directory(UPLOAD_FOLDER, file.path, as_attachment=True, download_name=file.name)

# Zusätzliche API-Routen für Verzeichnisverwaltung
@storage_bp.route('/api/directories', methods=['POST'])
@token_required
def api_create_directory():
    """API-Endpunkt zum Erstellen eines neuen Verzeichnisses"""
    user = g.current_user
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Verzeichnisname fehlt'}), 400
    
    parent_id = data.get('parent_id')
    
    # Überprüfen, ob das übergeordnete Verzeichnis existiert und dem Benutzer gehört
    if parent_id:
        parent_dir = Directory.query.filter_by(id=parent_id, user_id=user.id).first()
        if not parent_dir:
            return jsonify({'error': 'Übergeordnetes Verzeichnis nicht gefunden'}), 404
    
    # Verzeichnis erstellen
    directory = Directory(
        name=data['name'],
        user_id=user.id,
        parent_id=parent_id
    )
    
    db.session.add(directory)
    db.session.commit()
    
    return jsonify({
        'message': 'Verzeichnis erfolgreich erstellt',
        'directory': {
            'id': directory.id,
            'name': directory.name,
            'parent_id': directory.parent_id
        }
    }), 201

@storage_bp.route('/api/directories/<int:dir_id>', methods=['PATCH'])
@token_required
def api_update_directory(dir_id):
    """API-Endpunkt zum Aktualisieren eines Verzeichnisses"""
    user = g.current_user
    directory = Directory.query.filter_by(id=dir_id, user_id=user.id).first_or_404()
    
    data = request.get_json()
    
    if 'name' in data:
        directory.name = data['name']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Verzeichnis erfolgreich aktualisiert',
        'directory': {
            'id': directory.id,
            'name': directory.name
        }
    })

@storage_bp.route('/api/directories/<int:dir_id>', methods=['DELETE'])
@token_required
def api_delete_directory(dir_id):
    """API-Endpunkt zum Löschen eines Verzeichnisses"""
    user = g.current_user
    directory = Directory.query.filter_by(id=dir_id, user_id=user.id).first_or_404()
    
    # Zuerst müssen wir alle Unterverzeichnisse und -dateien löschen (rekursiv)
    def delete_directory_recursive(dir_id):
        # Unterverzeichnisse löschen
        subdirs = Directory.query.filter_by(parent_id=dir_id).all()
        for subdir in subdirs:
            delete_directory_recursive(subdir.id)
        
        # Dateien in diesem Verzeichnis löschen
        files = File.query.filter_by(directory_id=dir_id).all()
        for file in files:
            # Physische Datei löschen
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, file.path))
            except (OSError, FileNotFoundError):
                pass  # Ignoriere Fehler, wenn die Datei nicht existiert
            db.session.delete(file)
        
        # Verzeichniseintrag löschen
        dir_obj = Directory.query.get(dir_id)
        if dir_obj:
            db.session.delete(dir_obj)
    
    delete_directory_recursive(dir_id)
    db.session.commit()
    
    return jsonify({
        'message': 'Verzeichnis und alle Inhalte erfolgreich gelöscht'
    })

@storage_bp.route('/api/files/<int:file_id>', methods=['PATCH'])
@token_required
def api_update_file(file_id):
    """API-Endpunkt zum Aktualisieren einer Datei (z.B. Umbenennen)"""
    user = g.current_user
    file = File.query.filter_by(id=file_id, user_id=user.id).first_or_404()
    
    data = request.get_json()
    
    if 'name' in data:
        file.name = data['name']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Datei erfolgreich aktualisiert',
        'file': {
            'id': file.id,
            'name': file.name
        }
    })

@storage_bp.route('/api/files/<int:file_id>', methods=['DELETE'])
@token_required
def api_delete_file(file_id):
    """API-Endpunkt zum Löschen einer Datei"""
    user = g.current_user
    file = File.query.filter_by(id=file_id, user_id=user.id).first_or_404()
    
    # Physische Datei löschen
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, file.path))
    except (OSError, FileNotFoundError):
        pass  # Ignoriere Fehler, wenn die Datei nicht existiert
    
    # Datenbankeintrag löschen
    db.session.delete(file)
    db.session.commit()
    
    return jsonify({
        'message': 'Datei erfolgreich gelöscht'
    })