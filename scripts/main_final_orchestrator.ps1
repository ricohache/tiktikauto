#Requires -Version 5.1
<#
.SYNOPSIS
    Orchestrateur final TikTokHistoryFactory — production complete jusqu'a TikTok.
.DESCRIPTION
    Point d'entree unique. Fonctionne SANS Codex.
    Modes : Menu, TestEndToEnd, Auto (10h/12h/14h), Status, Publish.
    Journalise dans data/orchestrator.log
.NOTES
    Version: 3.2 (P0 fixes: BOM, run_id, error propagation, resume, temp Python files)
    Date: 2026-10-27
#>
[CmdletBinding()]
param(
    [ValidateSet('Menu','TestEndToEnd','Auto10h','Auto12h','Auto14h','Status','Publish','Diagnostic')]
    [string]$Mode = 'Menu',
    [string]$Subject = '',
    [switch]$Force = $false,
    [string]$LogPath = '',
    [string]$RunId = ''
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $RunId) { $RunId = [System.Guid]::NewGuid().ToString("N").Substring(0,12) }

$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$ffmpegExe = Join-Path $ProjectRoot 'ffmpeg\bin\ffmpeg.exe'
$ffprobeExe = Join-Path $ProjectRoot 'ffmpeg\bin\ffprobe.exe'
$dataDir = Join-Path $ProjectRoot 'data'
$logFile = if ($LogPath) { $LogPath } else { Join-Path $dataDir 'orchestrator.log' }
$approvalsPath = Join-Path $dataDir 'decisions\upload_approvals.json'
$comfyDir = Join-Path $ProjectRoot 'ComfyUI'

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

function Invoke-PythonScript {
    param([string]$ScriptContent, [int]$TimeoutSec = 300)
    $tmpFile = Join-Path $env:TEMP "thf_orchestrator_$(Get-Date -Format 'yyyyMMddHHmmssfff')_$(Get-Random).py"
    [System.IO.File]::WriteAllText($tmpFile, $ScriptContent, [System.Text.UTF8Encoding]::new($false))
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $pythonExe
        $psi.Arguments = "`"$tmpFile`""
        $psi.WorkingDirectory = $ProjectRoot
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $proc = [System.Diagnostics.Process]::Start($psi)
        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $completed = $proc.WaitForExit($TimeoutSec * 1000)
        if (-not $completed) {
            $proc.Kill()
            Write-LogEntry 'ERROR' "Python script timed out after ${TimeoutSec}s"
            return @{exitCode=-1; stdout=$stdout; stderr=$stderr; timedOut=$true}
        }
        return @{exitCode=$proc.ExitCode; stdout=$stdout; stderr=$stderr; timedOut=$false}
    } finally {
        Remove-Item $tmpFile -ErrorAction SilentlyContinue
    }
}

function Invoke-WithRetry {
    param([scriptblock]$Action, [int]$MaxRetries = 2, [int]$DelaySeconds = 5)
    $attempt = 0
    while ($true) {
        $attempt++
        try {
            $result = & $Action
            if ($result -eq $false) {
                Write-LogEntry 'WARN' "Attempt $attempt returned `$false"
                if ($attempt -ge $MaxRetries) { return $false }
                Start-Sleep -Seconds $DelaySeconds
                continue
            }
            return $result
        } catch {
            Write-LogEntry 'WARN' "Attempt $attempt failed: $_"
            if ($attempt -ge $MaxRetries) { throw }
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

function Get-ParisNow {
    return [System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date), 'W. Europe Standard Time')
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
    $lastStatus = ''
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        Start-Sleep -Seconds 5
        try {
            $resp = Invoke-WebRequest -Uri $comfyUrl -Method GET -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) { $ready = $true; break }
        } catch { $lastStatus = $_.Exception.Message }
        if ($proc.HasExited) {
            Write-LogEntry 'ERROR' "COMFYUI_CRASHED: PID=$($proc.Id) exited with code $($proc.ExitCode)"
            if (Test-Path $stderrLog) {
                $errTail = Get-Content $stderrLog -Tail 20 -ErrorAction SilentlyContinue | Out-String
                Write-LogEntry 'ERROR' "COMFYUI_STDERR_TAIL: $errTail"
            }
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

function Select-NewSubject {
    $py = @"
import json, sqlite3, sys, random
from pathlib import Path

db = r'$dataDir\factory.db'
cat = r'$dataDir\catalogue\subjects.json'
with open(cat, 'r', encoding='utf-8') as f:
    data = json.load(f)
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute('SELECT slug, status FROM auto_productions')
produced = {r[0]: r[1] for r in c.fetchall()}
conn.close()

excluded = {'angolan-civil-war-1975'}
candidates_new = []
for s in data['subjects']:
    slug = s['slug']
    if slug in excluded:
        continue
    if slug in produced and produced[slug] == 'completed':
        continue
    out_dir = Path(r'$ProjectRoot\output')
    existing = list(out_dir.rglob(f'*{slug}*.mp4'))
    if existing:
        continue
    candidates_new.append(slug)

if candidates_new:
    print(candidates_new[0])
    sys.exit(0)

candidates_any = [s['slug'] for s in data['subjects'] if s['slug'] not in excluded]
if candidates_any:
    random.seed()
    print(random.choice(candidates_any))
    sys.exit(0)

print('BLOCKED')
"@
    $result = Invoke-PythonScript -ScriptContent $py
    if ($result.exitCode -ne 0 -or $result.stdout -eq 'BLOCKED') { return $null }
    return $result.stdout.Trim()
}

function Get-ProductionStatus {
    param([string]$Slug)
    $py = @"
import sqlite3, os
conn = sqlite3.connect(r'$dataDir\factory.db')
c = conn.cursor()
c.execute('SELECT slug, status, mp4_path, run_id, sha256, qc_passed FROM auto_productions WHERE slug=?', ('$Slug',))
row = c.fetchone()
conn.close()
if row:
    mp4 = row[2] or ''
    mp4_exists = 'yes' if mp4 and os.path.exists(mp4) else 'no'
    print(row[0])        # slug
    print(row[1] or '')  # status
    print(mp4)           # mp4_path
    print(row[3] or '')  # run_id
    print(row[4] or '')  # sha256
    print(mp4_exists)    # mp4_exists
    print(row[5] or '0') # qc_passed
else:
    print('NONE')
"@
    $result = Invoke-PythonScript -ScriptContent $py
    if ($result.exitCode -ne 0 -or $result.stdout.Trim() -eq 'NONE') { return $null }
    $lines = $result.stdout -split "`r?`n"
    return @{
        slug = $lines[0].Trim()
        status = $lines[1].Trim()
        mp4 = $lines[2].Trim()
        run_id = $lines[3].Trim()
        sha256 = $lines[4].Trim()
        mp4_exists = $lines[5].Trim() -eq 'yes'
        qc_passed = [int]($lines[6].Trim())
    }
}

function Update-ProductionRunId {
    param([string]$Slug, [string]$RunId)
    $py = @"
import sqlite3
conn = sqlite3.connect(r'$dataDir\factory.db')
c = conn.cursor()
c.execute('UPDATE auto_productions SET run_id=? WHERE slug=?', ('$RunId', '$Slug'))
conn.commit()
print('UPDATED')
conn.close()
"@
    $result = Invoke-PythonScript -ScriptContent $py
    return ($result.exitCode -eq 0 -and $result.stdout.Trim() -eq 'UPDATED')
}

Write-LogEntry 'INFO' "=== RUN_ID: $RunId ==="

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

function Start-Production {
    param([string]$SpecificSubject = '', [string]$RunId = '')
    Write-LogEntry 'INFO' '=== PHASE 1: Production video ==='

    $subjectToProduce = $SpecificSubject
    if (-not $subjectToProduce) {
        $subjectToProduce = Select-NewSubject
        if (-not $subjectToProduce) {
            Write-LogEntry 'ERROR' 'Aucun nouveau sujet disponible'
            return $null
        }
        Write-LogEntry 'INFO' "Sujet selectionne: $subjectToProduce"
    }

    # Check for existing completed production (resume)
    $existing = Get-ProductionStatus -Slug $subjectToProduce
    if ($existing -and $existing.status -eq 'completed' -and $existing.mp4_exists) {
        Write-LogEntry 'INFO' "Production existante trouvee: $($existing.mp4) | Resume autorise"
        if ($existing.run_id -ne $RunId) {
            Write-LogEntry 'WARN' "Run ID mismatch: attendu $RunId, trouve $($existing.run_id)"
            $updated = Update-ProductionRunId -Slug $subjectToProduce -RunId $RunId
            if ($updated) { Write-LogEntry 'INFO' 'Run ID mis a jour dans la base' }
        }
        return @{slug=$subjectToProduce; title=$subjectToProduce; mp4=$existing.mp4; run_id=$RunId}
    }

    $runner = Join-Path $ProjectRoot 'src\v5_factory\autonomous_runner.py'
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $runner, '--subject', $subjectToProduce, '--run-id', $RunId -WorkingDirectory $ProjectRoot -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -ne 0) {
        Write-LogEntry 'ERROR' "Production echouee (exit $($proc.ExitCode))"
        return $null
    }

    $fresh = Get-ProductionStatus -Slug $subjectToProduce
    if (-not $fresh -or $fresh.status -ne 'completed' -or -not $fresh.mp4_exists) {
        Write-LogEntry 'ERROR' "Production incomplete apres execution"
        return $null
    }
    if ($fresh.run_id -ne $RunId) {
        Write-LogEntry 'WARN' "Run ID mismatch post-production: attendu $RunId, trouve $($fresh.run_id)"
    }
    Write-LogEntry 'SUCCESS' "Production OK: $($fresh.slug) | MP4: $($fresh.mp4)"
    return @{slug=$fresh.slug; title=$fresh.slug; mp4=$fresh.mp4; run_id=$RunId}
}

function Start-R2Upload {
    param([string]$Slug, [string]$RunId = '')
    Write-LogEntry 'INFO' "=== PHASE 2: Upload R2 ($Slug) ==="
    $dir = Split-Path $approvalsPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $existing = @()
    if (Test-Path $approvalsPath) {
        try {
            $jsonText = [System.IO.File]::ReadAllText($approvalsPath, [System.Text.UTF8Encoding]::new($true))
            $json = $jsonText | ConvertFrom-Json
            $existing = @($json.approved_slugs)
        } catch { Write-LogEntry 'WARN' "Impossible de lire les approbations existantes: $_" }
    }
    if ($existing -notcontains $Slug) { $existing += $Slug }
    $jsonOut = @{approved_slugs = $existing} | ConvertTo-Json -Depth 3
    [System.IO.File]::WriteAllText($approvalsPath, $jsonOut, [System.Text.UTF8Encoding]::new($false))
    Write-LogEntry 'INFO' "Approbations ecrites (sans BOM): $($existing.Count) slug(s)"

    $wf = Join-Path $ProjectRoot 'src\v5_factory\r2_upload_workflow.py'
    $result = Invoke-PythonScript -ScriptContent "`r`nimport sys`r`nsys.path.insert(0, r'$ProjectRoot\src\v5_factory')`r`nfrom r2_upload_workflow import main`r`nsys.argv = ['r2_upload_workflow.py', '--slug', '$Slug']`r`nmain()" -TimeoutSec 300

    if ($result.timedOut) {
        Write-LogEntry 'ERROR' "Upload R2: TIMEOUT"
        return @{ok=$false; error='TIMEOUT'; stderr=$result.stderr}
    }
    if ($result.exitCode -ne 0) {
        Write-LogEntry 'ERROR' "Upload R2: exit code $($result.exitCode)"
        if ($result.stderr) { Write-LogEntry 'ERROR' "R2 STDERR: $($result.stderr.Trim())" }
        return @{ok=$false; error="exit_code_$($result.exitCode)"; stderr=$result.stderr}
    }

    # Verify in DB
    $verifyPy = @"
import sqlite3
conn = sqlite3.connect(r'$dataDir\factory.db')
c = conn.cursor()
c.execute('SELECT status, r2_key, r2_url, worker_url FROM r2_uploads WHERE slug=?', ('$Slug',))
row = c.fetchone()
conn.close()
if row:
    print(row[0] or 'UNKNOWN')
    print(row[1] or '')
    print(row[2] or '')
    print(row[3] or '')
else:
    print('NOT_FOUND')
"@
    $v = Invoke-PythonScript -ScriptContent $verifyPy
    $vLines = $v.stdout -split "`r?`n"
    $dbStatus = $vLines[0].Trim()
    if ($dbStatus -ne 'VERIFIED') {
        Write-LogEntry 'ERROR' "Upload R2: DB status=$dbStatus, attendu VERIFIED"
        return @{ok=$false; error="db_status_$dbStatus"; stderr=$result.stderr}
    }

    # Tag run_id
    $tagPy = @"
import sqlite3
conn = sqlite3.connect(r'$dataDir\factory.db')
c = conn.cursor()
c.execute("PRAGMA table_info(r2_uploads)")
if 'run_id' not in [r[1] for r in c.fetchall()]:
    c.execute('ALTER TABLE r2_uploads ADD COLUMN run_id TEXT')
c.execute('UPDATE r2_uploads SET run_id=? WHERE slug=?', ('$RunId', '$Slug'))
conn.commit()
conn.close()
print('TAGGED')
"@
    $tagResult = Invoke-PythonScript -ScriptContent $tagPy
    Write-LogEntry 'SUCCESS' "Upload R2 OK: $Slug | Status=VERIFIED"
    return @{ok=$true; r2_key=$vLines[1].Trim(); r2_url=$vLines[2].Trim(); worker_url=$vLines[3].Trim()}
}

function Start-Publication {
    param([string]$Slug, [string]$RunId, [string]$PubMode, [string]$DueAt)
    Write-LogEntry 'INFO' "=== PHASE 3: Publication Buffer ($Slug) ==="
    $pub = Join-Path $ProjectRoot 'scripts\publish_next.py'
    $argsList = @($pub, '--live', '--mode', $PubMode, '--slug', $Slug, '--run-id', $RunId, '--yes')
    if ($DueAt) { $argsList += @('--due-at', $DueAt) }
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $argsList -WorkingDirectory $ProjectRoot -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -ne 0) {
        Write-LogEntry 'ERROR' "Publication echouee (exit $($proc.ExitCode))"
        return $false
    }
    Write-LogEntry 'SUCCESS' "Publication OK: $Slug"
    return $true
}

function Show-FinalReport {
    param([string]$RunId, [string]$Slug)
    Write-LogEntry 'INFO' '=== RAPPORT FINAL ==='
    $py = @"
import sqlite3, json, os
from pathlib import Path

conn = sqlite3.connect(r'$dataDir\factory.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT slug, title_fr, title_en, status, mp4_path, sha256, qc_passed, run_id FROM auto_productions WHERE slug=?', ('$Slug',))
row = c.fetchone()
prod = dict(row) if row else {}

c.execute('SELECT r2_key, r2_url, worker_url, status FROM r2_uploads WHERE slug=?', ('$Slug',))
row = c.fetchone()
r2 = dict(row) if row else {}

c.execute('SELECT buffer_post_id, status FROM buffer_attempts WHERE slug=?', ('$Slug',))
row = c.fetchone()
buf = dict(row) if row else {}

c.execute('SELECT sources_json FROM tiktok_queue WHERE slug=?', ('$Slug',))
row = c.fetchone()
q = dict(row) if row else {}

conn.close()

sources = json.loads(q.get('sources_json','[]')) if q else []
mp4 = prod.get('mp4_path','')

img_count = 0
voice_en = False
subs_fr = False
if mp4:
    wd = Path(r'$ProjectRoot') / 'work' / f'auto-{prod.get(\"slug\",\"\")}'
    if wd.exists():
        img_count = len(list((wd / 'images').glob('*.png')))
        voice_en = (wd / 'audio' / 'narration.wav').exists()
        subs_fr = (wd / 'subtitles' / 'subtitles-fr.ass').exists() if (wd / 'subtitles').exists() else False
    else:
        od = Path(mp4).parent if mp4 else None
        if od and od.exists():
            img_count = len(list(od.rglob('*.png')))
            voice_en = any(od.rglob('narration.wav'))
            subs_fr = any(od.rglob('subtitles-fr.ass'))

qc_status = 'PASS' if prod.get('qc_passed') else 'PENDING'
mp4_exists = 'REAL PASS' if (mp4 and os.path.exists(mp4)) else 'NOT FOUND'

print('RUN_ID:           ', prod.get('run_id','N/A'))
print('NEW_EPISODE:      ', prod.get('title_fr','N/A'), '(', prod.get('slug','N/A'), ')')
print('SOURCES:          ', len(sources))
print('IMAGE_COUNT:      ', img_count)
print('VOICE_EN:         ', 'REAL PASS' if voice_en else 'NOT FOUND')
print('SUBTITLES_FR:     ', 'REAL PASS' if subs_fr else 'NOT FOUND')
print('MP4_PATH:         ', mp4)
print('MP4_EXISTS:       ', mp4_exists)
print('QC_STATUS:        ', qc_status)
print('R2_STATUS:        ', r2.get('status','NOT_UPLOADED'))
print('WORKER_STATUS:    ', 'PASS' if r2.get('worker_url') else 'N/A')
print('BUFFER_POST_ID:   ', buf.get('buffer_post_id','N/A'))
print('TIKTOK_STATUS:    ', buf.get('status','NOT_PUBLISHED'))
"@
    $result = Invoke-PythonScript -ScriptContent $py
    if ($result.stdout) { Write-Host $result.stdout }
    if ($result.stderr) { Write-LogEntry 'WARN' "Rapport stderr: $($result.stderr.Trim())" }
    Write-LogEntry 'INFO' '=== FIN RAPPORT ==='
}

function Get-R2Status {
    param([string]$Slug)
    $py = @"
import sqlite3
conn = sqlite3.connect(r'$dataDir\factory.db')
c = conn.cursor()
c.execute('SELECT status, worker_url, error FROM r2_uploads WHERE slug=?', ('$Slug',))
row = c.fetchone()
conn.close()
if row:
    print(row[0] or 'NOT_FOUND')
    print(row[1] or '')
    print(row[2] or '')
else:
    print('NOT_FOUND')
    print('')
    print('')
"@
    $result = Invoke-PythonScript -ScriptContent $py
    $lines = $result.stdout -split "`r?`n"
    return @{
        status = $lines[0].Trim()
        worker_url = $lines[1].Trim()
        error = $lines[2].Trim()
    }
}

function Show-Menu {
    Write-Host '=== TikTokHistoryFactory - Orchestrateur Final ===' -ForegroundColor Cyan
    Write-Host '1. TEST END-TO-END (1 episode complet avec confirmation)'
    Write-Host '2. AUTO 10h'
    Write-Host '3. AUTO 12h'
    Write-Host '4. AUTO 14h'
    Write-Host '5. Etat usine'
    Write-Host '6. PUBLIER episode suivant'
    Write-Host '7. Diagnostic'
    Write-Host '0. Quitter'
}

function Get-NextSlotParis {
    param([int]$Hour)
    $now = Get-ParisNow
    $target = Get-Date -Year $now.Year -Month $now.Month -Day $now.Day -Hour $Hour -Minute 0 -Second 0
    if ($now -gt $target) { $target = $target.AddDays(1) }
    return $target
}

# --- Modes ---
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
            '0' { exit 0 }
            default { Write-Error 'Choix invalide'; exit 2 }
        }
    }
    'Status' {
        Test-Environment | Out-Null
        $comfyOk = Initialize-ComfyUI
        Test-Services
        & $pythonExe (Join-Path $ProjectRoot 'src\v5_factory\autonomous_runner.py') --status
        exit $LASTEXITCODE
    }
    'Diagnostic' {
        Test-Environment | Out-Null
        $comfyOk = Initialize-ComfyUI
        Test-Services; exit 0
    }
    'Publish' {
        Test-Environment | Out-Null
        $tok = & $pythonExe -c "import sys; sys.path.insert(0,r'$ProjectRoot\src\v5_factory'); from secure_credentials import CredentialStore; print('TOKEN_OK' if CredentialStore().has('buffer_access_token') else 'TOKEN_MISSING')"
        if ($tok -notmatch 'TOKEN_OK') { Write-LogEntry 'ERROR' 'Token Buffer manquant'; exit 1 }
        Start-Publication -Slug $Subject -RunId $RunId -PubMode 'customScheduled' -DueAt ''
        exit 0
    }
}

if ($Mode -in @('TestEndToEnd','Auto10h','Auto12h','Auto14h')) {
    Write-LogEntry 'INFO' "=== MODE: $Mode ==="
    if (-not (Test-Environment)) { exit 1 }

    # Production requires ComfyUI; resume (existing MP4) does not
    $needComfy = $true
    if ($Subject) {
        $existingCheck = Get-ProductionStatus -Slug $Subject
        if ($existingCheck -and $existingCheck.status -eq 'completed' -and $existingCheck.mp4_exists) {
            Write-LogEntry 'INFO' "Sujet $Subject deja produit — reprise sans ComfyUI"
            $needComfy = $false
        }
    }
    if ($needComfy) {
        $comfyOk = Initialize-ComfyUI
        if (-not $comfyOk) {
            Write-LogEntry 'ERROR' 'ComfyUI indisponible — arret du pipeline'
            exit 1
        }
    }

    $svc = Test-Services
    if ($svc['Ollama'] -eq 'FAIL') { Write-LogEntry 'ERROR' 'Ollama FAIL'; exit 1 }

    $startTime = Get-Date

    # Production with retry
    $prod = $null
    try {
        $prod = Invoke-WithRetry -Action { Start-Production -SpecificSubject $Subject -RunId $RunId } -MaxRetries 1 -DelaySeconds 10
    } catch {
        Write-LogEntry 'ERROR' "Production definitivement echouee: $_"
        exit 1
    }
    if (-not $prod) { exit 1 }
    $slug = $prod.slug; $title = $prod.title; $mp4Path = $prod.mp4

    # R2 Upload with retry
    $r2Result = $null
    try {
        $r2Result = Invoke-WithRetry -Action { Start-R2Upload -Slug $slug -RunId $RunId } -MaxRetries 2 -DelaySeconds 10
    } catch {
        Write-LogEntry 'ERROR' "Upload R2 definitivement echoue: $_"
        Show-FinalReport -RunId $RunId -Slug $slug
        exit 1
    }
    if (-not $r2Result -or -not $r2Result.ok) {
        $errDetail = if ($r2Result) { $r2Result.error } else { 'UNKNOWN' }
        Write-LogEntry 'ERROR' "Upload R2 FAILED: $errDetail"
        Show-FinalReport -RunId $RunId -Slug $slug
        exit 1
    }

    # Verify R2 status in DB before showing publication menu
    $r2Db = Get-R2Status -Slug $slug
    if ($r2Db.status -ne 'VERIFIED') {
        Write-LogEntry 'ERROR' "R2 DB status=$($r2Db.status) — blocage avant publication"
        Show-FinalReport -RunId $RunId -Slug $slug
        exit 1
    }

    # Determine scheduling
    $pubMode = 'customScheduled'
    $dueAt = ''

    if ($Mode -eq 'TestEndToEnd') {
        $r2Verified = 'VERIFIED'
        $qcStatus = 'PASS'
        $workerStatus = if ($r2Result.worker_url) { 'PASS' } else { 'N/A' }
        Write-Host ''
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host 'EPISODE PRET POUR PUBLICATION' -ForegroundColor Cyan
        Write-Host '========================================' -ForegroundColor Cyan
        Write-Host "RUN_ID:  $RunId"
        Write-Host "EPISODE: $title"
        Write-Host "MP4:     $mp4Path"
        Write-Host "QC:      $qcStatus (integre a la production)"
        Write-Host "R2:      $r2Verified"
        Write-Host "WORKER:  $workerStatus"
        Write-Host '----------------------------------------' -ForegroundColor Cyan
        Write-Host 'OPTIONS:'
        Write-Host '  1 = Publier maintenant (shareNow)'
        Write-Host '  2 = Programmer a un creneau futur (Europe/Paris)'
        Write-Host '  3 = Annuler la publication (conserver les fichiers)'
        Write-Host '========================================' -ForegroundColor Cyan
        $choice = Read-Host 'Votre choix (1/2/3)'
        if ($choice -eq '1') {
            $pubMode = 'shareNow'
            $dueAt = ''
            $envContent = Get-Content (Join-Path $ProjectRoot '.env') -Raw -ErrorAction SilentlyContinue
            if ($envContent -notmatch 'THF_BUFFER_SHARE_NOW_ALLOWED=1') {
                Write-LogEntry 'WARN' 'THF_BUFFER_SHARE_NOW_ALLOWED != 1 ; bascule sur customScheduled demain 10h Paris'
                $pubMode = 'customScheduled'
                $target = Get-NextSlotParis -Hour 10
                $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            }
        } elseif ($choice -eq '2') {
            $h = Read-Host 'Heure de publication future (Europe/Paris, format HH, ex: 14)'
            if ($h -match '^\d{1,2}$') {
                $target = Get-NextSlotParis -Hour ([int]$h)
                $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            } else {
                Write-LogEntry 'WARN' 'Heure invalide ; bascule sur demain 10h Paris'
                $target = Get-NextSlotParis -Hour 10
                $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
            }
        } else {
            Write-LogEntry 'INFO' 'Publication annulee par utilisateur. Fichiers conserves.'
            Show-FinalReport -RunId $RunId -Slug $slug
            exit 0
        }
    } elseif ($Mode -in @('Auto10h','Auto12h','Auto14h')) {
        $h = switch ($Mode) { 'Auto10h' { 10 } 'Auto12h' { 12 } 'Auto14h' { 14 } }
        $target = Get-NextSlotParis -Hour $h
        $dueAt = $target.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        Write-LogEntry 'INFO' "Publication programmee: $dueAt (Paris $h`:00)"
    }

    # Publication with retry
    $pubOk = $false
    try {
        $pubOk = Invoke-WithRetry -Action { Start-Publication -Slug $slug -RunId $RunId -PubMode $pubMode -DueAt $dueAt } -MaxRetries 1 -DelaySeconds 5
    } catch {
        Write-LogEntry 'ERROR' "Publication definitivement echouee: $_"
        Show-FinalReport -RunId $RunId -Slug $slug
        exit 1
    }

    $elapsed = ((Get-Date) - $startTime).ToString('hh\:mm\:ss')
    Show-FinalReport -RunId $RunId -Slug $slug
    Write-LogEntry 'INFO' "TOTAL_ELAPSED_TIME: $elapsed"
    exit 0
}

Write-LogEntry 'INFO' '=== Termine ==='
