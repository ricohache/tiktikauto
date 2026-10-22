<#
.SYNOPSIS
    Script d'initialisation du projet TikTokHistoryFactory.

.DESCRIPTION
    Prépare l'environnement : venv, dépendances, base de données, dossiers.
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== Initialisation TikTokHistoryFactory ===" -ForegroundColor Cyan

# Créer le venv
$VenvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "Création du venv Python..." -ForegroundColor Yellow
    python -m venv $VenvPath
}

# Activer le venv
$activate = Join-Path $VenvPath "Scripts\Activate.ps1"
. $activate

# Installer les dépendances
Write-Host "Installation des dépendances..." -ForegroundColor Yellow
pip install -q -e ".[dev]"

# Créer les dossiers manquants
@("data", "logs", "output", "renders") | ForEach-Object {
    $d = Join-Path $ProjectRoot $_
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

# Initialiser la base SQLite
Write-Host "Initialisation de la base SQLite..." -ForegroundColor Yellow
python -c "from tiktok_history_factory.database import init_database; from tiktok_history_factory.config import Settings; init_database(str(Settings().DB_PATH))"

Write-Host "Initialisation terminée avec succès." -ForegroundColor Green
Write-Host "Utilisez : .\scripts\orchestrator.ps1 -DryRun" -ForegroundColor Cyan
