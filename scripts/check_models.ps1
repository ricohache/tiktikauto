# Verifie la presence des modeles necessaires.

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "=== Verification des modeles ===" -ForegroundColor Cyan

$modelsRoot = Join-Path $ProjectRoot "ComfyUI\ComfyUI\models"

# Checkpoints
$cpDir = Join-Path $modelsRoot "checkpoints"
$cpFiles = Get-ChildItem -Path $cpDir -Filter "*.safetensors" -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Checkpoints :" -ForegroundColor White
if ($cpFiles) {
    $cpFiles | ForEach-Object { 
        $sizeGB = [math]::Round($_.Length / 1GB, 2)
        Write-Host "  OK $sizeGB Go" -ForegroundColor Green
    }
} else {
    Write-Host "  KO Aucun checkpoint trouve" -ForegroundColor Red
    Write-Host "     Place un .safetensors ici : $cpDir" -ForegroundColor DarkGray
}

# Diffusion models (Wan)
$dmDir = Join-Path $modelsRoot "diffusion_models"
$dmFiles = Get-ChildItem -Path $dmDir -Filter "*.safetensors" -ErrorAction SilentlyContinue
if (-not $dmFiles) {
    $dmFiles = Get-ChildItem -Path $dmDir -Filter "*.pt" -ErrorAction SilentlyContinue
}
Write-Host ""
Write-Host "Modeles de diffusion (Wan) :" -ForegroundColor White
if ($dmFiles) {
    $dmFiles | ForEach-Object { 
        $sizeGB = [math]::Round($_.Length / 1GB, 2)
        Write-Host "  OK $sizeGB Go" -ForegroundColor Green
    }
} else {
    Write-Host "  KO Aucun modele Wan trouve" -ForegroundColor Red
    Write-Host "     Place le modele ici : $dmDir" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Statut ===" -ForegroundColor Cyan
if ($cpFiles -and $dmFiles) {
    Write-Host "Tous les modeles sont presents !" -ForegroundColor Green
} else {
    Write-Host "Modeles manquants. Executer : .\scripts\download_models.ps1" -ForegroundColor Yellow
}
