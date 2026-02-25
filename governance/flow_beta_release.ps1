# ============================================================================
# ATLAS Governance - Beta Release Flow (Orchestrator)
# ============================================================================
# Fuehrt den kompletten Beta-Release-Flow aus:
#   1. Login (interaktiv, einmalig)
#   2. Version bump (patch, oder per Parameter)
#   3. PR: dev -> beta
#   4. CI-Checks abwarten
#   5. PR mergen
#   6. Git-Tag (beta)
#   7. Build (PyInstaller + Inno Setup)
#   8. Upload + Gates + Aktivierung (beta, optional)
#
# Verwendung:
#   .\flow_beta_release.ps1
#   .\flow_beta_release.ps1 -BumpType minor
#   .\flow_beta_release.ps1 -SkipBuild           # Nur PR-Flow, kein Build/Upload
#   .\flow_beta_release.ps1 -ReleaseNotes "Beta-Test fuer neue Features"
#   .\flow_beta_release.ps1 -Token $jwt -Force   # Non-interaktiv (fuer Agents/CI)
# ============================================================================

param(
    [ValidateSet("major", "minor", "patch")]
    [string]$BumpType = "patch",

    [string]$ReleaseNotes = "",
    [string]$Token = "",

    [switch]$SkipBuild,
    [switch]$Force,

    [int]$CheckInterval = 15,
    [int]$CheckTimeout = 600
)

. "$PSScriptRoot\_lib.ps1"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " ATLAS Beta Release Flow (dev -> beta)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Login ---

Write-Step "Admin-Login (fuer Release-Upload)..."

if (-not $SkipBuild) {
    if ($Token -ne "") {
        Write-Ok "Token per Parameter uebergeben (non-interaktiv)"
    }
    else {
        $Token = Invoke-AtlasLogin
    }
}
else {
    Write-Info "Build/Upload uebersprungen -- kein Login noetig"
}

# --- 2. Version Bump ---

Write-Step "Version bump ($BumpType)..."

& "$PSScriptRoot\09_version_bump.ps1" -Action bump -Type $BumpType -Commit -Push
if ($LASTEXITCODE -ne 0) {
    Write-Err "Version Bump fehlgeschlagen"
    exit 1
}

$version = Get-AtlasVersion
Write-Ok "Version: $version"

# --- 3. PR: dev -> beta ---

Write-Step "PR erstellen: dev -> beta..."

& "$PSScriptRoot\03_create_pr.ps1" -Base beta -Head dev -Title "ATLAS v$version: DEV -> BETA"
if ($LASTEXITCODE -ne 0) {
    Write-Err "PR-Erstellung fehlgeschlagen"
    exit 1
}

$prNumber = (Get-Content (Join-Path $PSScriptRoot ".last_pr") -Raw).Trim()
Write-Ok "PR #$prNumber erstellt"

# --- 4. CI-Checks abwarten ---

Write-Step "CI-Checks abwarten..."

& "$PSScriptRoot\04_wait_for_checks.ps1" -PRNumber $prNumber -Interval $CheckInterval -Timeout $CheckTimeout
if ($LASTEXITCODE -ne 0) {
    Write-Err "CI-Checks fehlgeschlagen oder Timeout"
    exit 1
}

# --- 5. PR mergen ---

Write-Step "PR mergen..."

& "$PSScriptRoot\05_merge_pr.ps1" -PRNumber $prNumber -Force
if ($LASTEXITCODE -ne 0) {
    Write-Err "PR-Merge fehlgeschlagen"
    exit 1
}

# --- 6. Git-Tag ---

Write-Step "Git-Tag erstellen (beta)..."

git checkout beta 2>&1 | Out-Null
git pull origin beta 2>&1 | Out-Null

& "$PSScriptRoot\10_git_tag.ps1" -Channel beta -Push
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Git-Tag konnte nicht erstellt werden (nicht kritisch)"
}

# --- 7 & 8. Build + Upload (optional) ---

if (-not $SkipBuild) {
    Write-Step "Installer bauen..."

    & "$PSScriptRoot\06_build_installer.ps1" -Version $version
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Build fehlgeschlagen"
        exit 1
    }

    Write-Step "Release hochladen (beta, optional)..."

    & "$PSScriptRoot\07_upload_release.ps1" `
        -Token $Token `
        -Channel beta `
        -ReleaseNotes $ReleaseNotes

    if ($LASTEXITCODE -ne 0) {
        Write-Err "Release-Upload fehlgeschlagen"
        exit 1
    }
}
else {
    Write-Info "Build und Upload uebersprungen (-SkipBuild)"
}

# --- Ergebnis ---

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host " Beta Release Flow abgeschlossen" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Version:  $version" -ForegroundColor White
Write-Host "  Channel:  beta" -ForegroundColor White
Write-Host "  Status:   active (optional)" -ForegroundColor White
Write-Host ""
