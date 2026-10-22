> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Configuration du pilote

Les seules valeurs modifiées sont celles du `.env` du projet, sauvegardé avant
modification. `.env.example` contient les valeurs publiques et aucun secret.

| Variable | Usage |
|---|---|
| OLLAMA_BASE_URL | `http://127.0.0.1:11434/api`, route native de l’installation connectée |
| OLLAMA_MODEL | `kimi-k3:cloud`, abonnement existant, quota réel non lu |
| OLLAMA_API_KEY | Vide pour la passerelle locale ; jamais dans les rapports |
| COMFYUI_BASE_URL | `http://127.0.0.1:8188` |
| COMFYUI_CHECKPOINT | `sd_xl_base_1.0.safetensors` |
| PIPER_MODEL_PATH | `tools/piper/voices/en_US-john-medium.onnx`, voix EN ; aucune sélection automatique FR |
| PILOT_DOSSIER | Dossier JSON révisé sous `data/subjects/` |
| PILOT_TRY_WAN | `false` par défaut ; `pilot --try-wan` effectue un seul essai borné |
| TIKTOK_PUBLISH_ENABLED | `false` ; aucune publication depuis le pilote |
| TIKTOK_PUBLISH_MODE | `LOCAL_EXPORT` |
| KWH_PRICE_EUR | Prix utilisé pour une estimation, pas une facture mesurée |

Le fournisseur LLM différencie `/api/chat` natif et `/v1/chat/completions` compatible
OpenAI. Ne pas utiliser l’ancienne URL `api.ollama.com/v1/chat`. Aucun réglage global
Ollama/Codex ni fichier de connexion n’a été modifié.

Les temps d’inférence sont bornés : image 900 s ; essai Wan 600 s ; TTS 120 s ;
Kimi 120 s. Le pilote interdit les retries infinis et ne bascule pas sur une API payante.

## Paramètres V2

`SPOKEN_LANGUAGE=en-US`, `SUBTITLE_LANGUAGE=fr-FR`, `TRANSLATION_LOCALE=fr-FR`,
`TTS_LENGTH_SCALE=1.0`, `COMFYUI_LORA=LineAniRedmondV2-Lineart-LineAniAF.safetensors`,
`COMFYUI_LORA_STRENGTH=1.0`, `PILOT_DOSSIER=data/subjects/thiaroye-1944-v2.json`.
La voix française installée est conservée pour les anciens essais. Les nouvelles
vidéos utilisent la paire V2 ; le fournisseur bloque une voix de langue incompatible.
Les versions de sortie sont distinctes ; ne pas réutiliser un chemin PNG après changement
de prompt : augmenter `image_revision` pour la scène concernée.
