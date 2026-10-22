> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Exploitation et reprise

```powershell
& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Doctor
& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Pilot
& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Status
& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Resume -JobId 4
& C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Export
```

Ces commandes fonctionnent depuis un autre dossier. Le job 4 est celui du pilote
créé dans cet environnement ; consulter Status si la base change. `-Topic` doit
correspondre au titre/slug du dossier. Un autre sujet requiert un dossier révisé
passé à `-Dossier`, pas une narration improvisée et non sourcée.

Sans argument : menu numéroté. `-Mode Test` lance unittest. Pour contrôler aussi
les vrais fichiers du pilote :

```powershell
Set-Location C:\TikTokHistoryFactory
$env:THF_INTEGRATION='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`-Mode TestImage` : une image GPU, avec reprise. `-Mode TestWan` : un seul essai
Wan de 17 images, 480×832, 12 étapes, 8 images/s. Le pilote avec essai optionnel :

```powershell
.\.venv\Scripts\python.exe -m tiktok_history_factory pilot --try-wan
```

La durée `-DurationSeconds 25` du lanceur est une cible indicative ; l’acceptation
reste une durée réellement mesurée entre 20 et 30 s. `-Publish:$true` est refusé.
Production et planification restent bloquées. Aucune tâche Windows n’a été créée.

Le pilote conserve les étapes valides et les preuves dans `work/`. Ne pas effacer
les checkpoints pour corriger un détail graphique : incrémenter la révision du
plan et conserver les anciens fichiers. Un export différent requiert une nouvelle
révision ; les exports précédents ne sont pas remplacés silencieusement.

Avant intervention sur la base : sauvegarde SQLite cohérente via `backup()`.
Ne pas utiliser `supervisor.py` : son schéma et sa boucle historique sont distincts.
`scripts/orchestrator.ps1` est maintenant un alias du lanceur, sans pip au runtime.

## Reprise V2

`C:\TikTokHistoryFactory\scripts\main.ps1 -Mode Pilot` utilise le dossier V2.
`-Mode Resume -JobId 5` reprend le pilote V2 ; `-Dossier` permet de préciser un dossier.
Export local uniquement, fichiers sous output/review/thiaroye-1944-v2/.
Anciennes versions préservées, ne pas utiliser le job 4 pour une nouvelle vidéo V2.
