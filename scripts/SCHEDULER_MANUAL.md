# TikTokHistoryFactory V5 — Configuration Planificateur Windows
# INSTRUCTIONS MANUELLES (sandbox non elevee)
#
# 1. Ouvrir PowerShell en administrateur
# 2. Executer: schtasks /create /tn "TikTokHistoryFactory_V5_08h" /tr "powershell.exe -ExecutionPolicy Bypass -File C:\TikTokHistoryFactory\scripts\run_auto.ps1" /sc daily /st 08:00 /ru SYSTEM
# 3. Executer: schtasks /create /tn "TikTokHistoryFactory_V5_14h" /tr "powershell.exe -ExecutionPolicy Bypass -File C:\TikTokHistoryFactory\scripts\run_auto.ps1" /sc daily /st 14:00 /ru SYSTEM
# 4. Executer: schtasks /create /tn "TikTokHistoryFactory_V5_20h" /tr "powershell.exe -ExecutionPolicy Bypass -File C:\TikTokHistoryFactory\scripts\run_auto.ps1" /sc daily /st 20:00 /ru SYSTEM
#
# IMPORTANT: Les taches sont DESACTIVEES par defaut. Pour activer:
#   schtasks /change /tn "TikTokHistoryFactory_V5_08h" /ENABLE
#   schtasks /change /tn "TikTokHistoryFactory_V5_14h" /ENABLE
#   schtasks /change /tn "TikTokHistoryFactory_V5_20h" /ENABLE
#
# Pour desactiver:
#   schtasks /change /tn "TikTokHistoryFactory_V5_08h" /DISABLE
#
# Pour supprimer:
#   schtasks /delete /tn "TikTokHistoryFactory_V5_08h" /F
#   schtasks /delete /tn "TikTokHistoryFactory_V5_14h" /F
#   schtasks /delete /tn "TikTokHistoryFactory_V5_20h" /F
