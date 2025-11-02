from datetime import datetime
import uuid
from flask import jsonify, request, send_file, g
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.blueprints.ocr import ocr_bp, OCR_UPLOAD_FOLDER
from app.blueprints.ocr.functions.chord_utils import ChordUtils
from app.blueprints.ocr.functions.converter import finalize_song_data, merge_ocr_sections, parse_ocr_section_to_preliminary, parse_raw_text_to_preliminary, preliminary_to_structured, rebuild_plain_text
from app.utils.auth import approved_user_required, ocr_user_required
from app import db
from app.models.storage import Directory, File as StorageFile
from app.blueprints.storage import UPLOAD_FOLDER
import hashlib
import json
import os
import re
import cv2
from app.blueprints.ocr.utils import process_ocr_result, get_ocr_reader

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ocr_bp.route('/api/upload', methods=['POST'])
@approved_user_required
def upload_file():
    """Upload an image or PDF file for OCR processing"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    try:
        # Generate unique filename
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}.{file_ext}"
        
        file_path = os.path.join(OCR_UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        
        if file_size > MAX_FILE_SIZE:
            os.remove(file_path)
            return jsonify({'error': f'File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB'}), 400
        
        return jsonify({
            'success': True,
            'file_id': unique_id,
            'filename': file.filename,
            'size': file_size,
            'type': file_ext
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@ocr_bp.route('/api/process', methods=['POST'])
@approved_user_required
def process_ocr():
    """Process uploaded file with OCR"""
    data = request.get_json()
    
    if not data or 'file_id' not in data:
        return jsonify({'error': 'File ID is required'}), 400
    
    file_id = data['file_id']
    language = data.get('language', 'en')
    section_name = data.get('section_name', 'Section')
    song_key = data.get('song_key', 'C')
    
    options = {
        'preprocessing': data.get('preprocessing', {}),
        'output_format': data.get('output_format', 'text')
    }
    
    try:
        # Find the file
        file_path = None
        for file in os.listdir(OCR_UPLOAD_FOLDER):
            if file.startswith(file_id):
                file_path = os.path.join(OCR_UPLOAD_FOLDER, file)
                break
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Load image
        image = cv2.imread(file_path)
        if image is None:
            return jsonify({'error': 'Could not load image'}), 400
        
        # Apply preprocessing if specified
        preprocessing = options.get('preprocessing', {})
        if preprocessing.get('grayscale'):
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Get OCR reader (lazy loaded)
        ocr_reader = get_ocr_reader()
        
        # Perform OCR
        result = ocr_reader.predict(image)
        
        if result and len(result) > 0 and result[0]:
            ocr_data = result[0]
            processed_data = process_ocr_result(ocr_data, song_key, section_name)
            # DEBUGGING: Print structured data
            print(processed_data)
            # Extract plain text with proper chord positioning
            plain_text = ""
            for line in processed_data['lines']:
                if line['type'] == 'lyrics':
                    # Simple concatenation for lyrics
                    plain_text += " ".join([item['text'] for item in line['content']]) + "\n"
                    print(plain_text)
                elif line['type'] == 'chords':
                    # Position chords based on their position_x
                    chord_items = line['content']
                    
                    if chord_items:
                        # Find min and max positions for scaling
                        positions = [item['position_x'] for item in chord_items]
                        min_pos = min(positions)
                        max_pos = max(positions)
                        
                        # Calculate character positions (assume ~10 pixels per character)
                        avg_char_width = 10
                        
                        # Build the chord line with proper spacing
                        chord_line = ""
                        last_char_pos = 0
                        
                        for item in chord_items:
                            # Convert pixel position to character position
                            pixel_pos = item['position_x']
                            char_pos = int((pixel_pos - min_pos) / avg_char_width)
                            
                            # Calculate spaces needed
                            spaces_needed = max(1, char_pos - last_char_pos)
                            
                            chord_line += " " * spaces_needed + item['chord']
                            last_char_pos = char_pos + len(item['chord'])
                        
                        plain_text += chord_line + "\n"
                        print(plain_text)
            
            return jsonify({
                'success': True,
                'file_id': file_id,
                'text': plain_text.strip(),
                'structured_data': processed_data,
                'confidence': 0.95,
                'language': language,
                'page_count': 1
            }), 200
        else:
            return jsonify({
                'success': True,
                'file_id': file_id,
                'text': 'No text detected in image',
                'structured_data': {'section_name': section_name, 'lines': []},
                'confidence': 0.0,
                'language': language,
                'page_count': 1
            }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@ocr_bp.route('/api/languages', methods=['GET'])
@approved_user_required
def get_languages():
    """Get available OCR languages"""
    languages = [
        {'code': 'en', 'name': 'English'},
        {'code': 'de', 'name': 'German'},
    ]
    return jsonify({'languages': languages})

@ocr_bp.route('/api/file/<file_id>', methods=['DELETE'])
@approved_user_required
def delete_file(file_id):
    """Delete uploaded file"""
    try:
        for file in os.listdir(OCR_UPLOAD_FOLDER):
            if file.startswith(file_id):
                file_path = os.path.join(OCR_UPLOAD_FOLDER, file)
                os.remove(file_path)
                return jsonify({'success': True, 'message': 'File deleted'}), 200
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        return jsonify({'error': f'Deletion failed: {str(e)}'}), 500
    

@ocr_bp.route('/api/finalize-song', methods=['POST'])
@approved_user_required
def finalize_song():
    """
    Finalize all OCR sections into a complete song JSON.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    sections = data.get('sections', [])
    title = data.get('title', 'Untitled')
    key = data.get('key', 'C')
    authors = data.get('authors', [])
    
    if not sections:
        return jsonify({'error': 'No sections provided'}), 400
    
    try:
        # Convert OCR sections to preliminary format
        preliminary_sections = merge_ocr_sections(sections)
        
        # Finalize into song JSON
        final_song = finalize_song_data(
            preliminary_sections=preliminary_sections,
            title=title,
            key=key,
            authors=authors
        )
        
        return jsonify({
            'success': True,
            'song': final_song
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Finalization failed: {str(e)}'}), 500

@ocr_bp.route('/api/section/edit', methods=['POST'])
@approved_user_required
def edit_section():
    """
    Edit a section's OCR text and reparse it with proper Python logic.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    text = data.get('text', '')
    section_name = data.get('section_name', 'Section')
    key = data.get('key', 'C')
    
    if not text.strip():
        return jsonify({'error': 'Text cannot be empty'}), 400
    
    try:
        # Parse the raw text into preliminary format
        preliminary_sections = parse_raw_text_to_preliminary(text)
        
        # Take the first section (or create one if none found)
        if preliminary_sections:
            prelim_section = preliminary_sections[0]
            prelim_section.title = section_name  # Use the provided section name
        else:
            # Create a simple section with the text as lyrics
            from app.blueprints.ocr.functions.cData import PreliminaryLine, PreliminarySection
            prelim_section = PreliminarySection(
                title=section_name,
                lines=[PreliminaryLine(text=text, is_chord_line=False, certainty=0.5)]
            )
        
        # Convert back to OCR-like structured data
        structured_data = preliminary_to_structured(prelim_section, key)
        
        # Rebuild plain text representation
        plain_text = rebuild_plain_text(structured_data)
        
        return jsonify({
            'success': True,
            'structured_data': structured_data,
            'text': plain_text
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Edit parsing failed: {str(e)}'}), 500
    

@ocr_bp.route('/api/finalize-and-upload', methods=['POST'])
@approved_user_required
@ocr_user_required
def finalize_and_upload():
    """
    Finalize song and upload to ocr folder, registering it in the database.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    sections = data.get('sections', [])
    title = data.get('title', 'Untitled')
    key = data.get('key', 'C')
    authors = data.get('authors', [])
    
    if not sections:
        return jsonify({'error': 'No sections provided'}), 400
    
    try:
        # Convert sections to preliminary format
        preliminary_sections = []
        for section_data in sections:
            section_name = section_data.get('section_name', 'Section')
            structured_data = section_data.get('structured_data', {})
            
            prelim_section = parse_ocr_section_to_preliminary(section_name, structured_data)
            if prelim_section and prelim_section.lines:
                preliminary_sections.append(prelim_section)
        
        # Finalize the song
        song_dict = finalize_song_data(preliminary_sections, title, key, authors)
        
        # Ensure ocr directory exists in database (at root level)
        ocr_dir = Directory.query.filter_by(name='ocr', parent_id=None).first()
        if not ocr_dir:
            ocr_dir = Directory(
                name='ocr',
                user_id=current_user.id,
                parent_id=None,
                is_admin_only=False
            )
            db.session.add(ocr_dir)
            db.session.flush()  # Get the ID
        
        # Create safe filename
        safe_filename = secure_filename(title)
        if not safe_filename:
            safe_filename = 'untitled'
        
        # Ensure .json extension
        if not safe_filename.endswith('.json'):
            safe_filename += '.json'
        
        # Check for duplicate filename and add number if needed
        base_name = safe_filename[:-5]  # Remove .json
        counter = 1
        final_display_name = safe_filename
        
        while StorageFile.query.filter_by(name=final_display_name, directory_id=ocr_dir.id).first():
            final_display_name = f"{base_name}_{counter}.json"
            counter += 1
        
        # Generate unique filename for storage (like the storage upload does)
        import uuid
        _, extension = os.path.splitext(final_display_name)
        unique_filename = str(uuid.uuid4()) + extension
        
        # Physical file path - store directly in UPLOAD_FOLDER like other files
        physical_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save the JSON file
        with open(physical_path, 'w', encoding='utf-8') as f:
            json.dump(song_dict, f, ensure_ascii=False, indent=2)
        
        # Get file size
        file_size = os.path.getsize(physical_path)
        
        # Create database entry
        # Path is just the unique filename (not a subdirectory path)
        new_file = StorageFile(
            name=final_display_name,  # Display name (what user sees)
            path=unique_filename,      # Actual filename on disk
            size=file_size,
            user_id=current_user.id,
            directory_id=ocr_dir.id    # This puts it in the 'ocr' folder virtually
        )
        db.session.add(new_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Song successfully uploaded',
            'filename': final_display_name,
            'file_id': new_file.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Finalization failed: {str(e)}'}), 500