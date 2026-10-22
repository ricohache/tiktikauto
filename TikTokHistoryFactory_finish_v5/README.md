# TikTokHistoryFactory — paquet de finalisation V5

**Il s'agit d'un outil de reprise, pas du MP4 final.** Le dossier Windows `C:\TikTokHistoryFactory` et les PNG/WAV sources ne sont pas disponibles dans l'environnement distant utilisé pour préparer ce paquet. Ce paquet ne prétend pas avoir rendu ou vérifié la vidéo historique sur la machine de l'utilisateur.

## Modifications par rapport à V4

- 22 plans à partir des **11 sources Emi2 V3** et de 11 illustrations complémentaires générées localement. Les illustrations V3 ne sont jamais remplacées.
- Prompts complémentaires centrés sur les personnages/objets. **Cadrages individuels configurables** dans `framing-v5.json` avec crop/zoom contrôlé. Le cadrage des personnes doit encore être revu sur les captures réelles.
- Voix anglaise naturelle produite localement avec la voix Piper du projet ; **pas d'accélération**, ni bande son silencieuse utilisée comme substitut. Le script s'arrête si la narration dépasse la durée disponible.
- Sous-titres français en Arial gras ~70 px, deux lignes max, texte blanc, contour noir, position basse sécurisée (marge 360 px), sans pavé opaque.
- Séparation explicite des images sources et de `concat_video_v2.mp4`, qui a des sous-titres brûlés et aucune voix : **ce MP4 n'est jamais utilisé comme média d'entrée**.
- Extrait de contrôle H.264/AAC, `review/control-excerpt.mp4`, produit et vérifié **avant** le rendu intégral. Trois captures de cet extrait disponibles dans `review/control-frames`.
- Validation FFprobe (codec, dimensions, FPS, durée, pistes), FFmpeg (décodage complet), **volumedetect** sur l'audio réellement rendu, contrôle structurel ASS/SRT, SHA256 du MP4 et rapport JSON.
- Storyboard JSON horodaté avec sources et cadrages, SRT, ASS, planche JPG et rapport qualité. Ce pipeline est réutilisable pour d'autres épisodes, avec adaptation du scénario et des prompts.
- Préserve le dossier V3 et le paquet V4. Ne modifie pas Codex, Ollama Cloud, les modèles ComfyUI, ni les permissions `tiktoknet`. Aucun service payant, aucune publication.

## Installation sur le PC disposant des médias originaux

1. Extraire cette archive dans `C:\TikTokHistoryFactory\tools\`. Elle crée `C:\TikTokHistoryFactory\tools\TikTokHistoryFactory_finish_v5\`.
2. Ouvrir PowerShell et lancer :

```powershell
& 'C:\TikTokHistoryFactory\tools\TikTokHistoryFactory_finish_v5\run_v5.ps1' -Project 'C:\TikTokHistoryFactory'
```

Lorsque Piper est hors du projet, préciser les chemins **réels** : `-Piper '...\piper.exe' -Voice '...\en_US_....onnx'`. Vérifier que l'environnement Python existant dispose de Pillow, que FFmpeg/libass et FFprobe sont dans le PATH et que ComfyUI a accès à `emi-2.safetensors`.

Pour auditer sans rendre, depuis le dossier extrait :

```powershell
python .\finish_pilot.py --project 'C:\TikTokHistoryFactory' --preflight
```

Un mode de test sur deux scènes est également disponible (`--test`). L'exécution normale utilise les 11 scènes. Si 11 images secondaires V5 sont déjà valides, `-SkipImageGeneration` évite le démarrage de ComfyUI.

## Emplacements attendus APRÈS exécution réelle (non vérifiés ici)

`C:\TikTokHistoryFactory\output\pilot-thiaroye-1944-90s-v5\`

- `thiaroye-1944-90s-v5-final.mp4` — vidéo **uniquement après** vérification réussie.
- `review\control-excerpt.mp4`, `review\control-frames\` — extrait de contrôle avant le rendu intégral.
- `storyboard-v5.json`, `storyboard-v4.jpg` — plans horodatés et planche de contrôle.
- `images\SC01_B.png` ... `SC11_B.png` — illustrations secondaires (les 11 originales restent dans V3).
- `audio\narration_english_v4.wav` et WAV par scène.
- `subtitles\subtitles-fr.srt`, `subtitles-fr.ass`, `timings.json`.
- `metadata\finish-report.json`, `metadata\shots.json`, `metadata\sources.json`, `metadata\framing-used.json`.
- `QC_REPORT.md`, `logs\` — contrôles techniques et historique d'exécution.

## Éléments non automatiquement certifiés

- Exactitude historique et absence d'anachronismes sur les dessins ; contrôle éditorial requis.
- Correspondance mot à mot des sous-titres avec la diction anglaise : la segmentation se base sur les **durées des scènes et la proportion de mots**, pas sur un alignement phonétique forcé ; un contrôle à l'écoute est donc requis.
- Placement exact par rapport aux futurs changements de l'interface TikTok et lisibilité sur smartphone.
- `volumedetect` confirme un signal audio mesurable, **pas** la justesse linguistique de la narration.

## Tests déjà réalisés hors du PC utilisateur

- Tests unitaires synthétiques FFmpeg/Pillow/ASS/volumedetect : **PASS**.
- Test de bout en bout avec **deux illustrations fictives par scène et audio sinusoïdal de test** : **PASS** (MP4 9,0 s, 4 plans, piste audio détectée, sous-titres 2 lignes, extrait préliminaire, SHA256, décodage sans erreur). Ce n'est **pas** un test sur Thiaroye ni un MP4 à publier.
