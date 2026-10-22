> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Architecture effectivement utilisée

`scripts/main.ps1` appelle le Python absolu du venv, sans installation pendant le
runtime. `cli.py pilot` sauvegarde SQLite puis sélectionne un dossier révisé.
`PipelineOrchestrator` assure l’anti-doublon par hash ; `PilotRunner` exécute :

1. Recherche : collecte HTTPS de sources explicitement autorisées, cache daté,
   extraits justificatifs contrôlés et claims liés aux références.
2. Scénario : Kimi Cloud via `/api/chat` de l’Ollama connecté. JSON textuel parsé
   localement ; le pilote interdit les ajouts au texte historique révisé.
3. Voix : WAV français Piper par scène, contrôle PCM et silence, durée mesurée,
   sous-titres alignés aux limites des phrases.
4. Images : workflow API SDXL, batch 1, seed déterministe, suivi history/view,
   contrôle PNG, métadonnées et empreinte ; inspection visuelle complémentaire.
5. Animation : Wan opt-in borné ou repli explicite FFmpeg.
6. Rendu : panoramiques/zooms, fondus, voix réelle, SRT gravé et mention IA.
7. QC : ffprobe, durée, A/V, résolution et décodage complet ; export pour revue.

`checkpoints.py` écrit les états JSON atomiquement et revérifie les fichiers par
SHA-256. Un verrou OS exclusif évite deux pilotes simultanés et se libère après
un crash du processus. Les images ont aussi leur propre état de job ComfyUI pour
retrouver une génération en cours. SQLite conserve statuts, résultats et durées.

Les données actuelles utilisent les dataclasses existantes et une validation
explicite de dossier. Le vaste schéma Pydantic du cahier initial n’est pas encore
intégralement matérialisé. La machine d’états globale et les agents de découverte
autonome restent des extensions ; le pilote réel ne dépend pas de ces interfaces.

Le statut final est `awaiting_review`, jamais publié. Les connecteurs TikTok
restent désactivés et leur implémentation distante n’est pas validée.

## Contrat bilingue V2

Pydantic `pipeline/contracts.py` valide unités EN/FR et paire de langues.
`media/bilingual_audio.py` produit WAV par unité et par scène et SRT aux frontières réelles.
Les images dépendent des champs visuels uniquement ; traduction/voix ne changent pas
leur empreinte. Checkpoints atomiques, verrou exclusif et exports immuables conservés.
