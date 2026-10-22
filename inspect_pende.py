import re

with open("src/v5_factory/auto_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the pende template
idx = content.find("'pende-revolt-1931': {")
if idx == -1:
    print("PENDE_TEMPLATE_NOT_FOUND")
    exit(1)

# Find the end of pende template
end_marker = "            }"
# Find the closing brace after pende scenes
pende_start = idx
search_from = pende_start + 500
close_idx = content.find("            }", search_from)
if close_idx == -1:
    print("CLOSE_NOT_FOUND")
    exit(1)

# Extract pende template for inspection
pende_template = content[pende_start:close_idx+13]
print("=== Current Pende template (first 500 chars) ===")
print(pende_template[:500])
print("...")
print("=== Length ===")
print(len(pende_template))
