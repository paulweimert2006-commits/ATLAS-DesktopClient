# ============================================================================
# ATLAS Governance - Changelog aus PR-History generieren
# ============================================================================
# Extrahiert Release Notes aus gemergten PRs seit dem letzten Tag.
#
# Verwendung:
#   .\14_changelog_from_pr.ps1                    # Seit letztem Tag
#   .\14_changelog_from_pr.ps1 -SinceTag v2.2.5  # Seit bestimmtem Tag
#   .\14_changelog_from_pr.ps1 -SinceDate "2026-02-01"
#   .\14_changelog_from_pr.ps1 -OutputFile ".release_notes.txt"
#   .\14_changelog_from_pr.ps1 -Json
# ============================================================================

param(
    [string]$SinceTag = "",
    [string]$SinceDate = "",
    [string]$BaseBranch = "main",
    [string]$OutputFile = "",
    [switch]$Json
)

. "$PSScriptRoot\_lib.ps1"

if ($Json) { Set-GovernanceMode -Json }

Assert-GhInstalled

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Changelog Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Zeitpunkt bestimmen ---

Write-Step "Zeitraum bestimmen..."

$sinceArg = ""

if ($SinceTag -ne "") {
    $tagDate = git log -1 --format="%aI" $SinceTag 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Tag '$SinceTag' nicht gefunden"
        exit 1
    }
    $sinceArg = $tagDate.Trim().Substring(0, 10)
    Write-Ok "Seit Tag $SinceTag ($sinceArg)"
}
elseif ($SinceDate -ne "") {
    $sinceArg = $SinceDate
    Write-Ok "Seit Datum: $sinceArg"
}
else {
    Invoke-GitSilent fetch --tags
    $lastTag = git tag --sort=-version:refname | Select-Object -First 1
    if ($lastTag) {
        $tagDate = git log -1 --format="%aI" $lastTag.Trim() 2>&1
        $sinceArg = $tagDate.Trim().Substring(0, 10)
        Write-Ok "Seit letztem Tag: $($lastTag.Trim()) ($sinceArg)"
    }
    else {
        $sinceArg = (Get-Date).AddDays(-30).ToString("yyyy-MM-dd")
        Write-Warn "Kein Tag gefunden. Verwende letzte 30 Tage: $sinceArg"
    }
}

# --- Gemergte PRs abrufen ---

Write-Step "Gemergte PRs abrufen (seit $sinceArg)..."

$prsJson = gh pr list `
    --state merged `
    --base $BaseBranch `
    --json number,title,mergedAt,author,labels,body `
    --limit 100 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Err "Konnte PRs nicht abrufen: $prsJson"
    exit 1
}

$allPrs = $prsJson | ConvertFrom-Json

$filteredPrs = @($allPrs | Where-Object {
    $_.mergedAt -and $_.mergedAt.Substring(0, 10) -ge $sinceArg
} | Sort-Object -Property mergedAt -Descending)

Write-Ok "$($filteredPrs.Count) PR(s) gefunden"

if ($filteredPrs.Count -eq 0) {
    Write-Info "Keine gemergten PRs seit $sinceArg"
    Write-JsonResult -Action "changelog" -Success $true -Data @{ prs = 0; notes = "" }
    exit 0
}

# --- Commits zaehlen (fuer Kontext) ---

Write-Step "Commits zaehlen..."

$commitCount = 0
if ($SinceTag -ne "") {
    $commitCount = [int](git rev-list --count "$SinceTag..HEAD" 2>&1)
}
else {
    $commitCount = [int](git rev-list --count --since="$sinceArg" HEAD 2>&1)
}
Write-Info "$commitCount Commit(s) im Zeitraum"

# --- Changelog zusammenstellen ---

Write-Step "Changelog generieren..."

$categories = @{
    features    = [System.Collections.ArrayList]::new()
    fixes       = [System.Collections.ArrayList]::new()
    refactoring = [System.Collections.ArrayList]::new()
    other       = [System.Collections.ArrayList]::new()
}

foreach ($pr in $filteredPrs) {
    $title = $pr.title
    $entry = "- $title (#$($pr.number))"

    $labelNames = @($pr.labels | ForEach-Object { $_.name })

    if ($title -match "^(feat|feature)" -or "feature" -in $labelNames) {
        $categories.features.Add($entry) | Out-Null
    }
    elseif ($title -match "^(fix|bug)" -or "bug" -in $labelNames) {
        $categories.fixes.Add($entry) | Out-Null
    }
    elseif ($title -match "^(refactor)" -or "refactoring" -in $labelNames) {
        $categories.refactoring.Add($entry) | Out-Null
    }
    else {
        $categories.other.Add($entry) | Out-Null
    }
}

$changelogLines = @()

if ($categories.features.Count -gt 0) {
    $changelogLines += "### Neue Features"
    $changelogLines += $categories.features
    $changelogLines += ""
}
if ($categories.fixes.Count -gt 0) {
    $changelogLines += "### Bugfixes"
    $changelogLines += $categories.fixes
    $changelogLines += ""
}
if ($categories.refactoring.Count -gt 0) {
    $changelogLines += "### Refactoring"
    $changelogLines += $categories.refactoring
    $changelogLines += ""
}
if ($categories.other.Count -gt 0) {
    $changelogLines += "### Sonstiges"
    $changelogLines += $categories.other
    $changelogLines += ""
}

$changelog = $changelogLines -join "`n"

# --- Ausgabe ---

Write-Host ""
Write-Host "--- Changelog ---" -ForegroundColor Cyan
Write-Host $changelog
Write-Host "--- Ende ---" -ForegroundColor Cyan

if ($OutputFile -ne "") {
    $changelog | Set-Content $OutputFile -Encoding UTF8
    Write-Ok "Gespeichert in: $OutputFile"
}

Write-JsonResult -Action "changelog" -Success $true -Data @{
    since      = $sinceArg
    pr_count   = $filteredPrs.Count
    commits    = $commitCount
    features   = $categories.features.Count
    fixes      = $categories.fixes.Count
    refactoring = $categories.refactoring.Count
    other      = $categories.other.Count
    notes      = $changelog
}
