# Rapport de Correction — Integration Buffer API TikTokHistoryFactory

**Date:** 2026-10-26
**Version:** v5_buffer_integration_CORRECTION
**Statut:** ADAPTATEUR BUFFER CORRIGE — TESTS MOCK PASS — API REELLE NON TESTEE (SANDBOX)

---

## 1. Resume executif

L'adaptateur Buffer API a ete corrige pour correspondre au schema GraphQL officiel Buffer. Le rapport precedent du 26/10/2026 concluait a tort que Buffer ne permettait pas la publication automatique TikTok. La documentation officielle confirme le contraire :
- Mode **Automatic** (Direct Publishing) disponible pour TikTok
- Programmation horaire via `dueAt` + `schedulingType=customScheduled`
- Signalement IA via `aiAssisted` + `metadata.tiktok.isAiGenerated`

Les fichiers critiques ont ete corriges sans reconstruction du projet. Aucune video n'a ete envoyee. Aucune publication n'a ete creee.

---

## 2. Corrections appliquees

### 2.1 buffer_adapter.py — CORRECTION API

| Element | Avant (incorrect) | Apres (correction)
|---------|-------------------|-------------------
| Query auth | `user { ... }` | `account { ... }` |
| Query channels | `channels { ... }` | `channels(input: {organizationId}) { ... }` |
| CreatePost | `channelIds: [id]` | `channelId: id` (singulier) |
| Scheduling | `scheduledAt` | `dueAt` + `schedulingType` |
| Mode | absent | `mode: "addToQueue"` ou `"customScheduled"` |
| Assets | `[{"url": "...", "type": "video"}]` | `[{"url": "...", "type": "video", "metadata": {}}]` |
| AI flag | `tiktokPostMetadata.isAiGenerated` | `aiAssisted: true` + `metadata.tiktok.isAiGenerated: true` |

**Fichier modifie :** `src/v5_factory/buffer_adapter.py`
**Sauvegarde :** `src/v5_factory/buffer_adapter.py.bak-20261026`

### 2.2 secure_credentials.py — CORRECTION SECURITE

**Probleme identifie :** La methode `set()` essayait de dechiffrer le coffre existant, et en cas d'echec de `json.loads()` (ligne `except Exception`), elle creait un dictionnaire vide et ecrasait silencieusement le coffre existant.

**Correction :** La methode `_load_existing()` a ete introduite. Elle tente de dechiffrer le coffre. En cas d'echec :
- Si un backup existe, tente de restaurer depuis le backup
- Sinon, leve explicitement `RuntimeError` avec message d'erreur detaille
- `set()` n'ecrase plus jamais silencieusement un coffre existant

**Teste :** Injection de donnees corrompues dans `credentials.bin`, verification que `set()` leve bien `RuntimeError`.

**Fichier modifie :** `src/v5_factory/secure_credentials.py`
**Sauvegarde :** `src/v5_factory/secure_credentials.py.bak-20261026`

### 2.3 buffer_config_cli.py — CORRECTION SECURITE (import fichier)

**Probleme signale :** Le menu PowerShell `BufferConfig` appelait `python buffer_config_cli.py` avec saisie interactive. Cependant, aucune injection en clair via `python -c` n'a ete trouvee dans le code actuel du projet. Le seul `python -c` identifie est dans `main_v5_final.ps1` pour le test MOCK TikTok, qui utilise des fausses cles.

**Precaution ajoutee :** L'option `--import-file PATH` permet d'importer la cle depuis un fichier local (ex: `buff.tkn`) sans que le secret ne transite par les arguments du processus Python. Seul le chemin du fichier est passe en argument, pas le secret.

**Fichier modifie :** `src/v5_factory/buffer_config_cli.py`
**Sauvegarde :** `src/v5_factory/buffer_config_cli.py.bak-20261026`

### 2.4 tiktok_publish_menu.py — MISE A JOUR

- Capacites Buffer mises a jour pour refleter le support reel de la publication automatique TikTok
- Ajout du mode `addToQueue` et de la programmation horaire

**Fichier modifie :** `src/v5_factory/tiktok_publish_menu.py`

### 2.5 video_hosting.py — AJOUT CLOUDFLARE R2

- Ajout du provider `CloudflareR2Provider` comme option recommandee
- 10 Go/mois gratuits, pas de frais de sortie, compatible S3
- Cloudinary conserve mais marque comme non recommande pour ce volume

**Fichier modifie :** `src/v5_factory/video_hosting.py`

### 2.6 test_buffer_mock.py — MISE A JOUR

- Mises a jour des requetes mock pour correspondre au nouveau schema `account`
- Ajout de validation du schema `createPost` (verifications des champs `channelId`, `aiAssisted`, `metadata.tiktok.isAiGenerated`, `schedulingType`, `mode`)
- Ajout d'un test de programmation horaire (`customScheduled` + `dueAt`)

**Fichier modifie :** `tests/test_buffer_mock.py`

---

## 3. Tests executes

### 3.1 Tests Mock (sans reseau)

| Test | Resultat |
|------|----------|
| verify_auth (schema account) | **MOCK PASS** |
| list_channels | **MOCK PASS** |
| get_tiktok_channel | **MOCK PASS** |
| create_post blocked by default | **MOCK PASS** |
| create_post schema validation (aiAssisted, metadata.tiktok.isAiGenerated, mode, schedulingType) | **MOCK PASS** |
| create_post scheduled (dueAt + customScheduled) | **MOCK PASS** |
| log_buffer_check SQLite | **MOCK PASS** |
| log_buffer_attempt SQLite | **MOCK PASS** |

**Commande :** `python tests/test_buffer_mock.py`

### 3.2 Tests DPAPI (securite)

| Test | Resultat |
|------|----------|
| Roundtrip chiffrement/dechiffrement | **REAL PASS** |
| Refus d'ecrasement silencieux (coffre corrompu) | **REAL PASS** |
| Ecriture atomique avec backup | **REAL PASS** |

**Note sandbox :** Le coffre DPAPI est lie au compte utilisateur Windows ET au repertoire `%LOCALAPPDATA%`. Le sandbox Codex utilise un `LOCALAPPDATA` temporaire qui change a chaque execution. Les coffres crees dans le sandbox ne persistent PAS entre les sessions. La vraie cle doit etre stockee et testee depuis un PowerShell utilisateur standard (hors sandbox).

### 3.3 Test API reelle (reseau)

| Test | Resultat |
|------|----------|
| verify_auth vers api.buffer.com | **BLOCKED** (sandbox reseau Codex — 403 Forbidden) |
| list_channels | **BLOCKED** (sandbox reseau Codex) |

**Preuve :** `urlopen error Tunnel connection failed: 403 Forbidden`

---

## 4. Hebergement video recommande

Buffer necessite une URL publique HTTPS pour chaque video. L'upload direct de fichier MP4 n'est PAS supporte.

### Option recommandee : Cloudflare R2

| Critere | Cloudflare R2 |
|---------|---------------|
| Quota gratuit | 10 Go/mois |
| Cout sortie (egress) | 0 $ |
| Duree conservation | Illimitee (compte actif) |
| Securite | HTTPS, API token S3-compatible |
| Cout apres quota | ~0.015 $/Go/mois (stockage) |
| Estimation pour 8 videos/mois (~50MB chacune) | ~400 MB/mois = **GRATUIT** |
| Compte requis | Oui (gratuit sur cloudflare.com) |

### Procedure d'activation (sans engagement)

1. Creer un compte Cloudflare (gratuit) sur https://dash.cloudflare.com
2. Activer R2 dans le tableau de bord
3. Creer un bucket (ex: `tiktokhistoryfactory-videos`)
4. Generer un API token S3-compatible (R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)
5. Noter l'endpoint R2 (ex: `https://<account>.r2.cloudflarestorage.com`)
6. Configurer un domaine public (ou utiliser URL presignee temporaire)
7. **NE PAS uploader de video sans accord explicite de l'utilisateur**

---

## 5. Conformite TikTok / Buffer

| Exigence | Statut | Methode |
|----------|--------|---------|
| Publication automatique | Supportee | `mode: "addToQueue"`, canal configure en "Automatic" dans Buffer |
| Programmation horaire | Supportee | `dueAt: "2026-10-27T10:00:00+02:00"` + `schedulingType: "customScheduled"` |
| Signalement contenu IA | Supportee | `aiAssisted: true` + `metadata.tiktok.isAiGenerated: true` |
| Description + hashtags | Supportee | Champ `text` |
| Mode "Notify Me" | A eviter | Verifier que le canal TikTok est bien en mode "Automatic" dans les parametres Buffer (pas "Notify Me") |

**Risque residuel :** Si le canal TikTok dans Buffer est configure en mode "Notify Me" au lieu de "Automatic", Buffer enverra une notification au lieu de publier directement. C'est un parametre a verifier dans l'interface Buffer web.

---

## 6. Anti-doublons SQLite

| Table | Contrainte | Action |
|-------|-----------|--------|
| `tiktok_queue` | `UNIQUE(slug)` | Empeche les doublons d'episodes |
| `buffer_attempts` | `UNIQUE(slug)` | Empeche les publications multiples du meme episode |
| `buffer_checks` | Aucune | Trace des verifications API (lecture seule) |

**Recuperation apres incident :**
- Status `pending` = pret a publier
- Status `failed` = erreur reseau, peut etre retente
- Status `published` = confirme par reponse Buffer API

---

## 7. Procedure pour la premiere publication

**Avant toute action :** S'assurer que :
1. La cle Buffer est stockee dans le coffre DPAPI (`buffer_config_cli.py --import-file`)
2. Le canal TikTok est verifie en mode "Automatic" dans Buffer
3. Les videos sont hebergees sur une URL publique HTTPS (Cloudflare R2)
4. Le flag `THF_BUFFER_PUBLISH_ALLOWED=1` est active explicitement

**Etapes :**

1. **Depuis PowerShell utilisateur (hors sandbox) :**
   ```powershell
   # Stocker la cle (une seule fois)
   C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\buffer_config_cli.py --import-file "C:\TikTokHistoryFactory\ComfyUI\buff.tkn"
   ```

2. **Verifier la connexion Buffer (lecture seule) :**
   ```powershell
   C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\buffer_adapter.py
   ```
   Confirmer : `account.id`, `channels` contient TikTok, canal en mode "Automatic".

3. **Heberger la premiere video sur Cloudflare R2 :**
   ```python
   from video_hosting import CloudflareR2Provider
   r2 = CloudflareR2Provider("...", "...", "...", "...", "https://votre-domaine.com")
   url = r2.upload(Path("output/ready/episode_01.mp4"), "episode_01")
   ```

4. **Creer la publication dans Buffer :**
   ```python
   from buffer_adapter import BufferAdapter
   from secure_credentials import CredentialStore
   store = CredentialStore()
   token = store.get("buffer_access_token")
   buf = BufferAdapter(token)
   result = buf.create_post(
       channel_id="chan_tiktok_xxx",
       text="Description + #hashtags",
       video_url="https://votre-domaine.com/thf/episode_01.mp4",
       due_at="2026-10-27T10:00:00+02:00",
       is_ai_generated=True,
       mode="customScheduled"
   )
   ```

5. **Verifier dans Buffer :** Confirmer que le post apparait dans la file Buffer avec le statut "Scheduled" et non "Notify Me".

6. **Repeter pour chaque video** (10h, 12h, 14h, Europe/Paris).

---

## 8. Risques residuels

| Risque | Probabilite | Mitigation |
|--------|-------------|------------|
| Sandbox Codex change LOCALAPPDATA | Certain | Stocker la cle hors sandbox via PowerShell utilisateur |
| Canal TikTok en mode "Notify Me" | Possible | Verifier dans Buffer web avant chaque publication |
| Hebergement R2 non configure | Bloquant | Configurer avant premiere publication |
| Quota Buffer depasse | Faible | Verifier `get_account_capabilities()` |
| Video supprimee de R2 avant publication | Faible | Conserver les videos locales en backup |
| Erreur dechiffrement DPAPI | Faible | Backup automatique a chaque ecriture |

---

## 9. Fichiers modifies et sauvegardes

| Fichier | Action | Sauvegarde |
|---------|--------|------------|
| `src/v5_factory/buffer_adapter.py` | CORRECTION API | `buffer_adapter.py.bak-20261026` |
| `src/v5_factory/buffer_config_cli.py` | AJOUT --import-file | `buffer_config_cli.py.bak-20261026` |
| `src/v5_factory/secure_credentials.py` | CORRECTION securite | `secure_credentials.py.bak-20261026` |
| `src/v5_factory/tiktok_publish_menu.py` | MISE A JOUR | Aucune |
| `src/v5_factory/video_hosting.py` | AJOUT R2 | Aucune |
| `tests/test_buffer_mock.py` | MISE A JOUR | Aucune |

---

**Rapport genere par:** TikTokHistoryFactory V5
**Date:** 2026-10-26
**Fichier:** reports/buffer_integration_report_20261026_CORRECTION.md
