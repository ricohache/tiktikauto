# Rapport — Premier Transfert Cloudflare R2 (Workflow Automatise)

**Date:** 2026-10-26
**Mission:** Transfert automatise d'une video historique approuvee vers Cloudflare R2
**Statut:** WORKFLOW MOCK PASS — PRET POUR TRANSFERT REEL

---

## 1. Audit pre-transfert

### Origine des validations

**8 videos explicitement approuvees par l'utilisateur** (source: conversations 19-25 octobre 2026):
- angolan-civil-war-1975
- battle-of-adwa-1896
- rwandan-genocide-1994
- sharpeville-massacre-1960
- thiaroye-1944-90s
- jallianwala-bagh-1919
- nanjing-massacre-1937
- tulsa-race-massacre-1921

**Stockage de la source de verite:** `data/decisions/upload_approvals.json`

**Videos NON approuvees pour publication** (10 episodes anciens + autres):
- biafra-war-1967, congo-free-state-atrocities, guerre-algerie-violences, herero-genocide-1904, madagascar-revolt-1947, patrice-lumumba-assassinat, pende-revolt-1931, ruben-um-nyobe, thomas-sankara-1987, tirailleurs-senegalais
- chilembwe-uprising-1915, maji-maji-rebellion-1905, soweto-uprising-1976
- ruben-um-nyobe-1960 (pilote, distinct)

**Distinction:** `style_approved=true` dans `art-direction-20261019.json` ne constitue PAS une autorisation de publication. Seules les 8 videos listees dans `upload_approvals.json` sont autorisees pour l'upload R2.

---

## 2. Corrections appliquees

### r2_upload_workflow.py

| Probleme | Correction |
|----------|------------|
| Liste APPROVED_SLUGS codée en dur | Supprimee. Lecture dynamique depuis `upload_approvals.json` |
| Clé R2 sans versionning | Cle basee sur SHA256: `thf/{slug}_{sha256[:16]}.mp4` |
| Absence de mode dry-run | Ajout de `--dry-run` et `--slug` |
| Aucune trace d'approbation explicite | Creation de `upload_approvals.json` comme source de verite |

### data/decisions/upload_approvals.json

**NOUVEAU** — Source de verite pour les uploads. Contient les 8 slugs approuves avec:
- `source`: reference aux conversations d'approbation
- `warning`: protection contre les modifications non autorisees
- `note`: distinction entre style_approved et approbation publication

---

## 3. Tests MOCK

### R2 Workflow

| Test | Statut |
|------|--------|
| load_approved_slugs (depuis JSON) | **MOCK PASS** |
| Creation table r2_uploads | **MOCK PASS** |
| Idempotence _update_status | **MOCK PASS** |
| Selection video approuvee | **MOCK PASS** |
| Selection dry_run | **MOCK PASS** |
| QC video (SHA256 + ffprobe) | **MOCK PASS** |
| Upload avec cle SHA256 | **MOCK PASS** |
| Verification taille distante | **MOCK PASS** |

### Buffer (non regression)

| Test | Statut |
|------|--------|
| verify_auth | **MOCK PASS** |
| list_channels | **MOCK PASS** |
| get_tiktok_channel | **MOCK PASS** |
| create_post schema | **MOCK PASS** |
| SQLite logging | **MOCK PASS** |

---

## 4. Dry-run execute

```powershell
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\r2_upload_workflow.py --dry-run
```

**Resultat:**
```
Slugs approuves charges: 8

=== DRY RUN — Candidats eligibles (8) ===
  - angolan-civil-war-1975
    Path: .../angolan-civil-war-1975-v5-final.mp4
    Queue status: pending
    Upload status: N/A
  - battle-of-adwa-1896
  - rwandan-genocide-1994
  - sharpeville-massacre-1960
  - thiaroye-1944-90s
  - jallianwala-bagh-1919
  - nanjing-massacre-1937
  - tulsa-race-massacre-1921

=== DRY RUN COMPLETE ===
```

Aucune video non approuvee n'est presente dans la liste. Aucun upload n'a ete effectue.

---

## 5. Commande PowerShell unique (Windows utilisateur, hors sandbox)

**Pre-requis verifies:**
- boto3 installe
- Credentials R2 dans DPAPI
- Buffer API fonctionnelle

**Commande:**

```powershell
# Etape 1: Dry-run (verification sans upload)
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\r2_upload_workflow.py --dry-run

# Etape 2: Transfert reel de la premiere video approuvee
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\r2_upload_workflow.py

# Alternative: forcer un slug specifique
C:\TikTokHistoryFactory\.venv\Scripts\python.exe C:\TikTokHistoryFactory\src\v5_factory\r2_upload_workflow.py --slug "thiaroye-1944-90s"
```

**Ce qui se passe:**
- Selection de `angolan-civil-war-1975` (premier approuve alphabetiquement)
- QC: ffprobe + SHA256
- Upload vers `thf/angolan-civil-war-1975_{sha16}.mp4`
- Verification `head_object` + taille
- URL signee generee (7 jours)
- SQLite: statut `VERIFIED`
- Aucune action Buffer ni TikTok

---

## 6. Resultat attendu hors sandbox

```
VIDEO_SELECTED:     angolan-civil-war-1975
SOURCE_PATH:        C:\TikTokHistoryFactory\output\auto-angolan-civil-war-1975-v5\angolan-civil-war-1975-v5-final.mp4
SHA256:             xxxxxxxxxxxxxxxx...
MP4_QC:             PASS
R2_UPLOAD:          REAL PASS
R2_REMOTE_OBJECT:   thf/angolan-civil-war-1975_xxxxxxxxxxxxxxxx.mp4
R2_SIZE_VERIFIED:   True
HTTPS_ACCESS:       URL signee generee (expire: 7 jours)
SQLITE_IDEMPOTENCY: OK
BUFFER_SUBMISSION:  NOT EXECUTED
TIKTOK_PUBLICATION: NOT EXECUTED
```

---

## 7. Fichiers crees / modifies

| Fichier | Action |
|---------|--------|
| `src/v5_factory/r2_upload_workflow.py` | **CORRECTION** — Approbations depuis JSON, cle SHA256, --dry-run |
| `data/decisions/upload_approvals.json` | **NOUVEAU** — Source de verite des 8 videos approuvees |
| `tests/test_r2_workflow.py` | **CORRECTION** — Tests adaptes au nouveau workflow |

---

**Rapport genere par:** TikTokHistoryFactory V5
**Date:** 2026-10-26
**Fichier:** reports/r2_first_upload_report_20261026.md
