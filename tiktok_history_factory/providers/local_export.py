
"""Export local MP4 + manifeste + sources."""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class LocalExportProvider:
    """Export complet vers le systeme de fichiers local."""

    def export(self, video_path: str, task_data: Dict[str, Any], output_dir: str) -> Dict[str, Any]:
        """Exporte la video, le manifeste et les sources."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        source = Path(video_path)
        if not source.is_file() or not source.stat().st_size:
            return {'status': 'BLOCKED', 'error': 'Source video missing or empty'}
        import shutil
        import hashlib
        destination = out / source.name
        if destination.exists() and destination.resolve() != source.resolve():
            if destination.read_bytes() != source.read_bytes():
                return {'status': 'BLOCKED', 'error': 'Different export already exists'}
        if destination.resolve() != source.resolve():
            shutil.copy2(source, destination)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        manifest = {
            "exported_at": datetime.now().isoformat(),
            "video_file": str(Path(video_path).name),
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            "task": task_data,
            "aigc_disclaimer": "Reconstitution historique generee par IA. Contenu documentaire.",
        }
        manifest_path = out / f"{timestamp}_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        return {
            "status": "READY_FOR_EXPORT",
            "output_dir": str(out),
            "manifest": str(manifest_path),
            'video_path': str(destination),
        }
