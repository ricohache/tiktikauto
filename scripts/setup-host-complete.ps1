#Requires -Version 5.1
# TikTokHistoryFactory - Setup Complet Autonome
# Usage: .\setup-host-complete.ps1 -Mode Full
[CmdletBinding()]
param(
    [ValidateSet("Check","Install","Start","Test","Full")]
    [string]$Mode = "Check",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$script:Results = @()
$script:ExitCode = 0
$FactoryPath = "C:\TikTokHistoryFactory"
$ComfyUIPath = "$FactoryPath\ComfyUI"
$LogFile = "$FactoryPath\logs\setup-complete.log"
$ApiUrl = "http://127.0.0.1:8188"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    try {
        if (-not (Test-Path "$FactoryPath\logs")) {
            New-Item -ItemType Directory -Path "$FactoryPath\logs" -Force | Out-Null
        }
        Add-Content -Path $LogFile -Value $line -Encoding UTF8
    } catch {}
}

function Add-Result {
    param([string]$Step, [string]$Status, [string]$Details = "")
    $script:Results += [PSCustomObject]@{
        Step = $Step
        Status = $Status
        Details = $Details
        Timestamp = Get-Date -Format "o"
    }
    $emoji = @{ PASS = "OK"; FAIL = "KO"; WARN = "!"; PENDING = "..."; SKIP = "-" }
    $sym = if ($emoji[$Status]) { $emoji[$Status] } else { "?" }
    Write-Log "$sym $Step : $Status - $Details"
}

# ==================== PHASE CHECK ====================
function Invoke-PhaseCheck {
    Write-Log "========================================"
    Write-Log "PHASE 1/5 : VERIFICATION DES PREREQUIS"
    Write-Log "========================================"
    
    # Windows
    $winBuild = [System.Environment]::OSVersion.Version.Build
    if ($winBuild -ge 22000) {
        Add-Result -Step "Windows" -Status "PASS" -Details "Build $winBuild"
    } else {
        Add-Result -Step "Windows" -Status "WARN" -Details "Build $winBuild"
    }
    
    # FFmpeg
    $ffmpeg = "$FactoryPath\ffmpeg\bin\ffmpeg.exe"
    if (Test-Path $ffmpeg) {
        try {
            $v = & $ffmpeg -version 2>$null | Select-Object -First 1
            Add-Result -Step "FFmpeg" -Status "PASS" -Details ($v -replace "ffmpeg version ","")
        } catch {
            Add-Result -Step "FFmpeg" -Status "PASS" -Details "Present"
        }
    } else {
        Add-Result -Step "FFmpeg" -Status "FAIL" -Details "Non trouve dans $FactoryPath\ffmpeg"
        $script:ExitCode = 1
    }
    
    # ComfyUI binaire
    $comfyPy = "$ComfyUIPath\python_embeded\python.exe"
    $comfyBat = "$ComfyUIPath\run_nvidia_gpu.bat"
    if ((Test-Path $comfyBat) -and (Test-Path $comfyPy)) {
        Add-Result -Step "ComfyUI binaire" -Status "PASS" -Details "Present"
        
        # Test CUDA
        try {
            $cudaCmd = "& `"$comfyPy`" -c `"import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')`""
            $cudaOut = Invoke-Expression $cudaCmd 2>$null
            if ($cudaOut -like "*CUDA: True*") {
                $gpuName = ($cudaOut | Select-String "GPU:") -replace "GPU: ",""
                Add-Result -Step "GPU CUDA" -Status "PASS" -Details $gpuName
            } else {
                Add-Result -Step "GPU CUDA" -Status "WARN" -Details "CUDA non disponible"
            }
        } catch {
            Add-Result -Step "GPU CUDA" -Status "WARN" -Details "Test impossible"
        }
    } else {
        Add-Result -Step "ComfyUI binaire" -Status "FAIL" -Details "Manquant"
        $script:ExitCode = 1
    }
    
    # Checkpoints
    $ckptDir = "$ComfyUIPath\ComfyUI\models\checkpoints"
    $ckpts = Get-ChildItem -Path $ckptDir -Filter "*.safetensors" -ErrorAction SilentlyContinue
    if ($ckpts -and $ckpts.Count -gt 0) {
        $totalSize = ($ckpts | Measure-Object -Property Length -Sum).Sum
        Add-Result -Step "Checkpoints" -Status "PASS" -Details "$($ckpts.Count) modele(s), $([math]::Round($totalSize/1GB,1)) Go"
    } else {
        Add-Result -Step "Checkpoints" -Status "WARN" -Details "Aucun modele trouve"
    }
    
    # ComfyUI serveur (si deja demarre)
    try {
        $sys = Invoke-RestMethod -Uri "$ApiUrl/system_stats" -Method GET -TimeoutSec 3
        Add-Result -Step "ComfyUI serveur" -Status "PASS" -Details "Actif, $($sys.devices[0].name)"
    } catch {
        Add-Result -Step "ComfyUI serveur" -Status "WARN" -Details "Inactif"
    }
    
    # Ollama
    try {
        $ollamaVersion = ollama --version 2>$null
        Add-Result -Step "Ollama CLI" -Status "PASS" -Details $ollamaVersion
    } catch {
        Add-Result -Step "Ollama CLI" -Status "WARN" -Details "Non installe"
    }
    
    # Espace disque
    try {
        $drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
        $freeGB = [math]::Floor($drive.FreeSpace / 1GB)
        if ($freeGB -gt 15) {
            Add-Result -Step "Espace disque" -Status "PASS" -Details "$freeGB Go disponibles"
        } else {
            Add-Result -Step "Espace disque" -Status "WARN" -Details "$freeGB Go (15+ recommandes)"
        }
    } catch {
        Add-Result -Step "Espace disque" -Status "WARN" -Details "Test impossible"
    }
}

# ==================== PHASE INSTALL ====================
function Invoke-PhaseInstall {
    Write-Log "========================================"
    Write-Log "PHASE 2/5 : INSTALLATION DES MODELES"
    Write-Log "========================================"
    
    $ckptDir = "$ComfyUIPath\ComfyUI\models\checkpoints"
    if (-not (Test-Path $ckptDir)) {
        New-Item -ItemType Directory -Path $ckptDir -Force | Out-Null
    }
    
    # animagine-xl-3.1
    $checkpointFile = "$ckptDir\animagine-xl-3.1.safetensors"
    $checkpointUrl = "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors"
    
    if ((Test-Path $checkpointFile) -and -not $Force) {
        $size = (Get-Item $checkpointFile).Length
        if ($size -gt 5GB) {
            Add-Result -Step "Modele animagine-xl-3.1" -Status "SKIP" -Details "Deja present ($([math]::Round($size/1GB,2)) Go)"
            return
        }
    }
    
    Write-Log "Telechargement animagine-xl-3.1 (~6.9 Go)..."
    Write-Log "URL: $checkpointUrl"
    Write-Log "Cela peut prendre 10-30 minutes selon la connexion."
    
    try {
        $tempFile = "$checkpointFile.tmp"
        
        # Essayer avec curl.exe d'abord
        $curlArgs = @("-L", "-o", $tempFile, $checkpointUrl)
        $proc = Start-Process -FilePath "curl.exe" -ArgumentList $curlArgs -PassThru -Wait
        
        if ($proc.ExitCode -ne 0 -or -not (Test-Path $tempFile)) {
            # Fallback avec Invoke-WebRequest
            Write-Log "curl a echoue, tentative avec PowerShell..."
            Invoke-WebRequest -Uri $checkpointUrl -OutFile $tempFile -TimeoutSec 3600
        }
        
        if (-not (Test-Path $tempFile)) {
            throw "Telechargement impossible"
        }
        
        $dlSize = (Get-Item $tempFile).Length
        if ($dlSize -lt 5GB) {
            throw "Fichier incomplet: $([math]::Round($dlSize/1MB,0)) Mo"
        }
        
        if (Test-Path $checkpointFile) {
            Remove-Item $checkpointFile -Force
        }
        Move-Item $tempFile $checkpointFile -Force
        Add-Result -Step "Modele animagine-xl-3.1" -Status "PASS" -Details "$([math]::Round($dlSize/1GB,2)) Go"
        Write-Log "Telechargement reussi !"
    } catch {
        Write-Log "ERREUR telechargement: $_" "ERROR"
        Add-Result -Step "Modele animagine-xl-3.1" -Status "FAIL" -Details $_
        Write-Log "Telechargement manuel:" "WARN"
        Write-Log "  1. Allez sur https://huggingface.co/cagliostrolab/animagine-xl-3.1" "WARN"
        Write-Log "  2. Telechargez animagine-xl-3.1.safetensors" "WARN"
        Write-Log "  3. Copiez-le dans: $ckptDir" "WARN"
        $script:ExitCode = 1
    }
}

# ==================== PHASE START ====================
function Invoke-PhaseStart {
    Write-Log "========================================"
    Write-Log "PHASE 3/5 : DEMARRAGE DES SERVICES"
    Write-Log "========================================"
    
    # Verifier si ComfyUI est deja actif
    try {
        $sys = Invoke-RestMethod -Uri "$ApiUrl/system_stats" -Method GET -TimeoutSec 5
        Add-Result -Step "ComfyUI serveur" -Status "SKIP" -Details "Deja actif, $($sys.devices[0].name)"
        return
    } catch {
        Write-Log "ComfyUI inactif. Demarrage..."
    }
    
    $pythonExe = "$ComfyUIPath\python_embeded\python.exe"
    $mainPy = "$ComfyUIPath\ComfyUI\main.py"
    
    if (-not (Test-Path $pythonExe) -or -not (Test-Path $mainPy)) {
        Add-Result -Step "ComfyUI serveur" -Status "FAIL" -Details "Fichiers manquants"
        $script:ExitCode = 1
        return
    }
    
    # Demarrer ComfyUI en arriere-plan
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $pythonExe
    $startInfo.Arguments = "-s `"$mainPy`" --windows-standalone-build --listen 127.0.0.1 --port 8188"
    $startInfo.WorkingDirectory = $ComfyUIPath
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $startInfo.CreateNoWindow = $true
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    
    $proc = [System.Diagnostics.Process]::Start($startInfo)
    Write-Log "ComfyUI demarre (PID $($proc.Id))"
    Write-Log "Attente du serveur (max 120s)..."
    
    # Attendre que le serveur reponde
    $started = $false
    $elapsed = 0
    while ($elapsed -lt 120) {
        Start-Sleep -Seconds 5
        $elapsed += 5
        try {
            $sys = Invoke-RestMethod -Uri "$ApiUrl/system_stats" -Method GET -TimeoutSec 5
            $started = $true
            break
        } catch {
            if ($elapsed % 15 -eq 0) {
                Write-Log "  Attente... ${elapsed}s"
            }
        }
    }
    
    if ($started) {
        $vramGB = [math]::Round($sys.devices[0].free_vram / 1024 / 1024 / 1024, 1)
        Add-Result -Step "ComfyUI serveur" -Status "PASS" -Details "PID $($proc.Id), $($sys.devices[0].name), VRAM libre: ${vramGB}Go"
    } else {
        Add-Result -Step "ComfyUI serveur" -Status "FAIL" -Details "Ne repond pas apres 120s"
        $script:ExitCode = 1
    }
}

# ==================== PHASE TEST ====================
function Invoke-PhaseTest {
    Write-Log "========================================"
    Write-Log "PHASE 4/5 : TESTS D INTEGRATION"
    Write-Log "========================================"
    
    # 1. Verifier API ComfyUI
    try {
        $sys = Invoke-RestMethod -Uri "$ApiUrl/system_stats" -Method GET -TimeoutSec 10
        Add-Result -Step "Test API" -Status "PASS" -Details "/system_stats OK"
    } catch {
        Add-Result -Step "Test API" -Status "FAIL" -Details $_
        $script:ExitCode = 1
        return
    }
    
    # 2. Verifier checkpoint
    $ckptFile = "$ComfyUIPath\ComfyUI\models\checkpoints\animagine-xl-3.1.safetensors"
    if (-not (Test-Path $ckptFile)) {
        Add-Result -Step "Test checkpoint" -Status "FAIL" -Details "animagine-xl-3.1.safetensors manquant"
        $script:ExitCode = 1
        return
    }
    Add-Result -Step "Test checkpoint" -Status "PASS" -Details "Present"
    
    # 3. Generer une image test
    $workflowFile = "$FactoryPath\workflows\comfyui\manga_animagine_xl.json"
    if (-not (Test-Path $workflowFile)) {
        Add-Result -Step "Test workflow" -Status "FAIL" -Details "Workflow non trouve"
        $script:ExitCode = 1
        return
    }
    
    $workflowJson = Get-Content $workflowFile -Raw
    $workflow = $workflowJson | ConvertFrom-Json
    
    # Modifier le prompt pour un test historique
    foreach ($node in $workflow.nodes) {
        if ($node.type -eq "CLIPTextEncode" -and $node.pos[1] -lt 400) {
            $node.widgets_values[0] = "masterpiece, best quality, highly detailed, historical manga scene, Edo period Japan, samurai warrior in ornate armor, traditional castle background, cherry blossoms, dramatic sunset lighting, ink wash painting style, seinen aesthetic, mature composition, ultra detailed"
        }
    }
    
    Write-Log "Envoi requete generation image..."
    $body = @{ prompt = $workflow } | ConvertTo-Json -Depth 20
    try {
        $result = Invoke-RestMethod -Uri "$ApiUrl/prompt" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10
        $promptId = $result.prompt_id
        Write-Log "Prompt ID: $promptId"
    } catch {
        Add-Result -Step "Test generation" -Status "FAIL" -Details "Envoi requete: $_"
        $script:ExitCode = 1
        return
    }
    
    # Attendre completion
    Write-Log "Attente generation (timeout 5 min)..."
    $completed = $false
    $elapsed = 0
    $startGen = Get-Date
    while ($elapsed -lt 300) {
        Start-Sleep -Seconds 10
        $elapsed = ([DateTime]::Now - $startGen).TotalSeconds
        try {
            $history = Invoke-RestMethod -Uri "$ApiUrl/history/$promptId" -Method GET -TimeoutSec 5
            if ($history -and ($history | Get-Member -Name $promptId)) {
                $completed = $true
                break
            }
        } catch {}
        if ($elapsed % 30 -lt 15) {
            Write-Log "  Attente... $([math]::Round($elapsed,0))s"
        }
    }
    
    if (-not $completed) {
        Add-Result -Step "Test generation" -Status "FAIL" -Details "Timeout apres 300s"
        $script:ExitCode = 1
        return
    }
    
    # Recuperer l'image
    $historyData = Invoke-RestMethod -Uri "$ApiUrl/history/$promptId" -Method GET -TimeoutSec 10
    $outputs = $historyData.$promptId.outputs
    if ($outputs -and $outputs.'9') {
        $imageInfo = $outputs.'9'.images[0]
        $imageUrl = "$ApiUrl/view?filename=$($imageInfo.filename)&subfolder=$($imageInfo.subfolder)&type=output"
        $imagePath = "$FactoryPath\output\first_manga_$(Get-Date -Format 'yyyyMMdd_HHmmss').png"
        
        Invoke-WebRequest -Uri $imageUrl -OutFile $imagePath -TimeoutSec 30
        $size = (Get-Item $imagePath).Length
        $duration = ([DateTime]::Now - $startGen).TotalSeconds
        
        Add-Result -Step "Test generation" -Status "PASS" -Details "$([math]::Round($duration,1))s, $([math]::Round($size/1KB,1)) Ko"
        Write-Log "Image generee: $imagePath"
        Write-Log "=== PREMIERE IMAGE MANGA HISTORIQUE REUSSIE ===" "SUCCESS"
    } else {
        Add-Result -Step "Test generation" -Status "FAIL" -Details "Aucune image dans les outputs"
        $script:ExitCode = 1
    }
}

# ==================== PHASE PILOT ====================
function Invoke-PhasePilot {
    Write-Log "========================================"
    Write-Log "PHASE 5/5 : PILOTE VIDEO COMPLET"
    Write-Log "========================================"
    Add-Result -Step "Pilote" -Status "PENDING" -Details "A implementer - necessite narration et montage"
}

# ==================== EXECUTION PRINCIPALE ====================
Write-Log "========================================"
Write-Log "TikTokHistoryFactory Setup"
Write-Log "Mode: $Mode"
Write-Log "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Log "========================================"

switch ($Mode) {
    "Check"   { Invoke-PhaseCheck }
    "Install" { Invoke-PhaseCheck; Invoke-PhaseInstall }
    "Start"   { Invoke-PhaseCheck; Invoke-PhaseStart }
    "Test"    { Invoke-PhaseCheck; Invoke-PhaseStart; Invoke-PhaseTest }
    "Full"    { Invoke-PhaseCheck; Invoke-PhaseInstall; Invoke-PhaseStart; Invoke-PhaseTest; Invoke-PhasePilot }
}

# Rapport final
$overall = if ($script:Results | Where-Object { $_.Status -eq "FAIL" }) { "FAIL" }
           elseif ($script:Results | Where-Object { $_.Status -eq "WARN" }) { "WARN" }
           else { "PASS" }

$jsonReport = @{
    timestamp = Get-Date -Format "o"
    mode = $Mode
    overall = $overall
    steps = $script:Results
    exit_code = $script:ExitCode
} | ConvertTo-Json -Depth 5

$reportDir = "$FactoryPath\reports"
if (-not (Test-Path $reportDir)) {
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
}
$reportPath = "$reportDir\setup-report-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
Set-Content -Path $reportPath -Value $jsonReport -Encoding UTF8

Write-Log "========================================"
Write-Log "Rapport: $reportPath"
Write-Log "Overall: $overall"
Write-Log "PASS: $(($script:Results | Where-Object { $_.Status -eq 'PASS' }).Count)"
Write-Log "WARN: $(($script:Results | Where-Object { $_.Status -eq 'WARN' }).Count)"
Write-Log "FAIL: $(($script:Results | Where-Object { $_.Status -eq 'FAIL' }).Count)"
Write-Log "========================================"

if ($script:ExitCode -eq 0 -and $Mode -eq "Full") {
    Write-Log "=== SETUP COMPLET TERMINE ===" "SUCCESS"
    Write-Log "Prochaine etape: python supervisor.py --test" "SUCCESS"
}

exit $script:ExitCode
