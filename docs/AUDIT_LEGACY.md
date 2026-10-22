> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Audit Legacy — TikTokHistoryFactory

Rapport d'audit de l'ébauche existante (étape 1) vs cahier des charges complet.
Date : 2026-10-16

## Problèmes identifiés

| # | Problème | Fichier/Ligne | Sévérité | Preuve | Correction | Test |
|---|----------|---------------|----------|--------|------------|------|
| 1 | README parle d'« histoire du manga » au lieu d'histoire illustrée en style manga | README.md | CRITIQUE | Texte : « histoire du manga (auteurs, événements, œuvres emblématiques) » | Réécrire complètement le README | Vérification manuelle |
| 2 | .env.example pointe vers un LLM local (gemma3:4b) au lieu d'Ollama Cloud | .env.example | IMPORTANT | `OLLAMA_MODEL=gemma3:4b` | Remplacer par `kimi-k3:cloud` par défaut ; garder local en option | Vérification du fichier |
| 3 | `Settings.LOG_LEVEL` utilisé mais absent de settings.py | pipeline/orchestrator.py:117 | IMPORTANT | `getattr(logging, Settings.LOG_LEVEL)` | Ajouter `LOG_LEVEL` à Settings | pytest |
| 4 | Chemins DB/LOG basés sur resolve() depuis cwd au lieu de racine projet | config/settings.py:16-17 | IMPORTANT | `Path(os.getenv("DB_PATH", "data/factory.db")).resolve()` | Utiliser `PROJECT_ROOT /` | pytest |
| 5 | run_cycle() marque toute tâche FAILED car pipeline non implémenté | pipeline/orchestrator.py:97 | IMPORTANT | `self.update_status(task.id, TaskStatus.FAILED, error="Pipeline non implémenté")` | Ne pas changer le statut ; logger seulement | pytest |
| 6 | README appelle `python -m tiktok_history_factory.database.init` qui n'existe pas | README.md | MOYEN | Commande inexistante | Créer le module ou corriger le README | Vérification |
| 7 | orchestrator.ps1 réinstalle les dépendances à chaque run | scripts/orchestrator.ps1 | MOYEN | `pip install -q -e ".[dev]"` dans le script | Séparer bootstrap et run | Exécution |
| 8 | Tests `py_compile` insuffisants — aucun test réel | tests/test_placeholder.py | IMPORTANT | Seuls imports testés | Ajouter vrais tests | pytest |
| 9 | Hash anti-doublon par slug brut insuffisant | database/models.py:53 | MOYEN | `hashlib.sha256(topic_slug.encode("utf-8"))` | Normaliser le slug + ajouter identifiants | pytest |
| 10 | État FAILED par défaut détruit la file sans raison métier | pipeline/orchestrator.py | IMPORTANT | Marque FAILED à cause de non-implémentation | Logger WARNING sans changer le statut | pytest |
| 11 | Pas de gestion de reprise après crash | pipeline/orchestrator.py | IMPORTANT | Aucun mécanisme de checkpoint | Ajouter transitions d'état robustes | pytest |
| 12 | Pas de contrat de données Pydantic | tout le projet | IMPORTANT | Aucun schéma typé | Définir schémas Topic, SourceDocument, etc. | pytest |
| 13 | Pas de modèles étendus (topics, documents, claims, character_sheets) | database/models.py | IMPORTANT | Seul VideoTask existe | Ajouter tables complètes | pytest |
| 14 | Pas de modes de publication TikTok définis | publishing/interfaces.py | IMPORTANT | Seul TikTokUploader abstrait | Implémenter modes LOCAL_EXPORT, TIKTOK_DRAFT, etc. | pytest |
| 15 | Pas de gestion de la voix (Piper) | media/interfaces.py | IMPORTANT | Seuls TTSProvider, ImageProvider abstraits | Ajouter intégration Piper ou fallback | pytest |
| 16 | Pas de scripts install.ps1, test.ps1, backup.ps1, update.ps1 | scripts/ | MOYEN | Seuls init.ps1 et orchestrator.ps1 existent | Créer tous les scripts manquants | Exécution |
| 17 | Pas de documentation INSTALLATION, CONFIGURATION, RUNBOOK, etc. | docs/ | MOYEN | Seul ARCHITECTURE.md existe | Créer tous les docs requis | Vérification |
| 18 | Pas de gestion du style manga (prompts, guides) | assets/ | IMPORTANT | Dossier n'existe pas | Créer style_guides, prompts | Vérification |
| 19 | Pas de mécanisme de planification Windows | scripts/schedule.ps1 | MOYEN | Aucun scheduler | Implémenter avec tâches désactivées | Vérification |
| 20 | Pas de gestion des coûts/métriques | monitoring/ | IMPORTANT | Module inexistant | Ajouter monitoring/logs.py, costs.py | pytest |

## Fichiers à créer / modifier

### À créer (nouveaux)
- `tiktok_history_factory/config/validation.py`
- `tiktok_history_factory/database/repository.py`
- `tiktok_history_factory/database/migrations.py`
- `tiktok_history_factory/pipeline/coordinator.py`
- `tiktok_history_factory/pipeline/states.py`
- `tiktok_history_factory/pipeline/queue.py`
- `tiktok_history_factory/pipeline/checkpoints.py`
- `tiktok_history_factory/agents/topics.py`
- `tiktok_history_factory/agents/research.py`
- `tiktok_history_factory/agents/factcheck.py`
- `tiktok_history_factory/agents/writer.py`
- `tiktok_history_factory/agents/storyboard.py`
- `tiktok_history_factory/agents/editorial_qc.py`
- `tiktok_history_factory/providers/ollama_cloud.py`
- `tiktok_history_factory/providers/history_sources.py`
- `tiktok_history_factory/providers/comfyui_images.py`
- `tiktok_history_factory/providers/comfyui_wan.py`
- `tiktok_history_factory/providers/piper_tts.py`
- `tiktok_history_factory/providers/ffmpeg.py`
- `tiktok_history_factory/providers/tiktok_official.py`
- `tiktok_history_factory/providers/local_export.py`
- `tiktok_history_factory/media/characters.py`
- `tiktok_history_factory/media/prompts.py`
- `tiktok_history_factory/media/assets.py`
- `tiktok_history_factory/media/subtitles.py`
- `tiktok_history_factory/media/animations.py`
- `tiktok_history_factory/media/audio.py`
- `tiktok_history_factory/media/compositor.py`
- `tiktok_history_factory/media/metadata.py`
- `tiktok_history_factory/publishing/eligibility.py`
- `tiktok_history_factory/publishing/drafts.py`
- `tiktok_history_factory/publishing/status.py`
- `tiktok_history_factory/monitoring/logs.py`
- `tiktok_history_factory/monitoring/metrics.py`
- `tiktok_history_factory/monitoring/health.py`
- `tiktok_history_factory/monitoring/costs.py`
- `tiktok_history_factory/cli.py`
- `scripts/main.ps1`
- `scripts/install.ps1`
- `scripts/test.ps1`
- `scripts/backup.ps1`
- `scripts/update.ps1`
- `scripts/schedule.ps1`
- `scripts/doctor.ps1` (existe, corriger)
- Tous les docs (`docs/INSTALLATION.md`, `docs/CONFIGURATION.md`, `docs/RUNBOOK.md`, etc.)

### À modifier
- `README.md` (complètement réécrit)
- `.env.example` (OLLAMA_MODEL, ajouter nouvelles variables)
- `pyproject.toml` (ajouter dépendances)
- `tiktok_history_factory/config/settings.py` (ajouter LOG_LEVEL, fiabiliser chemins)
- `tiktok_history_factory/pipeline/orchestrator.py` (ne pas marquer FAILED, ajouter états)
- `tiktok_history_factory/database/models.py` (schéma étendu)
- `tests/test_placeholder.py` (vrais tests)

### Fichiers conservés sans modification majeure
- `LICENSE`
- `.gitignore`
- `MANIFEST.in`


## Correctifs du pilote réel — 19 octobre 2026

Le rapport historique ci-dessus décrit l’état antérieur. Le chemin actif est désormais `cli pilot -> PilotRunner`, avec API ComfyUI réelle, Piper français, Kimi par Ollama local, sources HTTP et checkpoints. Les abstractions d’agents et `supervisor.py` ne définissent pas ce pilote ; le superviseur legacy reste exclu du lancement. Voir le rapport FINAL_REPORT_20261019_PILOT.md pour les preuves et limites.

## Corrections V2

Ancien pilote DRAFT_REJECTED : narration FR accélérée, gravure sépia et bandeau permanent.
Défauts corrigés dans le moteur : paire EN/FR explicite, interdiction accélération,
LoRA manga testé, priorité du style dans les prompts, drawtext retiré, détection noir/clipping.
La planification automatique et la découverte autonome restent non certifiées.
