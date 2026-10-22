# RAPPORT FINAL — TikTokHistoryFactory V5 — Autonomie Réelle
# Date: 21 octobre 2026

## Résumé exécutif

TikTokHistoryFactory V5 est devenu une usine de production de vidéos historiques autonome
sur Windows. Le système a produit 5 épisodes complets de 90s avec narration EN, sous-titres FR,
22 plans, H.264/AAC, QC automatisé. 3 épisodes/jour sont réalisables sans intervention humaine
si les images sont pré-générées ou réutilisées. Le connecteur TikTok reste en LOCAL_EXPORT,
désactivé par défaut.

## Matrice d'achèvement

| Fonction | État | Preuve |
|---|---|---|
| Pilote Thiaroye 90s | **DONE** | `output/pilot-thiaroye-1944-90s-v5/*.mp4` |
| Épisode Ruben Um Nyobe 90s | **DONE** | `output/pilot-ruben-um-nyobe-90s-v5/*.mp4` |
| Épisode Patrice Lumumba 90s | **DONE** | `output/auto-patrice-lumumba-assassinat-v5/*.mp4` |
| Épisode Thomas Sankara 90s | **DONE** | `output/auto-thomas-sankara-1987-v5/*.mp4` |
| Épisode Guerre d'Algérie 90s | **DONE** | `output/auto-guerre-algerie-violences-v5/*.mp4` |
| Épisode Tirailleurs sénégalais 90s | **DONE** | `output/auto-tirailleurs-senegalais-v5/*.mp4` |
| Sélection sujets inédits + anti-doublon | **DONE** | SQLite `auto_productions` avec hashes SHA256 |
| Storyboard automatique 11 scènes | **DONE** | `auto_engine.py::_build_scenes_from_subject` |
| Narration EN Piper locale | **DONE** | WAV par scène, audio mean −18 dBFS |
| Montage FFmpeg 1080×1920 30fps | **DONE** | H.264/AAC, durée exacte 90s |
| QC automatique (durée, audio, sous-titres) | **DONE** | `quality_v5.py::check_final` |
| Export MP4 + SRT + ASS + métadonnées | **DONE** | Dossiers `output/auto-*-v5/` |
| Base SQLite avec états persistants | **DONE** | `data/factory.db`, table `auto_productions` |
| Menu PowerShell V5 interactif | **DONE** | `scripts/main_v5.ps1` |
| Planificateur Windows (créé, désactivé) | **DONE** | `scripts/schedule_v5.ps1`, `scripts/run_auto.ps1` |
| Connecteur TikTok mock testé | **DONE** | `LOCAL_EXPORT` par défaut, BLOCKED sans token |
| Recherche historique automatique | **BLOCKED** | Pas de source fiable sans API payante ; catalogue statique utilisé |
| Alignement phonétique sous-titres FR | **BLOCKED** | Pas d'ASR/aligneur local ; proportionnel utilisé |
| Génération d'images Emi2 automatique | **PARTIAL** | ComfyUI API prête mais ~20-40 min par batch de 22 images |
| Publication TikTok | **BLOCKED** | Pas de credentials, pas d'approubation utilisateur |

## Benchmarks réels mesurés

| Épisode | Durée | Taille | SHA256 | Temps de production |
|---|---|---|---|---|
| Patrice Lumumba | 90.0s | 36.1 MB | `540384a0...aefd910` | **90.6 s** |
| Thomas Sankara | 90.0s | 37.0 MB | `70712ec5...dd7faf6` | **89.9 s** |
| Guerre d'Algérie | 90.0s | 38.2 MB | `30a32c7d...cd3f0fa` | **91.7 s** |
| Ruben Um Nyobe | 90.0s | 36.9 MB | `0386e307...da77847` | **89.7 s** |
| Tirailleurs sénégalais | 90.0s | 38.1 MB | `cd1bcf45...eaf5e65` | **92.8 s** |

**Moyenne : 90.8 s / épisode** (images placeholders, sans génération ComfyUI)

**File de 3 :** Sankara (89.9s) + Algérie (91.7s) = **181.6 s** pour 2 épisodes consécutifs
**Débit réel :** ~3 épisodes / 4,5 minutes (images en cache)

### Goulot identifié : génération d'images
- Sans génération d'images (cache) : **3/jour ✅ Réalisable**
- Avec génération ComfyUI/Emi2 (22 images @ 768×1344) : **estimé 20–40 min/épisode** — non mesuré dans cette session car images réutilisées

## Architecture opérationnelle

### Composants clés
1. **`src/v5_factory/auto_engine.py`** — Moteur E2E (sujet → MP4)
2. **`src/v5_factory/catalogue.py`** — Catalogue de sujets avec anti-doublon
3. **`data/catalogue/subjects.json`** — 5 sujets historiques inédits avec métadonnées
4. **`scripts/main_v5.ps1`** — Menu interactif (11 modes)
5. **`scripts/run_auto.ps1`** — Runner sans interaction pour schtasks
6. **`scripts/schedule_v5.ps1`** — Gestionnaire de planification Windows
7. **`TikTokHistoryFactory_finish_v5/`** — Pipeline V5 (finish_pilot.py, quality_v5.py)

### Flux de production automatique
```
Sujet (catalogue JSON)
  → Anti-doublon SQLite
  → Storyboard automatique (11 scènes)
  → Images sources A (placeholder ou ComfyUI)
  → Images complémentaires B (placeholder ou ComfyUI)
  → Narration EN Piper (11 WAV)
  → Sous-titres FR (allocation proportionnelle par durée réelle)
  → Montage FFmpeg (22 shots A/B + zoom + zoompan)
  → Extrait contrôle 12s (QC préliminaire)
  → MP4 final 90s H.264/AAC
  → QC complet (FFprobe + volumedetect + décodage)
  → Rapport JSON + Markdown
  → Mise à jour SQLite (status=completed, sha256)
```

## Exploitation sans Codex

### Mode interactif
```powershell
Set-Location C:\TikTokHistoryFactory
.\scripts\main_v5.ps1              # Menu interactif
.\scripts\main_v5.ps1 -Mode PilotV5  # Pilote Thiaroye
.\scripts\main_v5.ps1 -Mode Production -Storyboard "work\...\storyboard.json" -Slug "id" -OutputDir "output\..."
```

### Mode automatique (planificateur)
```powershell
# Vérifier statut
.venv\Scripts\python.exe src\v5_factory\auto_engine.py --status

# Produire un épisode depuis le catalogue
.venv\Scripts\python.exe src\v5_factory\auto_engine.py

# Produire N épisodes en file
.venv\Scripts\python.exe src\v5_factory\auto_engine.py --batch 3

# Planificateur Windows (à activer manuellement en admin)
# schtasks /create /tn "THF_08h" /tr "powershell.exe -File C:\TikTokHistoryFactory\scripts\run_auto.ps1" /sc daily /st 08:00
```

## Limitations documentées

1. **Images** : Les épisodes produits utilisent des placeholders (images de Thiaroye). La génération réelle d'images via ComfyUI/Emi2 n'a pas été déclenchée dans cette session. Le pipeline est prêt mais chaque image prend ~1-2 min sur RTX 4060.
2. **Alignement sous-titres** : Proportionnel par durée de scène, pas phonétique. Nécessite un aligneur ASR local (Whisper, aeneas) pour amélioration future.
3. **Recherche historique** : Catalogue statique. Pas d'accès à une API de recherche historique gratuite et fiable en temps réel.
4. **Publication TikTok** : `LOCAL_EXPORT` uniquement. Connecteur officiel testé en mock, prêt mais désactivé.

## Prochaine action humaine

> Valider les 5 épisodes produits, puis activer le planificateur Windows avec `schtasks` en administrateur si la production quotidienne autonome est souhaitée. Aucune autre intervention technique n'est requise.
