
"""Suivi des couts et estimation electrique."""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CostEstimate:
    ollama_cloud_tokens_used: int = 0
    ollama_cloud_cost_eur: float = 0.0
    gpu_compute_time_hours: float = 0.0
    kwh_price: float = 0.20
    gpu_power_watts: float = 120.0  # RTX 4060 ~120W
    estimated_kwh: float = 0.0
    estimated_electricity_eur: float = 0.0
    total_estimated_eur: float = 0.0

    def calculate(self) -> Dict[str, Any]:
        self.estimated_kwh = (self.gpu_compute_time_hours * self.gpu_power_watts) / 1000
        self.estimated_electricity_eur = self.estimated_kwh * self.kwh_price
        self.total_estimated_eur = self.ollama_cloud_cost_eur + self.estimated_electricity_eur
        return {
            "ollama_cloud_eur": self.ollama_cloud_cost_eur,
            "electricity_eur": round(self.estimated_electricity_eur, 4),
            "total_estimated_eur": round(self.total_estimated_eur, 4),
            "gpu_hours": self.gpu_compute_time_hours,
            "kwh": round(self.estimated_kwh, 4),
        }
