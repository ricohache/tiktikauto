#Requires -Version 5.1
<#
.SYNOPSIS
    TikTokHistoryFactory - Point d entree PowerShell.
.DESCRIPTION
    Responsabilites limitees : menu, verification ComfyUI/prerequis,
    appel unique de l orchestrateur Python, affichage resultat.
    Version: 4.0 (migration vers orchestrateur Python)
#>
[CmdletBinding()]
param(
    [ValidateSet('Menu','TestEndToEnd','Auto10h','Auto12h','Auto14h','Status','Publish','Diagnostic','Resume')]
    [string]$Mode = 'Menu',
    [string]$Subject = '',
    [switch]$Force = $false,
    [string]$LogPath = '',
    [string]$RunId = ''
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$ffmpegExe = Join-Path $ProjectRoot 'ffmpeg\bin\ffmpeg.exe'
$ffprobeExe = Join-Path $ProjectRoot 'ffmpeg\bin\ffprobe.exe'
$dataDir = Join-Path $ProjectRoot 'data'
$logFile = if ($LogPath) { $LogPath } else { Join-Path $dataDir 'orchestrator.log' }
$comfyDir = Join-Path $ProjectRoot 'ComfyUI'
$orchPath = Join-Path $ProjectRoot 'src\v5_factory\orchestrator.py'

function Write-LogEntry {
    param([string]$Level, [string]$Message)
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$ts [$Level] $Message"
    Add-Content -Path $logFile -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    switch ($Level) {
        'ERROR'   { Write-Host $line -ForegroundColor Red }
        'WARN'    { Write-Host $line -ForegroundColor Yellow }
        'SUCCESS' { Write-Host $line -ForegroundColor Green }
        default   { Write-Host $line -ForegroundColor Gray }
    }
}

function Initialize-ComfyUI {
    param([int]$TimeoutSeconds = 240)
    $comfyUrl = 'http://127.0.0.1:8188/system_stats'
    try {
        $resp = Invoke-WebRequest -Uri $comfyUrl -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-LogEntry 'INFO' "COMFYUI_ALREADY_RUNNING: HTTP $($resp.StatusCode)"
        return $true
    } catch {
        Write-LogEntry 'INFO' 'COMFYUI_NOT_RUNNING: will attempt autostart'
    }
    $pythonEmbedded = Join-Path $comfyDir 'python_embeded\python.exe'
    $mainPy = Join-Path $comfyDir 'ComfyUI\main.py'
    if (-not (Test-Path $pythonEmbedded)) {
        Write-LogEntry 'ERROR' "COMFYUI_START_FAILED: python_embeded not found"
        return $false
    }
    if (-not (Test-Path $mainPy)) {
        Write-LogEntry 'ERROR' "COMFYUI_START_FAILED: main.py not found"
        return $false
    }
    $logStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $stdoutLog = Join-Path $comfyDir "comfyui_autostart_${logStamp}_out.log"
    $stderrLog = Join-Path $comfyDir "comfyui_autostart_${logStamp}_err.log"
    $proc = $null
    try {
        $proc = Start-Process -FilePath $pythonEmbedded `
            -ArgumentList "-s","ComfyUI\main.py","--windows-standalone-build","--listen","127.0.0.1","--port","8188" `
            -WorkingDirectory $comfyDir -WindowStyle Hidden `
            -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru
    } catch {
        Write-LogEntry 'ERROR' "COMFYUI_START_FAILED: $_"
        return $false
    }
    Write-LogEntry 'INFO' "COMFYUI_STARTED: PID=$($proc.Id), OUT=$stdoutLog, ERR=$stderrLog"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $ready = $false
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        Start-Sleep -Seconds 5
        try {
            $resp = Invoke-WebRequest -Uri $comfyUrl -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        if ($proc.HasExited) {
            Write-LogEntry 'ERROR' "COMFYUI_CRASHED: PID=$($proc.Id) exited with code $($proc.ExitCode)"
            return $false
        }
    }
    $sw.Stop()
    if ($ready) {
        Write-LogEntry 'SUCCESS' "COMFYUI_READY: PID=$($proc.Id), elapsed $($sw.Elapsed.TotalSeconds.ToString('F1'))s"
        return $true
    } else {
        Write-LogEntry 'ERROR' "COMFYUI_TIMEOUT: not ready after ${TimeoutSeconds}s"
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        return $false
    }
}

function Test-Environment {
    Write-LogEntry 'INFO' '=== Verification environnement ==='
    $ok = $true
    if (-not (Test-Path $pythonExe)) { Write-LogEntry 'ERROR' "Python manquant"; $ok = $false }
    else { Write-LogEntry 'INFO' 'Python: OK' }
    if (-not (Test-Path $ffmpegExe)) { Write-LogEntry 'WARN' 'FFmpeg manquant' }
    else { Write-LogEntry 'INFO' 'FFmpeg: OK' }
    if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }
    return $ok
}

function Test-Services {
    Write-LogEntry 'INFO' '=== Verification services ==='
    $results = @{}
    try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:8188/system_stats' -Method GET -TimeoutSec 5 -UseBasicParsing; $results['ComfyUI'] = 'PASS' } catch { $results['ComfyUI'] = 'FAIL' }
    try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:11434/api/tags' -Method GET -TimeoutSec 5 -UseBasicParsing; $results['Ollama'] = 'PASS' } catch { $results['Ollama'] = 'FAIL' }
    try { $gpu = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null; if ($gpu) { $results['GPU'] = 'PASS (' + $gpu.Trim() + ')' } else { $results['GPU'] = 'ABSENT' } } catch { $results['GPU'] = 'FAIL' }
    try { $db = Join-Path $ProjectRoot 'data\factory.db'; if (Test-Path $db) { $results['SQLite'] = 'PASS' } else { $results['SQLite'] = 'NEW' } } catch { $results['SQLite'] = 'FAIL' }
    $results.GetEnumerator() | ForEach-Object { Write-LogEntry 'INFO' "$($_.Key): $($_.Value)" }
    return $results
}

function Show-Menu {
    Write-Host '=== TikTokHistoryFactory ===' -ForegroundColor Cyan
    Write-Host '1. TEST END-TO-END (1 episode complet avec confirmation)'
    Write-Host '2. AUTO 10h'
    Write-Host '3. AUTO 12h'
    Write-Host '4. AUTO 14h'
    Write-Host '5. Etat usine'
    Write-Host '6. PUBLIER episode (confirmation explicite)'
    Write-Host '7. Diagnostic'
    Write-Host '8. Reprendre Biafra 1967 (RUN_ID ffd86c8f2dcc)'
    Write-Host '0. Quitter'
}

function Invoke-Orchestrator {
    param([string]$ModeArg, [string]$SubjectArg = '', [string]$RunIdArg = '', [switch]$Resume = $false, [string]$PublishMode = '', [string]$DueAt = '')
    $argsList = @($orchPath, '--mode', $ModeArg)
    if ($SubjectArg) { $argsList += @('--subject', $SubjectArg) }
    if ($RunIdArg) { $argsList += @('--run-id', $RunIdArg) }
    if ($Resume) { $argsList += '--resume' }
    if ($PublishMode) { $argsList += @('--publish-mode', $PublishMode) }
    if ($DueAt) { $argsList += @('--due-at', $DueAt) }
    if ($ModeArg -eq 'Publish') { $argsList += '--publish' }

    Write-LogEntry 'INFO' "Orchestrator: python $orchPath $argsList"
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $argsList -WorkingDirectory $ProjectRoot -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $env:TEMP 'thf_stdout.txt') -RedirectStandardError (Join-Path $env:TEMP 'thf_stderr.txt')
    $stdout = Get-Content (Join-Path $env:TEMP 'thf_stdout.txt') -Raw -ErrorAction SilentlyContinue
    $stderr = Get-Content (Join-Path $env:TEMP 'thf_stderr.txt') -Raw -ErrorAction SilentlyContinue
    return @{ exitCode=$proc.ExitCode; stdout=$stdout; stderr=$stderr }
}

function Get-ParisNow {
    return [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date), 'W. Europe Standard Time')
}

function Get-NextSlotParis {
    param([int]$Hour)
    $now = Get-ParisNow
    $target = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $Hour -Minute 0 -Second 0
    if ($now -gt $target) { $target = $target.AddDays(1) }
    return $target
}

# --- Main flow ---
switch ($Mode) {
    'Menu' {
        Show-Menu
        $c = Read-Host 'Choix'
        switch ($c) {
            '1' { $Mode = 'TestEndToEnd' }
            '2' { $Mode = 'Auto10h' }
            '3' { $Mode = 'Auto12h' }
            '4' { $Mode = 'Auto14h' }
            '5' { $Mode = 'Status' }
            '6' { $Mode = 'Publish' }
            '7' { $Mode = 'Diagnostic' }
            '8' { $Mode = 'Resume'; $Subject = 'biafra-war-1967'; $RunId = 'ffd86c8f2dcc' }
            '0' { exit 0 }
            default { Write-Error 'Choix invalide'; exit 2 }
        }
    }
}

if ($Mode -eq 'Status') {
    Test-Environment | Out-Null
    $result = Invoke-Orchestrator -ModeArg 'Status'
    if ($result.stdout) { Write-Host $result.stdout }
    exit $result.exitCode
}

if ($Mode -eq 'Diagnostic') {
    Test-Environment | Out-Null
    $comfyOk = Initialize-ComfyUI
    Test-Services
    exit 0
}

if ($Mode -eq 'Publish') {
    if (-not $Subject) { Write-Error 'Subject requis pour publication'; exit 1 }
    if (-not $RunId) { Write-Error 'RunId requis pour publication'; exit 1 }
    $pubMode = 'customScheduled'
    $dueAt = ''
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host "PUBLICATION: $Subject | RUN_ID=$RunId"
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '  1 = Publier maintenant (shareNow)'
    Write-Host '  2 = Programmer a un creneau futur'
    Write-Host '  3 = Annuler'
    Write-Host '========================================' -ForegroundColor Cyan
    $choice = Read-Host 'Votre choix (1/2/3)'
    if ($choice -eq '1') {
        $pubMode = 'shareNow'
    } elseif ($choice -eq '2') {
        $h = Read-Host 'Heure de publication future (Europe/Paris, format HH, ex: 14)'
        if ($h -match '^\d{1,2}$') {
            $target = Get-NextSlotParis -Hour ([int]$h)
            $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        } else {
            $target = Get-NextSlotParis -Hour 10
            $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        }
    } else {
        Write-LogEntry 'INFO' 'Publication annulee par utilisateur.'
        exit 0
    }
    $result = Invoke-Orchestrator -ModeArg 'Publish' -SubjectArg $Subject -RunIdArg $RunId -PublishMode $pubMode -DueAt $dueAt
    if ($result.stdout) { Write-Host $result.stdout }
    if ($result.stderr) { Write-LogEntry 'WARN' $result.stderr }
    exit $result.exitCode
}

# Production modes: TestEndToEnd, Auto*, Resume
Write-LogEntry 'INFO' "=== MODE: $Mode ==="
if (-not (Test-Environment)) { exit 1 }

# Determine if ComfyUI is needed
$needComfy = $true
if ($Subject) {
    # Check if production already completed
    $checkPy = @"
import sqlite3, os
conn = sqlite3.connect(r'$dataDir\factory.db')
c = conn.cursor()
c.execute('SELECT status, mp4_path, qc_passed FROM auto_productions WHERE slug=?', ('$Subject',))
row = c.fetchone()
conn.close()
if row and row[0]=='completed' and os.path.exists(row[1]) and row[2]:
    print('SKIP_COMFY')
else:
    print('NEED_COMFY')
"@
    $tmpFile = Join-Path $env:TEMP "thf_check_$(Get-Random).py"
    [System.IO.File]::WriteAllText($tmpFile, $checkPy, [System.Text.UTF8Encoding]::new($false))
    $checkResult = & $pythonExe $tmpFile
    Remove-Item $tmpFile -ErrorAction SilentlyContinue
    if ($checkResult -eq 'SKIP_COMFY') {
        Write-LogEntry 'INFO' 'Sujet deja produit et QC passe - ComfyUI non requis'
        $needComfy = $false
    }
}

if ($needComfy) {
    $comfyOk = Initialize-ComfyUI
    if (-not $comfyOk) {
        Write-LogEntry 'ERROR' 'ComfyUI indisponible - arret'
        exit 1
    }
}

$svc = Test-Services
if ($svc['Ollama'] -eq 'FAIL') { Write-LogEntry 'ERROR' 'Ollama FAIL'; exit 1 }

$isResume = ($Mode -eq 'Resume')
$pyMode = if ($Mode -in @('TestEndToEnd','Resume')) { 'TestEndToEnd' } else { $Mode }

$result = Invoke-Orchestrator -ModeArg $pyMode -SubjectArg $Subject -RunIdArg $RunId -Resume:$isResume
if ($result.stdout) { Write-Host $result.stdout }
if ($result.stderr) { Write-LogEntry 'WARN' $result.stderr }

if ($result.exitCode -ne 0) {
    Write-LogEntry 'ERROR' "Orchestrator a retourne le code $($result.exitCode)"
    exit $result.exitCode
}

# Parse JSON result to determine next action
$jsonResult = $null
try {
    $jsonResult = $result.stdout | ConvertFrom-Json
} catch {
    Write-LogEntry 'WARN' 'Impossible de parser la sortie JSON'
}

if ($jsonResult -and $jsonResult.status -eq 'READY_FOR_PUBLICATION') {
    $rid = $jsonResult.run_id
    $slg = $jsonResult.slug
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host 'EPISODE PRET POUR PUBLICATION' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host "RUN_ID:  $rid"
    Write-Host "EPISODE: $slg"
    Write-Host '----------------------------------------' -ForegroundColor Cyan
    Write-Host 'OPTIONS:'
    Write-Host '  1 = Publier maintenant (shareNow)'
    Write-Host '  2 = Programmer a un creneau futur'
    Write-Host '  3 = Annuler la publication'
    Write-Host '========================================' -ForegroundColor Cyan
    $choice = Read-Host 'Votre choix (1/2/3)'
    if ($choice -eq '1') {
        $pubResult = Invoke-Orchestrator -ModeArg 'Publish' -SubjectArg $slg -RunIdArg $rid -PublishMode 'shareNow'
        if ($pubResult.stdout) { Write-Host $pubResult.stdout }
    } elseif ($choice -eq '2') {
        $h = Read-Host 'Heure de publication future (Europe/Paris, format HH, ex: 14)'
        if ($h -match '^\d{1,2}$') {
            $target = Get-NextSlotParis -Hour ([int]$h)
            $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        } else {
            $target = Get-NextSlotParis -Hour 10
            $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        }
        $pubResult = Invoke-Orchestrator -ModeArg 'Publish' -SubjectArg $slg -RunIdArg $rid -PublishMode 'customScheduled' -DueAt $dueAt
        if ($pubResult.stdout) { Write-Host $pubResult.stdout }
    } else {
        Write-LogEntry 'INFO' 'Publication annulee par utilisateur.'
    }
}

Write-LogEntry 'INFO' '=== Termine ==='
exit 0
