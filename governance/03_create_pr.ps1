# ============================================================================
# ATLAS Governance - PR erstellen
# ============================================================================
# Erstellt einen Pull Request via GitHub CLI.
#
# Verwendung:
#   .\03_create_pr.ps1 -Base beta -Head dev -Title "DEV -> BETA Sync"
#   .\03_create_pr.ps1 -Base main -Head beta -Title "BETA -> MAIN Release"
#
# Gibt die PR-Nummer als Exit-Wert zurueck und speichert sie in .last_pr
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [string]$Base,

    [Parameter(Mandatory = $true)]
    [string]$Head,

    [string]$Title = "ATLAS: $Head -> $Base",

    [string]$Body = "Automatischer Governance Flow"
)

. "$PSScriptRoot\_lib.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS PR: $Head -> $Base" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Assert-GhInstalled

Write-Step "Pruefen ob bereits ein offener PR existiert..."

$existingPr = gh pr list --base $Base --head $Head --state open --json number,title 2>&1
if ($LASTEXITCODE -eq 0 -and $existingPr -ne "[]") {
    $prData = $existingPr | ConvertFrom-Json
    if ($prData.Count -gt 0) {
        $prNum = $prData[0].number
        Write-Warn "Es existiert bereits ein offener PR: #$prNum ($($prData[0].title))"
        Write-Info "PR-Nummer: $prNum"

        $prNum | Out-File -FilePath (Join-Path $PSScriptRoot ".last_pr") -NoNewline -Encoding UTF8
        Write-Host ""
        Write-Host "PR_NUMBER=$prNum"
        exit 0
    }
}

Write-Step "Pruefen ob Unterschiede zwischen $Head und $Base bestehen..."

Invoke-GitSilent fetch origin $Base $Head
$diffCount = git rev-list --count "origin/$Base..origin/$Head" 2>&1
if ($LASTEXITCODE -ne 0 -or [int]$diffCount -eq 0) {
    Write-Warn "$Head hat keine neuen Commits gegenueber $Base. Kein PR noetig."
    exit 0
}

Write-Info "$diffCount Commit(s) von $Head nicht in $Base"

Write-Step "Pull Request erstellen..."

$prUrl = gh pr create `
    --base $Base `
    --head $Head `
    --title $Title `
    --body $Body 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Err "PR-Erstellung fehlgeschlagen: $prUrl"
    exit 1
}

$prNumber = Get-PrNumber $prUrl
Write-Ok "PR erstellt: $prUrl"
Write-Info "PR-Nummer: $prNumber"

$prNumber | Out-File -FilePath (Join-Path $PSScriptRoot ".last_pr") -NoNewline -Encoding UTF8

Write-Host ""
Write-Host "PR_NUMBER=$prNumber"
