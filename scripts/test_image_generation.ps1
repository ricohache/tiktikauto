#Requires -Version 5.1
<#
.SYNOPSIS
    Teste la generation d'image manga via ComfyUI sur Windows hote.
#>
[CmdletBinding()]
param(
    [string]$ComfyUIPath = "C:\TikTokHistoryFactory\ComfyUI",
    [string]$OutputPath = "C:\TikTokHistoryFactory\output",
    [string]$WorkflowFile = "C:\TikTokHistoryFactory\workflows\comfyui\manga_animagine_xl.json",
    [int]$TimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
$apiUrl = "http://127.0.0.1:8188"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path "$PSScriptRoot\..\logs\test-image-generation.log" -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

# 1. Verifier ComfyUI en ligne
Write-Log "=== Test generation image manga ==="
Write-Log "Verification ComfyUI..."
try {
    $response = Invoke-RestMethod -Uri "$apiUrl/system_stats" -Method GET -TimeoutSec 10
    Write-Log "ComfyUI actif. GPU : $($response.devices[0].name)"
} catch {
    Write-Log "ComfyUI non accessible. Demarrage..." "WARN"
    Start-Process -FilePath "powershell" -ArgumentList "-File `"$PSScriptRoot\start_comfyui.ps1`"" -WindowStyle Hidden
    Start-Sleep -Seconds 30
    $response = Invoke-RestMethod -Uri "$apiUrl/system_stats" -Method GET -TimeoutSec 10
    Write-Log "ComfyUI demarre. GPU : $($response.devices[0].name)"
}

# 2. Verifier checkpoint
$checkpoint = Join-Path $ComfyUIPath "ComfyUI\models\checkpoints\animagine-xl-3.1.safetensors"
if (-not (Test-Path $checkpoint)) {
    Write-Log "Checkpoint non trouve. Lancez d'abord install_models.ps1" "ERROR"
    exit 1
}
Write-Log "Checkpoint OK : $([math]::Round((Get-Item $checkpoint).Length/1GB,2)) Go"

# 3. Charger le workflow
Write-Log "Chargement workflow..."
$workflowJson = Get-Content $WorkflowFile -Raw
$workflow = $workflowJson | ConvertFrom-Json

# Modifier le prompt pour un test historique
$promptNode = $workflow.nodes | Where-Object { $_.type -eq "CLIPTextEncode" -and $_.pos[1] -lt 400 }
if ($promptNode) {
    $promptNode.widgets_values[0] = "masterpiece, best quality, highly detailed, historical manga scene, Edo period Japan, samurai duel at sunset, traditional architecture, ink wash painting, dramatic shadows, seinen style, emotional intensity, ultra detailed"
    Write-Log "Prompt modifie pour test historique."
}

# 4. Envoyer la requete
Write-Log "Envoi de la requete de generation..."
$body = @{
    prompt = $workflow
} | ConvertTo-Json -Depth 20

try {
    $startTime = Get-Date
    $result = Invoke-RestMethod -Uri "$apiUrl/prompt" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
    $promptId = $result.prompt_id
    Write-Log "Requete envoyee. Prompt ID : $promptId"
} catch {
    Write-Log "Erreur envoi requete : $_" "ERROR"
    exit 1
}

# 5. Attendre la completion
Write-Log "Attente de la generation (timeout : ${TimeoutSeconds}s)..."
$elapsed = 0
$completed = $false
while ($elapsed -lt $TimeoutSeconds) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    
    try {
        $history = Invoke-RestMethod -Uri "$apiUrl/history/$promptId" -Method GET -TimeoutSec 5
        if ($history -and ($history | Get-Member -Name $promptId)) {
            $completed = $true
            break
        }
    } catch {
        # Ignorer les erreurs reseau temporaires
    }
    
    Write-Log "  Attente... ${elapsed}s ecoules"
}

if (-not $completed) {
    Write-Log "Timeout apres ${TimeoutSeconds}s" "ERROR"
    exit 1
}

# 6. Recuperer l'image
$historyData = Invoke-RestMethod -Uri "$apiUrl/history/$promptId" -Method GET -TimeoutSec 10
$outputs = $historyData.$promptId.outputs
if ($outputs -and $outputs.'9') {
    $imageInfo = $outputs.'9'.images[0]
    $imageFilename = $imageInfo.filename
    $subfolder = $imageInfo.subfolder
    
    # Telecharger l'image
    $imageUrl = "$apiUrl/view?filename=$imageFilename&subfolder=$subfolder&type=output"
    $imagePath = Join-Path $OutputPath "test_manga_$(Get-Date -Format 'yyyyMMdd_HHmmss').png"
    
    Invoke-WebRequest -Uri $imageUrl -OutFile $imagePath -TimeoutSec 30
    
    $size = (Get-Item $imagePath).Length
    $duration = (Get-Date) - $startTime
    
    Write-Log "Image generee : $imagePath"
    Write-Log "Taille : $([math]::Round($size/1KB,1)) Ko"
    Write-Log "Duree : $([math]::Round($duration.TotalSeconds,1)) secondes"
    Write-Log "=== TEST REUSSI ===" "SUCCESS"
    
    # Rapport JSON
    $report = @{
        timestamp = (Get-Date -Format "o")
        status = "SUCCESS"
        image_path = $imagePath
        prompt_id = $promptId
        duration_seconds = [math]::Round($duration.TotalSeconds,1)
        file_size_kb = [math]::Round($size/1KB,1)
        gpu = $response.devices[0].name
    } | ConvertTo-Json
    
    $reportPath = Join-Path $OutputPath "test_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    Set-Content -Path $reportPath -Value $report -Encoding UTF8
    Write-Log "Rapport sauvegarde : $reportPath"
    
} else {
    Write-Log "Aucune image dans les outputs" "ERROR"
    exit 1
}
