# Planning is deliberately not registered by the pilot delivery.
[CmdletBinding()]
param([string[]]$Times = @(), [switch]$RegisterDisabled)
$ErrorActionPreference = 'Stop'
if (-not $RegisterDisabled) {
    Write-Host 'Aucune tache creee. Apres validation du pilote, fournir trois horaires et -RegisterDisabled.'
    exit 0
}
if ($Times.Count -ne 3 -or ($Times | Where-Object { $_ -notmatch '^([01][0-9]|2[0-3]):[0-5][0-9]$' })) {
    throw 'Fournir exactement trois horaires HH:mm distincts, choisis par le proprietaire.'
}
if (($Times | Select-Object -Unique).Count -ne 3) { throw 'Les horaires doivent etre distincts.' }
throw 'Enregistrement bloque : le debit multi-sujets et la validation du pilote ne sont pas encore certifies. Aucun horaire impose ni tache creee.'
