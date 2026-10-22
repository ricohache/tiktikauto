# Rapport final — TikTokHistoryFactory — 2026-10-19T11:35:57.517738+02:00

| Sous-système | État | Preuve / limite |
|---|---|---|
| Infrastructure | OK | Windows-11-10.0.26300-SP0; projet Python 3.11.9; ComfyUI 0.41.0; NVIDIA GeForce RTX 4060 Laptop GPU, 596.08, 8188 MiB; RAM 31.69 Gio CPU : Intel64 Family 6 Model 183 Stepping 1, GenuineIntel |
| Recherche historique | PARTIEL | 3 sources collectées, extraits retrouvés, 4 claims avec références Dossier révisé ; découverte autonome et preuve automatique de vérité non validées |
| Ollama Cloud | OK | Kimi-k3:cloud répond via Ollama local /api/chat ; réponse réelle et usage tokens conservés Solde et quotas du compte non consultés ; aucun crédit supplémentaire acheté |
| ComfyUI manga | OK | 4 illustrations locales SDXL, PNG 768x1344 avec workflow/seed/prompt_id/SHA-256 Modèle généraliste ; esthétique seinen et détails symboliques soumis à revue humaine |
| TTS français | OK | Piper 1.8.0, SIWIS fr_FR, WAV 22050 Hz mono non silencieux Écoute humaine et prononciation de Thiaroye non certifiées par une mesure automatique |
| Animation | OK | FFmpeg réel ; essai Wan : SUCCESS Le succès technique Wan ne prouve pas sa qualité visuelle ; voir WAN_BENCHMARK.md |
| FFmpeg | OK | 1080x1920 H.264/AAC, 30 fps, 29.100 s, décodage complet sans erreur  |
| Orchestration | PARTIEL | 7 phases réelles, statuts SQLite, verrou exclusif, checkpoints SHA-256, reprise sans nouveaux médias Pilote à dossier révisé ; automatisation générale multi-sujets non certifiée |
| SQLite | OK | Base intègre, job 4 awaiting_review, historiques de phases ; sauvegardes cohérentes Trois anciennes tâches de test conservées ; aucun ancien élément supprimé |
| Pilote vidéo réel | OK | C:\TikTokHistoryFactory\output\review\thiaroye-1944-pilote\revision-7-wan-attempt\pilot.mp4 AWAITING_REVIEW ; aucune publication autorisée |

## 01. Résumé exécutif

VERDICT GLOBAL = PARTIEL. Le pilote réel est opérationnel et exporté pour revue. La chaîne autonome générale et le débit quotidien ne sont pas déclarés validés.

## 02. Machine réellement observée

Windows-11-10.0.26300-SP0; projet Python 3.11.9; ComfyUI 0.41.0; NVIDIA GeForce RTX 4060 Laptop GPU, 596.08, 8188 MiB; RAM 31.69 Gio
CPU : Intel64 Family 6 Model 183 Stepping 1, GenuineIntel
Python ComfyUI : 3.13.14 (tags/v3.13.14:fd17997, Jun 10 2026, 13:03:48) [MSC v.1944 64 bit (AMD64)]
PyTorch : 2.14.0+cu130

## 03. État initial et sauvegardes

Base initiale : smoke test existant, aucun modèle image ni voix FR, connecteurs incomplets. Sauvegarde avant modifications : C:\TikTokHistoryFactory\backups\pilot-20261019-094855. Sauvegardes supplémentaires : backups/before-pilot-*, pilot-before-visual-revision-03, pilot-before-visual-revision-04 et pilot-before-final-render. Le dépôt racine n’est pas Git ; aucune initialisation de distant.

## 04. Fichiers créés ou corrigés

- MODIFIED : .env — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : .env.example — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : .gitignore — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\piper-1.8.0-COPYING — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\sdxl-LICENSE.md — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\sdxl-LICENSE.md.provenance.json — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\sdxl-README.md — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\sdxl-README.md.provenance.json — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\siwis-MODEL_CARD.md — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\siwis-MODEL_CARD.md.provenance.json — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\wan-Apache-2.0.txt — Pilot integration, verification or documentation; see subsystem reports
- CREATED : assets\licenses\wan-Apache-2.0.txt.provenance.json — Pilot integration, verification or documentation; see subsystem reports
- CREATED : data\subjects\thiaroye-1944.json — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\ARCHITECTURE.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\AUDIT_LEGACY.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\COMFYUI.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\CONFIGURATION.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\FACT_CHECKING.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\INSTALLATION.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\LICENCES.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\QUALITY.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\RUNBOOK.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : docs\SECURITY.md — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : pyproject.toml — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : README.md — Pilot integration, verification or documentation; see subsystem reports
- CREATED : requirements-lock.txt — Pilot integration, verification or documentation; see subsystem reports
- CREATED : scripts\acquire_pilot_assets.py — Pilot integration, verification or documentation; see subsystem reports
- CREATED : scripts\build_final_report.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : scripts\main.ps1 — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : scripts\orchestrator.ps1 — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : scripts\schedule.ps1 — Pilot integration, verification or documentation; see subsystem reports
- CREATED : tests\test_pilot_contracts.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tests\test_providers.py — Pilot integration, verification or documentation; see subsystem reports
- CREATED : tests\test_real_pilot.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\__main__.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\cli.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\config\settings.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\database\models.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\media\animations.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\media\compositor.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\media\prompts.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\media\subtitles.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\monitoring\health.py — Pilot integration, verification or documentation; see subsystem reports
- CREATED : tiktok_history_factory\pipeline\checkpoints.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\pipeline\orchestrator.py — Pilot integration, verification or documentation; see subsystem reports
- CREATED : tiktok_history_factory\pipeline\pilot.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\providers\comfyui_images.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\providers\comfyui_wan.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\providers\ffmpeg.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\providers\history_sources.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\providers\local_export.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\providers\ollama_cloud.py — Pilot integration, verification or documentation; see subsystem reports
- MODIFIED : tiktok_history_factory\providers\piper_tts.py — Pilot integration, verification or documentation; see subsystem reports
- CREATED : workflows\comfyui\pilot_sdxl_api.json — Pilot integration, verification or documentation; see subsystem reports
- CREATED : workflows\comfyui\wan22_5b_api.json — Pilot integration, verification or documentation; see subsystem reports
Liste des sources, scripts, dépendances et licences ; les médias et poids sont détaillés aux sections 5, 6 et 12. Caches Python et copies de sauvegarde exclus de cette liste. Aucune donnée utilisateur supprimée. .env contient des valeurs privées et reste exclu des exports.

## 05. Arborescence des livrables réels

output\review\thiaroye-1944-pilote\revision-7-wan-attempt\animation\clip.mp4
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\animation\clip.wan.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\animation\clip.workflow.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\animation\visual-review.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\artifact_hashes.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\audio\scene-01.wav
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\audio\scene-02.wav
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\audio\scene-03.wav
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\audio\scene-04.wav
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\caption.txt
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\characters.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\contact-sheet.jpg
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\cover.jpg
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\CREDITS.txt
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\manifest.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-01-v3.generation.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-01-v3.png
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-02-v3.generation.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-02-v3.png
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-03-v4.generation.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-03-v4.png
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-04-v3.generation.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\media\scene-04-v3.png
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\pilot.mp4
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\qc.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\scenario.txt
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\sources.md
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\storyboard.json
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\subtitles.ass
output\review\thiaroye-1944-pilote\revision-7-wan-attempt\subtitles.srt

## 06. Modèles, provenance et licences

SDXL officiel, 6 938 078 334 octets, révision 462165984030d82259a11f4367a4eed129e94a7b, Open RAIL++-M. Voix SIWIS 63 201 294 octets, CC-BY 4.0. Wan : 18 144 966 705 octets, Apache 2.0, détails et SHA-256 dans wan-model-evaluation.json. Vérifications locales consignées dans les .provenance.json. Piper GPL-3.0. Polices Windows seulement rasterisées. Aucun modèle NSFW spécialisé installé. Voir docs/LICENCES.md.

## 07. Fournisseurs et limites

Kimi Cloud par la passerelle existante http://127.0.0.1:11434/api/chat ; aucun réglage global modifié. ComfyUI local, Piper local CPU, montage local FFmpeg. Sources publiques et Hugging Face. Aucun service payant à l’usage ajouté. Solde du forfait inconnu.

## 08. Déroulement du pilote

- Assemblée nationale, question au gouvernement n°259 et réponse ministérielle, décembre 2024 : https://questions.assemblee-nationale.fr/q17/17-259QG.htm
- Martin Mourre, Thiaroye 1944, Presses universitaires de Rennes, notice de l'éditeur, 2017 : https://pur-editions.fr/product/8410/thiaroye-1944
- Wikipedia, Massacre de Thiaroye, introduction et références : https://fr.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&exintro=1&format=json&titles=Massacre_de_Thiaroye
Scénario français source-verrouillé, 4 scènes symboliques sans gore ni chiffre de victimes. PNG réels, fiche personnage composite, narration Piper, SRT/ASS alignés aux phrases, animation Wan+FFmpeg, MP4 et QC. Les illlustrations ne constituent pas des archives.

## 09. Tests exacts et codes de sortie

{
  "exit_code": 0,
  "log": "reports/tests-final.log",
  "command": "$env:THF_INTEGRATION='1'; .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v",
  "scope": "Unit tests including explicit mocks, plus integration checks of real pilot files",
  "timestamp": "2026-10-19T11:35:06.9365642+02:00",
  "count": 41,
  "other_observed_commands": [
    {
      "command": "& .\\scripts\\main.ps1 -Mode Doctor",
      "exit_code": 0,
      "result": "7 health checks OK"
    },
    {
      "command": "& C:\\TikTokHistoryFactory\\scripts\\main.ps1 -Mode Resume -JobId 4",
      "cwd": "C:\\",
      "exit_code": 0,
      "result": "All seven stages resumed without regeneration"
    },
    {
      "command": ".\\.venv\\Scripts\\python.exe -m tiktok_history_factory pilot --try-wan --work-dir C:\\TikTokHistoryFactory\\work\\pilot-thiaroye-1944",
      "exit_code": 0,
      "result": "Real 17-frame Wan generation and valid final MP4"
    },
    {
      "command": "PowerShell Parser::ParseFile on scripts/*.ps1; Python ast.parse on package/tests",
      "exit_code": 0,
      "result": "No syntax error in final checked sources"
    }
  ]
}
Tests API native/compatible OpenAI et erreurs OOM/timeout : simulations unitaires explicitement identifiées. Les tests d’intégration lisent les médias réels. Le test technique de SaveVideo à deux images unies est seulement un contrôle de contrat, jamais appelé vidéo Wan.

## 10. Récapitulatif des exigences

Voir REQUIREMENTS_MATRIX.md et .csv. Les lignes PARTIAL ne sont pas présentées comme terminées ; les exigences TikTok et production restent désactivées.

## 11. Benchmark réel

Images retenues, secondes de génération par fichier : [20.11, 20.11, 20.16, 22.11]. Le premier essai initial a pris 26,23 s, sans OOM. Pic VRAM SDXL non échantillonné, non inventé. Wan : SUCCESS, temps 86.48 s. Télémétrie GPU brute dans clip.wan.json si disponible. Les clips FFmpeg et la voix sont chronométrés dans run_history ; pas de capacité 3/jour déduite de ce seul épisode.

## 12. Fichiers livrés

Vidéo : C:\TikTokHistoryFactory\output\review\thiaroye-1944-pilote\revision-7-wan-attempt\pilot.mp4
Dossier complet : C:\TikTokHistoryFactory\output\review\thiaroye-1944-pilote\revision-7-wan-attempt
Preuves et médias intermédiaires : C:\TikTokHistoryFactory\work\pilot-thiaroye-1944
Licences : C:\TikTokHistoryFactory\assets\licenses

## 13. Coûts

Aucun achat, aucun abonnement nouveau, aucune API TTS/image à l’usage. Usage de l’abonnement Ollama existant dans sa connexion actuelle ; tokens retournés par les appels conservés, solde non connu. Énergie totale et facture électrique non mesurées. KWH_PRICE_EUR configurable ; une mesure GPU seule ne représente pas la consommation complète du PC.

## 14. Publication TikTok

NON PUBLIÉ. Aucun appel API TikTok, aucun upload, aucune tâche quotidienne créée ou activée. Exports locaux exclusivement destinés à une revue humaine.

## 15. Auto-corrections

Route Ollama corrigée ; API image réelle ; détection Piper fiable ; vrai stdin TTS et contrôle silence ; compositeur compatible ; boucle pilote et checkpoint ; sauvegarde DB ; anti-doublon SQL ; export bloqué sans fichier ; sous-titre résiduel corrigé ; anachronismes visuels rejetés ; résolution ASS explicite après inspection du MP4 ; tests d’intégration et de reprise. Un test a échoué à cause d’une indentation puis a été corrigé et relancé. Un lien de licence Wan absent du dépôt de poids a été remplacé par le texte officiel du dépôt Wan-Video.

## 16. Risques et restes à faire

IMPORTANT : revue humaine du style manga seinen, des accessoires, de la diction et des sources avant diffusion. IMPORTANT : recherche autonome multi-sujets, machine d’états exhaustive, Pydantic généralisé et planification réellement certifiée restent partiels. IMPORTANT : outils legacy supervisor.py et anciens générateurs ne doivent pas servir de lanceur ; schéma SQLite incompatible et boucle récurrente. MINEUR : découpage de sous-titres à la phrase, sans alignement mot à mot. Aucun blocage critique pour lire le pilote livré.

## 17. Démonstration reproductible

& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Doctor
& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Resume -JobId 4
& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Export
La reprise conserve les étapes validées. Ajouter --try-wan à la commande Python seulement pour le mode optionnel documenté. Le menu est disponible sans argument.

## 18. Conditions avant trois vidéos quotidiennes

Validation explicite du pilote par le propriétaire ; validation de plusieurs dossiers indépendants ; mesure du débit complet, incidents et reprises ; contrôle des quotas ; horaires choisis par le propriétaire ; concurrence GPU 1 ; tests de charge. Aucun horaire imposé ni production quotidienne déclenchée.

## 19. Adéquation à la demande

Vrai pilote historique français de 20–30 s, quatre dessins 2D détaillés et déclarés IA, non graphiques, médias réellement produits. Style guidé seinen, à valider humainement : SDXL généraliste ne garantit pas chaque détail. Chaîne pilote fonctionnelle ; autonomie documentaire générale non certifiée. Le test synthétique antérieur reste distinct et n’est pas livré comme pilote réel.

## 20. Prochaine action humaine unique

Visionner et écouter le pilote livré, puis valider ou préciser les corrections de style, d’histoire et de diction. Aucune activation de cadence ou de publication n’est demandée ici.

## Ce que je n’ai pas pu vérifier

Écoute humaine, certification d’une restitution historique visuelle exacte, fidélité stylistique garantie, solde Ollama, facture électrique et débit quotidien durable. Aucun compte TikTok testé.
