# Compatibility alias; runtime never installs dependencies.
[CmdletBinding()]
param([switch]$DryRun, [switch]$InitDb)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if ($InitDb) {
    & (Join-Path $ProjectRoot '.venv/Scripts/python.exe') -m tiktok_history_factory init
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
}
if ($DryRun) { & (Join-Path $PSScriptRoot 'main.ps1') -Mode dryrun }
else { & (Join-Path $PSScriptRoot 'main.ps1') -Mode Pilot }
exit $LASTEXITCODE
