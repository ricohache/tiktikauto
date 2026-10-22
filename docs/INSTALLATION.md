> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Installation locale du pilote

État du 19 octobre 2026 : ComfyUI portable et FFmpeg existants réutilisés.
Python du projet : `.venv/Scripts/python.exe`, indépendant du Python embarqué ComfyUI.
Piper 1.8.0 et Pillow 12.0.0 sont installés dans ce venv ; `requirements-lock.txt`
consigne les dépendances réellement installées. Aucune modification Windows globale.

```powershell
Set-Location C:\TikTokHistoryFactory
.\scripts\main.ps1 -Mode Doctor
# Seulement pour réparer/réinstaller les dépendances du projet :
.\scripts\main.ps1 -Mode Install
```

Le mode Install n’installe ni ComfyUI, ni FFmpeg, ni pilotes. Il utilise PyPI pour
le venv puis `scripts/acquire_pilot_assets.py` pour les modèles officiels épinglés.
Les téléchargements sont écrits en `.part`, vérifiés par taille et SHA-256 avant
renommage. Réserve disque minimale : 15 Gio au-delà des poids à télécharger.
Une interruption conserve les fichiers partiels ; la reprise HTTP utilise Range.

SDXL : `ComfyUI/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors`, 6 938 078 334 octets.
Voix : `tools/piper/voices/fr_FR-siwis-medium.onnx` et son `.json`, 63 201 294 octets
pour les poids. Licences et provenance dans `assets/licenses/` et les fichiers `.provenance.json`.

Wan optionnel : `python scripts/acquire_pilot_assets.py --wan` avec le Python du
venv. Les trois fichiers totalisent 18 144 966 705 octets ; ne pas installer de 14B.
Le diagnostic des seuls modèles ne prouve pas la réussite d’une inférence.

Les restrictions éventuelles d’un domaine de téléchargement doivent passer par
le mécanisme d’autorisation normal. Ne pas modifier `tiktoknet` ni Codex.

## Installation V2 locale

`python scripts/acquire_v2_assets.py` acquiert deux voix EN et un LoRA de 171 Mo,
avec versions et SHA éditeur. Les modèles SDXL/Wan existants ne sont pas téléchargés à nouveau.
Aucune modification Windows, Ollama ou Codex. Dépendances venv figées dans requirements-lock.txt.
