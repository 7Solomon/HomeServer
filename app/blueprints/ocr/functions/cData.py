import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .chord_utils import ChordUtils

# --- Intermediate Data Classes (for review/correction) ---
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
