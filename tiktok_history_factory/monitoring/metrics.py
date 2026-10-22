
"""Collecte des metriques de performance."""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime

@dataclass
class PhaseMetrics:
    phase: str
    started_at: float
    ended_at: float = 0.0
    success: bool = False
    error: str = ""
    vram_peak_mb: float = 0.0
    ram_peak_mb: float = 0.0

    @property
    def duration_ms(self) -> int:
        return int((self.ended_at - self.started_at) * 1000)

class MetricsCollector:
    """Collecte et aggrege les metriques par run."""

    def __init__(self):
        self.phases: List[PhaseMetrics] = []
        self.current_run: Dict[str, Any] = {}

    def start_phase(self, phase: str) -> PhaseMetrics:
        pm = PhaseMetrics(phase=phase, started_at=time.time())
        self.phases.append(pm)
        return pm

    def end_phase(self, phase: str, success: bool = True, error: str = "") -> PhaseMetrics:
        for pm in reversed(self.phases):
            if pm.phase == phase and pm.ended_at == 0.0:
                pm.ended_at = time.time()
                pm.success = success
                pm.error = error
                return pm
        return None

    def summary(self) -> Dict[str, Any]:
        total_ms = sum(p.duration_ms for p in self.phases)
        return {
            "total_duration_ms": total_ms,
            "phases_count": len(self.phases),
            "success_count": sum(1 for p in self.phases if p.success),
            "failed_count": sum(1 for p in self.phases if not p.success),
            "phases": [
                {"phase": p.phase, "duration_ms": p.duration_ms, "success": p.success}
                for p in self.phases
            ],
        }
