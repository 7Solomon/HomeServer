import json
import os
from flask import jsonify, g, request, send_from_directory
from werkzeug.utils import secure_filename

from app import db
# Make sure to import File and Directory models
from app.models.storage import File, Directory
from app.models.user import User # Add User import
from app.blueprints.storage.utils import delete_directory_recursive, is_descendant # Import helpers

# Use a consistent auth decorator, e.g., approved_user_required assumes it sets g.current_user
from app.utils.auth import admin_token, valid_token, approved_user_required
from app.blueprints.storage import UPLOAD_FOLDER, storage_bp
# Import utility if needed
# from .utils import allowed_file

# Define the song data folder
SONG_DATA_FOLDER = os.path.join(UPLOAD_FOLDER, 'song_data')
os.makedirs(SONG_DATA_FOLDER, exist_ok=True)

def is_valid_json_file(filename):
    """Check if file is a JSON file"""
    return filename.lower().endswith('.json')

@storage_bp.route('/api/song_data', methods=['GET'])
@valid_token
def list_song_data():
    """List all JSON files in the song_data folder with their properties"""
    if not os.path.exists(SONG_DATA_FOLDER):
        return jsonify({'files': []})
    
    files = []
    for filename in os.listdir(SONG_DATA_FOLDER):
        if not is_valid_json_file(filename):
            continue
            
        file_path = os.path.join(SONG_DATA_FOLDER, filename)
        if os.path.isfile(file_path):
            try:
                # Read the JSON file and extract its properties
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_content = json.load(f)

                    header = json_content.get('header', {})
                    name = header.get('name', 'Unknown')
                    authors = header.get('authors', [])


                # Add basic file info
                file_info = {
                    'filename': filename,
                    'name':name,
                    'authors':authors,
                }
                files.append(file_info)
            except json.JSONDecodeError:
                continue
    
    return jsonify({'files': files})

@storage_bp.route('/api/song_data/<filename>', methods=['GET'])
@valid_token
def download_song_data(filename):
    """Download a JSON file from the song_data folder"""
    if not is_valid_json_file(filename):
        return jsonify({'error': 'Only JSON files are allowed'}), 400
        
    return send_from_directory(SONG_DATA_FOLDER, filename, as_attachment=True)

@storage_bp.route('/api/song_data', methods=['POST'])
@admin_token
def upload_song_data():
    """Upload a JSON file to the song_data folder - requires admin token"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not is_valid_json_file(file.filename):
        return jsonify({'error': 'Only JSON files are allowed'}), 400
    
    try:
        # Validate JSON content
        json_data = json.load(file)
        # Reset file pointer after reading
        file.seek(0)
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(SONG_DATA_FOLDER, filename)
        file.save(file_path)
        
        return jsonify({
            'success': True,
            'message': 'JSON file uploaded successfully',
            'file': {
                'name': filename,
                'size': os.path.getsize(file_path),
                'properties': json_data
            }
        })
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 400

@storage_bp.route('/api/song_data/<filename>', methods=['DELETE'])
@admin_token
def delete_song_data(filename):
    """Delete a JSON file from the song_data folder - requires admin token"""
    if not is_valid_json_file(filename):
        return jsonify({'error': 'Only JSON files are allowed'}), 400
        
    file_path = os.path.join(SONG_DATA_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        os.remove(file_path)
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- API ENDPOINTS FOR STANDARD FILE/FOLDER OPERATIONS (Called by storage.js) ---

@storage_bp.route('/api/upload', methods=['POST'])
@approved_user_required # Requires an approved user token, sets g.current_user
def api_upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    directory_id_str = request.form.get('directory_id')
    directory_id = int(directory_id_str) if directory_id_str and directory_id_str.isdigit() else None

    # Validate directory exists and belongs to user
    if directory_id:
        target_dir = Directory.query.filter_by(id=directory_id, user_id=g.current_user.id).first()
        if not target_dir:
            return jsonify({'error': 'Target directory not found or permission denied'}), 404
    else:
        # Uploading to root for the current user
        pass

    filename = secure_filename(file.filename)
    # Consider adding logic to prevent overwrites or create unique names
    save_path = os.path.join(UPLOAD_FOLDER, filename) # Simplistic path, might need subfolders per user/dir
    try:
        file.save(save_path)
        file_size = os.path.getsize(save_path)

        new_file = File(
            name=filename,
            path=filename,  # Store relative path from UPLOAD_FOLDER
            size=file_size,
            user_id=g.current_user.id,
            directory_id=directory_id
        )
        db.session.add(new_file)
        db.session.commit()

        return jsonify({'message': 'File uploaded successfully', 'file_id': new_file.id}), 201
    except Exception as e:
        db.session.rollback()
        # Clean up the saved file if DB operation failed
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except OSError:
                pass # Log this error
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

@storage_bp.route('/api/directory/create', methods=['POST'])
@approved_user_required # Requires an approved user token, sets g.current_user
def api_create_directory():
    # Assuming form data based on storage.js modal
    name = request.form.get('name')
    parent_id_str = request.form.get('parent_id')
    parent_id = int(parent_id_str) if parent_id_str and parent_id_str.isdigit() else None

    if not name:
        return jsonify({'error': 'Directory name is required'}), 400

    # Validate parent directory exists and belongs to user
    if parent_id:
        parent_dir = Directory.query.filter_by(id=parent_id, user_id=g.current_user.id).first()
        if not parent_dir:
            return jsonify({'error': 'Parent directory not found or permission denied'}), 404
    else:
        # Creating in root for the current user
        pass

    # Check for existing directory with the same name in the same parent
    existing_dir = Directory.query.filter_by(name=name, parent_id=parent_id, user_id=g.current_user.id).first()
    if existing_dir:
        return jsonify({'error': 'A directory with this name already exists here.'}), 409 # Conflict

    try:
        new_dir = Directory(
            name=name,
            user_id=g.current_user.id, # Assumes decorator sets g.current_user
            parent_id=parent_id
        )
        db.session.add(new_dir)
        db.session.commit()
        return jsonify({'message': 'Directory created successfully', 'directory_id': new_dir.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create directory: {str(e)}'}), 500

@storage_bp.route('/api/directories/list', methods=['GET'])
@approved_user_required # Or @valid_token if any valid token can list dirs?
def api_list_directories():
    exclude_id_str = request.args.get('exclude')
    exclude_id = int(exclude_id_str) if exclude_id_str and exclude_id_str.isdigit() else None

    # Fetch directories belonging to the current user
    query = Directory.query.filter_by(user_id=g.current_user.id)

    if exclude_id:
        # Exclude the directory itself and its descendants to prevent moving into itself
        excluded_dir = Directory.query.get(exclude_id)
        if excluded_dir:
            excluded_ids = [excluded_dir.id]
            # Simple recursive check (can be optimized with CTEs for large hierarchies)
            children = Directory.query.filter(Directory.parent_id == excluded_dir.id).all()
            queue = children
            while queue:
                child = queue.pop(0)
                excluded_ids.append(child.id)
                queue.extend(Directory.query.filter(Directory.parent_id == child.id).all())
            query = query.filter(Directory.id.notin_(excluded_ids))

    directories = query.order_by(Directory.name).all()

    # Format the output (adjust path generation as needed)
    dir_list = []
    for d in directories:
        # Generate a simple path representation
        path_parts = [d.name]
        parent = d.parent
        while parent:
            path_parts.insert(0, parent.name)
            parent = parent.parent
        dir_list.append({'id': d.id, 'path': ' / '.join(path_parts)})

    return jsonify({'directories': dir_list})

# --- ADMIN API ENDPOINTS (Called by storage.js) ---

@storage_bp.route('/api/admin/delete/file/<int:file_id>', methods=['POST']) # JS uses POST, RESTfully should be DELETE
@admin_token # Requires admin token
def api_admin_delete_file(file_id):
     file = File.query.get_or_404(file_id)
     try:
         # Attempt to delete physical file - adjust path logic if needed
         file_path = os.path.join(UPLOAD_FOLDER, file.path)
         if os.path.exists(file_path):
             os.remove(file_path)
     except OSError as e:
         # Log error, maybe file was already gone or permissions issue
         print(f"Error deleting physical file {file.path}: {e}")
         # Decide if this should prevent DB deletion - maybe not?

     db.session.delete(file)
     db.session.commit()
     return jsonify({'message': 'File deleted successfully by admin'}), 200

@storage_bp.route('/api/admin/delete/directory/<int:dir_id>', methods=['POST']) # JS uses POST, RESTfully should be DELETE
@admin_token # Requires admin token
def api_admin_delete_directory(dir_id):
    directory = Directory.query.get_or_404(dir_id)
    try:
        # Use the recursive helper (ensure it's imported or defined here)
        delete_directory_recursive(directory) # This handles physical files and DB records
        # delete_directory_recursive already commits
        return jsonify({'message': 'Directory and contents deleted successfully by admin'}), 200
    except Exception as e:
        db.session.rollback() # Rollback in case of error during deletion
        return jsonify({'error': f'Failed to delete directory: {str(e)}'}), 500

@storage_bp.route('/api/admin/move/file/<int:file_id>', methods=['POST'])
@admin_token # Requires admin token
def api_admin_move_file(file_id):
    file = File.query.get_or_404(file_id)
    target_dir_id_str = request.form.get('directory_id') # Matches JS form data

    target_dir_id = None
    if target_dir_id_str and target_dir_id_str.lower() != 'root':
        target_dir_id = int(target_dir_id_str) if target_dir_id_str.isdigit() else None
        if target_dir_id:
            # Validate target directory exists (admin can move anywhere)
            target_dir = Directory.query.get(target_dir_id)
            if not target_dir:
                return jsonify({'error': 'Target directory not found'}), 404
        else:
             return jsonify({'error': 'Invalid target directory ID'}), 400

    # Update file's directory_id (None for root)
    file.directory_id = target_dir_id
    # Note: This doesn't move the physical file on disk, only the DB association.
    # Physical move logic would be needed if paths depend on directory structure.
    db.session.commit()
    return jsonify({'message': 'File moved successfully by admin'}), 200

@storage_bp.route('/api/admin/move/directory/<int:dir_id>', methods=['POST'])
@admin_token # Requires admin token
def api_admin_move_directory(dir_id):
    directory = Directory.query.get_or_404(dir_id)
    target_dir_id_str = request.form.get('parent_id') # Matches JS form data

    target_dir_id = None
    if target_dir_id_str and target_dir_id_str.lower() != 'root':
        target_dir_id = int(target_dir_id_str) if target_dir_id_str.isdigit() else None
        if target_dir_id:
            # Validate target directory exists
            target_dir = Directory.query.get(target_dir_id)
            if not target_dir:
                return jsonify({'error': 'Target directory not found'}), 404
            # Prevent moving a directory into itself or its descendants
            if is_descendant(target_dir, directory): # Use helper (ensure imported/defined)
                 return jsonify({'error': 'Cannot move a directory into itself or a subdirectory.'}), 400
        else:
            return jsonify({'error': 'Invalid target directory ID'}), 400

    # Update directory's parent_id (None for root)
    directory.parent_id = target_dir_id
    db.session.commit()
    return jsonify({'message': 'Directory moved successfully by admin'}), 200

@storage_bp.route('/api/admin/change-owner/<string:type>/<int:item_id>', methods=['POST'])
@admin_token
def api_admin_change_owner(type, item_id):
    user_id_str = request.form.get('user_id')
    if not user_id_str or not user_id_str.isdigit():
        return jsonify({'error': 'Valid User ID is required'}), 400

    user_id = int(user_id_str)
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Target user not found'}), 404

    item = None
    if type == 'file':
        item = File.query.get_or_404(item_id)
    elif type == 'directory':
        item = Directory.query.get_or_404(item_id)
        # Optionally: Recursively change owner of contents?
        # Currently only changes the owner of the directory itself.
    else:
        return jsonify({'error': 'Invalid item type'}), 400

    item.user_id = user.id
    db.session.commit()
    return jsonify({'message': f'{type.capitalize()} ownership changed to {user.username}'}), 200