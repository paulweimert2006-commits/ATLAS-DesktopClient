# ============================================================================
# ATLAS Governance - Full Governance Flow (Orchestrator)
# ============================================================================
# Fuehrt den kompletten Governance-Zyklus aus:
#   1. Branch Cleanup (alle ausser main/beta/dev loeschen)
#   2. Branch Reset (beta + dev auf main setzen)
#   3. Beta Release Flow (dev -> beta, Build, Upload)
#   4. Stable Release Flow (beta -> main, Build, Upload, Mandatory)
#
# ACHTUNG: Dies ist die aggressivste Operation.
#          Alle Feature-Branches werden geloescht!
#          beta und dev werden auf main zurueckgesetzt!
#          Ein MANDATORY Stable Release wird erstellt!
#
# Verwendung:
#   .\flow_full_governance.ps1
#   .\flow_full_governance.ps1 -SkipCleanup   # Ohne Branch-Cleanup
#   .\flow_full_governance.ps1 -SkipReset     # Ohne Branch-Reset
#   .\flow_full_governance.ps1 -SkipBuild     # Nur Git-Flow, kein Build/Upload
#   .\flow_full_governance.ps1 -Token $jwt -Force   # Non-interaktiv (Agents/CI)
# ============================================================================

param(
    [switch]$SkipCleanup,
    [switch]$SkipReset,
    [switch]$SkipBuild,
    [switch]$Force,

    [ValidateSet("major", "minor", "patch")]
    [string]$BumpType = "patch",

    [string]$ReleaseNotes = "",
    [string]$Token = "",

    [int]$CheckInterval = 15,
    [int]$CheckTimeout = 600
)

. "$PSScriptRoot\_lib.ps1"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Red
Write-Host " ATLAS Full Governance Flow" -ForegroundColor Red
Write-Host "========================================================" -ForegroundColor Red
Write-Host ""
Write-Host "  Dieser Flow fuehrt ALLE Governance-Schritte aus:" -ForegroundColor Yellow
Write-Host "    1. Alle Feature-Branches loeschen" -ForegroundColor Yellow
Write-Host "    2. beta + dev auf main zuruecksetzen" -ForegroundColor Yellow
Write-Host "    3. Beta Release (dev -> beta)" -ForegroundColor Yellow
Write-Host "    4. Stable Release (beta -> main, MANDATORY)" -ForegroundColor Yellow
Write-Host ""

if ($SkipCleanup) { Write-Info "Branch Cleanup: UEBERSPRUNGEN (-SkipCleanup)" }
if ($SkipReset)   { Write-Info "Branch Reset:   UEBERSPRUNGEN (-SkipReset)" }
if ($SkipBuild)   { Write-Info "Build/Upload:   UEBERSPRUNGEN (-SkipBuild)" }

if (-not $Force) {
    $proceed = Confirm-Action "Full Governance Flow starten? Tippe 'GOVERNANCE':" -RequiredInput "GOVERNANCE"
    if (-not $proceed) { exit 0 }
}
else {
    Write-Warn "Force-Modus: Bestaetigung uebersprungen"
}

$startTime = Get-Date

# =========================================================================
# PHASE 1: Branch Cleanup
# =========================================================================

if (-not $SkipCleanup) {
    Write-Host ""
    Write-Host "--- Phase 1: Branch Cleanup ---" -ForegroundColor Magenta

    & "$PSScriptRoot\01_cleanup_branches.ps1" -Force
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Branch Cleanup hatte Fehler (nicht kritisch, fahre fort)"
    }
}

# =========================================================================
# PHASE 2: Branch Reset
# =========================================================================

if (-not $SkipReset) {
    Write-Host ""
    Write-Host "--- Phase 2: Branch Reset ---" -ForegroundColor Magenta

    $resetArgs = @{}
    if ($Force) { $resetArgs["Force"] = $true }
    & "$PSScriptRoot\02_reset_branches.ps1" @resetArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Branch Reset fehlgeschlagen -- Abbruch"
        exit 1
    }
}

# =========================================================================
# PHASE 3: Beta Release Flow
# =========================================================================

Write-Host ""
Write-Host "--- Phase 3: Beta Release Flow ---" -ForegroundColor Magenta

$betaArgs = @{
    BumpType      = $BumpType
    CheckInterval = $CheckInterval
    CheckTimeout  = $CheckTimeout
}
if ($ReleaseNotes -ne "") { $betaArgs["ReleaseNotes"] = $ReleaseNotes }
if ($SkipBuild) { $betaArgs["SkipBuild"] = $true }
if ($Token -ne "") { $betaArgs["Token"] = $Token }
if ($Force) { $betaArgs["Force"] = $true }

& "$PSScriptRoot\flow_beta_release.ps1" @betaArgs
if ($LASTEXITCODE -ne 0) {
    Write-Err "Beta Release Flow fehlgeschlagen -- Abbruch"
    exit 1
}

# =========================================================================
# PHASE 4: Stable Release Flow
# =========================================================================

Write-Host ""
Write-Host "--- Phase 4: Stable Release Flow ---" -ForegroundColor Magenta

$stableArgs = @{
    CheckInterval = $CheckInterval
    CheckTimeout  = $CheckTimeout
}
if ($ReleaseNotes -ne "") { $stableArgs["ReleaseNotes"] = $ReleaseNotes }
if ($SkipBuild) { $stableArgs["SkipBuild"] = $true }
if ($Token -ne "") { $stableArgs["Token"] = $Token }
if ($Force) { $stableArgs["Force"] = $true }

& "$PSScriptRoot\flow_stable_release.ps1" @stableArgs
if ($LASTEXITCODE -ne 0) {
    Write-Err "Stable Release Flow fehlgeschlagen"
    exit 1
}

# =========================================================================
# ERGEBNIS
# =========================================================================

$duration = (Get-Date) - $startTime
$durationMin = [math]::Round($duration.TotalMinutes, 1)

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host " Full Governance Flow ABGESCHLOSSEN" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Dauer:    $durationMin Minuten" -ForegroundColor White
Write-Host "  Version:  $(Get-AtlasVersion)" -ForegroundColor White
Write-Host ""
Write-Host "  Ergebnis:" -ForegroundColor White
Write-Host "    - Nur main/beta/dev existieren" -ForegroundColor Green
Write-Host "    - Beta Release: active (optional)" -ForegroundColor Green
Write-Host "    - Stable Release: MANDATORY" -ForegroundColor Green
Write-Host "    - Alle alten Releases: deprecated" -ForegroundColor Green
Write-Host ""
