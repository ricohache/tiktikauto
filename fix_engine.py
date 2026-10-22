path = 'src/v5_factory/auto_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
old_line = '            print(f\'{row[0]:30s} | {row[1]:15s} | QC={row[3]} | {row[2] or \"\"}\')'
new_lines = '            mp4 = row[2] or ""\n            print(f"{row[0]:30s} | {row[1]:15s} | QC={row[3]} | {mp4}")'
content = content.replace(old_line, new_lines)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed')
