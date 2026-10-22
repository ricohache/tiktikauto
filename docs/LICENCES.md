> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Provenance et licences vérifiées — pilote

| Ressource | Origine et licence | Utilisation |
|---|---|---|
| SDXL base 1.0 | https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0 ; CreativeML Open RAIL++-M | Généraliste officiel, génération locale dessinée ; respecter les restrictions d’usage |
| Piper 1.8.0 | https://github.com/OHF-Voice/piper1-gpl ; GPL-3.0 | Exécutable local séparé ; pas de redistribution du runtime dans le MP4 |
| SIWIS fr_FR medium | https://huggingface.co/rhasspy/piper-voices ; fiche du modèle : données CC-BY 4.0 | Attribution dans CREDITS.txt ; voix synthétique indiquée |
| Wan 2.2 5B | https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged ; Apache 2.0 déclaré | Installation/essai selon rapport ; pas de 14B |
| Arial Windows | https://learn.microsoft.com/en-us/typography/fonts/font-faq | Texte rasterisé dans vidéo/image, fichiers de police non distribués |
| Musique | Aucune | Aucun morceau tiers ni bruitage de violence |

SDXL est un choix généraliste contrôlé ; Animagine 3.1 a été écarté parce que sa
fiche mentionne explicitement un entraînement/capacité NSFW. Aucun modèle NSFW
spécialisé ni checkpoint d’origine inconnue n’a été installé.

Révision SDXL : `462165984030d82259a11f4367a4eed129e94a7b`.
SHA-256 poids : `31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b`.
Révision voix : `c10ece1aade47bb51c153c893d14e5bf8e5b7117`.
SHA-256 voix : `641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99`.
Révision Wan : `ee6f4a40737a995bf5818954cfce6d59443b0f04`.
Tailles et empreintes Wan : `reports/wan-model-evaluation.json`.

SIWIS : Yamagishi, Junichi ; Honnet, Pierre-Edouard ; Garner, Philip ; Lazaridis,
Alexandros (2017), *The SIWIS French Speech Synthesis Database, 2016*, University
of Edinburgh, https://doi.org/10.7488/ds/1705 .
Licence : https://creativecommons.org/licenses/by/4.0/ . Transformation : synthèse
vocale par le modèle Piper français, non imitation d’une personne identifiée.

Les textes de licences et fiches consultés sont conservés dans `assets/licenses/`.
Les documents historiques sont des références, pas des photographies réutilisées.
Leur collecte locale ne confère pas un droit de redistribuer intégralement des
œuvres protégées. Le dossier exporté contient références et courts extraits.

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
