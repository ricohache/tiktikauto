from pathlib import Path
import json

path = Path(r'C:\TikTokHistoryFactory\src\v5_factory\auto_engine.py')
code = path.read_text(encoding='utf-8')
lines = code.split('\n')

insert = [
    '        # Charger templates supplementaires depuis tmp_templates.json',
    '        tmp_path = self.project / "tmp_templates.json"',
    '        if tmp_path.exists():',
    '            extra = json.loads(tmp_path.read_text(encoding="utf-8"))',
    '            for eslug, data in extra.items():',
    '                scenes_extra = []',
    '                for s in data.get("scenes", []):',
    '                    if isinstance(s, dict):',
    '                        scenes_extra.append((s["narration_en"], s["narration_fr"]))',
    '                    else:',
    '                        scenes_extra.append(s)',
    '                templates[eslug] = {"scenes": scenes_extra}',
]

new_lines = lines[:287] + insert + lines[287:]
path.write_text('\n'.join(new_lines), encoding='utf-8')
print('Patched successfully')
