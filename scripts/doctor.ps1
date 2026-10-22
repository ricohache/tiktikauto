#Requires -Version 5.1
# Doctor TikTokHistoryFactory
$report = @()
$report += "=== Diagnostic ==="
$os = Get-CimInstance Win32_OperatingSystem
$report += "OS: $($os.Caption) Build $($os.BuildNumber)"
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$report += "Disque: $([math]::Round($disk.FreeSpace/1GB,1)) Go libres"
$nv = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
if ($nv) { $report += "GPU: $($nv.Name)" } else { $report += "GPU: Non detecte" }
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ff) { $report += "FFmpeg: $($ff.Source)" } else { $report += "FFmpeg: Non trouve" }
$cp = "C:\TikTokHistoryFactory\ComfyUI"
if ((Test-Path "$cp\run_nvidia_gpu.bat") -and (Test-Path "$cp\python_embeded\python.exe")) {
    $report += "ComfyUI: Present"
} else {
    $report += "ComfyUI: Manquant"
}
$report | ForEach-Object { Write-Output $_ }
