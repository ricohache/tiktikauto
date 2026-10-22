<#
Non-destructive local Windows runner for TikTokHistoryFactory pilot V5.
Writes under output\pilot-thiaroye-1944-90s-v5; preserves V3 and V4.
Does not change Codex/Ollama/ComfyUI configuration or tiktoknet ACL.
#>
[CmdletBinding()]
param(
    [string]$Project='C:\TikTokHistoryFactory',
    [string]$Piper='',
    [string]$Voice='',
    [switch]$SkipImageGeneration,
    [switch]$UseNvenc
)
$ErrorActionPreference='Stop'
$Root = (Resolve-Path -LiteralPath $Project -ErrorAction Stop).Path
$Script = Join-Path $PSScriptRoot 'finish_pilot.py'
$Test = Join-Path $PSScriptRoot 'test_finish_pilot.py'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $Cmd) {throw 'Python not detected in project .venv or PATH'}
    $Python=$Cmd.Source
}
$Out=Join-Path $Root 'output\pilot-thiaroye-1944-90s-v5'
New-Item -ItemType Directory -Path (Join-Path $Out 'logs') -Force | Out-Null
$Log=Join-Path $Out ('logs\run_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+'.txt')
Start-Transcript -Path $Log | Out-Null
try {
    Write-Host '=== TIKTOKHISTORYFACTORY V5 : LOCAL PILOT FINALIZER ===' -ForegroundColor Cyan
    Write-Host "Project: $Root"
    Write-Host "Audit/report log: $Log"
    Write-Host '0. Local automated render and caption tests (no publication)'
    & $Python $Test
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic unit tests failed' }

    Write-Host '1. Inventory of existing V3 source media'
    & $Python $Script --project $Root --preflight
    if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; V3 originals preserved' }

    if (-not $SkipImageGeneration) {
        try {
            $null=Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 5
            Write-Host 'ComfyUI responding' -ForegroundColor Green
        } catch {
            $Launcher=Join-Path $Root 'scripts\start_comfyui.ps1'
            if (-not (Test-Path -LiteralPath $Launcher)) {
                throw 'ComfyUI unavailable and project launcher missing'
            }
            Write-Host 'Starting existing ComfyUI using project launcher only'
            & $Launcher
            $ready=$false
            for($attempt=0;$attempt -lt 12;$attempt++) {
                try {
                    $null=Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 5
                    $ready=$true
                    break
                } catch { Start-Sleep -Seconds 5 }
            }
            if (-not $ready) { throw 'ComfyUI still unavailable after start attempt' }
        }
    }

    Write-Host '2. Generate/reuse source illustrations, voice, subtitles, control preview, and final MP4'
    $Arg=@($Script,'--project',$Root)
    if($Piper) { $Arg+=@('--piper',$Piper) }
    if($Voice) { $Arg+=@('--voice',$Voice) }
    if($SkipImageGeneration) { $Arg+='--skip-image-generation' }
    if($UseNvenc) { $Arg+='--nvenc' }
    & $Python @Arg
    if($LASTEXITCODE -ne 0) { throw "Production failure (exit $LASTEXITCODE)" }
    $Mp4=Join-Path $Out 'thiaroye-1944-90s-v5-final.mp4'
    if (-not (Test-Path -LiteralPath $Mp4)) { throw "Final MP4 not found: $Mp4" }
    $Json=Join-Path $Out 'metadata\finish-report.json'
    $report=Get-Content -LiteralPath $Json -Raw | ConvertFrom-Json
    if ($report.test -or -not $report.qc.technical_checks_passed) {
        throw 'The output did not pass actual technical final checks'
    }
    Write-Host "FINAL VERIFIED BY FFmpeg, FFprobe AND AUDIO QC: $Mp4" -ForegroundColor Green
    Write-Host 'Human historic accuracy, framing and speech interpretation reviews remain necessary.'
} finally {
    Stop-Transcript | Out-Null
}
