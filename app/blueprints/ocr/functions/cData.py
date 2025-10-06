import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.blueprints.ocr.functions.chord_utils import ChordUtils


@dataclass
class PreliminaryLine:
    text: str
    is_chord_line: bool = False
    certainty: float = 0.0

@dataclass
class PreliminarySection:
    title: str
    lines: List[PreliminaryLine]

# --- Final Data Classes (for JSON output) ---
@dataclass
class Chord:
    position: int
    value: str
    def to_dict(self):
        return {"position": self.position, "value": self.value}

@dataclass
class LineData:
    lyrics: str
    chords: List[Chord]
    def to_dict(self):
        return {"lyrics": self.lyrics, "chords": [c.to_dict() for c in self.chords]}

@dataclass
class SongSection:
    title: str
    lines: List[LineData]
    def to_dict(self):
        return {"title": self.title, "lines": [l.to_dict() for l in self.lines]}

# --- Main Conversion Logic ---
def get_chord_line_certainty(line: str) -> float:
    line = line.strip()
    if not line:
        return 0.0
    
    tokens = re.split(r'\s+', line)
    if not tokens:
        return 0.0
        
    chord_tokens = [t for t in tokens if ChordUtils.is_potential_chord_token(t)]
    return len(chord_tokens) / len(tokens)

def parse_raw_text_to_preliminary(raw_text: str) -> List[PreliminarySection]:
    """Parses a full raw song text into a list of preliminary sections."""
    sections = []
    current_title = "Intro"
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
            is_chord = certainty > 0.6  # Threshold can be tuned
            current_lines.append(PreliminaryLine(line_text, is_chord, certainty))

    # Add the last section
    if current_lines:
        sections.append(PreliminarySection(title=current_title, lines=current_lines))
        
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
            # Reconstruct chord line with spacing
            chord_positions = []
            for chord_item in line.get('content', []):
                pos = int(chord_item.get('position_x', 0))
                chord = chord_item.get('original', chord_item.get('chord', ''))
                chord_positions.append((pos, chord))
            
            # Sort by position and create spaced chord line
            chord_positions.sort(key=lambda x: x[0])
            if chord_positions:
                chord_line = ""
                last_pos = 0
                for pos, chord in chord_positions:
                    # Scale positions down (they're in pixels, convert to character positions)
                    char_pos = pos // 10  # Rough approximation
                    spaces = max(0, char_pos - last_pos)
                    chord_line += " " * spaces + chord
                    last_pos = char_pos + len(chord)
                
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
    final_sections = []

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
                    chords = []
                    # Use finditer to get match objects with positions
                    for match in re.finditer(r'\S+', chord_line_text):
                        chord_text = match.group(0)
                        position = match.start()
                        if ChordUtils.is_potential_chord_token(chord_text):
                            nashville = ChordUtils.chord_to_nashville(chord_text, key)
                            clamped_pos = min(position, len(lyric_line.text))
                            chords.append(Chord(clamped_pos, nashville))
                    final_lines.append(LineData(lyric_line.text, chords))
                    i += 2 # Skip both lines
                else: # Chord-only instrumental line
                    chords = [Chord(match.start(), ChordUtils.chord_to_nashville(match.group(0), key))
                              for match in re.finditer(r'\S+', chord_line_text)
                              if ChordUtils.is_potential_chord_token(match.group(0))]
                    final_lines.append(LineData("", chords))
                    i += 1
            else: # Lyric-only line
                final_lines.append(LineData(line.text, []))
                i += 1
        
        final_sections.append(SongSection(prelim_section.title, final_lines))

    song_content_str = "".join([s.title + "".join(l.lyrics for l in s.lines) for s in final_sections])
    song_hash = hashlib.sha256(song_content_str.encode('utf-8')).hexdigest()

    # Assemble final dictionary
    song_dict = {
        "hash": song_hash,
        "header": {
            "name": title,
            "key": key,
            "authors": authors,
        },
        "sections": [s.to_dict() for s in final_sections]
    }
    return song_dict