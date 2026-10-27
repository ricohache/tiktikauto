# Rapport — Connexion Reelle Buffer API (TikTokHistoryFactory)

**Date:** 2026-10-26
**Mission:** Finalisation connexion Buffer API — REAL PASS depuis Windows utilisateur
**Statut:** TESTS LOCALES PASS — RESEAU BLOCKED PAR SANDBOX CODEX

---

## 1. Verifications demandees

### 1.1 Menu PowerShell — injection de secret dans python -c

**Verification:** `Select-String 'python.*-c'` sur `main_v5_final.ps1`

**Resultat:** Une seule occurrence trouvee, ligne 83, dans le bloc `TikTokMock`.
```powershell
& $pythonExe -c "
from tiktok_history_factory.providers.tiktok_official import TikTokOfficialProvider
...
p = TikTokOfficialProvider('fake_key', 'fake_secret')
"
```

**Conclusion:** Il n'y a **aucune injection de secret Buffer** dans un `python -c`. Le seul `python -c` du script utilise des fausses cles (`fake_key`, `fake_secret`) pour un test MOCK de l'API TikTok officielle (non Buffer). La section `BufferConfig` appelle `& $pythonExe $bufferConfig` (script Python dedie), sans arguments sensibles.

**Statut:** REAL PASS

### 1.2 buffer_config_cli.py — import sans exposition du secret

**Verification:** Revue du code `buffer_config_cli.py`

**Resultat:**
- Saisie interactive via `getpass.getpass()` (caractere masques)
- Option `--import-file PATH` lit la cle depuis un fichier local
- Le secret **n'est jamais affiche** dans la sortie standard
- Le secret **ne transite pas** dans les arguments du processus
- Seul le chemin du fichier est visible dans la ligne de commande

**Statut:** REAL PASS

### 1.3 buffer_adapter.py — recuperation DPAPI

**Verification:** Revue du bloc `if __name__ == '__main__':`

**Resultat:**
```python
store = CredentialStore()
token = store.get("buffer_access_token")
```
L'adaptateur charge automatiquement le token depuis le coffre DPAPI Windows. Aucune variable d'environnement `BUFFER_ACCESS_TOKEN` n'est attendue.

**Statut:** REAL PASS

---

## 2. Test d'execution local (sandbox Codex)

### Script prepare
Fichier: `src/v5_factory/buffer_verify_real.py`

Actions realisees:
1. Lecture de la cle depuis `C:\TikTokHistoryFactory\ComfyUI\buff.tkn` (fichier local)
2. Stockage dans CredentialStore DPAPI (sandbox temporaire)
3. Verification de persistance (lecture depuis une nouvelle instance CredentialStore)
4. Requetes GraphQL Buffer: `account`, `channels`, `get_tiktok_channel`

### Resultats du test local

```
Token source file: C:\TikTokHistoryFactory\ComfyUI\buff.tkn
Token file exists: True
Token length read from file: 43 chars
DPAPI roundtrip test: PASS
Token stored in DPAPI vault: SUCCESS
Token persistence verification: PASS
Token retrieved from fresh CredentialStore: OK (43 chars)

[1/3] GraphQL: account (verify auth)...
  status: NETWORK_ERROR
  error: <urlopen error Tunnel connection failed: 403 Forbidden>

[2/3] GraphQL: channels...
  Channels count: 0

[3/3] GraphQL: TikTok channel...
  TikTok channel: NOT FOUND
```

### Analyse
L'erreur `403 Forbidden` sur le tunnel de sortie confirme que le **sandbox Codex bloque les connexions HTTPS externes** vers `api.buffer.com`. Ce n'est pas un probleme de token, de code ou de DNS : c'est une restriction du sandbox d'execution.

**Statut:** LOCAL PASS (DPAPI + script) / NETWORK BLOCKED (sandbox)

---

## 3. Commande PowerShell pour execution hors sandbox

Cette commande doit etre executee dans un **PowerShell utilisateur standard** (hors session Codex), sans privilege administrateur.

### Etape A — Importer la cle dans le coffre DPAPI Windows (une seule fois)

```powershell
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\buffer_config_cli.py --import-file "C:\TikTokHistoryFactory\ComfyUI\buff.tkn"
```

**Ce qui se passe:**
- Le script lit `buff.tkn` depuis le disque
- Demande confirmation si un coffre existe deja
- Effectue un test DPAPI roundtrip avec une valeur fictive
- Chiffre et stocke la vraie cle dans `%LOCALAPPDATA%\TikTokHistoryFactory\credentials.bin`
- La cle n'apparait jamais dans les arguments de processus ni dans la sortie

### Etape B — Verifier la connexion Buffer (lecture seule)

```powershell
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\buffer_verify_real.py
```

**Ce qui se passe:**
- Charge la cle depuis le coffre DPAPI
- Execute `query GetAccount { account { id email name organizations { id name } } }`
- Execute `query GetChannels { channels { id name service username organization { id name } } }`
- Affiche les statuts, les identifiants tronques, et les eventuelles erreurs API
- Aucune publication n'est creee

### Etape C — Alternative plus simple (buffer_adapter.py directement)

```powershell
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\buffer_adapter.py
```

**Ce qui se passe:**
- Idem Etape B mais avec le script original
- Affiche les reponses JSON brutes de l'API Buffer

---

## 4. Exclusion de buff.tkn de Git

**Action realisee:** Ajout au `.gitignore` principal
```
# Buffer tokens
*.tkn
buff.tkn
```

**Verification:**
```powershell
Get-Content .gitignore | Select-String 'tkn'
```

**Resultat:**
```
*.tkn
buff.tkn
```

**Statut:** REAL PASS

---

## 5. File locale — 22 episodes

**Verification:** Requete SQLite `SELECT COUNT(*) FROM tiktok_queue`

**Resultat:** 22 episodes trouves, status `pending` pour tous.

| # | Slug | Remarque |
|---|------|----------|
| 1 | angolan-civil-war-1975 | |
| 2 | battle-of-adwa-1896 | |
| 3 | biafra-war-1967 | |
| 4 | chilembwe-uprising-1915 | |
| 5 | congo-free-state-atrocities | |
| 6 | guerre-algerie-violences | |
| 7 | herero-genocide-1904 | |
| 8 | jallianwala-bagh-1919 | |
| 9 | madagascar-revolt-1947 | |
| 10 | maji-maji-rebellion-1905 | |
| 11 | nanjing-massacre-1937 | |
| 12 | patrice-lumumba-assassinat | |
| 13 | pende-revolt-1931 | |
| 14 | ruben-um-nyobe | |
| 15 | ruben-um-nyobe-1960 | **Pilote distinct** (mp4 different) |
| 16 | rwandan-genocide-1994 | |
| 17 | sharpeville-massacre-1960 | |
| 18 | soweto-uprising-1976 | |
| 19 | thiaroye-1944-90s | |
| 20 | thomas-sankara-1987 | |
| 21 | tirailleurs-senegalais | |
| 22 | tulsa-race-massacre-1921 | |

**Note sur les doublons:** Les deux entrees `ruben-um-nyobe` et `ruben-um-nyobe-1960` ne sont pas des doublons. Leurs titres et chemins MP4 sont differents (l'un est le pilote, l'autre est l'episode final).

**Contraintes respectees:**
- Aucun statut de publication modifie
- Aucune suppression
- Aucun ajout

**Statut:** REAL PASS (22 episodes conserves, 0 doublon reel)

---

## 6. Resume des statuts REAL PASS / BLOCKED

| Test | Statut | Preuve |
|------|--------|--------|
| Menu PowerShell sans injection Buffer | **REAL PASS** | `main_v5_final.ps1` ligne 83 = MOCK TikTok avec fausses cles |
| buffer_config_cli.py import securise | **REAL PASS** | `--import-file` ne passe pas le secret en argument |
| buffer_adapter.py charge DPAPI | **REAL PASS** | `store.get("buffer_access_token")` dans `__main__` |
| DPAPI roundtrip (local) | **REAL PASS** | Test execute avec succes dans le sandbox |
| DPAPI persistance hors sandbox | **A VERIFIER** | Le sandbox change LOCALAPPDATA ; doit etre teste hors sandbox |
| Requete GraphQL `account` reelle | **BLOCKED** | `403 Forbidden` sur tunnel sandbox |
| Requete GraphQL `channels` reelle | **BLOCKED** | `403 Forbidden` sur tunnel sandbox |
| Canal TikTok detecte | **BLOCKED** | Depend des requetes reseau |
| buff.tkn exclu de Git | **REAL PASS** | Ajoute au `.gitignore` |
| 22 episodes sans doublon | **REAL PASS** | Requete SQLite confirmee |

---

## 7. Risques et prochaines etapes

### Risque: Sandbox Codex vs DPAPI persistant
Le coffre DPAPI cree dans le sandbox n'est **pas persistant** car le repertoire `%LOCALAPPDATA%` est temporaire dans le sandbox. La cle doit etre importee depuis un PowerShell utilisateur standard pour etre stockee dans le vrai profil Windows.

### Prochaine action recommandee
1. Depuis PowerShell utilisateur (hors Codex), executer l'**Etape A** ci-dessus
2. Executer l'**Etape B** pour obtenir le REAL PASS de l'API Buffer
3. Si les requetes reussissent, le fichier `buff.tkn` peut etre supprime du disque (apres confirmation utilisateur)
4. Si le canal TikTok n'apparait pas dans la liste des channels, verifier dans l'interface Buffer web que le canal est bien connecte en mode "Automatic"

---

**Rapport genere par:** TikTokHistoryFactory V5
**Date:** 2026-10-26
**Fichier:** reports/buffer_real_connection_report_20261026.md
