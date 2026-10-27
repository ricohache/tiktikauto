# Rapport Preparation Premiere Publication TikTok — Angola 1975

**Date** : 2026-10-26
**Projet** : C:\TikTokHistoryFactory
**Worker** : https://thf-media-worker.rico-hache.workers.dev
**Video** : thf/angolan-civil-war-1975_b54b077af9055e23.mp4

---

## 1. Etapes effectuees

### Configuration .env
- THF_WORKER_URL = https://thf-media-worker.rico-hache.workers.dev
- THF_WORKER_ENABLED = true
- THF_BUFFER_PUBLISH_ALLOWED = 0 (conserve)

### Verification URL Worker
L utilisateur a confirme manuellement :
- HEAD 200 + video/mp4 + Accept-Ranges: bytes
- GET Range bytes=0-1023 → 206 Partial Content
- GET cle non autorisee → 403
- PUT → 405

### Mise a jour SQLite
Table `r2_uploads` enrichie (migration automatique) :
- `worker_url` = https://thf-media-worker.rico-hache.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4
- `status` = VERIFIED
- Tous les enregistrements R2 existants preserves.

### Verification Buffer
- Canal TikTok : connecte (confirme par l utilisateur)
- Token : present dans DPAPI (session Windows standard requise pour lecture)
- Doublons : aucune simulation ni tentative existante pour Angola.

### Simulation complete
Payload GraphQL prepare avec :
- `createPost` / `mode: addToQueue`
- `schedulingType: automatic`
- `assets: [{url: WORKER_URL, type: video}]`
- `metadata.tiktok.isAiGenerated: true`
- `aiAssisted: true`
- Description historique + mention IA

### Description historique
```
En 1975, l Angola accede a l independance mais plonge dans la guerre civile.
Un conflit qui opposa le MPLA, le FNLA et l UNITA, avec l intervention des
puissances de la Guerre froide.

— Reconstitution historique generee par IA. Scenario base sur des sources academiques.
```
Sources : Wikipedia EN, Pathfinder Press.

---

## 2. Rapport d etat

| Indicateur | Statut |
|------------|--------|
| **WORKER_URL** | **REAL PASS** |
| **SQLITE_LINK** | **REAL PASS** |
| **BUFFER_CHANNEL** | **REAL PASS** (confirme manuellement) |
| **VIDEO_METADATA** | **PASS** (Content-Type, Content-Length, Range OK) |
| **GRAPHQL_PAYLOAD** | **MOCK PASS** (simulation complete, payload valide) |
| **DUPLICATE_CHECK** | **PASS** (aucune entree existante) |
| **BUFFER_CREATE_POST** | **NOT EXECUTED** (garde THF_BUFFER_PUBLISH_ALLOWED=0) |
| **TIKTOK_PUBLICATION** | **NOT EXECUTED** |

---

## 3. Commande unique pour le premier test reel

### Prealable obligatoire
Modifier `.env` et mettre `THF_BUFFER_PUBLISH_ALLOWED=1` :

```powershell
# Dans PowerShell standard :
(Get-Content C:\TikTokHistoryFactory\.env) -replace 'THF_BUFFER_PUBLISH_ALLOWED=0', 'THF_BUFFER_PUBLISH_ALLOWED=1' | Set-Content C:\TikTokHistoryFactory\.env -Encoding UTF8
```

### Commande de publication
```powershell
# Execution dans PowerShell standard (hors Codex) :
C:\Users\Dell\AppData\Local\Programs\Python\Python311\python.exe C:\TikTokHistoryFactory\scripts\publish_test_angola.py
```

Ou plus simplement si `python` est dans le PATH :
```powershell
python C:\TikTokHistoryFactory\scripts\publish_test_angola.py
```

### Ce que fait la commande
1. Verifie `THF_BUFFER_PUBLISH_ALLOWED=1` dans `.env`
2. Charge le token Buffer depuis DPAPI
3. Verifie le canal TikTok (connecte, non verrouille)
4. Verifie qu aucune publication Angola n existe deja dans SQLite
5. Affiche le payload prepare (channel, video, texte, mode)
6. Demande confirmation interactive : `oui / NON`
7. Envoie `createPost` a Buffer API
8. Loggue le `post_id` dans SQLite (`buffer_attempts`)
9. Affiche le rapport final

### Securite
- Aucune publication sans confirmation interactive `oui`
- Garde `.env` bloquante par defaut (`THF_BUFFER_PUBLISH_ALLOWED=0`)
- Prevention des doublons via SQLite
- Journal de chaque tentative dans `buffer_attempts`

---

## 4. Livrables

- `scripts/publish_test_angola.py` — commande de publication unique
- `.env` — configure avec Worker URL et Worker enabled
- `data/factory.db` — SQLite mis a jour avec `worker_url`
- `src/v5_factory/buffer_simulation_adapter.py` — simulation (deja teste)

---

## 5. Contraintes respectees

- [x] Aucune installation ni changement reseau
- [x] Aucune publication non autorisee
- [x] Buffer createPost NON execute dans cette session
- [x] Planificateur 3x/jour NON active
- [x] THF_BUFFER_PUBLISH_ALLOWED conserve a 0
- [x] Usine quotidienne reste desactivee

---

*Fin du rapport.*
