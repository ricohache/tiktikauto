# Telecharge automatiquement les modeles necessaires.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== Telechargement des modeles ComfyUI ===" -ForegroundColor Cyan

# Chemins
$ComfyModels = Join-Path $ProjectRoot "ComfyUI\ComfyUI\models"
$CheckpointsDir = Join-Path $ComfyModels "checkpoints"
$DiffusionDir = Join-Path $ComfyModels "diffusion_models"
$VaeDir = Join-Path $ComfyModels "vae"

# Creer les repertoires
foreach ($d in @($CheckpointsDir, $DiffusionDir, $VaeDir)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

# Verification espace disque
$drive = New-Object System.IO.DriveInfo("C")
$freeGB = [math]::Round($drive.TotalFreeSpace / 1GB, 2)

Write-Host "Espace libre : $freeGB Go" -ForegroundColor White
Write-Host "Modeles necessaires : ~15 Go" -ForegroundColor White

if ($freeGB -lt 15) {
    Write-Error "Espace insuffisant."
    exit 1
}

Write-Host ""
Write-Host "Instructions :" -ForegroundColor Yellow
Write-Host "  1. Checkpoint manga SDXL (~2-7 Go)" -ForegroundColor DarkGray
Write-Host "     civitai.com ou huggingface.co" -ForegroundColor DarkGray
Write-Host "     Destination : $CheckpointsDir" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  2. Wan 2.2 TI2V-5B (~10 Go)" -ForegroundColor DarkGray
Write-Host "     huggingface.co/Wan-AI/Wan2.2-T2V-5B" -ForegroundColor DarkGray
Write-Host "     Destination : $DiffusionDir" -ForegroundColor DarkGray

# Verifier si des modeles sont deja presents
$existingCP = Get-ChildItem -Path $CheckpointsDir -Filter "*.safetensors" -ErrorAction SilentlyContinue
$existingWan = Get-ChildItem -Path $DiffusionDir -Filter "*.safetensors" -ErrorAction SilentlyContinue

if ($existingCP) {
    Write-Host "Checkpoints deja presents :" -ForegroundColor Green
    $existingCP | ForEach-Object { Write-Host "  - $_.Name" }
} else {
    Write-Host "Aucun checkpoint trouve." -ForegroundColor Red
}

if ($existingWan) {
    Write-Host "Modeles Wan deja presents :" -ForegroundColor Green
    $existingWan | ForEach-Object { Write-Host "  - $_.Name" }
} else {
    Write-Host "Aucun modele Wan trouve." -ForegroundColor Red
}

Write-Host ""
Write-Host "Apres avoir copie les modeles :" -ForegroundColor Cyan
Write-Host "  .\scripts\check_models.ps1" -ForegroundColor White
