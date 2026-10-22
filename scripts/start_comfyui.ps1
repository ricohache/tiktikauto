# Demarrage autonome de ComfyUI sur la machine reelle
# Ce script doit etre execute hors de l'environnement Codex
$ErrorActionPreference = "Stop"
$comfyRoot = "C:\TikTokHistoryFactory\ComfyUI"
$logFile = "$comfyRoot\comfyui_autostart.log"

function Write-Log($msg) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $msg" | Tee-Object -FilePath $logFile -Append
}

Write-Log "=== Démarrage ComfyUI ==="
Write-Log "GPU detecte : $(nvidia-smi --query-gpu=name --format=csv,noheader)"

# Verifier Python embarque
$py = "$comfyRoot\python_embeded\python.exe"
if (-not (Test-Path $py)) {
    Write-Log "ERREUR : Python embarque introuvable"
    exit 1
}

# Verifier modeles
$cpDir = "$comfyRoot\ComfyUI\models\checkpoints"
$cpFiles = Get-ChildItem -Path $cpDir -Filter "*.safetensors" -ErrorAction SilentlyContinue
if (-not $cpFiles) {
    Write-Log "AVERTISSEMENT : Aucun checkpoint trouve. Telecharger un modele manga."
    Write-Log "  Exemple : https://civitai.com/search?query=manga+sdxl"
}

# Demarrer ComfyUI
Write-Log "Lancement : $py -s ComfyUI\main.py --windows-standalone-build"
$proc = Start-Process -FilePath $py -ArgumentList @("-s", "ComfyUI\main.py", "--windows-standalone-build", "--listen", "127.0.0.1", "--port", "8188") -WorkingDirectory $comfyRoot -PassThru -WindowStyle Normal

Write-Log "PID : $($proc.Id)"

# Attendre le demarrage
$maxWait = 120
$started = $false
for ($i = 0; $i -lt $maxWait; $i++) {
    Start-Sleep -Seconds 1
    if ($proc.HasExited) {
        Write-Log "ERREUR : ComfyUI s'est arrete prematurement (code $($proc.ExitCode))"
        exit 1
    }
    # Tester le port
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-Log "✅ ComfyUI demarre avec succes !"
            Write-Log "Acces : http://127.0.0.1:8188"
            $started = $true
            break
        }
    } catch { }
    if ($i % 10 -eq 0) {
        Write-Log "Attente demarrage... ($i/$maxWait)"
    }
}

if (-not $started) {
    Write-Log "ERREUR : ComfyUI n'a pas demarre apres $maxWait secondes"
    Write-Log "Consultez les logs ComfyUI ou executez run_nvidia_gpu.bat manuellement"
    exit 1
}

Write-Log "=== ComfyUI operationnel ==="
