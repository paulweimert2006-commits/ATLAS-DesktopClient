# ============================================================================
# ATLAS Governance - Idempotente Versionierung
# ============================================================================
# Liest die VERSION-Datei und erhoeht sie (bump) oder setzt sie (set).
# Idempotent: Schreibt nur bei tatsaechlicher Aenderung.
#
# Verwendung:
#   .\09_version_bump.ps1 -Action bump -Type patch        # 2.2.6 -> 2.2.7
#   .\09_version_bump.ps1 -Action bump -Type minor        # 2.2.6 -> 2.3.0
#   .\09_version_bump.ps1 -Action bump -Type major        # 2.2.6 -> 3.0.0
#   .\09_version_bump.ps1 -Action set -Version "3.0.0"    # -> 3.0.0
#   .\09_version_bump.ps1 -Action bump -Type patch -Commit -Push
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("bump", "set")]
    [string]$Action,

    [ValidateSet("major", "minor", "patch")]
    [string]$Type = "patch",

    [string]$Version = "",

    [switch]$Commit,
    [switch]$Push,
    [string]$Branch = ""
)

. "$PSScriptRoot\_lib.ps1"

$projectRoot = Get-ProjectRoot
$versionFile = Join-Path $projectRoot "VERSION"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Version Bump" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Aktuelle Version lesen ---

Write-Step "Aktuelle Version lesen..."

if (-not (Test-Path $versionFile)) {
    Write-Err "VERSION-Datei nicht gefunden: $versionFile"
    exit 1
}

$currentVersion = (Get-Content $versionFile -Raw).Trim()

if ($currentVersion -notmatch '^(\d+)\.(\d+)\.(\d+)$') {
    Write-Err "Ungueltige Version in VERSION-Datei: $currentVersion (erwartet: X.Y.Z)"
    exit 1
}

$major = [int]$Matches[1]
$minor = [int]$Matches[2]
$patch = [int]$Matches[3]

Write-Ok "Aktuelle Version: $currentVersion"

# --- Neue Version berechnen ---

Write-Step "Neue Version berechnen..."

$newVersion = ""

if ($Action -eq "bump") {
    switch ($Type) {
        "major" { $major++; $minor = 0; $patch = 0 }
        "minor" { $minor++; $patch = 0 }
        "patch" { $patch++ }
    }
    $newVersion = "$major.$minor.$patch"
    Write-Info "Bump: $currentVersion -> $newVersion ($Type)"
}
elseif ($Action -eq "set") {
    if ($Version -eq "") {
        Write-Err "-Version ist erforderlich fuer Action 'set'"
        exit 1
    }
    if ($Version -notmatch '^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$') {
        Write-Err "Ungueltige Version: $Version (erwartet: X.Y.Z oder X.Y.Z-suffix)"
        exit 1
    }
    $newVersion = $Version
    Write-Info "Set: $currentVersion -> $newVersion"
}

# --- Idempotenz-Check ---

if ($newVersion -eq $currentVersion) {
    Write-Ok "Version ist bereits $currentVersion (idempotent, keine Aenderung)"
    exit 0
}

# --- Schreiben ---

Write-Step "VERSION-Datei aktualisieren..."

[System.IO.File]::WriteAllText($versionFile, $newVersion, (New-Object System.Text.UTF8Encoding $false))
Write-Ok "VERSION: $currentVersion -> $newVersion"

# --- Optional: Commit ---

if ($Commit.IsPresent) {
    Write-Step "Version-Aenderung committen..."

    git add $versionFile 2>&1 | Out-Null
    $commitMsg = "chore(version): bump to $newVersion"
    git commit -m $commitMsg 2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Kein Commit erstellt (evtl. keine Aenderungen?)"
    }
    else {
        Write-Ok "Commit erstellt: $commitMsg"
    }

    if ($Push.IsPresent) {
        if ($Branch -eq "") {
            $Branch = Get-CurrentBranch
        }
        Write-Info "Pushe auf $Branch ..."
        git push origin $Branch 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Push fehlgeschlagen"
            exit 1
        }
        Write-Ok "Gepusht auf $Branch"
    }
}

Write-Host ""
Write-Host "VERSION=$newVersion"
