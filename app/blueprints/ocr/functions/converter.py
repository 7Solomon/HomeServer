from dataclasses import dataclass
from typing import List, Dict, Any
import re
import hashlib
from app.blueprints.ocr.functions.chord_utils import ChordUtils
from app.blueprints.ocr.functions.cData import PreliminaryLine, PreliminarySection, Chord, LineData, SongSection

def get_chord_line_certainty(line: str) -> float:
    """Enhanced chord line detection."""
    line = line.strip()
    if not line:
        return 0.0
    
    tokens = re.split(r'\s+', line)
    if not tokens:
        return 0.0
    
    chord_tokens = []
    for token in tokens:
        # Check traditional chords
        if ChordUtils.is_potential_chord_token(token):
            chord_tokens.append(token)
        # Check Nashville numbers
        elif re.match(r'^[b#]?[1-7][maug\-dim°ø+()\/\d]*$', token):
            chord_tokens.append(token)
        # Check pure numbers
        elif token.isdigit() and 1 <= int(token) <= 7:
            chord_tokens.append(token)
    
    ratio = len(chord_tokens) / len(tokens)
    
    # Also consider average token length (chords are typically short)
    avg_length = sum(len(t) for t in tokens) / len(tokens)
    
    # Boost certainty if tokens are short
    if avg_length < 4:
        ratio = min(1.0, ratio * 1.5)
    
    return ratio

def parse_raw_text_to_preliminary(raw_text: str) -> List[PreliminarySection]:
    """Parses a full raw song text into a list of preliminary sections."""
    sections = []
    current_title = "Section"
    current_lines = []
    
    section_pattern = re.compile(r'^\s*\[(.*?)\]\s*$', re.IGNORECASE)

    for line_text in raw_text.split('\n'):
        match = section_pattern.match(line_text)
        if match:
            # Save the previous section if it has content
            if current_lines:
                sections.append(PreliminarySection(title=current_title, lines=current_lines))
            # Start a new section
            current_title = match.group(1).strip()
            current_lines = []
        elif line_text.strip():
            certainty = get_chord_line_certainty(line_text)
            is_chord = certainty > 0.5  # Lower threshold for better detection
            current_lines.append(PreliminaryLine(line_text, is_chord, certainty))

    # Add the last section
    if current_lines:
        sections.append(PreliminarySection(title=current_title, lines=current_lines))
    
    # If no sections were created, return the whole text as one section
    if not sections and raw_text.strip():
        lines = []
        for line_text in raw_text.split('\n'):
            if line_text.strip():
                certainty = get_chord_line_certainty(line_text)
                is_chord = certainty > 0.5
                lines.append(PreliminaryLine(line_text, is_chord, certainty))
        if lines:
            sections.append(PreliminarySection(title="Section", lines=lines))
        
    return sections

def parse_ocr_section_to_preliminary(section_name: str, ocr_data: Dict[str, Any]) -> PreliminarySection:
    """
    Convert OCR output from a single section into a PreliminarySection.
    
    Args:
        section_name: Name of the section (e.g., "Verse 1", "Chorus")
        ocr_data: The structured OCR data with 'lines' containing chord/lyric info
    
    Returns:
        PreliminarySection ready for review/correction
    """
    preliminary_lines = []
    
    if 'lines' not in ocr_data:
        return PreliminarySection(title=section_name, lines=[])
    
    for line in ocr_data['lines']:
        line_type = line.get('type', 'unknown')
        
        if line_type == 'chords':
            # Reconstruct chord line with proper spacing based on pixel positions
            chord_positions = []
            for chord_item in line.get('content', []):
                pos_x = chord_item.get('position_x', 0)
                chord = chord_item.get('original', chord_item.get('chord', ''))
                chord_positions.append((pos_x, chord))
            
            # Sort by position
            chord_positions.sort(key=lambda x: x[0])
            
            if chord_positions:
                # Calculate scaling factor: find the pixel width and map to reasonable character positions
                min_x = min(pos for pos, _ in chord_positions)
                max_x = max(pos for pos, _ in chord_positions)
                pixel_width = max_x - min_x
                
                # Assume average character width of ~8-12 pixels
                # For a typical line of 80 characters, that's about 640-960 pixels
                avg_char_width = 10  # pixels per character (adjust if needed)
                
                chord_line = ""
                last_char_pos = 0
                
                for pos_x, chord in chord_positions:
                    # Convert pixel position to character position
                    char_pos = int((pos_x - min_x) / avg_char_width)
                    
                    # Calculate spaces needed
                    spaces_needed = max(1, char_pos - last_char_pos)  # At least 1 space
                    
                    chord_line += " " * spaces_needed + chord
                    last_char_pos = char_pos + len(chord)
                
                preliminary_lines.append(PreliminaryLine(
                    text=chord_line.strip(),
                    is_chord_line=True,
                    certainty=1.0
                ))
        
        elif line_type == 'lyrics':
            # Concatenate lyric text
            lyric_text = " ".join([item.get('text', '') for item in line.get('content', [])])
            if lyric_text.strip():
                preliminary_lines.append(PreliminaryLine(
                    text=lyric_text.strip(),
                    is_chord_line=False,
                    certainty=sum(item.get('confidence', 0.5) for item in line.get('content', [])) / max(len(line.get('content', [])), 1)
                ))
    
    return PreliminarySection(title=section_name, lines=preliminary_lines)

def merge_ocr_sections(ocr_sections: List[Dict[str, Any]]) -> List[PreliminarySection]:
    """
    Convert multiple OCR section outputs into preliminary sections.
    
    Args:
        ocr_sections: List of dicts with keys 'section_name' and 'structured_data'
    
    Returns:
        List of PreliminarySection objects
    """
    preliminary_sections = []
    
    for section in ocr_sections:
        section_name = section.get('section_name', 'Unknown')
        ocr_data = section.get('structured_data', {})
        
        prelim_section = parse_ocr_section_to_preliminary(section_name, ocr_data)
        if prelim_section.lines:  # Only add non-empty sections
            preliminary_sections.append(prelim_section)
    
    return preliminary_sections

def finalize_song_data(
    preliminary_sections: List[PreliminarySection],
    title: str,
    key: str,
    authors: List[str] = []
) -> Dict[str, Any]:
    """Converts the corrected preliminary data into the final song JSON structure."""
    data = {}

    for prelim_section in preliminary_sections:
        final_lines = []
        i = 0
        lines = prelim_section.lines
        
        while i < len(lines):
            line = lines[i]
            if line.is_chord_line:
                chord_line_text = line.text
                # Check for a following lyric line
                if i + 1 < len(lines) and not lines[i+1].is_chord_line:
                    lyric_line = lines[i+1]
                    chords_dict = {}
                    
                    # Use finditer to get match objects with positions
                    for match in re.finditer(r'\S+', chord_line_text):
                        chord_text = match.group(0)
                        position = match.start()
                        
                        # Check if it's a traditional chord OR Nashville number
                        is_traditional = ChordUtils.is_potential_chord_token(chord_text)
                        is_nashville = re.match(r'^[b#]?[1-7][maug\-dim°ø+()\/\d]*$', chord_text)
                        
                        if is_traditional:
                            # Convert traditional chord to Nashville
                            nashville = ChordUtils.chord_to_nashville(chord_text, key)
                            clamped_pos = min(position, len(lyric_line.text))
                            chords_dict[str(clamped_pos)] = nashville
                        elif is_nashville:
                            # Already Nashville, use as-is
                            clamped_pos = min(position, len(lyric_line.text))
                            chords_dict[str(clamped_pos)] = chord_text
                    
                    final_lines.append({
                        "lyrics": lyric_line.text,
                        "chords": chords_dict
                    })
                    i += 2  # Skip both lines
                else: 
                    # Chord-only instrumental line
                    chords_dict = {}
                    for match in re.finditer(r'\S+', chord_line_text):
                        chord_text = match.group(0)
                        position = match.start()
                        
                        is_traditional = ChordUtils.is_potential_chord_token(chord_text)
                        is_nashville = re.match(r'^[b#]?[1-7][maug\-dim°ø+()\/\d]*$', chord_text)
                        
                        if is_traditional:
                            nashville = ChordUtils.chord_to_nashville(chord_text, key)
                            chords_dict[str(position)] = nashville
                        elif is_nashville:
                            chords_dict[str(position)] = chord_text
                    
                    final_lines.append({
                        "lyrics": "",
                        "chords": chords_dict
                    })
                    i += 1
            else: 
                # Lyric-only line (no chords)
                final_lines.append({
                    "lyrics": line.text,
                    "chords": {}
                })
                i += 1
        
        # Add section to data dictionary
        data[prelim_section.title] = final_lines

    # Calculate hash from all content
    song_content_str = "".join([
        section_name + "".join(line["lyrics"] for line in section_lines)
        for section_name, section_lines in data.items()
    ])
    song_hash = hashlib.sha256(song_content_str.encode('utf-8')).hexdigest()

    # Assemble final dictionary in the correct structure
    song_dict = {
        "hash": song_hash,
        "header": {
            "name": title,
            "key": key,
            "authors": authors,
        },
        "data": data
    }
    return song_dict


def preliminary_to_structured(prelim_section, key):
    """
    Convert PreliminarySection back to structured OCR data format.
    """
    lines = []
    
    for line in prelim_section.lines:
        if line.is_chord_line:
            # Parse chord tokens and their positions
            chord_content = []
            import re
            for match in re.finditer(r'\S+', line.text):
                chord_text = match.group(0)
                position = match.start()
                
                # Check if it's a traditional chord OR a Nashville number
                is_nashville_number = re.match(r'^[b#]?[1-7][maug\-dim°ø+()\/\d]*$', chord_text)
                is_traditional_chord = ChordUtils.is_potential_chord_token(chord_text)
                
                if is_traditional_chord:
                    # Convert traditional chord to Nashville
                    nashville = ChordUtils.chord_to_nashville(chord_text, key)
                    chord_content.append({
                        'position_x': position * 10,  # Convert char to pixel
                        'chord': nashville,
                        'original': chord_text,
                        'confidence': line.certainty
                    })
                elif is_nashville_number:
                    # Already a Nashville number, keep as-is
                    chord_content.append({
                        'position_x': position * 10,
                        'chord': chord_text,  # Keep the Nashville notation
                        'original': chord_text,
                        'confidence': line.certainty
                    })
            
            if chord_content:
                lines.append({
                    'index': len(lines),
                    'type': 'chords',
                    'content': chord_content
                })
        else:
            # Lyric line
            lines.append({
                'index': len(lines),
                'type': 'lyrics',
                'content': [{
                    'text': line.text,
                    'confidence': line.certainty
                }]
            })
    
    return {
        'section_name': prelim_section.title,
        'key': key,
        'lines': lines,
        'chords': [l for l in lines if l['type'] == 'chords'],
        'lyrics': [l for l in lines if l['type'] == 'lyrics']
    }


def rebuild_plain_text(structured_data):
    """
    Rebuild plain text from structured data with proper spacing.
    """
    plain_text = ""
    
    for line in structured_data['lines']:
        if line['type'] == 'lyrics':
            plain_text += " ".join([item['text'] for item in line['content']]) + "\n"
        elif line['type'] == 'chords':
            chord_items = line['content']
            
            if chord_items:
                positions = [item['position_x'] for item in chord_items]
                min_pos = min(positions)
                avg_char_width = 10
                
                chord_line = ""
                last_char_pos = 0
                
                for item in chord_items:
                    pixel_pos = item['position_x']
                    char_pos = int((pixel_pos - min_pos) / avg_char_width)
                    spaces_needed = max(1, char_pos - last_char_pos)
                    
                    chord_line += " " * spaces_needed + item['chord']
                    last_char_pos = char_pos + len(item['chord'])
                
                plain_text += chord_line + "\n"
    
    return plain_text.strip()