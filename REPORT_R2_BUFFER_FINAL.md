# Rapport R2 → Buffer → TikTok : URL Vidéo Stable

**Date** : 2026-10-26
**Projet** : C:\TikTokHistoryFactory
**Vidéo de référence** : `angolan-civil-war-1975`
**Bucket** : `tiktokhistoryfactory-media` (privé)
**Objet R2** : `thf/angolan-civil-war-1975_b54b077af9055e23.mp4`

---

## 1. Résumé des états validés

| Composant | Statut | Détails |
|-----------|--------|---------|
| R2_UPLOAD (transfert vers R2) | **REAL PASS** | Transfert réel confirmé, taille vérifiée |
| R2_SIZE_VERIFIED | **REAL PASS** | Concordance locale / distante |
| SQLite (upload) | **REAL PASS** | Table `r2_uploads` enrichie avec `worker_url`, `buffer_post_id`, `buffer_status` |
| Worker Cloudflare (code) | **MOCK PASS** | Logique TypeScript implémentée et testée en Python (7/7 tests OK) |
| Worker Cloudflare (déploiement) | **NON TESTÉ** | Code prêt, `wrangler.toml` configuré, attente accord utilisateur |
| Buffer Simulation Adapter | **MOCK PASS** | Payload complète préparée, doublons détectés, SQLite log OK (7/7 tests OK) |
| Buffer createPost réel | **NON TESTÉ** | Bloqué par garde `THF_BUFFER_PUBLISH_ALLOWED=1` |
| URL stable Worker en production | **NON TESTÉ** | Nécessite déploiement + validation externe |
| Usine quotidienne (3×/jour) | **NON ACTIVÉE** | Nécessite activation manuelle (`THF_WORKER_ENABLED=true` + `THF_BUFFER_PUBLISH_ALLOWED=1`) |

---

## 2. Architecture de distribution

### Avant (problème)
- URL signée S3 générée par `boto3.generate_presigned_url()`.
- Durée de vie limitée (7 jours).
- Buffer déconseille les URLs présignées expirantes.

### Après (solution)
- **Worker Cloudflare** (`thf-media-worker`) agit comme proxy HTTPS lecture-seule vers le bucket R2 privé.
- **URL stable** : `https://thf-media-worker.<account>.workers.dev/thf/<key>`
- Le bucket reste privé. Aucune politique publique.
- Seules les clés listées dans `ALLOWED_KEYS` (env var) sont servies.
- Support natif de `GET`, `HEAD`, `Range`, `video/mp4`.
- Coût : inclus dans le forfait gratuit Cloudflare (100 000 req/jour).

### Sécurité
- `PUT` / `DELETE` → **405 Method Not Allowed**.
- Clé non autorisée → **403 Forbidden**.
- Clé manquante → **404 Not Found**.
- Secrets R2 jamais exposés dans l’URL publique.

---

## 3. Livrables créés

### Cloudflare Worker
- `src/cloudflare_worker/thf-media-worker/src/index.ts`
- `src/cloudflare_worker/thf-media-worker/wrangler.toml`
- `src/cloudflare_worker/thf-media-worker/package.json`
- `src/cloudflare_worker/thf-media-worker/tsconfig.json`
- `src/cloudflare_worker/thf-media-worker/README.md`

### Modules Python
- `src/v5_factory/cloudflare_worker_adapter.py`
- `src/v5_factory/buffer_simulation_adapter.py`
- `src/v5_factory/video_hosting.py` (patché : `get_worker_url`)
- `src/v5_factory/r2_upload_workflow.py` (patché : colonnes SQLite, URL stable, migration)

### Configuration
- `.env` (patché : `THF_WORKER_URL` + `THF_WORKER_ENABLED`)

### Tests
- `tests/test_worker_mock.py` — 7/7 OK
- `tests/test_buffer_simulation.py` — 7/7 OK

---

## 4. Actions minimales restantes

### Étape A — Déploiement Worker (requise avant activation)
1. Installer Node.js ≥ 18 et `wrangler` (`npm install -g wrangler`).
2. Authentifier : `wrangler login`.
3. Vérifier dans `wrangler.toml` que `bucket_name = "tiktokhistoryfactory-media"`.
4. Déployer :
   ```bash
   cd src/cloudflare_worker/thf-media-worker
   npm install
   wrangler deploy
   ```
5. Noter l’URL affichée (ex: `https://thf-media-worker.<account>.workers.dev`).

### Étape B — Configuration usine
1. Éditer `C:\TikTokHistoryFactory\.env` :
   ```
   THF_WORKER_URL=https://thf-media-worker.<account>.workers.dev
   THF_WORKER_ENABLED=true
   ```
2. Relancer tout script Python pour prendre en compte les variables.

### Étape C — Validation réelle externe
Exécuter depuis un terminal **hors session Cloudflare** :

```bash
# GET + type
curl -I "https://thf-media-worker.<account>.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
# Attendu : 200, content-type: video/mp4, accept-ranges: bytes

# Range
curl -I -H "Range: bytes=0-1023" \
  "https://thf-media-worker.<account>.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
# Attendu : 206 Partial Content

# Forbidden
curl -I "https://thf-media-worker.<account>.workers.dev/thf/unknown.mp4"
# Attendu : 403

# PUT interdit
curl -X PUT -I "https://thf-media-worker.<account>.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
# Attendu : 405
```

### Étape D — Publication Buffer (premier test réel)
1. Vérifier que le canal TikTok est connecté et non verrouillé :
   ```powershell
   python src\v5_factory\buffer_verify_real.py
   ```
2. Si `TIKTOK_CHANNEL_ID` est OK, activer l’écriture :
   ```powershell
   $env:THF_BUFFER_PUBLISH_ALLOWED="1"
   ```
3. Exécuter `r2_upload_workflow.py` pour l’Angola (il produira l’URL stable).
4. Appeler `buffer_adapter.py` → `create_post` avec l’URL stable.
5. Vérifier dans le tableau Buffer que la vidéo est en file.

### Étape E — Activation usine quotidienne
- Le fichier `run_daily.py` (ou l’orchestrateur choisi) doit :
  1. Sélectionner 3 vidéos approuvées non encore publiées.
  2. Vérifier `THF_WORKER_ENABLED=true`.
  3. Upload R2 → URL stable Worker.
  4. Appeler Buffer `create_post` avec `schedulingType=automatic`.
  5. Planifier à 10 h, 12 h et 14 h Europe/Paris.
- **Garde finale** : si `THF_BUFFER_PUBLISH_ALLOWED != "1"`, l’usine reste en mode simulation.

---

## 5. Contrainte finale respectée

- Aucune mutation `createPost` n’a été exécutée.
- Aucune vidéo n’a été publiée ni planifiée.
- Seule la vidéo Angola est préparée ; les autres ne sont pas transférées.
- L’usine quotidienne (3 publications/jour) reste désactivée en l’absence des deux flags `THF_WORKER_ENABLED` + `THF_BUFFER_PUBLISH_ALLOWED`.
- Codex sert uniquement au développement et à la validation ; l’exécution autonome se fera sans intervention Codex après autorisation.

---

*Fin du rapport.*
