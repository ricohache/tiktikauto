# THF Media Worker — Cloudflare Worker pour Buffer

Ce Worker expose une URL HTTPS stable et immuable pour chaque vidéo MP4
stockée dans le bucket R2 privé `tiktokhistoryfactory-media`.

## Principe de sécurité

- Le bucket R2 reste **privé**. Aucune politique publique.
- Seules les clés explicitement listées dans `ALLOWED_KEYS` sont servies.
- Aucune écriture (PUT/DELETE) n’est possible via l’URL publique.
- Les secrets R2 ne quittent jamais l’infrastructure Cloudflare.

## Prérequis

- Node.js ≥ 18
- Compte Cloudflare (forfait gratuit suffisant)
- Bucket R2 existant : `tiktokhistoryfactory-media`
- Wrangler CLI installé globalement : `npm install -g wrangler`
- Authentification Wrangler : `wrangler login`

## Déploiement

```bash
cd src/cloudflare_worker/thf-media-worker
npm install
wrangler deploy
```

Après déploiement, Wrangler affiche l’URL du Worker, par exemple :
`https://thf-media-worker.<account>.workers.dev`

## Configuration

1. **Mettre à jour `wrangler.toml`** :
   - Vérifiez que `bucket_name` correspond à votre bucket R2.
   - Mettez à jour `[vars] ALLOWED_KEYS` pour chaque nouvelle vidéo à publier.

2. **Variables d’environnement côté usine** (fichier `.env`) :
   ```
   THF_WORKER_URL=https://thf-media-worker.<account>.workers.dev
   THF_WORKER_ENABLED=false   # passer à true après validation réelle
   ```

## Validation réelle post-déploiement

Exécutez depuis un terminal extérieur à votre session Cloudflare :

```bash
# 1. GET sans authentification — doit retourner 200 et video/mp4
curl -I "https://thf-media-worker.<account>.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"

# 2. HTTP Range — doit retourner 206 Partial Content
curl -I -H "Range: bytes=0-1023" \
  "https://thf-media-worker.<account>.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"

# 3. Taille et type
curl -sI "https://thf-media-worker.<account>.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4" | grep -E "(content-length|content-type|accept-ranges)"

# 4. Clé non autorisée — doit retourner 403
curl -I "https://thf-media-worker.<account>.workers.dev/thf/unknown.mp4"

# 5. PUT interdit — doit retourner 405
curl -X PUT -I "https://thf-media-worker.<account>.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
```

## Coûts

- **Worker** : 100 000 requêtes/jour gratuites (suffisant pour 3 vidéos/jour).
- **R2** : pas de frais de sortie entre Worker et R2 ; stockage au-delà de 10 Go = 0,015 $/Go/mois.
- **Bande passante sortante** (vers Buffer/TikTok) : gratuite via Worker.
