<#
TikTokHistoryFactory V5 — Menu principal PowerShell
Production locale de vidéos historiques manga TikTok (90s, narration EN, sous-titres FR)
Aucune publication automatique. Connecteur TikTok désactivé par défaut.
#>
[CmdletBinding()]
param(
    [ValidateSet('Menu','Doctor','Preflight','Test','Pilot','PilotV5','Production','Status','Resume','Export','ExportV5','Schedule','Config','TikTokMock')]
    [string]$Mode = 'Menu',
    [string]$Topic = '',
    [string]$Dossier = '',
    [string]$Storyboard = '',
    [string]$Slug = '',
    [string]$OutputDir = '',
    [int]$JobId = 0,
    [int]$DurationSeconds = 90,
    [int]$MaxVideos = 3,
    [switch]$DryRun,
    [switch]$SkipImages,
    [switch]$Nvenc
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Environnement Python local manquant.' }

function Show-Menu {
    Write-Host '=== TikTokHistoryFactory V5 ===' -ForegroundColor Cyan
    Write-Host '1 Diagnostic complet | 2 Préflight V5 | 3 Tests unitaires'
    Write-Host '4 Pilote Thiaroye V5 | 5 Production générique V5 | 6 État des tâches'
    Write-Host '7 Exporter un rendu | 8 Planification (INACTIVE) | 9 Config | 10 Tests TikTok Mock | 0 Quitter'
}

if ($Mode -eq 'Menu') {
    Show-Menu
    $choice = Read-Host 'Choix'
    switch ($choice) {
        '1' { $Mode = 'Doctor' }
        '2' { $Mode = 'Preflight' }
        '3' { $Mode = 'Test' }
        '4' { $Mode = 'PilotV5' }
        '5' { $Mode = 'Production' }
        '6' { $Mode = 'Status' }
        '7' { $Mode = 'ExportV5' }
        '8' { $Mode = 'Schedule' }
        '9' { $Mode = 'Config' }
        '10' { $Mode = 'TikTokMock' }
        '0' { exit 0 }
        default { Write-Error 'Choix invalide'; exit 2 }
    }
}

$env:PATH += ";$ProjectRoot\ffmpeg\bin"

switch ($Mode) {
    'Doctor' {
        Write-Host '=== DIAGNOSTIC ===' -ForegroundColor Green
        $diagnostics = @{}
        # Python
        try { & $pythonExe --version 2>&1; $diagnostics['Python'] = 'PASS' } catch { $diagnostics['Python'] = 'FAIL' }
        # FFmpeg
        try { & ffmpeg -version | Select-Object -First 1; $diagnostics['FFmpeg'] = 'PASS' } catch { $diagnostics['FFmpeg'] = 'FAIL' }
        # ComfyUI
        try { $stats = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 5; $diagnostics['ComfyUI'] = 'PASS (' + $stats.system.comfyui_version + ')' } catch { $diagnostics['ComfyUI'] = 'FAIL' }
        # Piper
        try { $piper = & (Join-Path $ProjectRoot '.venv\Scripts\piper.exe') --help 2>$null | Select-Object -First 1; $diagnostics['Piper'] = 'PASS' } catch { $diagnostics['Piper'] = 'FAIL' }
        # GPU
        try { $gpu = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; $diagnostics['GPU'] = 'PASS (' + $gpu + ')' } catch { $diagnostics['GPU'] = 'FAIL' }
        $diagnostics | Format-Table -AutoSize
        exit 0
    }
    'Preflight' {
        & $pythonExe (Join-Path $ProjectRoot 'TikTokHistoryFactory_finish_v5\finish_pilot.py') --project $ProjectRoot --preflight
        exit $LASTEXITCODE
    }
    'Test' {
        Write-Host 'Tests unitaires V5...' -ForegroundColor Cyan
        & $pythonExe (Join-Path $ProjectRoot 'TikTokHistoryFactory_finish_v5\test_finish_pilot.py')
        $unit = $LASTEXITCODE
        Write-Host "Unit tests: $(if ($unit -eq 0) { 'PASS' } else { 'FAIL' })"
        # Test imports modulaires
        & $pythonExe -c "from tiktok_history_factory.pipeline.orchestrator import PipelineOrchestrator; print('Import orchestrator: PASS')"
        & $pythonExe -c "from tiktok_history_factory.providers.tiktok_official import TikTokOfficialProvider; p=TikTokOfficialProvider('',''); print('TikTok provider default mode:', p.mode)"
        exit 0
    }
    'PilotV5' {
        Write-Host '=== PILOTE THIAROYE V5 ===' -ForegroundColor Cyan
        $v5script = Join-Path $ProjectRoot 'TikTokHistoryFactory_finish_v5\finish_pilot.py'
        $args = @('--project', $ProjectRoot)
        if ($SkipImages) { $args += '--skip-image-generation' }
        if ($Nvenc) { $args += '--nvenc' }
        & $pythonExe $v5script @args
        exit $LASTEXITCODE
    }
    'Production' {
        Write-Host '=== PRODUCTION GENERIQUE V5 ===' -ForegroundColor Cyan
        if (-not $Storyboard -or -not $Slug -or -not $OutputDir) {
            Write-Error 'Paramètres requis: -Storyboard <path> -Slug <id> -OutputDir <path>'
            exit 2
        }
        $orch = Join-Path $ProjectRoot 'src\v5_factory\orchestrator_generic.py'
        $args = @('--storyboard', $Storyboard, '--slug', $Slug, '--output', $OutputDir, '--project', $ProjectRoot)
        if ($Nvenc) { $args += '--nvenc' }
        & $pythonExe $orch @args
        exit $LASTEXITCODE
    }
    'Status' {
        & $pythonExe -m tiktok_history_factory list 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'Aucune tâche en base (SQLite peut ne pas exister encore).'
        }
        Write-Host 'Rendus V5 disponibles:'
        Get-ChildItem -Path (Join-Path $ProjectRoot 'output') -Directory | ForEach-Object {
            $mp4s = Get-ChildItem -Path $_.FullName -Filter '*.mp4' -Recurse -ErrorAction SilentlyContinue
            if ($mp4s) { Write-Host "  $($_.Name): $($mp4s.Count) MP4(s)" }
        }
        exit 0
    }
    'ExportV5' {
        Write-Host '=== EXPORT LOCAL V5 ===' -ForegroundColor Cyan
        $outDir = Join-Path $ProjectRoot 'output'
        $dirs = Get-ChildItem -Path $outDir -Directory | Where-Object { (Get-ChildItem -Path $_.FullName -Filter '*.mp4' -Recurse -ErrorAction SilentlyContinue) }
        if (-not $dirs) { Write-Host 'Aucun rendu V5 trouvé.'; exit 1 }
        $dirs | ForEach-Object { $i=0 } { $i++; Write-Host "$i. $($_.Name)" }
        $sel = Read-Host 'Sélectionner le numéro à exporter'
        $target = $dirs[$sel-1].FullName
        $exportDir = Join-Path $outDir 'ready' $dirs[$sel-1].Name
        New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
        Get-ChildItem -Path $target -Filter '*.mp4' -Recurse | ForEach-Object {
            Copy-Item $_.FullName (Join-Path $exportDir $_.Name) -Force
            Write-Host "Exporté: $($_.Name)"
        }
        Write-Host "Export terminé dans: $exportDir"
        exit 0
    }
    'Schedule' {
        Write-Host '=== PLANIFICATION WINDOWS ===' -ForegroundColor Yellow
        Write-Host 'ÉTAT: INACTIVE. Aucune tâche planifiée ne sera créée sans consentement explicite.'
        Write-Host 'Pour activer après validation: utiliser schtasks /create avec déclencheurs horaires.'
        Write-Host 'Les tâches planifiées seraient: 3 créneaux/jour, Europe/Paris, désactivées par défaut.'
        exit 0
    }
    'Config' {
        Write-Host '=== CONFIGURATION ===' -ForegroundColor Cyan
        $envPath = Join-Path $ProjectRoot '.env'
        if (Test-Path $envPath) {
            Get-Content $envPath | Where-Object { -not $_.StartsWith('#') -and $_.Trim() -ne '' -and -not $_.Contains('TOKEN') -and -not $_.Contains('SECRET') -and -not $_.Contains('KEY') } | ForEach-Object { Write-Host $_ }
        }
        Write-Host 'TikTok publish mode:' (Get-Content $envPath | Select-String 'TIKTOK_PUBLISH_MODE')
        Write-Host 'TikTok enabled:' (Get-Content $envPath | Select-String 'TIKTOK_PUBLISH_ENABLED')
        exit 0
    }
    'TikTokMock' {
        Write-Host '=== TEST CONNECTEUR TIKTOK MOCK ===' -ForegroundColor Cyan
        & $pythonExe -c "
from tiktok_history_factory.providers.tiktok_official import TikTokOfficialProvider

# Test mode LOCAL_EXPORT (défaut)
p = TikTokOfficialProvider('fake_key', 'fake_secret')
result = p.upload_video('test.mp4', 'Test', 'Description test')
print('LOCAL_EXPORT:', result['status'], '| mode:', result['mode'])

# Test mode TIKTOK_DRAFT sans token
p2 = TikTokOfficialProvider('fake_key', 'fake_secret', mode='TIKTOK_DRAFT')
result2 = p2.upload_video('test.mp4', 'Test', 'Description test')
print('TIKTOK_DRAFT (no token):', result2['status'])

# Test mode TIKTOK_PUBLIC sans credentials
p3 = TikTokOfficialProvider('', '', mode='TIKTOK_PUBLIC')
result3 = p3.upload_video('test.mp4', 'Test', 'Description test')
print('TIKTOK_PUBLIC (no creds):', result3['status'], '|', result3.get('error',''))

print('TikTok mock tests: PASS')
"
        exit 0
    }
}
