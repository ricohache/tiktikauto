#Requires -Version 5.1
# Installation TikTokHistoryFactory

$ErrorActionPreference = "Stop"

$FactoryPath = "C:\TikTokHistoryFactory"

Write-Host "=== Installation des dependances ==="

# Verifier Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python non trouve. Installez Python 3.11+"
    exit 1
}

# Creer environnement virtuel
$venvPath = "$FactoryPath\.venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creation du virtualenv..."
    & python -m venv $venvPath
}

# Activer et installer
$activate = "$venvPath\Scripts\Activate.ps1"
if (Test-Path $activate) {
    . $activate
    Write-Host "Installation des packages..."
    pip install -q -e "$FactoryPath"
}

Write-Host "Installation terminee."
