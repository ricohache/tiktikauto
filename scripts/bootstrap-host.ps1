#Requires -Version 5.1
# TikTokHistoryFactory Bootstrap
param([ValidateSet('Check','Install','Start','Test','Full','Help')][string]$Action='Check')
$ErrorActionPreference='Stop'
$FactoryPath='C:\TikTokHistoryFactory'
$ComfyUIPath='$FactoryPath\ComfyUI'
$LogFile='$FactoryPath\logs\bootstrap.log'
function Write-Log{param([string]$Message,[string]$Level='INFO')
$ts=Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$line="[$ts] [$Level] $Message"
Write-Host $line
Add-Content -Path $LogFile -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue}
Write-Log '=== TikTokHistoryFactory Bootstrap ==='
Write-Log "Action: $Action"
$Results=@()
Add-Result -Step 'Windows' -Status 'PASS' -Details "Build $([System.Environment]::OSVersion.Version.Build)"
$ffmpeg='$FactoryPath\ffmpeg\bin\ffmpeg.exe'
if(Test-Path $ffmpeg){Add-Result -Step 'FFmpeg' -Status 'PASS' -Details 'Present'}
else{Add-Result -Step 'FFmpeg' -Status 'FAIL' -Details 'Non trouve'}
$comfyPy='$ComfyUIPath\python_embeded\python.exe'
if((Test-Path '$ComfyUIPath\run_nvidia_gpu.bat')-and(Test-Path $comfyPy)){Add-Result -Step 'ComfyUI' -Status 'PASS' -Details 'Present'}
else{Add-Result -Step 'ComfyUI' -Status 'FAIL' -Details 'Manquant'}
$ckptDir='$ComfyUIPath\ComfyUI\models\checkpoints'
$ckpts=Get-ChildItem -Path $ckptDir -Filter '*.safetensors' -ErrorAction SilentlyContinue
if($ckpts-and($ckpts.Count-gt 0)){Add-Result -Step 'Checkpoints' -Status 'PASS' -Details "$($ckpts.Count) modele(s)"}
else{Add-Result -Step 'Checkpoints' -Status 'WARN' -Details 'Aucun'}
Write-Log "Resultats: $($Results.Count)"
Write-Log 'Bootstrap termine'
function Add-Result{param([string]$Step,[string]$Status,[string]$Details='')
$script:Results+=[PSCustomObject]@{Step=$Step;Status=$Status;Details=$Details}
Write-Log "$Step : $Status - $Details"}
exit 0