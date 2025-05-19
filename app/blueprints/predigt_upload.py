#from datetime import datetime, timezone
#from urllib import request as urllib_request # Alias to avoid conflict with flask.request
#from app.models.predigt import Predigt
#from app.utils.auth import admin_token
#from flask import Blueprint, jsonify, request # Added flask.request
#from app.workables.predigt_upload.youtube import get_last_livestream_data, download_youtube_audio_from_url # Updated import
#from app.workables.predigt_upload.ftp_handler import list_ftp_files, upload_file_ftp # Added upload_file_ftp
#from app.workables.predigt_upload.audio import compress_audio # Added compress_audio
#import os # For checking file existence before compression
#from app import db
#
#predigt_upload_api_bp = Blueprint('predigt_upload', __name__)
#
#@admin_token
#@predigt_upload_api_bp.route('/api/predigt_upload/get_youtube_list/<int:max>', methods=['POST'])
#def get_youtube_videos(max):
#    result = get_last_livestream_data(max)
#    for entry in result:
#        predigt_entry = Predigt.query.filter_by(youtube_url=entry['URL']).first()
#        if not predigt_entry:
#            predigt_entry = Predigt(
#                title=entry['title'],
#                youtube_url=entry['URL'],
#                youtube_video_id=entry['id'],
#                status='streamed',
#            )
#            db.session.add(predigt_entry)
#    db.session.commit()
#    return jsonify({'message': 'Searched youtube', 'result': result}), 200
#
#@admin_token
#@predigt_upload_api_bp.route('/api/predigt_upload/download/<str:id>', methods=['POST'])
#def download_youtube_video(id):
#    entry = Predigt.query.filter_by(id=id).first()
#    try:
#        download_path = download_youtube_audio_from_url(entry.youtube_url) 
#        entry.local_file_path = download_path
#        entry.downloaded_at = datetime.now(timezone.utc)
#        entry.status = 'downloaded'
#        db.session.commit()
#        return jsonify({'message': 'Downloading video', 'path': download_path}), 200
#    except Exception as e:
#        entry.error_message = str(e)
#        entry.status = 'error'
#        return jsonify({'message': 'Error downloading video', 'error': str(e)}), 500
#
#@admin_token
#@predigt_upload_api_bp.route('/api/predigt_upload/get_server_list/<int:max>', methods=['POST'])
#def get_server_list(max):
#    result = list_ftp_files() 
#    return jsonify({'message': 'Searched server', 'result': result}), 200
#
#@admin_token
#@predigt_upload_api_bp.route('/api/predigt_upload/upload_file/<str:id>', methods=['POST'])
#def handle_upload_file():
#    entry = Predigt.query.filter_by(youtube_url=id['URL']).first()
#
#
#    if not entry.local_file_path or not entry.remote_file_name:
#        return jsonify({'message': 'Error: Missing local_file_path or remote_file_name in request'}), 400
#
#    if not os.path.exists(entry.local_file_path):
#        return jsonify({'message': f'Error: Local file not found: {entry.local_file_path}'}), 404
#
#    try:
#        #print(f"Compressing audio file: {local_file_path}")
#        compressed_file_path = compress_audio(entry.local_file_path)
#        entry.local_file_path = compressed_file_path
#        entry.is_compressed = True
#        entry.compressed_at = datetime.now(timezone.utc)
#        db.session.commit()
#        #print(f"Uploading {local_file_path} to {remote_subdir}/{remote_file_name if remote_subdir else remote_file_name}")
#        success = upload_file_ftp(entry.local_file_path, entry.remote_file_name, entry.remote_subdir)
#
#        if success:
#            return jsonify({'message': 'File uploaded successfully', 'remote_path': f"{entry.remote_subdir or '/'}/{entry.remote_file_name}"}), 200
#        else:
#            return jsonify({'message': 'Error uploading file to FTP server'}), 500
#    except Exception as e:
#        # Log the full error for debugging on the server
#        print(f"An error occurred during file upload process: {str(e)}")
#        return jsonify({'message': 'An internal error occurred', 'error': str(e)}), 500