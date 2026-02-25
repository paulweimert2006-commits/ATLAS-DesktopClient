# ============================================================================
# ATLAS Governance - Stable Release Flow (Orchestrator)
# ============================================================================
# Fuehrt den kompletten Stable-Release-Flow aus:
#   1. Login (interaktiv, einmalig)
#   2. PR: beta -> main
#   3. CI-Checks abwarten
#   4. PR mergen
#   5. Git-Tag (stable)
#   6. Build (PyInstaller + Inno Setup)
#   7. Alle alten Releases deprecaten
#   8. Upload + Gates + Aktivierung (stable, MANDATORY)
#
# Verwendung:
#   .\flow_stable_release.ps1
#   .\flow_stable_release.ps1 -SkipBuild            # Nur PR-Flow
#   .\flow_stable_release.ps1 -ReleaseNotes "..."
#   .\flow_stable_release.ps1 -Token $jwt -Force    # Non-interaktiv (fuer Agents/CI)
# ============================================================================

param(
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
Write-Host " ATLAS Stable Release Flow (beta -> main)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "  ACHTUNG: Dieser Flow erstellt ein MANDATORY Release." -ForegroundColor Yellow
Write-Host "  Alle Clients werden zum Update gezwungen." -ForegroundColor Yellow
Write-Host "  Alle aelteren Releases werden auf 'deprecated' gesetzt." -ForegroundColor Yellow
Write-Host ""

# --- 1. Login ---

Write-Step "Admin-Login..."

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

# --- 2. PR: beta -> main ---

Write-Step "PR erstellen: beta -> main..."

$version = Get-AtlasVersion

& "$PSScriptRoot\03_create_pr.ps1" -Base main -Head beta -Title "ATLAS v$version: BETA -> MAIN (Stable Release)"
if ($LASTEXITCODE -ne 0) {
    Write-Err "PR-Erstellung fehlgeschlagen"
    exit 1
}

$prNumber = (Get-Content (Join-Path $PSScriptRoot ".last_pr") -Raw).Trim()
Write-Ok "PR #$prNumber erstellt"

# --- 3. CI-Checks abwarten ---

Write-Step "CI-Checks abwarten..."

& "$PSScriptRoot\04_wait_for_checks.ps1" -PRNumber $prNumber -Interval $CheckInterval -Timeout $CheckTimeout
if ($LASTEXITCODE -ne 0) {
    Write-Err "CI-Checks fehlgeschlagen oder Timeout"
    exit 1
}

# --- 4. PR mergen ---

Write-Step "PR mergen..."

& "$PSScriptRoot\05_merge_pr.ps1" -PRNumber $prNumber -Force
if ($LASTEXITCODE -ne 0) {
    Write-Err "PR-Merge fehlgeschlagen"
    exit 1
}

# --- 5. Git-Tag ---

Write-Step "Git-Tag erstellen (stable)..."

git checkout main 2>&1 | Out-Null
git pull origin main 2>&1 | Out-Null

& "$PSScriptRoot\10_git_tag.ps1" -Channel stable -Push
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Git-Tag konnte nicht erstellt werden (nicht kritisch)"
}

# --- 6, 7, 8. Build + Upload + Deprecate (ATOMIC: Upload ZUERST!) ---
#
# KRITISCH: Die Reihenfolge ist absichtlich Upload-First.
# Wenn Deprecate zuerst laeuft und Upload dann fehlschlaegt,
# gibt es KEIN aktives Release mehr -- alle Clients blockieren.
# Deshalb: Neues Release hochladen + aktivieren, DANN alte deprecaten.

if (-not $SkipBuild) {
    Write-Step "Installer bauen..."

    & "$PSScriptRoot\06_build_installer.ps1" -Version $version
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Build fehlgeschlagen"
        exit 1
    }

    Write-Step "Release hochladen (stable, MANDATORY)..."

    & "$PSScriptRoot\07_upload_release.ps1" `
        -Token $Token `
        -Channel stable `
        -Mandatory `
        -ReleaseNotes $ReleaseNotes

    if ($LASTEXITCODE -ne 0) {
        Write-Err "Release-Upload fehlgeschlagen -- alte Releases bleiben UNVERAENDERT (sicher)"
        exit 1
    }

    Write-Step "Alle alten Releases deprecaten..."

    & "$PSScriptRoot\08_deprecate_releases.ps1" -Token $Token -Force
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Deprecate teilweise fehlgeschlagen (pruefen!) -- neues Release ist aber aktiv"
    }
}
else {
    Write-Info "Build und Upload uebersprungen (-SkipBuild)"
}

# --- Ergebnis ---

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host " Stable Release Flow abgeschlossen" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Version:  $version" -ForegroundColor White
Write-Host "  Channel:  stable" -ForegroundColor White
Write-Host "  Status:   MANDATORY" -ForegroundColor White
Write-Host "  Alte Releases: deprecated" -ForegroundColor White
Write-Host ""
Write-Host "  Alle Clients werden beim naechsten Start zum Update gezwungen." -ForegroundColor Yellow
Write-Host ""
