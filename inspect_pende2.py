import re

with open("src/v5_factory/auto_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find current pende template
idx = content.find("'pende-revolt-1931': {")
if idx == -1:
    print("PENDE_NOT_FOUND")
    exit(1)

# Extract and show current template length
pende_start = idx
search_from = pende_start + 500
close_idx = content.find("            }", search_from)
if close_idx == -1:
    print("CLOSE_NOT_FOUND")
    exit(1)

current = content[pende_start:close_idx+13]
print(f"Current Pende template length: {len(current)} chars")
print("First scene EN:")
# Find first EN text
m = re.search(r'\(\"([^\"]+)\"', current)
if m:
    print(f"  {m.group(1)[:80]}...")
print("Last scene EN:")
m = re.search(r'\(\"([^\"]+)\"[^)]*\)\s*\]', current)
if m:
    print(f"  {m.group(1)[:80]}...")
