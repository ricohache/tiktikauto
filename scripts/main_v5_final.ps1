#Requires -Version 5.1
<#
.SYNOPSIS
    Menu principal autonome TikTokHistoryFactory V5.
.DESCRIPTION
    Production locale de videos historiques manga TikTok (90s, narration EN, sous-titres FR).
    Aucune publication automatique. Connecteur Buffer en mode lecture seule par defaut.
    Ne modifie aucune permission, profil reseau ou configuration globale.
#>
[CmdletBinding()]
param(
    [ValidateSet('Menu','Status','Batch1','Batch3','Resume','Export','TikTokMock','TikTokPublish','BufferConfig','Diagnostic','Quit')]
    [string]$Mode = 'Menu'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Environnement Python local manquant.' }

function Show-Menu {
    Write-Host '=== TikTokHistoryFactory V5 - Usine Autonome ===' -ForegroundColor Cyan
    Write-Host '1. Generer 1 episode (decouverte + production + QC)'
    Write-Host '2. Generer 3 episodes (file quotidienne)'
    Write-Host '3. Etat de l usine (SQLite, GPU, file TikTok)'
    Write-Host '4. Reprendre apres incident'
    Write-Host '5. Exporter les episodes prets pour TikTok'
    Write-Host '6. Test connecteur TikTok (MOCK, aucun envoi)'
    Write-Host '7. Diagnostic complet'
    Write-Host '8. Publication TikTok — consulter file, etat, metadonnees'
    Write-Host '9. Configurer cle API Buffer (securisee — jamais en clair)'
    Write-Host '0. Quitter'
}

$runner = Join-Path $ProjectRoot 'src\v5_factory\autonomous_runner.py'
$tiktokMenu = Join-Path $ProjectRoot 'src\v5_factory\tiktok_publish_menu.py'
$bufferConfig = Join-Path $ProjectRoot 'src\v5_factory\buffer_config_cli.py'

switch ($Mode) {
    'Menu' {
        Show-Menu
        $choice = Read-Host 'Choix'
        switch ($choice) {
            '1' { $Mode = 'Batch1' }
            '2' { $Mode = 'Batch3' }
            '3' { $Mode = 'Status' }
            '4' { $Mode = 'Resume' }
            '5' { $Mode = 'Export' }
            '6' { $Mode = 'TikTokMock' }
            '7' { $Mode = 'Diagnostic' }
            '8' { $Mode = 'TikTokPublish' }
            '9' { $Mode = 'BufferConfig' }
            '0' { exit 0 }
            default { Write-Error 'Choix invalide'; exit 2 }
        }
    }
    'Status' {
        & $pythonExe $runner --status
        exit $LASTEXITCODE
    }
    'Batch1' {
        Write-Host '=== GENERATION 1 EPISODE ===' -ForegroundColor Cyan
        & $pythonExe $runner --batch 1
        exit $LASTEXITCODE
    }
    'Batch3' {
        Write-Host '=== GENERATION 3 EPISODES ===' -ForegroundColor Cyan
        & $pythonExe $runner --batch 3
        exit $LASTEXITCODE
    }
    'Resume' {
        Write-Host '=== REPRISE APRES INCIDENT ===' -ForegroundColor Cyan
        & $pythonExe $runner --resume
        exit $LASTEXITCODE
    }
    'Export' {
        Write-Host '=== EXPORT TIKTOK ===' -ForegroundColor Cyan
        & $pythonExe $runner --export
        exit $LASTEXITCODE
    }
    'TikTokMock' {
        Write-Host '=== TEST CONNECTEUR TIKTOK MOCK ===' -ForegroundColor Cyan
        & $pythonExe -c "
from tiktok_history_factory.providers.tiktok_official import TikTokOfficialProvider
import json
p = TikTokOfficialProvider('fake_key', 'fake_secret')
r = p.upload_video('test.mp4', 'Test', 'Description test')
print('Mode:', r['mode'])
print('Status:', r['status'])
print('Note:', r['note'])
print('TikTokMock: PASS (aucun appel API effectue)')
"
        exit 0
    }
    'TikTokPublish' {
        Write-Host '=== PUBLICATION TIKTOK ===' -ForegroundColor Cyan
        & $pythonExe $tiktokMenu
        exit 0
    }
    'BufferConfig' {
        Write-Host '=== CONFIGURATION BUFFER API (SEcurisee) ===' -ForegroundColor Yellow
        Write-Host "La cle sera lue de maniere securisee (masquee) et stockee"
        Write-Host "via DPAPI Windows. Elle ne passera JAMAIS en argument de processus."
        Write-Host ""
        # Appelle le script Python dedie qui utilise getpass
        & $pythonExe $bufferConfig
        exit 0
    }
    'Diagnostic' {
        Write-Host '=== DIAGNOSTIC ===' -ForegroundColor Green
        $diagnostics = @{}
        try { & $pythonExe --version 2>&1; $diagnostics['Python'] = 'PASS' } catch { $diagnostics['Python'] = 'FAIL' }
        try { $ff = & (Join-Path $ProjectRoot 'ffmpeg\bin\ffmpeg.exe') -version 2>$null | Select-Object -First 1; $diagnostics['FFmpeg'] = 'PASS' } catch { $diagnostics['FFmpeg'] = 'FAIL' }
        try { $gpu = & nvidia-smi --query-gpu=name --format=csv,noheader 2>$null; if ($gpu) { $diagnostics['GPU'] = 'PASS (' + $gpu + ')' } else { $diagnostics['GPU'] = 'ABSENT' } } catch { $diagnostics['GPU'] = 'FAIL' }
        try { & $pythonExe $runner --status 2>$null; $diagnostics['FactoryDB'] = 'PASS' } catch { $diagnostics['FactoryDB'] = 'FAIL' }
        $diagnostics.GetEnumerator() | ForEach-Object { Write-Host ($_.Key + ': ' + $_.Value) }
        exit 0
    }
}

if ($Mode -ne 'Menu') {
    & $PSCommandPath -Mode $Mode
}
