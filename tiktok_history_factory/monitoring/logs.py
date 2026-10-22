
"""Journalisation structuree des executions."""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class StructuredLogger:
    """Logger JSON pour les metriques et evenements."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("tiktok_history_factory")

    def log_event(self, event_type: str, task_id: int = None, phase: str = None,
                  duration_ms: int = None, success: bool = None, error: str = None,
                  extra: Dict[str, Any] = None) -> Dict[str, Any]:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "task_id": task_id,
            "phase": phase,
            "duration_ms": duration_ms,
            "success": success,
            "error": error,
            "extra": extra or {},
        }
        log_file = self.log_dir / f"events_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry
