import json
from pathlib import Path

templates = json.load(open(r'C:\\TikTokHistoryFactory\\tmp_templates.json','r',encoding='utf-8'))
src = Path(r'C:\\TikTokHistoryFactory\\src\\v5_factory\\auto_engine.py').read_text(encoding='utf-8')

start_marker = '        templates = {'
start_idx = src.find(start_marker)
if start_idx < 0:
    raise ValueError('templates block not found')

brace_count = 0
end_idx = start_idx
for i in range(start_idx, len(src)):
    if src[i] == '{': brace_count += 1
    if src[i] == '}': brace_count -= 1
    if brace_count == 0:
        end_idx = i
        break

lines = []
lines.append('        templates = {')
for slug, data in templates.items():
    indent = '            '
    lines.append(indent + \"'\" + slug + \"': {\")
    lines.append(indent + \"    'scenes': [\")
    for en, fr in data['scenes']:
        en_esc = en.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"')
        fr_esc = fr.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"')
        lines.append(indent + \"        (\\\"\" + en_esc + \"\\\", \\\"\" + fr_esc + \"\\\"),\")
    lines.append(indent + \"    ]\")
    lines.append(indent + \"},\")
lines.append('        }')
new_block = chr(10).join(lines)

new_src = src[:start_idx] + new_block + src[end_idx+1:]
compile(new_src, '<string>', 'exec')
print('Syntax OK')
for slug, data in templates.items():
    total = sum(len(en.split()) for en, fr in data['scenes'])
    print(slug + ': ' + str(len(data['scenes'])) + ' scenes, ~' + str(total) + ' EN words')
Path(r'C:\\TikTokHistoryFactory\\src\\v5_factory\\auto_engine.py').write_text(new_src, encoding='utf-8')
print('Patched auto_engine.py')
