# Benchmark Wan 2.2 TI2V 5B — 19 octobre 2026

**Essai réel réussi techniquement.** Référence : première illustration SDXL du pilote.
Un seul appel GPU Wan ; aucun essai OOM répété. Aucune modification ComfyUI globale.

| Mesure | Résultat |
|---|---:|
| Modèle | wan2.2_ti2v_5B_fp16.safetensors |
| Résolution native | 480 × 832 |
| Images / cadence / durée | 17 / 8 fps / 2,125 s |
| Sampling | 12 étapes, uni_pc, simple, CFG 5, shift 8 |
| Seed | 19441201 |
| Temps total du job | 86.48 s |
| Pic mémoire utilisée de la carte entière | 7022.0 Mio |
| Pic utilisation GPU | 100.0 % |
| Pic puissance GPU observée | 95.77 W |
| Pic température observée | 87.0 °C |
| Échantillons GPU | 21 |
| ffprobe / décodage complet | réussis |

Encodeur UMT5 chargé sur CPU ; offloading natif ComfyUI. Les trois poids ont été
vérifiés par SHA-256 publié avant l’essai. RAM libre avant le job :
11.79 Gio. Le pic RAM total n’a pas été échantillonné.
La mémoire GPU inclut l’affichage et les autres allocations de la carte ; elle ne
mesure pas exclusivement les tenseurs Wan. Les températures n’ont été mesurées
que pendant cet essai bref, pas lors d’une charge durable.

## Contrôle visuel et choix

Trois images extraites à 0, 1 et 2 secondes ont été inspectées. Le dessin reste
cohérent, sans nouvelle personne ni violence graphique. Le mouvement est très
subtil ; aucune animation riche n’est revendiquée. Cette inspection technique par
l’agent ne remplace pas l’approbation de l’utilisateur.

Le pilote Wan+FFmpeg contient ce clip de 2,125 s au début du premier plan, puis
maintient sa dernière image pour couvrir la phrase. Les autres plans utilisent
les mouvements FFmpeg. La variante entièrement FFmpeg utilise des zooms et des
panoramiques sur les quatre images et conserve davantage leur résolution.
Les deux variantes sont réelles, distinctes et conservées pour comparaison.

- Wan brut : `work/pilot-thiaroye-1944/wan/clip.mp4`
- Variante Wan : `output/review/thiaroye-1944-pilote/revision-6-wan-attempt/pilot.mp4`
- Variante FFmpeg : `output/review/thiaroye-1944-pilote/revision-6/pilot.mp4`
- Télémétrie et workflow : `work/pilot-thiaroye-1944/wan/clip.wan.json`, `clip.workflow.json`

Le téléchargement initial de 18,14 Go n’est pas inclus dans les 86,48 s du job.
Aucune capacité de trois épisodes/jour ni stabilité thermique prolongée n’est
certifiée par ce seul essai. En cas d’échec ou de délai >600 s, le fournisseur
annule uniquement son propre job et l’orchestrateur choisit FFmpeg.
