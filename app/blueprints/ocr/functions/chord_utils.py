# chord_utils.py
import re
from typing import List, Dict, Union

class ChordUtils:
    """
    A Python translation of the Dart ChordUtils class for parsing, converting,
    and validating musical chords and Nashville numbers.
    """
    _sharp_keys = ['C', 'G', 'D', 'A', 'E', 'B', 'F#', 'C#', 'G#', 'D#', 'A#']
    _notes_sharp = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    _notes_flat = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

    _scale_intervals = {
        'major': [0, 2, 4, 5, 7, 9, 11],
        'minor': [0, 2, 3, 5, 7, 8, 10],
    }

    _major_scale_qualities = ['', 'm', 'm', '', '', 'm', 'dim']
    _minor_scale_qualities = ['m', 'dim', '', 'm', 'm', '', '']

    _bass_note_pattern = re.compile(r'^[A-Ga-g][#b]?$')
    _chord_pattern = re.compile(
        r'^([A-Ga-g][#b]?)'  # Root note
        r'(m|maj|min|aug|dim|sus|add|\+|°|ø|-)?'  # Quality/type
        r'(\d+)?'  # Number/extension
        r'(sus\d+|add\d+|aug|dim|\+|\(.*?\))*'  # Additional modifiers
        r'(\*)?$'  # Optional asterisk
    )

    @staticmethod
    def parse_key(key: str) -> Dict[str, str]:
        if key.endswith('m') and not key.endswith('dim') and len(key) > 1:
            return {'root': key[:-1], 'scale': 'minor'}
        return {'root': key, 'scale': 'major'}

    @staticmethod
    @property
    def available_keys() -> List[str]:
        keys = set()
        root_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        for note in root_notes:
            keys.add(note)
            keys.add(f'{note}m')
        return sorted(list(keys))

    @staticmethod
    def _generate_scale(key: str) -> List[str]:
        key_info = ChordUtils.parse_key(key)
        root, scale_type = key_info['root'], key_info['scale']

        use_sharps = root in ChordUtils._sharp_keys or ('b' not in root and len(root) == 1)
        chromatic_scale = ChordUtils._notes_sharp if use_sharps else ChordUtils._notes_flat

        try:
            start_index = chromatic_scale.index(root)
        except ValueError:
            try:
                # Fallback for enharmonic equivalents
                start_index = ChordUtils._notes_flat.index(root) if use_sharps else ChordUtils._notes_sharp.index(root)
            except ValueError:
                raise ValueError(f"Invalid key root: {root}")

        intervals = ChordUtils._scale_intervals[scale_type]
        return [chromatic_scale[(start_index + i) % 12] for i in intervals]

    @staticmethod
    def _apply_accidental(note: str, accidental: str) -> str:
        if not accidental:
            return note
        try:
            index = ChordUtils._notes_sharp.index(note)
        except ValueError:
            index = ChordUtils._notes_flat.index(note)
        
        if accidental == 'b':
            index = (index - 1 + 12) % 12
        elif accidental == '#':
            index = (index + 1) % 12
        
        return ChordUtils._notes_flat[index] if 'b' in note else ChordUtils._notes_sharp[index]

    @staticmethod
    def nashville_to_chord(nashville: str, key: str) -> str:
        if nashville == "N.C." or not key:
            return nashville
        
        # Handle slash chords recursively
        if '/' in nashville:
            parts = nashville.split('/', 1)
            base_nashville = parts[0].strip()
            bass_nashville = parts[1].strip()
            base_chord = ChordUtils.nashville_to_chord(base_nashville, key)
            bass_chord = ChordUtils.nashville_to_chord(bass_nashville, key)
            return f"{base_chord}/{bass_chord}"

        key_info = ChordUtils.parse_key(key)
        scale = ChordUtils._generate_scale(key)
        
        accidental = ''
        number_str = nashville
        if nashville.startswith(('b', '#')):
            accidental = nashville[0]
            number_str = nashville[1:]
            
        # Find where the number ends and modifiers begin
        num_match = re.match(r'^(\d+)(.*)', number_str)
        if not num_match:
            return nashville # Invalid format

        number = int(num_match.group(1))
        modifiers = num_match.group(2)
        
        if not (1 <= number <= 7):
            return nashville

        root_note = scale[number - 1]
        if accidental:
            root_note = ChordUtils._apply_accidental(root_note, accidental)
        
        # If no quality is specified, use the default for the scale degree
        if not any(c in modifiers for c in ['m', 'dim', 'aug', '+', '°']) and not accidental:
            qualities = ChordUtils._minor_scale_qualities if key_info['scale'] == 'minor' else ChordUtils._major_scale_qualities
            default_quality = qualities[number - 1]
            return f"{root_note}{default_quality}{modifiers}"
        
        return f"{root_note}{modifiers}"

    @staticmethod
    def chord_to_nashville(chord: str, key: str) -> str:
        if chord == "N.C." or not key:
            return chord

        # Handle slash chords recursively
        if '/' in chord:
            parts = chord.split('/', 1)
            base_part = parts[0].strip()
            bass_part = parts[1].strip()
            base_nashville = ChordUtils.chord_to_nashville(base_part, key)
            # Bass part is just the number
            bass_nashville_num = ChordUtils.chord_to_nashville(bass_part, key)
            bass_nashville_num = re.sub(r'[^b#\d]', '', bass_nashville_num)
            return f"{base_nashville}/{bass_nashville_num}"

        key_info = ChordUtils.parse_key(key)
        scale = ChordUtils._generate_scale(key)
        note_to_number_map = {note.lower(): str(i + 1) for i, note in enumerate(scale)}
        
        match = ChordUtils._chord_pattern.match(chord)
        if not match:
            return chord
        
        components = match.groups()
        root = components[0]
        modifiers = "".join(filter(None, components[1:]))

        nashville_number = None
        accidental_prefix = ''

        if root.lower() in note_to_number_map:
            nashville_number = note_to_number_map[root.lower()]
        else: # Chromatic note
            try:
                note_index = ChordUtils._notes_sharp.index(root)
            except ValueError:
                note_index = ChordUtils._notes_flat.index(root)
            
            for i, scale_note in enumerate(scale):
                try:
                    scale_note_index = ChordUtils._notes_sharp.index(scale_note)
                except ValueError:
                    scale_note_index = ChordUtils._notes_flat.index(scale_note)
                
                if (note_index + 1) % 12 == scale_note_index:
                    accidental_prefix = 'b'
                    nashville_number = str(i + 1)
                    break
                if (note_index - 1 + 12) % 12 == scale_note_index:
                    accidental_prefix = '#'
                    nashville_number = str(i + 1)
                    break
        
        if nashville_number is None:
            return chord

        # Check if the quality is default for the scale degree
        if not accidental_prefix:
            qualities = ChordUtils._minor_scale_qualities if key_info['scale'] == 'minor' else ChordUtils._major_scale_qualities
            default_quality = qualities[int(nashville_number) - 1]
            
            chord_quality = (components[1] or "")
            if (chord_quality == 'm' and default_quality == 'm') or \
               (chord_quality == '' and default_quality == '') or \
               (chord_quality == 'dim' and default_quality == 'dim'):
                # It's the default, so strip the quality
                modifiers = "".join(filter(None, components[2:]))

        return f"{accidental_prefix}{nashville_number}{modifiers}"


    @staticmethod
    def is_potential_chord_token(token: str) -> bool:
        token = token.strip()
        if not token or token == "N.C.":
            return True
        
        if '/' in token:
            parts = token.split('/', 1)
            if len(parts) == 2:
                main_chord, bass_note = parts[0].strip(), parts[1].strip()
                return bool(ChordUtils._chord_pattern.match(main_chord) and \
                            ChordUtils._bass_note_pattern.match(bass_note))
            return False

        return bool(ChordUtils._chord_pattern.match(token))

    @staticmethod
    def extract_chords_from_line(line: str) -> List[str]:
        return [token for token in line.split() if ChordUtils.is_potential_chord_token(token)]