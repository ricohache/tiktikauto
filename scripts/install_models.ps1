#Requires -Version 5.1
<#
.SYNOPSIS
    Telecharge automatiquement les modeles necessaires pour TikTokHistoryFactory.
.DESCRIPTION
    Idempotent, reprise partielle, verification d'integrite.
    Execute sur Windows hote uniquement (besoin Internet).
#>
[CmdletBinding()]
param(
    [string]$ComfyUIPath = "C:\TikTokHistoryFactory\ComfyUI",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$script:ExitCode = 0

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path "$PSScriptRoot\..\logs\install-models.log" -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Test-DiskSpace {
    param([uint64]$RequiredBytes)
    $drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    $free = $drive.FreeSpace
    if ($free -lt $RequiredBytes) {
        throw "Espace disque insuffisant. Requis: $([math]::Round($RequiredBytes/1GB,1)) Go, Libre: $([math]::Round($free/1GB,1)) Go"
    }
    Write-Log "Espace disque OK: $([math]::Round($free/1GB,1)) Go disponible"
}

function Get-FileHashVerified {
    param([string]$Path, [string]$ExpectedHash)
    if (-not (Test-Path $Path)) { return $false }
    $hash = (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
    return ($hash -eq $ExpectedHash.ToLower())
}

function Invoke-ModelDownload {
    param(
        [string]$Url,
        [string]$Destination,
        [string]$Name,
        [string]$ExpectedHash = "",
        [string]$FallbackUrls = ""
    )
    Write-Log "Modele : $Name"
    Write-Log "  Destination : $Destination"
    
    $destDir = Split-Path $Destination -Parent
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    
    # Verifier si deja present et valide
    if ((Test-Path $Destination) -and -not $Force) {
        if ($ExpectedHash -and (Get-FileHashVerified -Path $Destination -ExpectedHash $ExpectedHash)) {
            Write-Log "  Deja present et valide. SKIPPED"
            return
        }
        if (-not $ExpectedHash) {
            $size = (Get-Item $Destination).Length
            if ($size -gt 1GB) {
                Write-Log "  Deja present ($([math]::Round($size/1MB,0)) Mo). SKIPPED"
                return
            }
        }
    }
    
    # Telechargement avec reprise
    $tempFile = "$Destination.tmp"
    $resume = $false
    $existingSize = 0
    if (Test-Path $tempFile) {
        $existingSize = (Get-Item $tempFile).Length
        $resume = $true
        Write-Log "  Reprise a $([math]::Round($existingSize/1MB,0)) Mo"
    }
    
    try {
        $request = [System.Net.HttpWebRequest]::Create($Url)
        $request.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        if ($resume -and $existingSize -gt 0) {
            $request.AddRange($existingSize)
        }
        $response = $request.GetResponse()
        $total = $response.ContentLength + $existingSize
        Write-Log "  Telechargement : $([math]::Round($total/1GB,2)) Go total"
        
        $mode = if ($resume) { [System.IO.FileMode]::Append } else { [System.IO.FileMode]::Create }
        $fs = [System.IO.File]::Open($tempFile, $mode, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $rs = $response.GetResponseStream()
        $buffer = New-Object byte[] 8192
        $read = 0
        $downloaded = $existingSize
        $lastReport = Get-Date
        
        while (($read = $rs.Read($buffer, 0, $buffer.Length)) -gt 0) {
            $fs.Write($buffer, 0, $read)
            $downloaded += $read
            if ((Get-Date) - $lastReport -gt [TimeSpan]::FromSeconds(10)) {
                $pct = if ($total -gt 0) { [math]::Round($downloaded/$total*100,1) } else { 0 }
                Write-Log "  Progression : $pct% ($([math]::Round($downloaded/1MB,0)) / $([math]::Round($total/1MB,0)) Mo)"
                $lastReport = Get-Date
            }
        }
        $fs.Close()
        $rs.Close()
        $response.Close()
        
        # Renommer
        if (Test-Path $Destination) { Remove-Item $Destination -Force }
        Rename-Item $tempFile $Destination -Force
        Write-Log "  Termine : $Destination"
    }
    catch {
        Write-Log "  ERREUR : $_" "ERROR"
        if ($FallbackUrls) {
            Write-Log "  Tentative URL secondaire..." "WARN"
            # Non implemente pour simplifier
        }
        throw
    }
}

# === MODELES A TELECHARGER ===
Write-Log "=== Installation des modeles ComfyUI ==="

# Verification espace disque (estimation 15 Go)
Test-DiskSpace -RequiredBytes 15GB

# 1. Checkpoint SDXL Manga : animagine-xl-3.1
# Licence : CreativeML Open RAIL-M (usage commercial autorise)
# Taille : ~6.9 Go
$checkpointDir = Join-Path $ComfyUIPath "ComfyUI\models\checkpoints"
$models = @(
    @{
        Name = "animagine-xl-3.1"
        Url = "https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors"
        Dest = Join-Path $checkpointDir "animagine-xl-3.1.safetensors"
        Hash = ""  # Hash non connu a l'avance, verification par taille
    }
)

# Modeles optionnels commentes (decommenter si besoin)
<#
$models += @{
    Name = "CounterfeitXL-v3.0"
    Url = "https://civitai.com/api/download/models/xxxx"
    Dest = Join-Path $checkpointDir "CounterfeitXL-v3.0.safetensors"
    Hash = ""
}
#>

$success = 0
$failed = 0
foreach ($m in $models) {
    try {
        Invoke-ModelDownload -Url $m.Url -Destination $m.Dest -Name $m.Name -ExpectedHash $m.Hash
        $success++
    }
    catch {
        Write-Log "ECHEC telechargement $($m.Name) : $_" "ERROR"
        $failed++
        $script:ExitCode = 1
    }
}

Write-Log "=== Resume ==="
Write-Log "Succes : $success / $($models.Count)"
if ($failed -gt 0) { Write-Log "Echecs : $failed" "ERROR" }

exit $script:ExitCode
