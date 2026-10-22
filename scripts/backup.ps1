
<#
.SYNOPSIS
    Sauvegarde la base de donnees et les rapports.
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $ProjectRoot "backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$target = Join-Path $backupDir "backup_$timestamp"
New-Item -ItemType Directory -Force -Path $target | Out-Null

# Copier DB
if (Test-Path "$ProjectRoot\dataactory.db") {
    Copy-Item "$ProjectRoot\dataactory.db" "$target" -Force
    Write-Host "Base de donnees sauvegardee." -ForegroundColor Green
}

# Copier rapports
if (Test-Path "$ProjectRoot
eports") {
    Copy-Item "$ProjectRoot
eports" "$target" -Recurse -Force
    Write-Host "Rapports sauvegardes." -ForegroundColor Green
}

Write-Host "Backup dans : $target" -ForegroundColor Cyan
