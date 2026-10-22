> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Images et animation locales

ComfyUI portable existant : `ComfyUI/ComfyUI`, API `127.0.0.1:8188`.
Le Python embarqué et PyTorch/CUDA de cette instance sont conservés.

Le fournisseur construit le workflow API `pilot_sdxl_api.json` : checkpoint,
deux encodeurs de texte, latent, KSampler, décodage VAE et SaveImage.
768×1344, batch 1, 28 étapes, DPM++ 2M/Karras, CFG 7. Seeds et prompt_id sont
consignés dans chaque `.generation.json` et dans le PNG ComfyUI.

Les graphes `manga_*.json` hérités sont des graphes d’éditeur ; ils ne sont pas
envoyés directement à `/prompt`. Les nouveaux graphes `*_api.json` sont destinés
à l’API. La soumission attend une vraie sortie history/view et vérifie le fichier.

Les essais ont montré des anachronismes malgré les prompts : une inspection est
obligatoire. Les versions rejetées sont conservées et les plans corrigés utilisent
des cadrages simples sans identité historique inventée.

Wan optionnel : graphe natif 5B issu du template officiel installé, shift 8,
uni_pc/simple, batch 1, 480×832, 17 images, 12 étapes, 8 images/s. Encodeur texte
sur CPU et gestion mémoire native ComfyUI. Échéance 600 s ; annulation uniquement
du job concerné via l’API jobs, puis repli FFmpeg. Rapport réel dans
`reports/WAN_BENCHMARK.md`. Un modèle installé ne vaut pas un benchmark réussi.

Référence : https://docs.comfy.org/tutorials/video/wan/wan2_2

## Comparaison V2

`python scripts/compare_v2.py` : même seed 19441204, 768×1344, 28 pas DPM++2M/Karras, CFG7.
Base puis LoRA 0,7/1,0. Workflows complets dans les fichiers generation.json.
La première comparaison trop photographique est conservée ; la seconde place les
consignes manga avant la scène. Choix agent : LoRA1,0, sous réserve de revue utilisateur.
