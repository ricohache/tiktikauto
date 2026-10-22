> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# TikTokHistoryFactory

Production locale d’un pilote historique avec narration anglaise et sous-titres français, illustré à l’encre en direction
manga seinen. Aucun upload, aucune cadence quotidienne activée.

Le pilote Thiaroye utilise de vraies images SDXL sur RTX 4060, Piper John anglais, SDXL + LoRA LineAniRedmond V2,
Kimi Cloud via Ollama existant, des sources collectées et un montage FFmpeg vertical.
Les variantes rejetées et les sauvegardes sont conservées. Le rendu reste soumis à
une revue humaine historique, visuelle et de diction ; aucun portrait n’identifie une victime.

```powershell
Set-Location C:\TikTokHistoryFactory
.\scripts\main.ps1 -Mode Doctor
.\scripts\main.ps1 -Mode Pilot
.\scripts\main.ps1 -Mode Status
.\scripts\main.ps1 -Mode Resume -JobId 5
.\scripts\main.ps1 -Mode Export
```

Sans argument, le lanceur affiche un menu. Le pilote reprend les étapes dont les
empreintes sont inchangées ; il n’entraîne pas une nouvelle série quotidienne.
Durée cible : 20–30 secondes sur la vraie voix, sans accélération. Une diction naturelle peut justifier un dépassement documenté. Les images sont générées
en 768×1344, puis recadrées et rendues en 1080×1920 à 30 images/s.

Les livrables sont dans `output/review/thiaroye-1944-v2/` et les preuves dans
`work/pilot-thiaroye-1944-v2/`. Le rapport final identifie la révision à examiner.

## Limites confirmées

- Le pilote est borné à un dossier historique révisé. La recherche autonome de
  nouveaux sujets, sans contrôle éditorial, n’est pas validée.
- SDXL officiel est un modèle généraliste : la fidélité du style et des détails
  historiques exige une inspection ; les premiers essais anachroniques ont été rejetés.
- Wan est optionnel et dispose d’un repli FFmpeg explicite. Son état réel figure
  dans `reports/WAN_BENCHMARK.md` ; aucune réussite n’est déduite de sa seule installation.
- Pas de publication TikTok ni de planificateur activé. Le débit de trois vidéos
  quotidiennes n’est pas certifié.
- Les interfaces abstraites et outils anciens ne sont pas tous des implémentations
  opérationnelles. Utiliser le lanceur et le pilote documentés, pas `supervisor.py`.

Voir [installation](docs/INSTALLATION.md), [exploitation](docs/RUNBOOK.md),
[licences](docs/LICENCES.md), [qualité](docs/QUALITY.md) et les rapports dans `reports/`.
