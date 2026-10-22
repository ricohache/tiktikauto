
<#
.SYNOPSIS
    Mise a jour du projet (sauvegarde + update).
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Sauvegarde avant mise a jour..." -ForegroundColor Yellow
.\scriptsackup.ps1

Write-Host "Mise a jour terminee (aucune action automatique)." -ForegroundColor Green
Write-Host "Verifier les changements et relancer les tests." -ForegroundColor Cyan
