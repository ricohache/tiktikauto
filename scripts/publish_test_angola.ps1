<#
.SYNOPSIS
    Publie la video Angola sur TikTok via Buffer API.
.DESCRIPTION
    Commande unique pour le premier test reel.
    A EXECUTER EN DEHORS DE CODEX dans PowerShell standard.
.NOTES
    Version: 3.0 (corrige check_existing_posts + resume + blocage strict)
    Date: 2026-10-27
#>
param(
    [string]$ProjectRoot = "C:\TikTokHistoryFactory",
    [string]$Mode = "customScheduled"  # addToQueue | shareNow | customScheduled
)

$ErrorActionPreference = "Stop"
$EnvFile = "$ProjectRoot\.env"

Write-Host '=== Publication test TikTok — Angola 1975 ===' -ForegroundColor Cyan
Write-Host "Mode demande : $Mode" -ForegroundColor Cyan
Write-Host 'Cette commande va envoyer UN createPost reel vers Buffer API.' -ForegroundColor Yellow
Write-Host ''

# 0. Time guard : refuser si 10 h est depassee (heure locale systeme = Europe/Paris)
$nowLocal = Get-Date
if ($nowLocal -ge (Get-Date -Year 2026 -Month 10 -Day 27 -Hour 10 -Minute 0)) {
    Write-Host "BLOCKED : Il est deja $($nowLocal.ToString('HH:mm')) (10 h Paris depassee). Programmation refusee." -ForegroundColor Red
    exit 1
}

# 1. Garde THF_BUFFER_PUBLISH_ALLOWED
$envContent = Get-Content $EnvFile -Raw
if ($envContent -notmatch 'THF_BUFFER_PUBLISH_ALLOWED\s*=\s*1') {
    Write-Host 'BLOCKED : THF_BUFFER_PUBLISH_ALLOWED n est pas egal a 1.' -ForegroundColor Red
    Write-Host 'Pour activer : modifiez .env ou executez :' -ForegroundColor Yellow
    Write-Host '  $env:THF_BUFFER_PUBLISH_ALLOWED = "1"'
    exit 1
}

# 1b. Garde shareNow explicite
if ($Mode -eq "shareNow") {
    if ($envContent -notmatch 'THF_BUFFER_SHARE_NOW_ALLOWED\s*=\s*1') {
        Write-Host 'BLOCKED : THF_BUFFER_SHARE_NOW_ALLOWED n est pas egal a 1.' -ForegroundColor Red
        Write-Host 'Le mode shareNow exige une autorisation explicite.' -ForegroundColor Yellow
        exit 1
    }
}

# 1c. Default dueAt pour customScheduled
$dueAt = $null
if ($Mode -eq "customScheduled") {
    $dueAt = "2026-10-27T09:00:00Z"
    Write-Host "customScheduled active. dueAt = $dueAt" -ForegroundColor Cyan
}

# 2. Charger le token depuis DPAPI (via Python)
Write-Host 'Chargement token Buffer depuis DPAPI...' -ForegroundColor Gray
$tokenScript = @"
import sys
sys.path.insert(0, r'C:\TikTokHistoryFactory\src\v5_factory')
from secure_credentials import CredentialStore
store = CredentialStore()
token = store.get('buffer_access_token')
if token:
    print('TOKEN_OK')
    print(token)
else:
    print('TOKEN_MISSING')
"@
$pyOutput = python -c $tokenScript
if ($pyOutput -notmatch 'TOKEN_OK') {
    Write-Host 'BLOCKED : Token Buffer introuvable dans DPAPI.' -ForegroundColor Red
    exit 1
}
$bufferToken = ($pyOutput -split "`n")[1].Trim()
Write-Host "Token charge : $($bufferToken.Length) caracteres" -ForegroundColor Green

# 3. Verifier le canal TikTok
Write-Host 'Verification canal TikTok...' -ForegroundColor Gray
$channelScript = @"
import sys, json
sys.path.insert(0, r'C:\TikTokHistoryFactory\src\v5_factory')
from buffer_adapter import BufferAdapter
buf = BufferAdapter(\"$bufferToken\")
ch = buf.get_tiktok_channel()
if ch and not ch.get('_error'):
    if ch.get('isDisconnected'):
        print('DISCONNECTED')
    elif ch.get('isLocked'):
        print('LOCKED')
    else:
        print('OK')
        print(ch['id'])
        print(ch.get('name', 'TikTok'))
else:
    print('NOT_FOUND')
"@
$chOutput = python -c $channelScript
$chLines = $chOutput -split "`n"
if ($chLines[0].Trim() -ne 'OK') {
    Write-Host "BLOCKED : Canal TikTok non disponible ($($chLines[0].Trim()))." -ForegroundColor Red
    exit 1
}
$channelId = $chLines[1].Trim()
$channelName = $chLines[2].Trim()
Write-Host "Canal TikTok OK : $channelName (id=$channelId)" -ForegroundColor Green

# 4. Verifier doublons SQLite
Write-Host 'Verification doublons SQLite...' -ForegroundColor Gray
$dupScript = @"
import sqlite3
conn = sqlite3.connect(r'C:\TikTokHistoryFactory\data\factory.db')
c = conn.cursor()
c.execute('SELECT status, buffer_post_id FROM buffer_attempts WHERE slug = ?', ('angolan-civil-war-1975',))
row = c.fetchone()
if row:
    print(f'DUPLICATE:{row[0]}:{row[1]}')
else:
    print('UNIQUE')
conn.close()
"@
$dupOutput = python -c $dupScript
if ($dupOutput -match '^DUPLICATE:') {
    Write-Host "BLOCKED : Doublon detecte ($dupOutput)." -ForegroundColor Red
    exit 1
}
Write-Host 'Aucun doublon SQLite. PASS' -ForegroundColor Green

# 4b. Verifier doublons Buffer API (nouvelle structure GraphQL)
Write-Host 'Verification doublons Buffer API...' -ForegroundColor Gray
$dupBufferScript = @"
import sys, json
sys.path.insert(0, r'C:\TikTokHistoryFactory\src\v5_factory')
from buffer_adapter import BufferAdapter
buf = BufferAdapter(\"$bufferToken\")
result = buf.check_existing_posts(\"$channelId\", \"angolan-civil-war-1975\")
print(json.dumps(result, ensure_ascii=False))
"@
$dupBufOutput = python -c $dupBufferScript
$dupBufObj = $dupBufOutput | ConvertFrom-Json
if ($dupBufObj.status -eq "ERROR") {
    Write-Host "BLOCKED : Verification Buffer API impossible." -ForegroundColor Red
    Write-Host $dupBufObj.error -ForegroundColor Red
    exit 1
}
if ($dupBufObj.matches.Count -gt 0) {
    Write-Host "BLOCKED : Doublon detecte dans Buffer API ($($dupBufObj.matches.Count) post(s))." -ForegroundColor Red
    exit 1
}
Write-Host 'Aucun doublon Buffer API. PASS' -ForegroundColor Green

# 5. Construire payload
$videoUrl = "https://thf-media-worker.rico-hache.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
$description = @"
En 1975, l'Angola accede a l'independance mais plonge dans la guerre civile. Un conflit qui opposa le MPLA, le FNLA et l'UNITA, avec l'intervention des puissances de la Guerre froide.

Sources : Office of the Historian, U.S. Department of State (history.state.gov) ; Uppsala Conflict Data Program (ucdp.uu.se).

Reconstitution historique generee par IA.
"@

# 6. Resume avant confirmation
Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host 'RESUME AVANT PUBLICATION' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host "  VIDEO          = Angola 1975"
Write-Host "  CHANNEL        = $channelId"
Write-Host "  DATE_PARIS     = 27/10/2026 10:00"
Write-Host "  DUE_AT_UTC     = $($dueAt)"
Write-Host "  MODE           = $Mode"
Write-Host "  DOUBLON_SQLITE = NO"
Write-Host "  DOUBLON_BUFFER = NO"
Write-Host '========================================' -ForegroundColor Cyan

# 7. Confirmation
Write-Host ''
$confirm = Read-Host 'Confirmez l envoi reel de createPost (oui/NON)'
if ($confirm -ne 'oui') {
    Write-Host 'Publication annulee.' -ForegroundColor Red
    exit 0
}

# 8. Execution createPost
Write-Host ''
Write-Host 'Envoi createPost a Buffer API...' -ForegroundColor Cyan
$createScript = @"
import sys, json
sys.path.insert(0, r'C:\TikTokHistoryFactory\src\v5_factory')
from buffer_adapter import BufferAdapter
buf = BufferAdapter(\"$bufferToken\")
result = buf.create_post(
    channel_id='\"$channelId\"',
    text='''\"$description\"''',
    video_url='\"$videoUrl\"',
    is_ai_generated=True,
    mode='\"$Mode\"',
    due_at='\"$dueAt\"'
)
print(json.dumps(result, ensure_ascii=False))
"@
$createOutput = python -c $createScript
Write-Host $createOutput -ForegroundColor Gray

# 9. Parser resultat et logger
$resultObj = $createOutput | ConvertFrom-Json
if ($resultObj.status -eq "SUCCESS") {
    $postId = $resultObj.post.id
    Write-Host ''
    Write-Host '=== Publication reussie ===' -ForegroundColor Green
    Write-Host "Buffer post ID : $postId"
    Write-Host "Statut         : $($resultObj.post.status)"
    Write-Host "DueAt          : $($resultObj.post.dueAt)"
} elseif ($resultObj.status -eq "BLOCKED") {
    Write-Host 'PUBLICATION BLOQUEE.' -ForegroundColor Red
    Write-Host $resultObj.error -ForegroundColor Red
    exit 1
} elseif ($resultObj.status -eq "MUTATION_ERROR") {
    Write-Host 'MUTATION ERROR.' -ForegroundColor Red
    Write-Host $resultObj.error -ForegroundColor Red
    exit 1
} else {
    Write-Host 'ERREUR inattendue.' -ForegroundColor Red
    Write-Host ($resultObj | ConvertTo-Json) -ForegroundColor Red
    exit 1
}

# Logger dans SQLite
$logScript = @"
import sqlite3
conn = sqlite3.connect(r'C:\TikTokHistoryFactory\data\factory.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS buffer_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE,
    status TEXT,
    error TEXT,
    buffer_post_id TEXT,
    attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
)''')
c.execute('INSERT OR REPLACE INTO buffer_attempts (slug, status, buffer_post_id, error) VALUES (?, ?, ?, ?)', ('angolan-civil-war-1975', 'PUBLISHED', '$postId', None))
conn.commit()
conn.close()
print('SQLite log OK')
"@
python -c $logScript

Write-Host ''
Write-Host '=== Termine ===' -ForegroundColor Green
Write-Host 'Buffer publication : REAL PASS'
if ($Mode -eq 'customScheduled') { Write-Host "TikTok publication : PLANIFIEE (customScheduled + dueAt=$dueAt)" } else { Write-Host 'TikTok publication : PLANIFIEE (addToQueue + automatic)' }
Write-Host 'Usine quotidienne  : NON activee (3x/jour desactivee)'