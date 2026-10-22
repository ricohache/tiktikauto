> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# Securite

## Secrets

- Tous les tokens/cles dans `.env` (non versionne)
- Aucun secret dans le code source
- `.env.example` sans valeurs reelles

## Acces locaux

- ComfyUI : 127.0.0.1 uniquement (jamais 0.0.0.0)
- Pas de tunnel, pas d'exposition Internet
- SQLite locale, pas de serveur externe

## Publication

- LOCAL_EXPORT par defaut (aucun appel API)
- TIKTOK_PUBLIC jamais active sans consentement
- Pas de bot, pas de Selenium, pas de contournement
- Pas de cookie vole ni simulation de clic

## Budget

- Aucune depense externe pendant le pilote
- Ollama Cloud : respecter les quotas existants
- Estimation electrique configurable

## Mise a jour

- Pas de mise a jour globale Windows/Pilotes sans accord
- Environnement venv isole
- Pas de modification systeme


## Pilote du 19 octobre 2026

Aucune modification de Codex, tiktoknet, des réglages globaux Ollama ni des protections Windows. Les autorisations d’exécution ponctuelles de téléchargement ne modifient pas ces réglages. Les sauvegardes peuvent contenir le `.env` privé et restent exclues des exports et de Git. Les sources HTTPS sont limitées à des hôtes explicitement autorisés, redirections bornées, taille maximale 8 Mio. Les médias API ont aussi une limite de taille. Les sorties du pilote restent AWAITING_REVIEW et ne sont jamais envoyées à TikTok.
