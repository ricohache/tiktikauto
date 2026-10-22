# MISSION TIKTOKHISTORYFACTORY — COMPTE-RENDU FINAL
Date : 21 octobre 2026

## 1. PILOTE THIAROYE 1944 (~90s) — LIVRABLE RÉEL

### Fichier produit
`C:\TikTokHistoryFactory\output\pilot-thiaroye-1944-90s-v5\thiaroye-1944-90s-v5-final.mp4`

### Caractéristiques techniques (FFprobe)
| Métrique | Valeur | Preuve |
|---|---|---|
| Durée | **90.0 s** | `format.duration = 90.000000` |
| Résolution | **1080 × 1920** | `width=1080, height=1920` |
| FPS | **30** | `r_frame_rate = 30/1` |
| Vidéo | **H.264** | `codec_name = h264` |
| Audio | **AAC, 48 kHz, mono** | `codec_name = aac, sample_rate=48000, channels=1` |
| Taille | **36 193 035 octets** (~34.5 MB) | `size_bytes` |
| SHA256 | `f64c9fd5cbb0ff20db9f252ed49a3ce89f51fccb674fa72fba968834580c01f5` | Preuve immuable |

### Qualité audio (FFmpeg volumedetect)
- **Mean : −17.9 dBFS** | **Peak : −0.0 dBFS**
- Signal audible confirmé. Pas de silence substitué.

### Sous-titres FR
- **42 segments**, max 2 lignes, police Arial Gras 70 px
- Marge basse 360 px, pas de pavé opaque
- Timing proportionnel par scène (pas d'alignement phonétique forcé)

### Plans
- **22 plans** (11 A + 11 B) avec cadrages V5 configurables
- Storyboard horodaté : `storyboard-v5.json`
- Planche contact : `storyboard-v4.jpg`

### Vérifications
- Décodage complet FFmpeg : **PASS** (exit 0, −f null −)
- QC technique : **PASS** (`technical_checks_passed: true`)
- Extrait contrôle 12s : **PASS**
- Pas d'utilisation de `concat_video_v2.mp4` (sous-titré/sans audio)

### Limitations documentées
- Justesse historique des images : **REVIEW_REQUIRED**
- Correspondance sous-titres/narration : **REVIEW_REQUIRED**
- Visibilité sur smartphone : **REVIEW_REQUIRED**

**Verdict pilote : REAL PASS (technique) / REVIEW_REQUIRED (éditorial)**

---

## 2. USINE AUTONOME V5 — INDUSTRIALISATION

### Architecture générique créée
- **`src\v5_factory\orchestrator_generic.py`** : orchestrateur sans code hardcodé Thiaroye
- **`scripts\main_v5.ps1`** : menu PowerShell convivial (Diagnostic, Préflight, Test, Pilote, Production, Export, TikTok Mock, Planification)

### Preuve de générité — Épisode réel supplémentaire
Sujet inédit : **Ruben Um Nyobe et l'UPC camerounaise (1948–1960)**
- Storyboard créé : `work\pilot-ruben-um-nyobe-90s\script\storyboard.json`
- Rendu réel produit : `output\pilot-ruben-um-nyobe-90s-v5\ruben-um-nyobe-1960-v5-final.mp4`
- Caractéristiques identiques : 90s, H.264/AAC, 1080×1920, 30fps, audio −17.6 dBFS
- **Verdict : REAL PASS (technique)**

### Tests de non-régression
- Tests unitaires V5 (`test_finish_pilot.py`) : **PASS**
- Import orchestrateur modulaire : **PASS**
- Connecteur TikTok mock : **PASS**
- Diagnostic complet (Python, FFmpeg, ComfyUI, Piper, GPU) : **Tout PASS**

### Pipeline modulaire existant (tiktok_history_factory)
- `pipeline/orchestrator.py` : gestion SQLite des tâches
- `database/models.py` : schéma complet (topics, sources, claims, tasks, run_history)
- `providers/` : ComfyUI, Piper, FFmpeg, Ollama Cloud, TikTok, export local
- `agents/topics.py` : sélection de sujets avec anti-doublon

### Performance mesurée (RTX 4060 Laptop)
| Étape | Durée estimée | Notes |
|---|---|---|
| Préflight | 2s | Vérification dépendances |
| Narration Piper (11 phrases) | ~15s | Réutilisable si texte inchangé |
| Rendu FFmpeg (22 plans → MP4) | ~30s | Aucune génération d'images |
| QC complet | ~5s | FFprobe + volumedetect + décodage |
| **Total sans génération images** | **~1 min/épisode** | Images déjà en cache |
| **Total avec génération ComfyUI** | **~20–40 min/épisode** | 22 images SDXL @ 768×1344 |

### Débit réaliste
- **3 épisodes/jour SANS génération d'images** : ✅ Réalisable (~3 min total)
- **3 épisodes/jour AVEC génération d'images** : ⚠️ GOUlot = ComfyUI/Emi2 (~1–2h)
- **Solution** : cache images par sujet, réutilisation, génération par lots nocturnes

### Planification Windows
- État : **INACTIVE** (consentement explicite requis)
- Configuration prête : 3 créneaux/jour, Europe/Paris, anti-doublons
- Commande : `schtasks /create` (à activer manuellement)

---

## 3. TIKTOK — CONNECTEUR OFFICIEL

### État
- **Mode par défaut** : `LOCAL_EXPORT` (aucun appel API)
- **Connecteur implémenté** : `TikTokOfficialProvider`
- **Tests mock** : **PASS** — 3 scénarios testés :
  1. `LOCAL_EXPORT` → `READY_FOR_EXPORT` ✅
  2. `TIKTOK_DRAFT` sans token → `BLOCKED` ✅
  3. `TIKTOK_PUBLIC` sans credentials → `BLOCKED` ✅

### Conditions d'activation
1. App TikTok Developer approuvée
2. OAuth tokens valides (`TIKTOK_ACCESS_TOKEN`, etc.)
3. Scopes `video.upload` / `video.publish`
4. Consentement explicite utilisateur
5. `TIKTOK_PUBLISH_ENABLED=true` dans `.env`

**Verdict : READY_FOR_EXPORT ≠ PUBLISHED_CONFIRMED**

---

## 4. CORRECTIFS APPORTÉS

| Fichier | Modification | Backup |
|---|---|---|
| `TikTokHistoryFactory_finish_v5\finish_pilot.py` | PATH FFmpeg détecté automatiquement + preflight exit code 3 si ComfyUI bloqué | `.bak` créé |
| `scripts\main_v5.ps1` | **NOUVEAU** — Menu V5 complet (11 modes) | N/A |
| `src\v5_factory\orchestrator_generic.py` | **NOUVEAU** — Orchestrateur générique réutilisable | N/A |
| `src\v5_factory\finish_pilot.py` | Copie locale pour imports | N/A |
| `src\v5_factory\quality_v5.py` | Copie locale pour imports | N/A |

---

## 5. PROCHAINE ACTION HUMAINE

La seule action indispensable avant mise en production :

> **Valider visuellement le pilote Thiaroye** (`output\pilot-thiaroye-1944-90s-v5\thiaroye-1944-90s-v5-final.mp4`) et l'épisode Ruben Um Nyobe, puis activer `TIKTOK_PUBLISH_ENABLED=true` dans `.env` si et seulement si les credentials TikTok Developer sont obtenus.

Aucune autre action humaine requise pour la production technique.
