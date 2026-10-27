#Requires -Version 5.1
<#
.SYNOPSIS
    Preparation des creneaux quotidiens Windows Task Scheduler.
    AUCUNE TACHE N EST ACTIVEE sans consentement explicite.
#>
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$runner = Join-Path $ProjectRoot 'src\v5_factory\autonomous_runner.py'

$slots = @(
    @{Name='THF_Morning'; Hour=8; Minute=0},
    @{Name='THF_Afternoon'; Hour=14; Minute=0},
    @{Name='THF_Evening'; Hour=20; Minute=0}
)

$dataDir = Join-Path $ProjectRoot 'data'
if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }

foreach ($slot in $slots) {
    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>TikTokHistoryFactory V5 - $($slot.Name)</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-10-26T$($slot.Hour.ToString('00')):$($slot.Minute.ToString('00')):00</StartBoundary>
      <Enabled>false</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>$pythonExe</Command>
      <Arguments>"$runner" --batch 1</Arguments>
      <WorkingDirectory>$ProjectRoot</WorkingDirectory>
    </Exec>
  </Actions>
  <Settings>
    <Enabled>false</Enabled>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <StartWhenAvailable>true</StartWhenAvailable>
  </Settings>
</Task>
"@
    $path = Join-Path $dataDir "task_$($slot.Name).xml"
    $xml | Out-File $path -Encoding utf8
    Write-Host "[SCHEDULER] Fichier de tache prepare: $path ($($slot.Hour):$($slot.Minute)) - DESACTIVE"
}

Write-Host ""
Write-Host "=== TACHES PREPAREES MAIS NON ACTIVEES ===" -ForegroundColor Yellow
Write-Host "Pour activer manuellement depuis PowerShell administrateur :"
Write-Host "  schtasks /create /xml '\data\task_THF_Morning.xml' /tn 'THF_Morning'"
Write-Host "  schtasks /create /xml '\data\task_THF_Afternoon.xml' /tn 'THF_Afternoon'"
Write-Host "  schtasks /create /xml '\data\task_THF_Evening.xml' /tn 'THF_Evening'"
Write-Host ""
Write-Host "Les taches sont configurees ENABLED=false dans le XML."
