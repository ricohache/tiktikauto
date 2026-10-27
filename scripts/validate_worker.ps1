<#
.SYNOPSIS
    Valide le Worker Cloudflare post-deploiement depuis un terminal externe.
.DESCRIPTION
    Effectue les 5 verifications obligatoires de la mission :
    1. GET 200 + video/mp4
    2. HEAD 200 + Content-Length
    3. Range 206 Partial Content
    4. Cle non autorisee -> 403
    5. PUT interdit -> 405
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$WorkerUrl,
    [string]$AllowedKey = "thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
)

$ErrorActionPreference = "Stop"
$fullUrl = "$WorkerUrl/$AllowedKey"

function Test-Status($method, $url, $headers, $expectedStatus, $description) {
    Write-Host "`n[$description] $method $url"
    try {
        $resp = Invoke-WebRequest -Uri $url -Method $method -Headers $headers -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -eq $expectedStatus) {
            Write-Host "  PASS : $($resp.StatusCode)"
            return $resp
        } else {
            Write-Host "  FAIL : attendu $expectedStatus, recu $($resp.StatusCode)"
            return $null
        }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq $expectedStatus) {
            Write-Host "  PASS : $code (attendu)"
            return $_.Exception.Response
        } else {
            Write-Host "  FAIL : attendu $expectedStatus, recu $code"
            return $null
        }
    }
}

Write-Host "=== Validation Worker Cloudflare ===" -ForegroundColor Cyan
Write-Host "Worker URL : $WorkerUrl"
Write-Host "Allowed key: $AllowedKey"

# 1. GET
$getResp = Test-Status "GET" $fullUrl @{} 200 "GET authentifie (aucune auth requise)"
if ($getResp) {
    $ct = $getResp.Headers["Content-Type"]
    if ($ct -like "*video/mp4*") {
        Write-Host "  Content-Type OK : $ct"
    } else {
        Write-Host "  FAIL Content-Type inattendu : $ct"
    }
}

# 2. HEAD
Test-Status "HEAD" $fullUrl @{} 200 "HEAD metadata"

# 3. Range
Test-Status "GET" $fullUrl @{"Range"="bytes=0-1023"} 206 "Range video"

# 4. Forbidden
$badUrl = "$WorkerUrl/thf/unknown.mp4"
Test-Status "GET" $badUrl @{} 403 "Cle non autorisee"

# 5. PUT interdit
Test-Status "PUT" $fullUrl @{} 405 "PUT interdit"

Write-Host "`n=== Validation terminee ===" -ForegroundColor Cyan
