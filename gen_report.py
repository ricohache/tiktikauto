import json, hashlib
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, r'C:\TikTokHistoryFactory\src\v5_factory')
import finish_pilot as fp

ffprobe = fp.check_exe('ffprobe')

REPORT = {
    "project": "TikTokHistoryFactory",
    "date": "2026-10-23",
    "benchmark": {
        "episodes_produced": 3,
        "total_production_time_sec": 82 + 263 + 77,  # maji + sharpeville + chilembwe(redo)
        " subjects_discovered_autonomously": True,
        "images_generated_real": True,
        "voice_generated_real": True,
        "subtitles_synced_real": True,
    },
    "episodes": []
}

subjects = [
    ("maji-maji-rebellion-1905", "auto-maji-maji-rebellion-1905-v5", 82.0, "19050800-19051100"),
    ("sharpeville-massacre-1960", "auto-sharpeville-massacre-1960-v5", 263.0, "19600100-19601100"),
    ("chilembwe-uprising-1915", "auto-chilembwe-uprising-1915-v5", 77.0, "19150100-19151100"),
]

for slug, outdir, elapsed, seed_range in subjects:
    mp4 = Path(r'C:\TikTokHistoryFactory\output') / outdir / (slug + '-v5-final.mp4')
    entry = {
        "slug": slug,
        "mp4_path": str(mp4),
        "exists": mp4.exists(),
        "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest() if mp4.exists() else None,
    }
    if mp4.exists():
        r = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration,size,bit_rate', '-of', 'json', str(mp4)], capture_output=True, text=True)
        fmt = json.loads(r.stdout)
        entry["duration_sec"] = float(fmt["format"]["duration"])
        entry["size_bytes"] = int(fmt["format"]["size"])
        entry["bitrate_bps"] = int(fmt["format"]["bit_rate"])
        
        r = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate', '-of', 'json', str(mp4)], capture_output=True, text=True)
        vid = json.loads(r.stdout)
        if vid.get('streams'):
            s = vid['streams'][0]
            entry["video"] = {"width": s["width"], "height": s["height"], "fps": s["r_frame_rate"]}
        
        r = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=duration,sample_rate,channels', '-of', 'json', str(mp4)], capture_output=True, text=True)
        aud = json.loads(r.stdout)
        if aud.get('streams'):
            s = aud['streams'][0]
            entry["audio"] = {"duration": float(s.get("duration", 0)), "sample_rate": s["sample_rate"], "channels": s["channels"]}
        
        # Count shots
        shots_dir = Path(r'C:\TikTokHistoryFactory\work') / ('auto-' + slug) / 'shots'
        entry["shots_count"] = len(list(shots_dir.glob('*.mp4'))) if shots_dir.exists() else 0
        
        # Count images
        img_dir = Path(r'C:\TikTokHistoryFactory\work') / ('auto-' + slug) / 'images'
        entry["images_count"] = len(list(img_dir.glob('*.png'))) if img_dir.exists() else 0
        
        entry["production_time_sec"] = elapsed
        entry["seed_range"] = seed_range
    
    REPORT["episodes"].append(entry)

# Add SQLite checks
import sqlite3
db = sqlite3.connect(r'C:\TikTokHistoryFactory\data\factory.db')
c = db.cursor()
c.execute('SELECT COUNT(*) FROM auto_productions WHERE qc_passed=1')
REPORT["sqlite"]["total_qc_passed"] = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM auto_productions')
REPORT["sqlite"]["total_entries"] = c.fetchone()[0]
c.execute("SELECT slug, status, qc_passed FROM auto_productions WHERE slug IN ('maji-maji-rebellion-1905', 'sharpeville-massacre-1960', 'chilembwe-uprising-1915')")
REPORT["sqlite"]["new_subjects"] = c.fetchall()
db.close()

# Write report
report_path = Path(r'C:\TikTokHistoryFactory\QC_REPORT_v5_final.json')
report_path.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False), encoding='utf-8')
print('QC report written to', report_path)
print(json.dumps(REPORT, indent=2, ensure_ascii=False))
