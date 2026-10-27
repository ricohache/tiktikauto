from pathlib import Path

path = Path(r'C:\TikTokHistoryFactory\src\v5_factory\auto_engine.py')
code = path.read_text(encoding='utf-8')
lines = code.split('\n')

for i, line in enumerate(lines):
    if 'voice_durations.append(round(TARGET_SECONDS / len(scenes), 3))' in line:
        indent = '        '
        insert = [
            '',
            indent + '# Ajuster goal a la narration reelle pour eviter coupures ou silences',
            indent + 'total_voice = sum(voice_durations)',
            indent + 'if total_voice + 1 > goal:',
            indent + '    goal = total_voice + 1',
            indent + '    print(f"[DURATION] Goal adjusted to {goal}s based on voice ({total_voice}s)")',
        ]
        new_lines = lines[:i+1] + insert + lines[i+1:]
        path.write_text('\n'.join(new_lines), encoding='utf-8')
        print('Patch applied at line', i+1)
        break
else:
    print('Target line not found')
