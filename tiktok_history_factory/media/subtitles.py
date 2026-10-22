
"""Generation et rendu des sous-titres SRT."""
from dataclasses import dataclass
from typing import List
import re

@dataclass
class SubtitleSegment:
    start_ms: int
    end_ms: int
    text: str

class SubtitleGenerator:
    """Genere des sous-titres synchronises a partir d'un script."""

    def __init__(self, words_per_second: float = 2.5):
        self.words_per_second = words_per_second

    def split_into_segments(self, script_text: str, total_duration_ms: int) -> List[SubtitleSegment]:
        """Decoupe le script en segments temporises."""
        words = script_text.split()
        if not words:
            return []
        segment_count = (len(words) + 2) // 3
        if total_duration_ms < segment_count:
            raise ValueError('Audio too short for subtitle segments')
        segments = []
        current_words = []
        current_start = 0
        for i, word in enumerate(words):
            current_words.append(word)
            if len(current_words) >= 3 or i == len(words) - 1:
                end_ms = round((len(segments) + 1) * total_duration_ms / segment_count)
                segments.append(SubtitleSegment(
                    start_ms=current_start,
                    end_ms=end_ms,
                    text=" ".join(current_words)
                ))
                current_start = end_ms
                current_words = []
        return segments

    def to_srt(self, segments: List[SubtitleSegment]) -> str:
        """Exporte au format SRT."""
        lines = []
        for i, seg in enumerate(segments, 1):
            lines.append(str(i))
            lines.append(f"{_ms_to_srt(seg.start_ms)} --> {_ms_to_srt(seg.end_ms)}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

def _ms_to_srt(ms: int) -> str:
    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
