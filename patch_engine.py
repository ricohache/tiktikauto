import re

with open("src/v5_factory/auto_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Change the subtitle call in _run_v5_production
old_call = """        # Sous-titres alignes par duree phonetique reelle
        ass_path, timings_json, nsubs = self._generate_aligned_subtitles(
            scenes, timings, goal, out / "subtitles"
        )"""

new_call = """        # Sous-titres alignes sur les durees video reelles (pas WAV)
        scene_durations = [round(f / FPS, 3) for f in frames]
        ass_path, timings_json, nsubs = self._generate_aligned_subtitles(
            scenes, scene_durations, out / "subtitles"
        )"""

if old_call in content:
    content = content.replace(old_call, new_call)
    print("[PATCH 1] subtitle call fixed")
else:
    print("[PATCH 1] subtitle call NOT found")

# Fix 2: Change the method signature
old_sig = "def _generate_aligned_subtitles(self, scenes, timings, goal, subtitles_dir):"
new_sig = "def _generate_aligned_subtitles(self, scenes, scene_durations, subtitles_dir):"

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print("[PATCH 2] method signature fixed")
else:
    print("[PATCH 2] method signature NOT found")

# Fix 3: Update the method body to use scene_durations
old_body = """        all_subs = []
        cumulative_time = 0.0
        for i, s in enumerate(scenes):
            dur = timings[i]"""

new_body = """        all_subs = []
        cumulative_time = 0.0
        for i, s in enumerate(scenes):
            dur = scene_durations[i]"""

if old_body in content:
    content = content.replace(old_body, new_body)
    print("[PATCH 3] method body fixed")
else:
    print("[PATCH 3] method body NOT found")

with open("src/v5_factory/auto_engine.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
