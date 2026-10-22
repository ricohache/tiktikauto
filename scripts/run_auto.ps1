# TikTokHistoryFactory V5 — Runner autonome pour planificateur Windows
# Ce script est conçu pour être appelé par schtasks sans interaction humaine
$ErrorActionPreference = 'Stop'
$Project = 'C:\TikTokHistoryFactory'
Set-Location $Project
$env:PATH += ";$Project\ffmpeg\bin"

$Python = Join-Path $Project '.venv\Scripts\python.exe'
$Engine = Join-Path $Project 'src\v5_factory\auto_engine.py'
$LogDir = Join-Path $Project 'logs'
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$Log = Join-Path $LogDir ("auto_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.log')

Start-Transcript -Path $Log | Out-Null
try {
    Write-Host "=== TikTokHistoryFactory V5 — RUNNER ===" -ForegroundColor Cyan
    Write-Host "Heure: $(Get-Date)"
    Write-Host "Projet: $Project"
    
    # Verrou GPU — attendre si un autre job utilise ComfyUI
    $maxWait = 600  # 10 minutes max
    $waited = 0
    while ($waited -lt $maxWait) {
        try {
            $stats = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 5 -ErrorAction SilentlyContinue
            # Si ComfyUI répond, on considère qu'il est libre (pas de queue en cours détectable simplement)
            Write-Host 'ComfyUI disponible'
            break
        } catch {
            Write-Host "ComfyUI indisponible, attente... ($waited/$maxWait s)"
            Start-Sleep -Seconds 30
            $waited += 30
        }
    }
    
    # Lancer production automatique
    Write-Host 'Lancement production auto...'
    & $Python $Engine
    
    $exitCode = $LASTEXITCODE
    Write-Host "Exit code: $exitCode"
    
    if ($exitCode -ne 0) {
        Write-Warning "Production échouée avec code $exitCode"
    }
} catch {
    Write-Error "ERREUR CRITIQUE: $_"
} finally {
    Stop-Transcript | Out-Null
    Write-Host "Log sauvegardé: $Log"
}
