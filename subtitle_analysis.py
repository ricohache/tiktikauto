import json
from pathlib import Path

p = Path('C:/TikTokHistoryFactory/output/auto-pende-revolt-1931-v5/subtitles/timings.json')
cues = json.loads(p.read_text(encoding='utf-8'))

print('=== ANALYSE SOUS-TITRES PENDE 1931 ===')
print(f'Total segments: {len(cues)}')
print(f'Duree totale couverte: {cues[-1]["end"]:.3f}s')
print(f'Target: 90s')
print(f'Manque: {90 - cues[-1]["end"]:.1f}s de sous-titres')
print()
print('Detail par segment:')
for i, cue in enumerate(cues, 1):
    dur = cue['end'] - cue['start']
    words = len(cue['lines'][0].split())
    chars = len(cue['lines'][0])
    print(f'{i:2d}: [{cue["start"]:6.2f} - {cue["end"]:6.2f}] ({dur:5.2f}s) {words:2d} mots, {chars:3d} car | {cue["lines"][0][:60]}')
