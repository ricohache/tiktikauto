> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Contrôle qualité V2

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
