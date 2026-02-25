# ============================================================================
# ATLAS Governance - Alte Releases auf deprecated setzen
# ============================================================================
# Setzt alle aktiven Releases (active/mandatory) auf deprecated,
# optional mit Ausnahme eines bestimmten Release.
#
# Verwendung:
#   .\08_deprecate_releases.ps1 -Token $token
#   .\08_deprecate_releases.ps1 -Token $token -ExcludeId 42
#   .\08_deprecate_releases.ps1 -Token $token -Force
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [string]$Token,

    [int]$ExcludeId = 0,

    [switch]$Force
)

. "$PSScriptRoot\_lib.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Releases deprecaten" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ExcludeId aus .last_release_id lesen wenn nicht angegeben
if ($ExcludeId -eq 0) {
    $lastReleaseFile = Join-Path $PSScriptRoot ".last_release_id"
    if (Test-Path $lastReleaseFile) {
        $ExcludeId = [int](Get-Content $lastReleaseFile -Raw).Trim()
        Write-Info "ExcludeId aus .last_release_id gelesen: $ExcludeId"
    }
}

Write-Step "Aktive Releases abrufen..."

$response = Invoke-AtlasApi -Endpoint "/admin/releases" -Method GET -Token $Token

if (-not $response) {
    Write-Err "Konnte Releases nicht abrufen"
    exit 1
}

$releases = $response.data
if (-not $releases) { $releases = $response }

$activeReleases = @($releases | Where-Object {
    $_.status -in @("active", "mandatory") -and [int]$_.id -ne $ExcludeId
})

if ($activeReleases.Count -eq 0) {
    Write-Ok "Keine aktiven Releases zum Deprecaten gefunden."
    exit 0
}

Write-Info "Folgende Releases werden auf 'deprecated' gesetzt:"
foreach ($r in $activeReleases) {
    Write-Host "    - ID $($r.id): v$($r.version) ($($r.channel), $($r.status))" -ForegroundColor Yellow
}

if ($ExcludeId -gt 0) {
    Write-Info "Ausgenommen: Release ID $ExcludeId"
}

if (-not $Force) {
    $proceed = Confirm-Action "$($activeReleases.Count) Release(s) werden auf 'deprecated' gesetzt."
    if (-not $proceed) { exit 0 }
}

Write-Step "Releases deprecaten..."

$succeeded = 0
$failed = 0

foreach ($r in $activeReleases) {
    $result = Invoke-AtlasApi `
        -Endpoint "/admin/releases/$($r.id)" `
        -Method PUT `
        -Token $Token `
        -Body @{ status = "deprecated" }

    if ($result -and $result.success) {
        Write-Ok "Release $($r.id) (v$($r.version)): deprecated"
        $succeeded++
    }
    else {
        Write-Warn "Release $($r.id) konnte nicht deprecated werden"
        $failed++
    }
}

Write-Host ""
if ($failed -eq 0) {
    Write-Ok "Alle $succeeded Release(s) erfolgreich deprecated"
}
else {
    Write-Warn "$succeeded erfolgreich, $failed fehlgeschlagen"
}
