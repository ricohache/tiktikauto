# Tests de finalisation V5 — 20 octobre 2026

## Contexte

Tests effectués dans un conteneur Linux isolé, **sans** accès au PC `C:\TikTokHistoryFactory`. Les visuels et la narration de ces tests sont entièrement **synthétiques** : ils ne démontrent ni l'existence ni la conformité du pilote historique définitif.

## Résultats vérifiés

| Contrôle | Résultat |
| --- | --- |
| Compilation Python des modules | PASS |
| Découpage des sous-titres (2 lignes max) | PASS |
| Police ASS grasse 70 px / contour / marge 360 px | PASS |
| Allocation exacte des trames | PASS |
| Rendu d'images fictives en H.264 vertical | PASS |
| Incrustation ASS libass et présence SRT | PASS |
| Vérification signal sonore avec `volumedetect` | PASS, pic synthétique -18 dBFS |
| `ffprobe` H.264/AAC, 1080 × 1920, 30 FPS | PASS |
| Décodage FFmpeg sans erreur | PASS |
| Exécution synthétique de bout en bout sur deux scènes | PASS |
| Durée de sortie synthétique de bout en bout | 9,0 s — **pas 90 s** |
| Nombre de plans du test de bout en bout | 4 — **pas 22** |
| Production réelle sur les PNG Emi2 et la voix du PC | **NON EFFECTUÉE : sources inaccessibles** |

## Condition pour déclarer le pilote terminé

`C:\TikTokHistoryFactory\output\pilot-thiaroye-1944-90s-v5\thiaroye-1944-90s-v5-final.mp4` doit exister réellement sur le PC source et `metadata\finish-report.json` doit contenir `test=false` et `qc.technical_checks_passed=true`. Le rendu doit ensuite être revu visuellement et à l'écoute avec `QC_REPORT.md` et les captures de `review\`.
