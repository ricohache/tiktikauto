# Smoke test TikTokHistoryFactory — 19 octobre 2026

## Verdict

**Test technique assemblé avec succès ; pilote manga automatisé BLOQUÉ.**
Un seul sujet : Champollion et la pierre de Rosette. Aucune production planifiée,
aucune publication, aucune installation et aucune modification des permissions.
Les fichiers source, la configuration et la base existante n'ont pas été modifiés
par cet audit. Les nouveaux artefacts sont dans `work/smoke-20261019/`.
Aucune modification importante nécessitant une sauvegarde n'a été effectuée.

## OK

- 23 tests unitaires exécutés : 23 réussis. Ils ne prouvent pas le fonctionnement
  du pipeline complet : certains tests valident explicitement ses placeholders.
- Tous les fichiers Python du package passent l'analyse syntaxique AST.
- Tous les scripts `scripts/*.ps1` passent le parseur PowerShell ; leur exécution
  complète, dont les installations et planifications, n'a pas été déclenchée.
- CLI `doctor` : Python, FFmpeg, SQLite et espace disque OK.
- SQLite existante : `PRAGMA integrity_check = ok` ; trois tâches en `created`.
  Consultation en lecture seule, sans exécuter le superviseur.
- ComfyUI `/system_stats`, `/queue`, `/object_info` : HTTP 200. RTX 4060 Laptop,
  environ 8 Go VRAM. File vide avant le test.
- Soumission réelle d'un workflow ComfyUI `EmptyImage -> SaveImage`, suivi via
  `/history`, téléchargement via `/view` : succès. Ce workflow ne fait aucune
  inférence de diffusion ; il valide le transport et l'exécution de tâches.
- Ollama `/api/tags` : HTTP 200. `phi4-mini:latest` est installé, contrairement au
  modèle local configuré `gemma3:4b`, absent de l'inventaire consulté.
- Appel réel `/api/chat` avec `phi4-mini:latest`, budget 100 tokens et timeout
  90 secondes : succès ; réponse et narration sauvegardées. Il s'agissait d'une
  consigne de restitution d'un texte historique court, pas d'une recherche autonome.
- Hugging Face : HTTP 200 sur la page d'accueil. Aucun modèle téléchargé ; cela
  ne valide pas les téléchargements de gros fichiers ni les dépôts restreints.
- Voix Windows SAPI réelle : WAV mono 22050 Hz, 11,93 s, RMS 3475 (non silencieux).
- Assemblage avec le véritable `FFmpegProvider.assemble_slideshow` : succès.
  MP4 H.264 1080x1920, AAC, vidéo 15,28 s / audio 11,93 s ; décodage intégral sans
  erreur. Carte visuelle inspectée. Écoute humaine et qualité éditoriale non validées.
- Publication désactivée, mode `LOCAL_EXPORT`.

## BLOQUÉ

- Aucun checkpoint disponible côté API ComfyUI et connecteur local. Les listes
  UNET et CLIP sont également vides : aucune pile de génération d'image prête.
  Le connecteur `generate_image` retourne `BLOCKED`.
- Piper absent du PATH et des emplacements inspectés ; aucun modèle français
  configuré (`PIPER_MODEL_PATH` vide). Seule voix SAPI détectée : Microsoft Zira
  Desktop, en-US. La lecture du français est un secours technique, pas une voix
  française validée.
- L'appel du connecteur LLM avec l'URL configurée `https://api.ollama.com/v1`
  échoue : tunnel HTTP 403. Clé API absente. Cela ne remet pas en cause le réseau
  local validé : le modèle local fonctionne via `/api/chat`.
- Wikipedia : appel HTTP et connecteur `search` échouent avec tunnel HTTP 403.
  La vérification documentaire du texte historique n'est donc pas validée.
- Le premier appel via `OllamaCloudClient` dirigé vers l'API locale a expiré
  à 60 secondes ; l'essai borné suivant via HTTP natif a abouti. La latence à froid
  doit être prise en compte, sans conclure à une panne réseau.

## À CORRIGER

1. `pipeline/orchestrator.py::run_cycle` ne produit rien : il laisse la tâche en
   `created`. Le pilote CLI ne constitue pas un pipeline fonctionnel.
2. `providers/comfyui_images.py` ne soumet pas de workflow, même avec un modèle ;
   il retourne `READY_BUT_REQUIRES_WORKFLOW`. Le connecteur Wan est aussi un
   placeholder. Les trois workflows fournis sont au format interface `nodes/links`,
   pas au format de prompt API directement soumissible.
3. Le connecteur Ollama concatène `/chat` tout en utilisant le format natif
   `options.num_predict`. Avec la base configurée `/v1`, l'URL devient `/v1/chat`.
   Choisir explicitement l'API native `/api/chat` ou un contrat compatible OpenAI.
4. `PiperTTSProvider.available` vaut à tort True avec le simple nom `piper` et un
   chemin modèle vide. Sa recherche renvoie le nom même si l'exécutable est absent.
   L'interface de synthèse doit être vérifiée contre le binaire réellement choisi.
5. `media/compositor.py` appelle `assemble_video`, méthode absente du fournisseur
   FFmpeg (qui expose `assemble_slideshow`) ; contrat de retour incompatible et
   gravure de sous-titres laissée en TODO.
6. Le MP4 du test dépasse l'audio d'environ 3,35 s malgré `-shortest` : borner
   explicitement la durée du rendu avec la durée audio mesurée.
7. `scripts/main.ps1 -Mode pilot -Topic ...` ignore `Topic`. Les scripts CLI
   doivent propager les codes d'échec. `__main__.py` ignore le retour de `main()`.
8. `doctor` ne contrôle ni les modèles ComfyUI, ni Piper, ni une inférence Ollama :
   son état OK est limité aux quatre vérifications de base.
9. `supervisor.py` possède une autre définition de `video_tasks` et une boucle
   récurrente ; ne pas l'utiliser comme pilote du schéma existant. Son pipeline
   peut annoncer un succès après un échec de génération d'image.
10. README, rapports anciens et commentaires de configuration sont périmés sur
    l'indisponibilité générale du réseau. Ils ne reflètent pas ce smoke test.

## Artefacts

- `work/smoke-20261019/smoke.mp4` : test technique, mire annotée et voix de secours.
- `narration.txt`, `ollama_response.json` : texte et réponse réelle du modèle.
- `prompts.json` : sujet, prompt manga préparé, prompt négatif et limites.
- `technical_workflow.json`, `comfy_submission.json`, `comfy_history.json` : preuve
  de soumission et de récupération ComfyUI.
- `technical_card.png`, `card.png`, `voice.wav` : médias du test.
- `assembly.json`, `ffprobe.json`, `decode.json` : résultats de rendu et contrôle.

## Prochaine action unique recommandée

**Implémenter un point d'entrée `smoke` borné à un sujet, reliant les fournisseurs
réels et refusant explicitement les prérequis absents.** Réutiliser l'API Ollama
locale validée et `assemble_slideshow`, puis y brancher la soumission ComfyUI et
la voix française. L'installation seule d'un checkpoint ne suffirait pas :
l'orchestrateur et le connecteur d'image sont encore des placeholders.
Le téléchargement d'un checkpoint et d'une voix reste un prérequis pour faire
passer ensuite ce test en véritable pilote manga français.
