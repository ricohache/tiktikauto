<#
.SYNOPSIS
    Active l'usine TikTokHistoryFactory apres validation manuelle.
.DESCRIPTION
    Met a jour .env avec THF_WORKER_ENABLED=true et THF_BUFFER_PUBLISH_ALLOWED=1.
    Affiche un resume des conditions prealables et demande confirmation.
    Ne modifie aucune autre configuration.
#>
param(
    [string]$WorkerUrl = "",
    [switch]$Force = $false
)

$envPath = "C:\TikTokHistoryFactory\.env"

Write-Host "=== Activation Usine TikTokHistoryFactory ===" -ForegroundColor Yellow
Write-Host "Cette operation active la publication reelle."
Write-Host "Conditions prealables :"
Write-Host "  1. Worker Cloudflare deploye et valide (scripts\validate_worker.ps1)"
Write-Host "  2. Canal TikTok connecte dans Buffer (buffer_verify_real.py)"
Write-Host "  3. URL Worker connue"
Write-Host ""

if (-not $Force) {
    $confirm = Read-Host "Confirmez-vous l'activation ? (oui/non)"
    if ($confirm -ne "oui") {
        Write-Host "Activation annulee." -ForegroundColor Red
        exit 0
    }
}

$lines = Get-Content $envPath
$newLines = @()
$hasWorkerUrl = $false
$hasWorkerEnabled = $false
$hasBufferAllowed = $false

foreach ($line in $lines) {
    if ($line -match "^THF_WORKER_URL=") {
        if ($WorkerUrl) {
            $newLines += "THF_WORKER_URL=$WorkerUrl"
        } else {
            $newLines += $line
        }
        $hasWorkerUrl = $true
    } elseif ($line -match "^THF_WORKER_ENABLED=") {
        $newLines += "THF_WORKER_ENABLED=true"
        $hasWorkerEnabled = $true
    } elseif ($line -match "^THF_BUFFER_PUBLISH_ALLOWED=") {
        $newLines += "THF_BUFFER_PUBLISH_ALLOWED=1"
        $hasBufferAllowed = $true
    } else {
        $newLines += $line
    }
}

if (-not $hasWorkerUrl -and $WorkerUrl) {
    $newLines += "THF_WORKER_URL=$WorkerUrl"
}
if (-not $hasWorkerEnabled) {
    $newLines += "THF_WORKER_ENABLED=true"
}
if (-not $hasBufferAllowed) {
    $newLines += "THF_BUFFER_PUBLISH_ALLOWED=1"
}

Set-Content -Path $envPath -Value ($newLines -join "`n") -Encoding UTF8

Write-Host ""
Write-Host ".env mis a jour :" -ForegroundColor Green
Write-Host "  THF_WORKER_ENABLED=true"
Write-Host "  THF_BUFFER_PUBLISH_ALLOWED=1"
if ($WorkerUrl) {
    Write-Host "  THF_WORKER_URL=$WorkerUrl"
}
Write-Host ""
Write-Host "L'usine est maintenant activee pour 3 publications/jour (10h, 12h, 14h CET)."
Write-Host "Desactivez a tout moment en remettant THF_WORKER_ENABLED=false dans .env"
