# Rapport de Correction — Detection Canal TikTok Buffer

**Date:** 2026-10-26
**Mission:** Corriger la detection du canal TikTok dans l'API Buffer
**Statut:** MOCK PASS — Pret pour test REAL sous Windows utilisateur

---

## 1. Diagnostic du probleme

**Symptome:** La requete `channels` retournait 0 canal, bien que l'interface Buffer web affiche 1 canal TikTok connecte.

**Cause racine:** La requete GraphQL `channels` **requiert** un `organizationId` en argument (`input: {organizationId: ID}`). Sans cet argument, Buffer retourne une liste vide sans erreur explicite. L'ancien code appelait `list_channels()` sans jamais resoudre l'organizationId depuis `account.organizations`.

**Consequence:** L'adaptateur ne trouvait jamais le canal TikTok, bloquant toute publication automatique.

---

## 2. Corrections appliquees

### 2.1 buffer_adapter.py

| Probleme | Correction |
|----------|------------|
| `list_channels()` sans organizationId | Ajout de `_get_first_organization_id()` qui extrait l'ID depuis `account.organizations` |
| Requete `channels` sans argument | Modifiee pour passer obligatoirement `input: {organizationId: ...}` |
| `channelCount` non verifie | Ajoute dans `verify_auth` : `organizations { ... channelCount }` |
| Erreurs GraphQL silencieusement ignorees | `list_channels` retourne `[{"_error": ...}]` au lieu de `[]` |
| `get_tiktok_channel` sans organizationId | Auto-resolution de l'org ID si non fourni |

**Fichier modifie:** `src/v5_factory/buffer_adapter.py`

### 2.2 buffer_verify_real.py

- Le script utilise maintenant **uniquement** le token DPAPI deja stocke (pas de re-import depuis `buff.tkn`)
- Recupere `organizationId` depuis `account.organizations[0].id`
- Passe explicitement `organizationId` a `list_channels()`
- Affiche `channelCount` pour comparaison visuelle
- Distingue clairement : erreur GraphQL, erreur reseau, liste vide reelle

**Fichier modifie:** `src/v5_factory/buffer_verify_real.py`

### 2.3 test_buffer_mock.py

- Ajout de tests pour `_get_first_organization_id()`
- Verification que `list_channels` passe bien `organizationId` dans la requete
- Test de propagation d'erreurs GraphQL (ne doit pas retourner `[]`)
- Tests de `create_post` avec schema complet conserve

**Fichier modifie:** `tests/test_buffer_mock.py`

---

## 3. Resultats des tests MOCK

| Test | Resultat |
|------|----------|
| verify_auth (avec channelCount) | **MOCK PASS** |
| _get_first_organization_id | **MOCK PASS** |
| list_channels (auto-resolved org) | **MOCK PASS** |
| get_tiktok_channel (auto-resolved org) | **MOCK PASS** |
| list_channels (explicit org_id) | **MOCK PASS** |
| list_channels propage erreurs GraphQL | **MOCK PASS** |
| get_tiktok_channel propage erreurs GraphQL | **MOCK PASS** |
| create_post blocked by default | **MOCK PASS** |
| create_post schema validation | **MOCK PASS** |
| create_post scheduled | **MOCK PASS** |
| SQLite logging | **MOCK PASS** |

**Commande:** `python tests/test_buffer_mock.py`

---

## 4. Commande pour test REAL sous Windows utilisateur

**Pre-requis:** Le token Buffer doit deja etre stocke dans DPAPI (via `buffer_config_cli.py --import-file` execute hors sandbox).

```powershell
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\buffer_verify_real.py
```

**Attendu si tout fonctionne:**
```
AUTH:               OK (account=xxxx...)
ORGANIZATION:       My organization (id=xxxx...)
CHANNEL_COUNT:      1 (expected)
CHANNELS_FOUND:     1
  - tiktok: MonCompteTikTok (id=xxxx...)
TIKTOK_CHANNEL_ID:  xxxx...
TIKTOK_CONNECTED:   YES
```

**Si le probleme persiste:**
- Verifier que le compte API dispose des permissions sur l'organisation
- Verifier dans l'interface Buffer que le canal TikTok est bien connecte a l'organisation "My organization"
- Verifier que le token n'est pas limite a un scope restreint

---

## 5. Points de vigilance

1. **Permissions API:** Le token doit avoir acces a l'organisation contenant le canal TikTok. Si le token est lie a un autre compte/organisation, `channels` retournera une liste vide.

2. **Mode "Automatic" vs "Notify Me":** Meme si le canal est detecte, la publication automatique requiert que le canal TikTok soit configure en mode "Automatic" (Direct Publishing) dans les parametres Buffer. Le mode "Notify Me" cree un rappel au lieu de publier.

3. **Cache interne:** `_channel_cache` et `_account_cache` sont reinitialises a chaque nouvelle instance de `BufferAdapter`. En cas de modification du canal cote Buffer, recreer l'instance.

---

## 6. Fichiers modifies

| Fichier | Action |
|---------|--------|
| `src/v5_factory/buffer_adapter.py` | CORRECTION — auto-resolution organizationId, channelCount, propagation erreurs |
| `src/v5_factory/buffer_verify_real.py` | CORRECTION — utilise DPAPI existant, passe organizationId, affiche channelCount |
| `tests/test_buffer_mock.py` | AJOUT — tests organizationId et propagation erreurs |

---

**Rapport genere par:** TikTokHistoryFactory V5
**Date:** 2026-10-26
**Fichier:** reports/buffer_channel_fix_report_20261026.md
