import json
import os
from flask import jsonify, g, request, send_from_directory
from werkzeug.utils import secure_filename

from app import db
from app.models.storage import File
from app.utils.auth import admin_token, valid_token
from app.blueprints.storage import UPLOAD_FOLDER, storage_bp

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