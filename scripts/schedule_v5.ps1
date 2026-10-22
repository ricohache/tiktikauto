# TikTokHistoryFactory V5 - Planification Windows (INACTIVE par defaut)
# Usage: .\scripts\schedule_v5.ps1 -Action Create|Delete|Status
[CmdletBinding()]
param(
    [ValidateSet('Create','Delete','Status')]
    [string]$Action = 'Status',
    [string]$Project = 'C:\TikTokHistoryFactory',
    [string]$Slots = '08:00,14:00,20:00',
    [switch]$Enable
)
$ErrorActionPreference = 'Stop'
$TaskName = 'TikTokHistoryFactory_V5_DailyProduction'
$Python = Join-Path $Project '.venv\Scripts\python.exe'
$Script = Join-Path $Project 'src\v5_factory\auto_engine.py'

function Get-Status {
    $tasks = Get-ScheduledTask -TaskName "$TaskName*" -ErrorAction SilentlyContinue
    if (-not $tasks) {
        Write-Host 'Aucune tache planifiee trouvee.' -ForegroundColor Yellow
        return
    }
    foreach ($t in $tasks) {
        Write-Host "Task: $($t.TaskName) | State: $($t.State) | Next: $($t.NextRunTime)"
    }
}

function Remove-Tasks {
    Get-ScheduledTask -TaskName "$TaskName*" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host 'Taches supprimees.' -ForegroundColor Green
}

function New-Tasks {
    $slots = $Slots -split ',' | ForEach-Object { $_.Trim() }
    for ($i = 0; $i -lt $slots.Count; $i++) {
        $time = $slots[$i]
        $name = "$TaskName`_Slot$($i+1)" 
        $cmd = "Set-Location '$Project'; [System.Environment]::SetEnvironmentVariable('PATH', [System.Environment]::GetEnvironmentVariable('PATH', 'Process') + ';$Project\ffmpeg\bin', 'Process'); & '$Python' '$Script'"
        $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-ExecutionPolicy Bypass -Command `"$cmd`""
        $trigger = New-ScheduledTaskTrigger -Daily -At $time
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Highest
        Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
        if (-not $Enable) {
            Disable-ScheduledTask -TaskName $name | Out-Null
        }
        $status = if ($Enable) { 'ACTIVE' } else { 'DISABLED' }
        Write-Host "Cree: $name a $time | Etat: $status"
    }
}

switch ($Action) {
    'Status' { Get-Status }
    'Create' { Remove-Tasks; New-Tasks; Write-Host 'Planification creee.' -ForegroundColor Cyan }
    'Delete' { Remove-Tasks }
}
