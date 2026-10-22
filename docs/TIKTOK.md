> V2 active au 19/10/2026 : narration EN, sous-titres FR, aucun bandeau IA permanent. Le pilote V1 est DRAFT_REJECTED. Les déclarations IA restent dans la caption et les métadonnées.

# TikTok — Publication

## Etat actuel

- **Mode par defaut** : LOCAL_EXPORT (aucun appel API)
- **Publication reelle** : BLOQUEE par defaut
- **API officielle** : Necessite compte Developpeur approuve

## API TikTok

### Requis
- Compte Developpeur TikTok
- Application avec scopes `video.upload` et/ou `video.publish`
- Consentement utilisateur (OAuth)
- Client Key / Client Secret

### Limites
- Clients non verifies : visibilite privee possible
- Quotas stricts sur les uploads
- Contenu AIGC : mention obligatoire si applicable

## Modes implementes

1. **LOCAL_EXPORT** (actif) : MP4 + manifeste JSON, import manuel
2. **TIKTOK_DRAFT** (bloque) : Brouillon via API si credentials
3. **TIKTOK_PRIVATE** (bloque) : Upload prive si autorise
4. **TIKTOK_PUBLIC** (JAMAIS sans consentement explicite)

## Actions humaines requises

- Creer compte Developpeur TikTok
- Soumettre application pour approbation
- Configurer .env avec credentials
- Activer TIKTOK_PUBLISH_ENABLED=true manuellement
- Valider chaque publication
