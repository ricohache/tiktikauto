import os

base = r'C:\TikTokHistoryFactory'
scripts = os.path.join(base, 'scripts')
logs = os.path.join(base, 'logs')
reports = os.path.join(base, 'reports')

for d in [scripts, logs, reports]:
    os.makedirs(d, exist_ok=True)

# === SCRIPT PRINCIPAL : setup-host-complete.ps1 ===
setup_content = r'''#Requires -Version 5.1
# TikTokHistoryFactory - Setup Complet Autonome
# Usage: .\setup-host-complete.ps1 -Mode Full
[CmdletBinding()]
param(
    [ValidateSet("Check","Install","Start","Test","Full")]
    [string] = "Check",
    [switch]
)

Continue = "Stop"
 = @()
 = 0
 = "C:\TikTokHistoryFactory"
 = "\ComfyUI"
 = "\logs\setup-complete.log"

function Write-Log {
    param([string], [string] = "INFO")
     = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
     = "[] [] "
    Write-Host 
    try {
        if (-not (Test-Path "\logs")) { New-Item -ItemType Directory -Path "\logs" -Force | Out-Null }
        Add-Content -Path  -Value  -Encoding UTF8
    } catch {}
}

function Add-Result {
    param([string], [string], [string] = "")
     += [PSCustomObject]@{ Step=; Status=; Details=; Timestamp=(Get-Date -Format "o") }
     = @{ PASS="OK"; FAIL="KO"; WARN="!"; PENDING="..."; SKIP="-" }
     = if ([]) { [] } else { "?" }
    Write-Log "  :  - "
}

# === PHASE CHECK ===
function Invoke-PhaseCheck {
    Write-Log "========================================"
    Write-Log "PHASE 1/4 : VERIFICATION DES PREREQUIS"
    Write-Log "========================================"
    
    # Windows
     = [System.Environment]::OSVersion.Version.Build
    if ( -ge 22000) {
        Add-Result -Step "Windows" -Status "PASS" -Details "Build "
    } else {
        Add-Result -Step "Windows" -Status "WARN" -Details "Build "
    }
    
    # FFmpeg
     = "\ffmpeg\bin\ffmpeg.exe"
    if (Test-Path ) {
        try {
             = &  -version 2> | Select-Object -First 1
            Add-Result -Step "FFmpeg" -Status "PASS" -Details ( -replace "ffmpeg version ","")
        } catch {
            Add-Result -Step "FFmpeg" -Status "PASS" -Details "Present"
        }
    } else {
        Add-Result -Step "FFmpeg" -Status "FAIL" -Details "Non trouve dans \ffmpeg"
         = 1
    }
    
    # ComfyUI binaire
     = "\python_embeded\python.exe"
    if ((Test-Path "\run_nvidia_gpu.bat") -and (Test-Path )) {
        Add-Result -Step "ComfyUI binaire" -Status "PASS" -Details "Present"
        
        # Test CUDA
        try {
             = &  -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')" 2>
            if ( -like "*CUDA: True*") {
                 = ( | Select-String "GPU:") -replace "GPU: ","")
                Add-Result -Step "GPU CUDA" -Status "PASS" -Details 
            } else {
                Add-Result -Step "GPU CUDA" -Status "WARN" -Details "CUDA non disponible"
            }
        } catch {
            Add-Result -Step "GPU CUDA" -Status "WARN" -Details "Test impossible: "
        }
    } else {
        Add-Result -Step "ComfyUI binaire" -Status "FAIL" -Details "Manquant"
         = 1
    }
    
    # Checkpoints
     = "\ComfyUI\models\checkpoints"
     = Get-ChildItem -Path  -Filter "*.safetensors" -ErrorAction SilentlyContinue
    if ( -and .Count -gt 0) {
         = ( | Measure-Object -Property Length -Sum).Sum
        Add-Result -Step "Checkpoints" -Status "PASS" -Details "0 modele(s), 0 Go"
    } else {
        Add-Result -Step "Checkpoints" -Status "WARN" -Details "Aucun modele trouve"
    }
    
    # Espace disque
    try {
         = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
         = [math]::Floor(.FreeSpace / 1GB)
        if ( -gt 15) {
            Add-Result -Step "Espace disque" -Status "PASS" -Details " Go disponibles"
        } else {
            Add-Result -Step "Espace disque" -Status "WARN" -Details " Go (15+ recommandes)"
        }
    } catch {
        Add-Result -Step "Espace disque" -Status "WARN" -Details "Test impossible"
    }
}

# === PHASE INSTALL ===
function Invoke-PhaseInstall {
    Write-Log "========================================"
    Write-Log "PHASE 2/4 : INSTALLATION DES MODELES"
    Write-Log "========================================"
    
     = "\ComfyUI\models\checkpoints"
    if (-not (Test-Path )) { New-Item -ItemType Directory -Path  -Force | Out-Null }
    
    # animagine-xl-3.1
     = "\animagine-xl-3.1.safetensors"
     = "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors"
    
    if ((Test-Path ) -and -not ) {
         = (Get-Item ).Length
        if ( -gt 5GB) {
            Add-Result -Step "Modele animagine-xl-3.1" -Status "SKIP" -Details "Deja present (0 Go)"
            return
        }
    }
    
    Write-Log "Telechargement animagine-xl-3.1 (~6.9 Go)..."
    Write-Log "URL: "
    Write-Log "Cela peut prendre 10-30 minutes selon la connexion."
    
    try {
         = ".tmp"
         = @("-L", "-o", , )
         = Start-Process -FilePath "curl.exe" -ArgumentList  -PassThru -Wait
        
        if (.ExitCode -ne 0 -or -not (Test-Path )) {
            # Essayer avec Invoke-WebRequest
            Write-Log "curl a echoue, tentative avec PowerShell..."
            Invoke-WebRequest -Uri  -OutFile  -TimeoutSec 3600
        }
        
        if (-not (Test-Path )) {
            throw "Telechargement impossible"
        }
        
         = (Get-Item ).Length
        if ( -lt 5GB) {
            throw "Fichier incomplet: 0 Mo"
        }
        
        if (Test-Path ) { Remove-Item  -Force }
        Move-Item   -Force
        Add-Result -Step "Modele animagine-xl-3.1" -Status "PASS" -Details "0 Go"
        Write-Log "Telechargement reussi !"
    } catch {
        Write-Log "ERREUR telechargement: " "ERROR"
        Add-Result -Step "Modele animagine-xl-3.1" -Status "FAIL" -Details 
        Write-Log "Telechargement manuel:" "WARN"
        Write-Log "  1. Allez sur https://huggingface.co/cagliostrolab/animagine-xl-3.1" "WARN"
        Write-Log "  2. Telechargez animagine-xl-3.1.safetensors" "WARN"
        Write-Log "  3. Copiez-le dans: " "WARN"
         = 1
    }
}

# === PHASE START ===
function Invoke-PhaseStart {
    Write-Log "========================================"
    Write-Log "PHASE 3/4 : DEMARRAGE DES SERVICES"
    Write-Log "========================================"
    
     = "http://127.0.0.1:8188"
    
    # Verifier si ComfyUI est deja actif
    try {
         = Invoke-RestMethod -Uri "/system_stats" -Method GET -TimeoutSec 5
        Add-Result -Step "ComfyUI serveur" -Status "SKIP" -Details "Deja actif, "
        return
    } catch {
        Write-Log "ComfyUI inactif. Demarrage..."
    }
    
     = "\python_embeded\python.exe"
     = "\ComfyUI\main.py"
    
    if (-not (Test-Path ) -or -not (Test-Path )) {
        Add-Result -Step "ComfyUI serveur" -Status "FAIL" -Details "Fichiers manquants"
         = 1
        return
    }
    
    # Demarrer ComfyUI en arriere-plan
     = New-Object System.Diagnostics.ProcessStartInfo
    .FileName = 
    .Arguments = "-s "" --windows-standalone-build --listen 127.0.0.1 --port 8188"
    .WorkingDirectory = 
    .WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    .CreateNoWindow = True
    .UseShellExecute = False
    .RedirectStandardOutput = True
    .RedirectStandardError = True
    
     = [System.Diagnostics.Process]::Start()
    Write-Log "ComfyUI demarre (PID )"
    Write-Log "Attente du serveur (max 120s)..."
    
    # Attendre que le serveur reponde
     = False
     = 0
    while ( -lt 120) {
        Start-Sleep -Seconds 5
         += 5
        try {
             = Invoke-RestMethod -Uri "/system_stats" -Method GET -TimeoutSec 5
             = True
            break
        } catch {
            if ( % 15 -eq 0) {
                Write-Log "  Attente... s"
            }
        }
    }
    
    if () {
        Add-Result -Step "ComfyUI serveur" -Status "PASS" -Details "PID , "
        Write-Log "VRAM libre:  Go"
    } else {
        Add-Result -Step "ComfyUI serveur" -Status "FAIL" -Details "Ne repond pas apres 120s"
         = 1
    }
}

# === PHASE TEST ===
function Invoke-PhaseTest {
    Write-Log "========================================"
    Write-Log "PHASE 4/4 : TESTS D'INTEGRATION"
    Write-Log "========================================"
    
     = "http://127.0.0.1:8188"
    
    # 1. Verifier API ComfyUI
    try {
         = Invoke-RestMethod -Uri "/system_stats" -Method GET -TimeoutSec 10
        Add-Result -Step "Test API" -Status "PASS" -Details "/system_stats OK"
    } catch {
        Add-Result -Step "Test API" -Status "FAIL" -Details 
         = 1
        return
    }
    
    # 2. Verifier checkpoint
     = "\ComfyUI\models\checkpoints\animagine-xl-3.1.safetensors"
    if (-not (Test-Path )) {
        Add-Result -Step "Test checkpoint" -Status "FAIL" -Details "animagine-xl-3.1.safetensors manquant"
         = 1
        return
    }
    Add-Result -Step "Test checkpoint" -Status "PASS" -Details "Present"
    
    # 3. Generer une image test
     = "\workflows\comfyui\manga_animagine_xl.json"
    if (-not (Test-Path )) {
        Add-Result -Step "Test workflow" -Status "FAIL" -Details "Workflow non trouve"
         = 1
        return
    }
    
     = Get-Content  -Raw
     =  | ConvertFrom-Json
    
    # Modifier le prompt pour un test historique
    foreach ( in .nodes) {
        if (.type -eq "CLIPTextEncode" -and .pos[1] -lt 400) {
            .widgets_values[0] = "masterpiece, best quality, highly detailed, historical manga scene, Edo period Japan, samurai warrior in ornate armor, traditional castle background, cherry blossoms, dramatic sunset lighting, ink wash painting style, seinen aesthetic, mature composition, ultra detailed"
        }
    }
    
    Write-Log "Envoi requete generation..."
     = @{ prompt =  } | ConvertTo-Json -Depth 20
    try {
         = Invoke-RestMethod -Uri "/prompt" -Method POST -Body  -ContentType "application/json" -TimeoutSec 10
         = .prompt_id
        Write-Log "Prompt ID: "
    } catch {
        Add-Result -Step "Test generation" -Status "FAIL" -Details "Envoi requete: "
         = 1
        return
    }
    
    # Attendre completion
    Write-Log "Attente generation (timeout 5 min)..."
     = False
     = 0
     = Get-Date
    while ( -lt 300) {
        Start-Sleep -Seconds 10
         = ([DateTime]::Now - ).TotalSeconds
        try {
             = Invoke-RestMethod -Uri "/history/" -Method GET -TimeoutSec 5
            if ( -and ( | Get-Member -Name )) {
                 = True
                break
            }
        } catch {}
        if ( % 30 -lt 15) {
            Write-Log "  Attente... 0s"
        }
    }
    
    if (-not ) {
        Add-Result -Step "Test generation" -Status "FAIL" -Details "Timeout apres 300s"
         = 1
        return
    }
    
    # Recuperer l'image
     = Invoke-RestMethod -Uri "/history/" -Method GET -TimeoutSec 10
     = ..outputs
    if ( -and .'9') {
         = .'9'.images[0]
         = "/view?filename=&subfolder=&type=output"
         = "\output\first_manga_20261017_052523.png"
        
        Invoke-WebRequest -Uri  -OutFile  -TimeoutSec 30
         = (Get-Item ).Length
         = ([DateTime]::Now - ).TotalSeconds
        
        Add-Result -Step "Test generation" -Status "PASS" -Details "0s, 0 Ko"
        Write-Log "Image generee: "
        Write-Log "=== PREMIERE IMAGE MANGA HISTORIQUE REUSSIE ===" "SUCCESS"
    } else {
        Add-Result -Step "Test generation" -Status "FAIL" -Details "Aucune image dans les outputs"
         = 1
    }
}

# === EXECUTION PRINCIPALE ===
Write-Log "========================================"
Write-Log "TikTokHistoryFactory Setup"
Write-Log "Mode: "
Write-Log "Date: 2026-10-17 05:25:23"
Write-Log "========================================"

switch () {
    "Check"   { Invoke-PhaseCheck }
    "Install" { Invoke-PhaseCheck; Invoke-PhaseInstall }
    "Start"   { Invoke-PhaseCheck; Invoke-PhaseStart }
    "Test"    { Invoke-PhaseCheck; Invoke-PhaseStart; Invoke-PhaseTest }
    "Full"    { Invoke-PhaseCheck; Invoke-PhaseInstall; Invoke-PhaseStart; Invoke-PhaseTest }
}

# Rapport final
 = if ( | Where-Object { .Status -eq "FAIL" }) { "FAIL" }
           elseif ( | Where-Object { .Status -eq "WARN" }) { "WARN" }
           else { "PASS" }

 = @{
    timestamp = Get-Date -Format "o"
    mode = 
    overall = 
    steps = 
    exit_code = 
} | ConvertTo-Json -Depth 5

 = "\reports"
if (-not (Test-Path )) { New-Item -ItemType Directory -Path  -Force | Out-Null }
 = "\setup-report-20261017-052523.json"
Set-Content -Path  -Value  -Encoding UTF8

Write-Log "========================================"
Write-Log "Rapport: "
Write-Log "Overall: "
Write-Log "PASS: 0"
Write-Log "WARN: 0"
Write-Log "FAIL: 0"
Write-Log "========================================"

if ( -eq 0 -and  -eq "Full") {
    Write-Log "=== SETUP COMPLET TERMINE ===" "SUCCESS"
    Write-Log "Prochaine etape: .\scripts\main.ps1 -Mode pilot" "SUCCESS"
}

exit 
'''

setup_path = os.path.join(scripts, 'setup-host-complete.ps1')
with open(setup_path, 'w', encoding='utf-8') as f:
    f.write(setup_content)

print(f'Setup script: {os.path.getsize(setup_path)} octets')
print('Scripts generes avec succes')
"""

# Ecrire et executer le generateur
with open(r'C:\TikTokHistoryFactory\_gen.py', 'w', encoding='utf-8') as f:
    f.write(pythonGen)

import subprocess
result = subprocess.run([r'C:\TikTokHistoryFactory\.venv\Scripts\python.exe', r'C:\TikTokHistoryFactory\_gen.py'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
