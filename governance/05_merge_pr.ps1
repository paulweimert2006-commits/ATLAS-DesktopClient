# ============================================================================
# ATLAS Governance - PR mergen
# ============================================================================
# Mergt einen Pull Request via GitHub CLI (Squash-Merge).
#
# Verwendung:
#   .\05_merge_pr.ps1 -PRNumber 42
#   .\05_merge_pr.ps1 -PRNumber 42 -Strategy merge
#   .\05_merge_pr.ps1                          # liest .last_pr
#   .\05_merge_pr.ps1 -Force                   # ohne Bestaetigung
# ============================================================================

param(
    [string]$PRNumber = "",

    [ValidateSet("squash", "merge", "rebase")]
    [string]$Strategy = "squash",

    [switch]$Force
)

. "$PSScriptRoot\_lib.ps1"

Assert-GhInstalled

if ($PRNumber -eq "") {
    $lastPrFile = Join-Path $PSScriptRoot ".last_pr"
    if (Test-Path $lastPrFile) {
        $PRNumber = (Get-Content $lastPrFile -Raw).Trim()
    }
    if ($PRNumber -eq "") {
        Write-Err "Keine PR-Nummer angegeben und keine .last_pr Datei gefunden."
        exit 1
    }
    Write-Info "PR-Nummer aus .last_pr gelesen: $PRNumber"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS PR Merge: #$PRNumber ($Strategy)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Step "PR-Details abrufen..."

$prJson = gh pr view $PRNumber --json title,baseRefName,headRefName,state,mergeable 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Konnte PR #$PRNumber nicht abrufen: $prJson"
    exit 1
}

$pr = $prJson | ConvertFrom-Json
Write-Info "Titel:  $($pr.title)"
Write-Info "Flow:   $($pr.headRefName) -> $($pr.baseRefName)"
Write-Info "Status: $($pr.state)"

if ($pr.state -ne "OPEN") {
    Write-Warn "PR ist nicht offen (Status: $($pr.state)). Nichts zu tun."
    exit 0
}

if (-not $Force) {
    $proceed = Confirm-Action "PR #$PRNumber ($($pr.headRefName) -> $($pr.baseRefName)) per $Strategy mergen?"
    if (-not $proceed) { exit 0 }
}

Write-Step "PR mergen..."

$mergeArgs = @("pr", "merge", $PRNumber, "--$Strategy")

$result = & gh @mergeArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Merge fehlgeschlagen: $result"
    exit 1
}

Write-Ok "PR #$PRNumber erfolgreich gemerged ($Strategy)"

Write-Step "Lokales Repository aktualisieren..."
git fetch --all --prune 2>&1 | Out-Null
git pull 2>&1 | Out-Null
Write-Ok "Lokales Repository aktualisiert"
