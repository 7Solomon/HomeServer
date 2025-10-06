import cv2
import numpy as np
from PIL import Image
from app.blueprints.ocr.functions.chord_utils import ChordUtils

# Lazy load PaddleOCR
_ocr_reader = None

def get_ocr_reader():
    """Lazy initialize OCR reader"""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_reader = PaddleOCR(use_angle_cls=True, lang='en')
        except ImportError as e:
            raise ImportError(
                "PaddleOCR dependencies not installed. "
                "Install with: pip install paddlepaddle paddleocr"
            ) from e
    return _ocr_reader

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff', 'bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_chord(text):
    """Check if the text is likely a chord using ChordUtils."""
    text = text.strip().replace('?', '').replace('_', '')
    return ChordUtils.is_potential_chord_token(text)

def convert_chord_to_nashville(chord, key):
    """Convert a chord to Nashville using ChordUtils."""
    chord = chord.replace('?', '').replace('_', '').strip()
    return ChordUtils.chord_to_nashville(chord, key)

def extract_ocr_data(ocr_result):
    """
    Extract data from OCRResult object.
    PaddleX OCRResult has: rec_texts, rec_scores, dt_polys (or rec_polys)
    """
    extracted_data = []
    
    # Try accessing as dict directly (the correct way for PaddleX)
    try:
        if hasattr(ocr_result, 'keys'):
            # PaddleX uses rec_texts (plural) and rec_scores (plural)
            if 'rec_texts' in ocr_result and 'dt_polys' in ocr_result:
                texts = ocr_result['rec_texts']
                boxes = ocr_result['dt_polys']
                scores = ocr_result.get('rec_scores', [0.9] * len(texts))
                
                print(f"Found {len(texts)} texts, {len(boxes)} boxes, {len(scores)} scores")
                
                for i in range(len(texts)):
                    if i < len(boxes) and texts[i]:  # Skip None or empty texts
                        box = boxes[i]
                        text = texts[i]
                        score = scores[i] if i < len(scores) else 0.9
                        
                        # Convert box to [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] format
                        if box is not None and len(box) >= 4:
                            # Box might already be in correct format or numpy array
                            if isinstance(box[0], (list, tuple)) and len(box[0]) == 2:
                                bbox = [[float(box[j][0]), float(box[j][1])] for j in range(4)]
                            # Handle numpy array
                            elif hasattr(box[0], '__len__') and len(box[0]) == 2:
                                bbox = [[float(box[j][0]), float(box[j][1])] for j in range(4)]
                            # Or flat array [x1,y1,x2,y2,x3,y3,x4,y4]
                            elif len(box) == 8:
                                bbox = [[float(box[j*2]), float(box[j*2+1])] for j in range(4)]
                            # Or [x_min, y_min, x_max, y_max]
                            elif len(box) == 4 and not hasattr(box[0], '__len__'):
                                x_min, y_min, x_max, y_max = box
                                bbox = [[float(x_min), float(y_min)], [float(x_max), float(y_min)], 
                                        [float(x_max), float(y_max)], [float(x_min), float(y_max)]]
                            else:
                                print(f"Unexpected box format at index {i}: {box}")
                                continue
                            
                            extracted_data.append([bbox, (text, float(score))])
                
                if extracted_data:
                    print(f"Successfully extracted {len(extracted_data)} items")
                    return extracted_data
            
            # Try alternative field names with rec_polys
            elif 'rec_texts' in ocr_result and 'rec_polys' in ocr_result:
                texts = ocr_result['rec_texts']
                boxes = ocr_result['rec_polys']
                scores = ocr_result.get('rec_scores', [0.9] * len(texts))
                
                print(f"Found {len(texts)} texts (using rec_polys)")
                
                for i in range(len(texts)):
                    if i < len(boxes) and texts[i]:
                        box = boxes[i]
                        text = texts[i]
                        score = scores[i] if i < len(scores) else 0.9
                        
                        if box is not None and len(box) >= 4:
                            if hasattr(box[0], '__len__') and len(box[0]) == 2:
                                bbox = [[float(box[j][0]), float(box[j][1])] for j in range(4)]
                            else:
                                print(f"Box format at index {i}: {box}")
                                continue
                            
                            extracted_data.append([bbox, (text, float(score))])
                
                if extracted_data:
                    print(f"Successfully extracted {len(extracted_data)} items from rec_polys")
                    return extracted_data
    except Exception as e:
        print(f"Error accessing OCR result as dict: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"Could not extract data from OCR result")
    print(f"Available keys: {list(ocr_result.keys()) if hasattr(ocr_result, 'keys') else 'N/A'}")
    
    return []

def cluster_to_lines(ocr_result, y_threshold=10):
    """Groups OCR result bounding boxes into lines based on their y-coordinates."""
    lines = []
    current_line = []
    current_y = None

    if not ocr_result or len(ocr_result) == 0:
        print("OCR result is empty")
        return lines

    try:
        # Sort by y-coordinate of first point in bbox
        # Use float() to avoid numpy array comparison issues
        sorted_results = sorted(
            enumerate(ocr_result), 
            key=lambda item: float(item[1][0][0][1])
        )
    except (IndexError, TypeError, KeyError, ValueError) as e:
        print(f"Error sorting OCR results: {e}")
        if len(ocr_result) > 0:
            print(f"First item structure: {ocr_result[0]}")
        return lines

    for i, (bbox, (text, confidence)) in sorted_results:
        # Calculate average y coordinate from the 4 corner points
        try:
            avg_y = sum([float(point[1]) for point in bbox]) / 4
        except (TypeError, IndexError) as e:
            print(f"Error calculating avg_y for bbox {bbox}: {e}")
            continue

        if current_y is None or abs(avg_y - current_y) < y_threshold:
            current_line.append(i)
            current_y = avg_y
        else:
            lines.append(current_line)
            current_line = [i]
            current_y = avg_y

    if current_line:
        lines.append(current_line)

    return lines

def process_ocr_result(ocr_result, key, section_name):
    """Process OCR result to extract chords and lyrics."""
    print(f"\n=== Processing OCR Result for '{section_name}' ===")
    print(f"OCR result type: {type(ocr_result)}")
    
    # Extract data from OCRResult object if needed
    extracted_data = extract_ocr_data(ocr_result)
    
    if not extracted_data or len(extracted_data) == 0:
        print("No data extracted from OCR result")
        return {
            'section_name': section_name,
            'key': key,
            'lines': [],
            'chords': [],
            'lyrics': []
        }

    print(f"Processing {len(extracted_data)} OCR items")
    
    line_numbers = cluster_to_lines(extracted_data)
    
    if not line_numbers:
        print("No lines detected after clustering")
        return {
            'section_name': section_name,
            'key': key,
            'lines': [],
            'chords': [],
            'lyrics': []
        }
    
    processed_lines = []

    for i, line_indices in enumerate(line_numbers):
        line_data = {'index': i, 'type': 'unknown', 'content': []}
        
        line_texts = []
        for idx in line_indices:
            try:
                bbox, (text, confidence) = extracted_data[idx]
                line_texts.append((idx, text, confidence, bbox))
            except (ValueError, TypeError, IndexError) as e:
                print(f"Error unpacking item {idx}: {e}")
                continue
        
        if not line_texts:
            continue
        
        # Check if all items in line are chords
        is_chord_line = all(is_chord(text) for _, text, _, _ in line_texts)
        
        if is_chord_line and len(line_texts) > 0:
            line_data['type'] = 'chords'
            for idx, text, confidence, bbox in line_texts:
                try:
                    avg_x = sum(float(bbox[j][0]) for j in range(4)) / 4
                except (TypeError, IndexError) as e:
                    print(f"Error calculating avg_x: {e}")
                    avg_x = 0
                
                clean_text = text.replace('?', '').replace('_', '').strip()
                nashville_chord = convert_chord_to_nashville(clean_text, key)
                
                line_data['content'].append({
                    'position_x': avg_x,
                    'chord': nashville_chord,
                    'original': text,
                    'confidence': confidence
                })
            
            line_data['content'].sort(key=lambda x: x['position_x'])
            
        else:
            line_data['type'] = 'lyrics'
            for idx, text, confidence, bbox in line_texts:
                line_data['content'].append({
                    'text': text,
                    'confidence': confidence
                })
        
        processed_lines.append(line_data)

    chords = [line for line in processed_lines if line['type'] == 'chords']
    lyrics = [line for line in processed_lines if line['type'] == 'lyrics']

    print(f"Processed {len(processed_lines)} lines: {len(chords)} chord lines, {len(lyrics)} lyric lines")

    return {
        'section_name': section_name,
        'key': key,
        'lines': processed_lines,
        'chords': chords,
        'lyrics': lyrics
    }