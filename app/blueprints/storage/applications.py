from datetime import datetime
import json
import os
import requests
from app.blueprints.storage import UPLOAD_FOLDER, storage_bp

from app.utils.auth import admin_required, valid_token
from flask import jsonify, g, request, send_from_directory, render_template
from werkzeug.utils import secure_filename

APPLICATION_FOLDER = os.path.join(UPLOAD_FOLDER, 'applications')

def get_latest_github_release():
    """Fetch latest release from GitHub API"""
    try:
        response = requests.get(
            'https://api.github.com/repos/7Solomon/P2pChords/releases/latest',
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"GitHub API error: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitHub release: {e}")
        return None

def process_release_assets(release_data):
    """Process release assets and categorize by platform"""
    if not release_data or 'assets' not in release_data:
        return {}
    
    assets = release_data['assets']
    processed_assets = {
        'windows': None,
        'linux': None,
        'android': None
    }
    
    for asset in assets:
        name = asset['name'].lower()
        
        # Windows detection
        if ('windows' in name or name.endswith('.exe') or name.endswith('.msi')):
            processed_assets['windows'] = asset
        
        # Linux detection
        elif ('linux' in name or name.endswith('.appimage') or 
              name.endswith('.deb') or name.endswith('.rpm')):
            processed_assets['linux'] = asset
        
        # Android detection
        elif ('android' in name or name.endswith('.apk')):
            processed_assets['android'] = asset
    
    return processed_assets

@storage_bp.route('/admin/p2p_download/page')
@admin_required
def p2p_download():
    """Serves the P2P Downloader page with GitHub release data."""
    current_date = datetime.now().strftime('%d.%m.%Y')
    
    # Fetch latest release from GitHub
    release_data = get_latest_github_release()
    
    if release_data:
        # Process release data
        processed_assets = process_release_assets(release_data)
        
        # Format release date
        release_date = None
        if 'published_at' in release_data:
            try:
                release_datetime = datetime.fromisoformat(
                    release_data['published_at'].replace('Z', '+00:00')
                )
                release_date = release_datetime.strftime('%d.%m.%Y')
            except ValueError:
                release_date = None
        
        context = {
            'current_date': current_date,
            'release_data': {
                'tag_name': release_data.get('tag_name', 'Unbekannt'),
                'name': release_data.get('name', 'Neueste Version'),
                'published_at': release_date,
                'html_url': release_data.get('html_url', ''),
                'body': release_data.get('body', ''),
                'assets': processed_assets
            },
            'github_available': True
        }
    else:
        # Fallback if GitHub is not available
        context = {
            'current_date': current_date,
            'github_available': False,
            'release_data': None
        }
    
    return render_template('storage/p2p_download.html', **context)

@storage_bp.route('/admin/p2p_download/api/latest')
@admin_required
def p2p_download_api():
    """API endpoint to get latest release data"""
    release_data = get_latest_github_release()
    
    if release_data:
        processed_assets = process_release_assets(release_data)
        
        return jsonify({
            'success': True,
            'data': {
                'tag_name': release_data.get('tag_name'),
                'name': release_data.get('name'),
                'published_at': release_data.get('published_at'),
                'html_url': release_data.get('html_url'),
                'body': release_data.get('body'),
                'assets': processed_assets
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch latest release from GitHub'
        }), 500




@storage_bp.route('/admin/p2p_download/download_exe', methods=['GET'])
@admin_required
def download_exe():
    """Download the P2PChord downloader file"""
    directory_to_serve_from = os.path.abspath(APPLICATION_FOLDER)
    return send_from_directory(directory_to_serve_from, 'P2PChordsInstaller.exe', as_attachment=True)

@storage_bp.route('/admin/p2p_download/download_linux', methods=['GET'])
@admin_required
def download_linux():
    """Download the P2PChord downloader file"""
    directory_to_serve_from = os.path.abspath(APPLICATION_FOLDER)
    return send_from_directory(directory_to_serve_from, 'P2PChordsLinuxInstaller.exe', as_attachment=True)

@storage_bp.route('/admin/p2p_download/download_apk', methods=['GET'])
@admin_required
def download_apk():
    """Download the P2PChord APK"""
    directory_to_serve_from = os.path.abspath(APPLICATION_FOLDER)
    return send_from_directory(directory_to_serve_from, 'P2PChords.apk', as_attachment=True)