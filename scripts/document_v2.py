"""Update operational documentation without rewriting archived V1 reports."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
banner = '> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.\n\n'
for p in (root/'docs').glob('*.md'):
    t=p.read_text(encoding='utf-8')
    if not t.startswith('> V2 active'):
        p.write_text(banner+t,encoding='utf-8')
p=root/'README.md'
t=p.read_text(encoding='utf-8').replace('pilote historique français','pilote historique avec narration anglaise et sous-titres français').replace('Piper SIWIS français','Piper John anglais, SDXL + LoRA LineAniRedmond V2').replace('Resume -JobId 4','Resume -JobId 5').replace('Durée admise : 20–30 secondes, mesurée sur la vraie voix.', 'Durée cible : 20–30 secondes sur la vraie voix, sans accélération. Une diction naturelle peut justifier un dépassement documenté.').replace('output/review/thiaroye-1944-pilote/','output/review/thiaroye-1944-v2/').replace('work/pilot-thiaroye-1944/','work/pilot-thiaroye-1944-v2/')
p.write_text(banner+t,encoding='utf-8')
p=root/'docs/QUALITY.md'
p.write_text(banner+'''# Contrôle qualité V2

Le contrat validé par Pydantic est `schema_version=2`, `audio_language=en`,
`spoken_language=en-US/en-GB`, `subtitle_language=fr-FR`, `translation_locale=fr-FR`.
Les dossiers historiques V1 restent lisibles, mais le nouveau moteur vocal exige la paire V2.

- Voix locale : anglais réel, longueur Piper >=1, aucun `atempo` ni étirement temporel.
- Débit cible 120–145 mots/minute ; garde technique 110–150. Comptage des mots anglais
  avec séparation des traits d’union, sur durée des vrais WAV ; pauses ajoutées de 250 ms.
- Traduction française relue, un WAV par unité sémantique. Les frontières des sous-titres
  viennent des nombres d’échantillons, pas d’un alignement estimé mot à mot.
- SRT/ASS UTF-8, deux lignes maximum de 40 caractères. Taille ASS 54 px sur canevas
  1080×1920 ; marge basse 260 px, latérales 70 px. Visages composés dans la partie haute.
- MP4 H.264/yuv420p, AAC/48000 Hz, 1080×1920/30 fps ; décalage A/V <=0,15 s.
- RMS non nul, mesure du pic et du clipping PCM ; clipping >0,1% bloqué.
- `blackdetect` sur tout le film : noir >=98% des pixels sur >=0,04 s bloqué.
  Les anciens fondus au noir ont été retirés ; mouvement doux Ken Burns conservé.
- Décodage complet du MP4 ; génération PNG réelle, dimensions, métadonnées et SHA.
- Aucun filtre drawtext de bandeau permanent. Commentaire MP4/caption transparents sur l’IA.
- Cache SHA et empreintes d’entrées. Traduction modifiée : pas d’invalidation des images.

Le moteur ne peut pas prouver seul l’intelligibilité à l’oreille ni la fidélité historique
des dessins. Le lexique `Thiaroye -> Tya-roy` est une approximation audio à écouter,
pas une transcription phonétique certifiée. Le style, les détails vestimentaires et
la ressemblance du personnage composite restent soumis à revue humaine.
Aucune acceptation artistique du propriétaire n’est enregistrée.

Tests : `THF_INTEGRATION=1` puis `python -m unittest discover -s tests -v`.
Les mocks API sont séparés des vérifications de médias réels.
''',encoding='utf-8')
p=root/'docs/CONFIGURATION.md'
t=p.read_text(encoding='utf-8').replace('Modèle SIWIS fr_FR sous `tools/piper/voices/`', '`tools/piper/voices/en_US-john-medium.onnx`, voix EN ; aucune sélection automatique FR')
t+='''
## Paramètres V2

`SPOKEN_LANGUAGE=en-US`, `SUBTITLE_LANGUAGE=fr-FR`, `TRANSLATION_LOCALE=fr-FR`,
`TTS_LENGTH_SCALE=1.0`, `COMFYUI_LORA=LineAniRedmondV2-Lineart-LineAniAF.safetensors`,
`COMFYUI_LORA_STRENGTH=1.0`, `PILOT_DOSSIER=data/subjects/thiaroye-1944-v2.json`.
La voix française installée est conservée pour les anciens essais. Les nouvelles
vidéos utilisent la paire V2 ; le fournisseur bloque une voix de langue incompatible.
Les versions de sortie sont distinctes ; ne pas réutiliser un chemin PNG après changement
de prompt : augmenter `image_revision` pour la scène concernée.
'''
p.write_text(t,encoding='utf-8')
p=root/'docs/LICENCES.md'
t=p.read_text(encoding='utf-8')+'''
## Ajouts V2 vérifiés avant acquisition

- Auteur ArtificialGuyBR : [LineAniRedmond V2](https://huggingface.co/artificialguybr/LineAniRedmond-LinearMangaSDXL-V2),
  commit `411d5335378c13e63bf0d5376b405a39e9a869cb`, CreativeML OpenRAIL-M déclaré
  dans la fiche de l’auteur ; LoRA SDXL Base, 170540028 octets,
  SHA256 `1692a2c7d285f6c94b7910bc8f8ec2758163ba2710214bd35bb20cc94d2488c8`.
  Fiche spécialisée manga lineart, aucun objectif NSFW annoncé ; contenu exact du jeu
  d’entraînement non fourni. Aucun artiste vivant ciblé. Les restrictions OpenRAIL
  et celles de la base SDXL restent applicables.
- Voix `en_US-john-medium` et `en_US-kristin-medium`, dépôt officiel
  [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices).
  Fiches individuelles archivées dans assets/licenses : données LibriVox domaine public.
  Kristin entraînée de zéro ; John ajustée depuis Kristin. Pas de nouvelle collecte
  de voix ni clonage d’une personne sur demande. Repo MIT, runtime Piper 1.8 GPL-3.0.
  Versions/tailles/SHA du dépôt consignées dans les `.provenance.json`.
- Lessac, Ryan et voix ajustées depuis une base de licence restrictive : non retenues.
- Pydantic 2.13.5 MIT, installé uniquement dans le venv du projet.

Aucun achat ou nouvelle API payante. Pas de musique ajoutée.
'''
p.write_text(t,encoding='utf-8')
for name, addition in {
 'RUNBOOK.md': '\n## Reprise V2\n\n`C:\\TikTokHistoryFactory\\scripts\\main.ps1 -Mode Pilot` utilise le dossier V2.\n`-Mode Resume -JobId 5` reprend le pilote V2 ; `-Dossier` permet de préciser un dossier.\nExport local uniquement, fichiers sous output/review/thiaroye-1944-v2/.\nAnciennes versions préservées, ne pas utiliser le job 4 pour une nouvelle vidéo V2.\n',
 'COMFYUI.md': '\n## Comparaison V2\n\n`python scripts/compare_v2.py` : même seed 19441204, 768×1344, 28 pas DPM++2M/Karras, CFG7.\nBase puis LoRA 0,7/1,0. Workflows complets dans les fichiers generation.json.\nLa première comparaison trop photographique est conservée ; la seconde place les\nconsignes manga avant la scène. Choix agent : LoRA1,0, sous réserve de revue utilisateur.\n',
 'FACT_CHECKING.md': '\n## Traduction V2\n\nLe dossier Thiaroye V2 réutilise les trois sources et quatre claims vérifiés du pilote.\nNarration anglaise et traduction française appariées par unité, sans chiffre de morts,\nordre nominatif ni dialogue inventé. Les personnages et objets sont illustratifs.\nLeur mémoire demeure est une conclusion commémorative, pas une citation historique.\n',
 'ARCHITECTURE.md': '\n## Contrat bilingue V2\n\nPydantic `pipeline/contracts.py` valide unités EN/FR et paire de langues.\n`media/bilingual_audio.py` produit WAV par unité et par scène et SRT aux frontières réelles.\nLes images dépendent des champs visuels uniquement ; traduction/voix ne changent pas\nleur empreinte. Checkpoints atomiques, verrou exclusif et exports immuables conservés.\n',
 'AUDIT_LEGACY.md': '\n## Corrections V2\n\nAncien pilote DRAFT_REJECTED : narration FR accélérée, gravure sépia et bandeau permanent.\nDéfauts corrigés dans le moteur : paire EN/FR explicite, interdiction accélération,\nLoRA manga testé, priorité du style dans les prompts, drawtext retiré, détection noir/clipping.\nLa planification automatique et la découverte autonome restent non certifiées.\n',
 'INSTALLATION.md': '\n## Installation V2 locale\n\n`python scripts/acquire_v2_assets.py` acquiert deux voix EN et un LoRA de 171 Mo,\navec versions et SHA éditeur. Les modèles SDXL/Wan existants ne sont pas téléchargés à nouveau.\nAucune modification Windows, Ollama ou Codex. Dépendances venv figées dans requirements-lock.txt.\n'
}.items():
 p=root/'docs'/name
 p.write_text(p.read_text(encoding='utf-8')+addition,encoding='utf-8')
print('V2 operational documentation updated')
