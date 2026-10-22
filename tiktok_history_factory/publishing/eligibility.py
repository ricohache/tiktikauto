
"""Verification de l'eligibilite a la publication."""
from typing import Dict, Any

class EligibilityChecker:
    """Verifie qu'une video peut etre publiee."""

    REQUIRED_STATUSES = ["APPROVED", "READY_FOR_EXPORT", "READY_FOR_UPLOAD"]

    def check(self, task_status: str, video_path: str = "", has_sources: bool = False) -> Dict[str, Any]:
        """Retourne l'eligibilite et les raisons de blocage eventuelles."""
        errors = []
        if task_status not in self.REQUIRED_STATUSES:
            errors.append(f"Statut {task_status} non eligible")
        if not has_sources:
            errors.append("Sources manquantes")
        if not video_path:
            errors.append("Chemin video non fourni")

        return {
            "eligible": len(errors) == 0,
            "errors": errors,
            "can_proceed": task_status == "APPROVED" and len(errors) == 0,
        }
