import json
import os
from app.blueprints.storage import UPLOAD_FOLDER, storage_bp

from app.utils.auth import admin_required, valid_token
from flask import jsonify, g, request, send_from_directory, render_template
from werkzeug.utils import secure_filename

APPLICATION_FOLDER = os.path.join(UPLOAD_FOLDER, 'applications')

@storage_bp.route('/admin/p2p_download/page')
@admin_required
def p2p_download():
    """Serves the P2P Downloader page."""
    return render_template('storage/p2p_download.html')


@storage_bp.route('/admin/p2p_download/download_exe', methods=['GET'])
@admin_required
def download_exe():
    """Download the P2PChord downloader file"""
    directory_to_serve_from = os.path.abspath(APPLICATION_FOLDER)
    return send_from_directory(directory_to_serve_from, 'P2PChordsInstaller.exe', as_attachment=True)

@storage_bp.route('/admin/p2p_download/download_apk', methods=['GET'])
@admin_required
def download_apk():
    """Download the P2PChord APK"""
    directory_to_serve_from = os.path.abspath(APPLICATION_FOLDER)
    return send_from_directory(directory_to_serve_from, 'P2PChords.apk', as_attachment=True)
