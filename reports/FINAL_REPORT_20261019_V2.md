# Rapport final V2 — TikTokHistoryFactory

Date: 2026-10-19T10:24:09.717415+00:00

## 01. Résumé exécutif

VERDICT GLOBAL = PARTIEL. Nouveau pilote réel livré, technique conforme au contrat EN/FR. Qualité artistique et diction non acceptées au nom du propriétaire. Aucun upload.

## 02. Machine observée

RTX4060 Laptop 8GB, pilote596.08; RAM34029125632 octets dans system_stats; Windows 10.0.26300; Python 3.11.9; ComfyUI0.41.0, torch2.14.0+cu130, Piper1.8.0, Pydantic2.13.5. Disque libre à la livraison: 124.2 GiB. CPU détaillé: inventaire V1 conservé, pas remesuré par CIM (accès refusé).

## 03. État initial et sauvegardes

V1 préservé comme DRAFT_REJECTED. File ComfyUI vide et aucun .part trouvé avant travail. Inventaire processus via CIM refusé; contrôle de file et fichiers effectué. Sauvegardes V2: C:\TikTokHistoryFactory\backups\v2-before-20261019-115710, C:\TikTokHistoryFactory\backups\v2-before-art-correction, C:\TikTokHistoryFactory\backups\v2-before-final-art-20261019, C:\TikTokHistoryFactory\backups\v2-before-scene-corrections-20261019. Backups SQLite avant chaque exécution.

## 04. Fichiers créés/modifiés/supprimés

Inventaire et SHA dans le JSON changes. Principaux: settings, Piper, prompts, ComfyUI LoRA, compositeur, contrats Pydantic, bilingue, pilote, CLI, main.ps1, tests, docs. Dossier sujet V2 ajouté, ancien intact. Aucun fichier utilisateur supprimé. Les rapports V1 restent archivés.

## 05. Arborescence finale

Code réutilisé sous tiktok_history_factory; sources data/subjects; travail work/pilot-thiaroye-1944-v2; livrables C:\TikTokHistoryFactory\output\review\thiaroye-1944-v2\revision-3; import manuel C:\TikTokHistoryFactory\output\ready\5_v2_final.mp4; comparaisons work/v2-comparison*; rapports reports/*V2* et tests-v2.*.

## 06. Modèles et licences

SDXL Base officiel existant + LineAniRedmond V2 auteur ArtificialGuyBR, commit411d5335378c13e63bf0d5376b405a39e9a869cb, LoRA170540028 octets, OpenRAIL-M. SDXL OpenRAIL++ conservé. John/Kristin: fiches LibriVox domaine public, repo MIT, John depuis Kristin entraînée de zéro. Wan Apache2 existant. Toutes provenances/tailles/SHA dans assets/licenses et .provenance.json. Pas de garantie sur les droits de chaque donnée image d’entraînement non publiée.

## 07. Fournisseurs et budget

ComfyUI localhost8188 GPU; Piper CPU venv; Kimi cloud via Ollama localhost11434/api/chat, compte existant. Aucun paramètre global modifié. Deux voix et LoRA acquis gratuitement; Pydantic installé seulement dans venv. Commandes autorisées hors sandbox pour CDN et tests, sans changement du profil réseau.

## 08. Pipeline réel

Thiaroye1944: trois sources, quatre claims, narration EN en huit unités FR appariées, quatre PNG768x1344, voix22.533s, 123.05 mots/minute sans changement de tempo. Images finales versions3/2/3/2. Wan17images480x832, FFmpeg1080x1920/30fps/H264/AAC, SRT/ASS, QC et export. Personnage fictif composite; décor et tasse illustratifs.

## 09. Tests et commandes

51 tests réussis, dont mocks explicitement nommés et huit tests intégration médias réels; zéro skip final. Journal tests-v2.log. Suite lancée trop tôt pendant Wan: échec conservé tests-v2-inflight.*, puis corrigé par attente de fin, sans assouplir les tests. Permission temporaire os.replace vérifiée hors sandbox. AST PowerShell0erreur; compileall0; doctor0; reprise0; détails commandes dans JSON.

## 10. Matrice exigences

Matrice A–U conservée avec réserves générales et complétée par exigences V2, preuves et limites. DONE ne signifie pas acceptation esthétique. Publication et planification restent désactivées; automatisation de nouveaux sujets non certifiée.

## 11. Benchmark

{"status": "SUCCESS", "seconds": 78.31, "width": 480, "height": 832, "frames": 17, "fps": 8, "samples": 19, "peak_observed_gpu_memory_mib": 6958.0, "max_observed_temperature_c": 88.0, "scope": "Whole-GPU samples every ~4 seconds; not a continuous allocation peak or electricity meter", "fallback": "C:\\TikTokHistoryFactory\\output\\review\\thiaroye-1944-v2\\revision-3\\pilot.mp4", "wan_alternative": "C:\\TikTokHistoryFactory\\output\\review\\thiaroye-1944-v2\\revision-3-wan-attempt\\pilot.mp4", "source": "C:\\TikTokHistoryFactory\\work\\pilot-thiaroye-1944-v2\\wan\\clip.wan.json"}. Historique des temps par phase dans JSON pilot.phases. CPU/RAM peak non mesurés pour toute la mission; température et VRAM Wan sont des échantillons, pas des pics continus.

## 12. Livrables

C:\TikTokHistoryFactory\output\review\thiaroye-1944-v2\revision-3 : pilot.mp4, narration-en.wav, voice-manifest.json, subtitles.srt/.ass, scenario.txt, translation-fr.txt, storyboard.json, media/PNG et graphes, sources.md, caption.txt, CREDITS, manifest, qc, contact-sheet, review-frames et comparatif ancien/nouveau. Variante Wan: C:\TikTokHistoryFactory\output\review\thiaroye-1944-v2\revision-3-wan-attempt\pilot.mp4

## 13. Coûts

Achat externe nouveau: 0€. Abonnement Ollama existant utilisé, quota restant non lu. Électricité non mesurée au compteur; toute estimation doit utiliser tarif configuré et puissance machine entière, pas seulement GPU. Aucune nouvelle API payante.

## 14. TikTok

NON PUBLIÉ. Aucun compte connecté, upload/draft/scheduler lancé. SQLite tâche5 awaiting_review, IDs de publication vides. Import manuel possible techniquement après acceptation; vérification des règles de plateforme requise avant publication future.

## 15. Auto-corrections

Première comparaison trop photographique: priorité donnée au style dans le prompt. Deux scènes refusées à la revue: arbre photographique avec silhouettes et porche évoquant un décor japonais; seules ces scènes régénérées. Accélération FR supprimée; voix EN explicite et refus du fallback FR. Paragraphes remplacés par unités bilingues; filtre IA retiré; fondus noirs retirés; QC blackdetect/clipping; dépendances visuelles séparées de la traduction. Tests de régression ajoutés.

## 16. Risques et restes

IMPORTANT — Propriétaire: juger style et écoute; agent ne peut certifier une écoute humaine. Historien/relecteur: vêtements/décor génériques non certifiés comme reconstruction exacte. IMPORTANT — Développeur: découverte indépendante de sujets, tous contrats métier Pydantic et schéma DB/migrations générales restent partiels; seules les entrées bilingues sont strictement validées. Planificateur3/jour non finalisé et non activé. MINEUR — débit de lecture variable, nom Thiaroye approximé par lexique. Aucun blocage technique du pilote courant.

## 17. Démonstration reproductible

Set-Location C:\TikTokHistoryFactory ; .\scripts\main.ps1 -Mode Doctor ; .\scripts\main.ps1 -Mode Resume -JobId 5 ; .\scripts\main.ps1 -Mode Export . Reprise à entrées identiques: sept phases réutilisées, aucune nouvelle génération. --try-wan explicite uniquement si souhaité; même clip repris par empreinte.

## 18. Passage à trois vidéos/jour

NON ACTIVÉ. Nécessite validation humaine du pilote, sujets/sources nouveaux indépendants, tests de charge60–90s, quotas Cloud, budget disque et disponibilité PC, horaires explicites, GPUconcurrence1. Un pilote22.53s ne certifie pas cette cadence; machine éteinte ne produit rien.

## 19. Adéquation et ce qui reste non vérifié

Historique illustrée en manga, pas histoire du manga. EN audio et FR traduit réels, budget externe0, exports locaux. Non vérifié: acceptation esthétique, écoute humaine de la diction, exactitude archivistique du décor/vêtement, autonomie tous sujets, charge quotidienne, API TikTok réelle, électricité mesurée. Le candidat ne doit pas être appelé production autonome complète.

## 20. Prochaine action humaine unique

Regarder et écouter le pilote V2 pour accepter ou préciser le style manga, la voix et la prononciation de Thiaroye.

## Tableau final

| Composant | Existant avant | Modification V2 | Test réel | Résultat | Preuve | Risque résiduel |
|---|---|---|---|---|---|---|
| Sources/Kimi | Sources and native Kimi working | Claims retained; source-locked English script with reviewed French translation | Cached source SHA/excerpts + actual Kimi response | OK / REAL | work/pilot-thiaroye-1944-v2/research; script/llm-response.json | Human editorial review; no automatic truth proof |
| English voice | French accelerated voice rejected | Piper John, utterances, no acceleration | Actual WAV 123.05 WPM; PCM verified | OK technique / revue écoute requise | narration-en.wav; voice-manifest.json | Proper names and naturalness not certified by agent listening |
| French captions | Long whole-sentence blocks | Eight translated units, <=2 lines, exact WAV boundaries | Actual SRT/ASS and 8 extracted caption frames | OK / REAL | subtitles.srt; subtitles.ass; subtitles-review.jpg | Reading rates vary; one unit ~18.9 chars/s, date intentionally slower |
| Manga | Sepia engraving rejected | Verified manga LoRA, two comparisons, final corrections | Real PNG/graph/SHA + visual inspection | PARTIAL / CANDIDATE | contact-sheet.jpg; editorial-review.json | Owner acceptance and archive-level wardrobe/building fidelity pending |
| Compositor | Permanent AI drawtext banner | Filter removed; disclosure in metadata/caption | Real command log, decode and full blackdetect | OK / REAL | render/ffmpeg-log.json; qc.json | Future platform rules must be checked before any publication |
| Wan/fallback | V1 real Wan installed | One new I2V test, paired FFmpeg-only export | Actual Wan 78.31s; full decode | OK / REAL | reports/WAN_BENCHMARK_V2.json | Very subtle 2.125s clip; 8GB requires offload |
| Resume/CLI | Atomic checkpoints and SQLite | Bilingual inputs, visual-only dependencies, new job5 | Seven RESUMED stages from C:\, exit0 | OK / REAL | tests-v2.log; checkpoints.json | General subject discovery and full production scheduling still incomplete |
| TikTok/scheduler | Disabled | Remain disabled | Default configuration tests, SQLite no publication ID | BLOQUÉ volontairement | tests-v2.log; DB job5 | No account authorization or daily-production acceptance |

VERDICT : PARTIEL — pilote réel livré ; revue artistique et écoute requises.

Regarder et écouter le pilote V2 pour accepter ou préciser le style manga, la voix et la prononciation de Thiaroye.