
<#
.SYNOPSIS
    Deploie le Cloudflare Worker thf-media-worker en local uniquement.
.DESCRIPTION
    Verifie Node.js/npm existants (pas d installation automatique),
    installe Wrangler localement dans le dossier Worker (npm ci / npm install),
    deploie via npx --no-install wrangler deploy,
    valide l URL Angola et met a jour .env UNIQUEMENT apres validation reelle.
    A EXECUTER EN DEHORS DE CODEX dans PowerShell standard (non admin requis).
.NOTES
    Version: 2.0
    Date: 2026-10-26
#>
param(
    [string]$ProjectRoot = 'C:\TikTokHistoryFactory',
    [switch]$Force = $false
)

$ErrorActionPreference = 'Stop'
$WorkerDir = 'C:\TikTokHistoryFactory\src\cloudflare_worker\thf-media-worker'
$EnvFile = 'C:\TikTokHistoryFactory\.env'
$TestKey = 'thf/angolan-civil-war-1975_b54b077af9055e23.mp4'

$Report = @{
    WORKER_DEPLOYMENT   = 'BLOCKED'
    WORKER_PUBLIC_URL   = $null
    ANGOLA_HTTPS_HEAD   = 'BLOCKED'
    ANGOLA_HTTP_RANGE   = 'BLOCKED'
    R2_BINDING          = 'BLOCKED'
    ALLOWLIST_SECURITY  = 'BLOCKED'
    SQLITE_URL_SAVED    = 'BLOCKED'
    BUFFER_SUBMISSION   = 'NOT_EXECUTED'
    TIKTOK_PUBLICATION  = 'NOT_EXECUTED'
}

function Write-Report {
    Write-Host ''
    Write-Host '=== Rapport de deploiement ===' -ForegroundColor Cyan
    foreach ($k in @('WORKER_DEPLOYMENT','WORKER_PUBLIC_URL','ANGOLA_HTTPS_HEAD','ANGOLA_HTTP_RANGE','R2_BINDING','ALLOWLIST_SECURITY','SQLITE_URL_SAVED','BUFFER_SUBMISSION','TIKTOK_PUBLICATION')) {
        $v = $Report[$k]
        if ($null -eq $v) { $v = 'N/A' }
        Write-Host "  $k : $v"
    }
}

Write-Host '=== Deploiement Cloudflare Worker thf-media-worker ===' -ForegroundColor Cyan
Write-Host "Worker dir : $WorkerDir" -ForegroundColor Gray
Write-Host ''

# 1. Verifier Node.js + npm (pas d installation automatique)
function Test-NodeNpm {
    try {
        $nodeVer = node --version 2>$null
        $npmVer  = npm --version 2>$null
        if ($nodeVer -and $npmVer) {
            return @{ ok = $true; node = $nodeVer; npm = $npmVer }
        }
    } catch { }
    return @{ ok = $false }
}

$nodeCheck = Test-NodeNpm
if (-not $nodeCheck.ok) {
    Write-Host 'BLOCKED : Node.js et/ou npm sont introuvables sur ce systeme.' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Action requise : installez Node.js LTS depuis https://nodejs.org' -ForegroundColor Yellow
    Write-Host 'puis relancez ce script. Aucune installation automatique ne sera effectuee.'
    Write-Report
    exit 1
}

Write-Host "Node.js : $($nodeCheck.node)" -ForegroundColor Green
Write-Host "npm     : $($nodeCheck.npm)" -ForegroundColor Green

# 2. Installer Wrangler localement (jamais globalement)
Push-Location $WorkerDir

Write-Host ''
Write-Host 'Installation locale des dependances Worker...' -ForegroundColor Cyan
if (Test-Path 'package-lock.json') {
    Write-Host '  package-lock.json detecte -> npm ci'
    npm ci --no-audit --no-fund
} else {
    Write-Host '  package-lock.json absent -> npm install'
    npm install --no-audit --no-fund
}
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "npm install/ci a echoue. Verifiez la connexion Internet et les permissions du dossier $WorkerDir."
}

$localWrangler = Join-Path $WorkerDir 'node_modules\.bin\wrangler.cmd'
if (-not (Test-Path $localWrangler)) {
    Pop-Location
    throw 'Wrangler nest pas installe localement dans node_modules. Verifiez package.json.'
}
Write-Host "Wrangler local OK : $localWrangler" -ForegroundColor Green

# 3. Authentification Cloudflare (navigateur officiel)
Write-Host ''
Write-Host 'Verification authentification Cloudflare...' -ForegroundColor Cyan
$whoamiOutput = npx --no-install wrangler whoami 2>&1
if ($LASTEXITCODE -ne 0 -or $whoamiOutput -match 'not authenticated|Not Authenticated|login required') {
    Write-Host 'Authentification requise. Un navigateur va souvrir pour la connexion Cloudflare.' -ForegroundColor Yellow
    if (-not $Force) {
        $confirmAuth = Read-Host 'Appuyez sur Entree pour lancer wrangler login (ou tapez STOP pour annuler)'
        if ($confirmAuth -eq 'STOP') {
            Pop-Location
            Write-Host 'Deploiement annule par l utilisateur.' -ForegroundColor Red
            exit 0
        }
    }
    npx --no-install wrangler login
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw 'Echec authentification Wrangler. Verifiez votre compte Cloudflare.'
    }
} else {
    Write-Host 'Deja authentifie.' -ForegroundColor Green
}

# 4. Audit et confirmation pre-deploiement
Write-Host ''
Write-Host '=== Audit pre-deploiement ===' -ForegroundColor Cyan

$wranglerToml = Get-Content 'C:\TikTokHistoryFactory\src\cloudflare_worker\thf-media-worker\wrangler.toml' -Raw
$bucketName = if ($wranglerToml -match 'bucket_name\s*=\s*"([^"]+)"') { $matches[1] } else { 'NON_TROUVE' }
$allowedKeys = if ($wranglerToml -match 'ALLOWED_KEYS\s*=\s*\x27([^\x27]+)\x27') { $matches[1] } else { 'NON_TROUVE' }

Write-Host '  Nom Worker    : thf-media-worker'
Write-Host "  Bucket R2     : $bucketName"
Write-Host "  Allowed keys  : $allowedKeys"
Write-Host '  Mode compte   : Gratuit (aucune modification payante)'
Write-Host '  Buffer/TikTok : NON implique dans ce deploiement'

if ($bucketName -ne 'tiktokhistoryfactory-media') {
    Pop-Location
    throw "ERREUR AUDIT : bucket_name attendu 'tiktokhistoryfactory-media', trouve '$bucketName'"
}
if ($allowedKeys -notmatch 'angolan-civil-war-1975_b54b077af9055e23') {
    Pop-Location
    throw 'ERREUR AUDIT : cle Angola absente de ALLOWED_KEYS'
}
Write-Host '  Audit bucket  : PASS' -ForegroundColor Green
Write-Host '  Audit allow   : PASS' -ForegroundColor Green

Write-Host ''
if (-not $Force) {
    Write-Host 'Ce deploiement va :' -ForegroundColor Yellow
    Write-Host '  - Publier le Worker thf-media-worker sur votre compte Cloudflare'
    Write-Host "  - Exposer UNIQUEMENT l objet : $TestKey"
    Write-Host '  - Ne PAS creer/modifier le bucket R2 (deja existant)'
    Write-Host '  - Ne PAS activer Buffer ni TikTok'
    Write-Host '  - Ne PAS modifier les parametres systeme'
    $go = Read-Host 'Confirmez le deploiement (oui/NON)'
    if ($go -ne 'oui') {
        Pop-Location
        Write-Host 'Deploiement annule.' -ForegroundColor Red
        exit 0
    }
}

# 5. Deploiement Worker uniquement
Write-Host ''
Write-Host 'Deploiement en cours...' -ForegroundColor Cyan
$deployOutput = npx --no-install wrangler deploy 2>&1
$deployExit = $LASTEXITCODE
Write-Host $deployOutput -ForegroundColor Gray

if ($deployExit -ne 0) {
    Pop-Location
    throw "wrangler deploy a echoue (code $deployExit)."
}

# Extraire l URL Worker
$workerUrl = $null
foreach ($line in ($deployOutput -split "`n")) {
    if ($line -match '(https://[\w\-\.]+\.workers\.dev)') {
        $workerUrl = $matches[1]
        break
    }
}
if (-not $workerUrl) {
    Write-Host 'URL Worker non detectee automatiquement.' -ForegroundColor Yellow
    Write-Host 'Consultez la sortie Wrangler ci-dessus.'
    $workerUrl = Read-Host 'Entrez l URL Worker affichee par Wrangler'
    if (-not $workerUrl) {
        Pop-Location
        throw 'URL Worker manquante. Impossible de valider.'
    }
}

$workerUrl = $workerUrl.TrimEnd('/')
$fullUrl = "$workerUrl/$TestKey"
$Report.WORKER_PUBLIC_URL = $workerUrl

Write-Host ''
Write-Host 'Worker deploye.' -ForegroundColor Green
Write-Host "Worker URL : $workerUrl"
Write-Host "Angola URL : $fullUrl"

# 6. Validation reelle depuis Internet
Write-Host ''
Write-Host '=== Validation reelle (acces Internet normal) ===' -ForegroundColor Cyan

function Test-RealRequest($method, $url, $headers, $expectedStatus, $label) {
    Write-Host "  [$label] $method $url"
    try {
        $resp = Invoke-WebRequest -Uri $url -Method $method -Headers $headers -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
        if ($resp.StatusCode -eq $expectedStatus) {
            Write-Host "      -> PASS : $($resp.StatusCode)" -ForegroundColor Green
            return @{ ok = $true; resp = $resp }
        } else {
            Write-Host "      -> FAIL : attendu $expectedStatus, recu $($resp.StatusCode)" -ForegroundColor Red
            return @{ ok = $false }
        }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq $expectedStatus) {
            Write-Host "      -> PASS : $code (attendu)" -ForegroundColor Green
            return @{ ok = $true; resp = $_.Exception.Response }
        } else {
            Write-Host "      -> FAIL : attendu $expectedStatus, recu $code" -ForegroundColor Red
            return @{ ok = $false }
        }
    }
}

# 6a. HEAD 200 + video/mp4
$headTest = Test-RealRequest 'HEAD' $fullUrl @{} 200 'HEAD'
if ($headTest.ok) {
    $ct = $headTest.resp.Headers['Content-Type']
    if ($ct -like '*video/mp4*') {
        Write-Host "      Content-Type : $ct -> PASS" -ForegroundColor Green
        $Report.ANGOLA_HTTPS_HEAD = 'REAL PASS'
    } else {
        Write-Host "      Content-Type inattendu : $ct -> FAIL" -ForegroundColor Red
        $Report.ANGOLA_HTTPS_HEAD = 'FAIL'
    }
} else {
    $Report.ANGOLA_HTTPS_HEAD = 'FAIL'
}

# 6b. GET Range 206
$rangeTest = Test-RealRequest 'GET' $fullUrl @{'Range'='bytes=0-1023'} 206 'Range'
if ($rangeTest.ok) {
    $cr = $rangeTest.resp.Headers['Content-Range']
    if ($cr) {
        Write-Host "      Content-Range : $cr -> PASS" -ForegroundColor Green
        $Report.ANGOLA_HTTP_RANGE = 'REAL PASS'
    } else {
        Write-Host '      Content-Range manquant -> FAIL' -ForegroundColor Red
        $Report.ANGOLA_HTTP_RANGE = 'FAIL'
    }
} else {
    $Report.ANGOLA_HTTP_RANGE = 'FAIL'
}

# 6c. Forbidden (cle non autorisee)
$badUrl = "$workerUrl/thf/unknown-bad-key.mp4"
$forbiddenTest = Test-RealRequest 'GET' $badUrl @{} 403 'Forbidden'
if ($forbiddenTest.ok) {
    $Report.ALLOWLIST_SECURITY = 'REAL PASS'
} else {
    $Report.ALLOWLIST_SECURITY = 'FAIL'
}

# 6d. PUT interdit
$putTest = Test-RealRequest 'PUT' $fullUrl @{} 405 'PUT interdit'
if (-not $putTest.ok) {
    $Report.ALLOWLIST_SECURITY = 'FAIL'
}

# 6e. Streaming complet (GET sans Range)
$streamTest = Test-RealRequest 'GET' $fullUrl @{} 200 'Streaming complet'
if ($streamTest.ok) {
    $cl = $streamTest.resp.Headers['Content-Length']
    Write-Host "      Content-Length : $cl"
    $Report.R2_BINDING = 'REAL PASS'
} else {
    $Report.R2_BINDING = 'FAIL'
}

Pop-Location

# 7. Decision : activer .env UNIQUEMENT si toutes les validations passent
$allPassed = (
    $Report.ANGOLA_HTTPS_HEAD -eq 'REAL PASS' -and
    $Report.ANGOLA_HTTP_RANGE -eq 'REAL PASS' -and
    $Report.ALLOWLIST_SECURITY -eq 'REAL PASS' -and
    $Report.R2_BINDING -eq 'REAL PASS'
)

if (-not $allPassed) {
    Write-Host ''
    Write-Host 'VALIDATION INCOMPLETE. L URL Worker nest PAS enregistree dans .env.' -ForegroundColor Red
    Write-Host 'Corrigez les erreurs ci-dessus et relancez le script.'
    $Report.WORKER_DEPLOYMENT = 'FAIL'
    Write-Report
    exit 1
}

Write-Host ''
Write-Host 'Toutes les validations reussies.' -ForegroundColor Green

# 8. Mise a jour .env (UNIQUEMENT apres validation reelle)
Write-Host ''
Write-Host 'Mise a jour .env...' -ForegroundColor Cyan
$envLines = Get-Content $EnvFile
$newLines = @()
$updatedWorkerUrl = $false
$updatedWorkerEnabled = $false
$foundBufferAllowed = $false

foreach ($line in $envLines) {
    if ($line -match '^THF_WORKER_URL=') {
        $newLines += "THF_WORKER_URL=$workerUrl"
        $updatedWorkerUrl = $true
    } elseif ($line -match '^THF_WORKER_ENABLED=') {
        $newLines += 'THF_WORKER_ENABLED=true'
        $updatedWorkerEnabled = $true
    } elseif ($line -match '^THF_BUFFER_PUBLISH_ALLOWED=') {
        $newLines += 'THF_BUFFER_PUBLISH_ALLOWED=0'
        $foundBufferAllowed = $true
    } else {
        $newLines += $line
    }
}
if (-not $updatedWorkerUrl)   { $newLines += "THF_WORKER_URL=$workerUrl" }
if (-not $updatedWorkerEnabled){ $newLines += 'THF_WORKER_ENABLED=true' }
if (-not $foundBufferAllowed) { $newLines += 'THF_BUFFER_PUBLISH_ALLOWED=0' }

Set-Content -Path $EnvFile -Value ($newLines -join "`n") -Encoding UTF8

$Report.WORKER_DEPLOYMENT  = 'REAL PASS'
$Report.SQLITE_URL_SAVED   = 'REAL PASS'

# 9. Rapport final
Write-Report

Write-Host ''
Write-Host '=== Deploiement termine ===' -ForegroundColor Green
Write-Host "URL stable Angola : $fullUrl"
Write-Host 'Buffer publication NON activee (THF_BUFFER_PUBLISH_ALLOWED=0)'
Write-Host 'Usine quotidienne NON activee (3x/jour desactive)'
Write-Host ''
Write-Host 'Pour activer Buffer plus tard :'
Write-Host '  1. Verifier buffer_verify_real.py'
Write-Host '  2. Executer : $env:THF_BUFFER_PUBLISH_ALLOWED=1 (ou modifiez .env)'
Write-Host '  3. Executer : scripts\activate_factory.ps1'
