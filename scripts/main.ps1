#Requires -Version 5.1
[CmdletBinding()]
param(
    [ValidateSet('Menu','Doctor','Install','Test','Pilot','TestImage','TestWan','Status','Resume','Export','Config','Schedule','dryrun','comfyui','Production')]
    [string]$Mode = 'Menu',
    [string]$Topic = '',
    [string]$Dossier = '',
    [int]$JobId = 0,
    [int]$DurationSeconds = 25,
    [int]$MaxVideos = 3,
    [bool]$Publish = $false,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Environnement Python local manquant.' }
if ($Publish) { throw 'Publication interdite dans le pilote.' }
if ($DurationSeconds -lt 20 -or $DurationSeconds -gt 30) { throw 'Le pilote doit durer de 20 a 30 secondes.' }
if ($DryRun) { $Mode = 'dryrun' }
if ($Mode -eq 'Menu') {
    Write-Host 'TikTokHistoryFactory - pilote local sans publication'
    Write-Host '1 Diagnostic | 2 Installer les manquants | 3 Tests | 4 Pilote reel'
    Write-Host '5 Image GPU | 6 Etat Wan | 7 Taches | 8 Reprise | 9 Configuration'
    Write-Host '10 Exports | 11 Planification (desactivee) | 12 Quitter'
    $choice = Read-Host 'Choix'
    $menuModes = @{'1'='Doctor';'2'='Install';'3'='Test';'4'='Pilot';'5'='TestImage';'6'='TestWan';'7'='Status';'8'='Resume';'9'='Config';'10'='Export';'11'='Schedule'}
    if ($choice -eq '12') { exit 0 }
    if (-not $menuModes.ContainsKey($choice)) { Write-Error 'Choix invalide'; exit 2 }
    $Mode = $menuModes[$choice]
}
switch ($Mode) {
    'Doctor' { & $pythonExe -m tiktok_history_factory doctor; exit $LASTEXITCODE }
    'Test' { & $pythonExe -m unittest discover -s tests -v; exit $LASTEXITCODE }
    'Install' {
        Write-Host 'Installation locale des dependances manquantes et verification des modeles officiels. Aucun composant systeme.'
        & $pythonExe -m pip install -r requirements-lock.txt
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
        & $pythonExe scripts/acquire_pilot_assets.py
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
        & $pythonExe scripts/acquire_v2_assets.py
        exit $LASTEXITCODE
    }
    'TestImage' { & $pythonExe -m tiktok_history_factory test-image; exit $LASTEXITCODE }
    'TestWan' { & $pythonExe -m tiktok_history_factory test-wan; exit $LASTEXITCODE }
    'Production' { Write-Error 'Production quotidienne bloquee avant validation humaine du pilote.'; exit 2 }
    'Schedule' { Write-Host 'Aucune tache planifiee activee. Activation soumise a validation du pilote et horaires explicites.'; exit 0 }
    'Status' { & $pythonExe -m tiktok_history_factory list; exit $LASTEXITCODE }
    'Config' { & $pythonExe -m tiktok_history_factory doctor; Write-Host 'Configuration locale : .env ; secrets non affiches.'; exit $LASTEXITCODE }
    'Export' { Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'output/review') -Filter pilot.mp4 -Recurse | Select-Object FullName,Length; exit 0 }
    'dryrun' { & $pythonExe -m tiktok_history_factory doctor; exit $LASTEXITCODE }
    'comfyui' { Write-Host 'Utiliser scripts/start_comfyui.ps1 si le serveur existant est arrete.'; exit 0 }
}
# Pilot and Resume share the same idempotent runner. A job ID is resolved to its dossier.
if ($JobId) {
    $tasks = & $pythonExe -c 'import json; from tiktok_history_factory.config.settings import Settings; from tiktok_history_factory.database.models import DatabaseManager; print(json.dumps(DatabaseManager(str(Settings().DB_PATH)).list_tasks(limit=10000)))'
    $task = ($tasks | ConvertFrom-Json) | Where-Object { $_.id -eq $JobId }
    if (-not $task) { throw 'JobId inconnu.' }
    $Topic = $task.topic_slug
}
Write-Host 'Un seul pilote documente, images GPU, voix anglaise et sous-titres francais, export pour revue. Aucun upload.'
$pilotArgs = @('-m','tiktok_history_factory','pilot')
if ($Mode -eq 'Resume') { $pilotArgs += '--resume' }
if ($Topic) { $pilotArgs += @('--topic',$Topic) }
if ($Dossier) { $pilotArgs += @('--dossier',$Dossier) }
& $pythonExe @pilotArgs
exit $LASTEXITCODE
