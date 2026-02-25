# ============================================================================
# ATLAS Governance - Automatisches Git-Tagging
# ============================================================================
# Erstellt Git-Tags basierend auf der VERSION-Datei.
# Idempotent: Erstellt Tag nur, wenn er nicht existiert.
#
# Konvention:
#   stable: vX.Y.Z           (z.B. v2.2.6)
#   beta:   vX.Y.Z-beta.N    (z.B. v2.2.6-beta.1, automatisch hochgezaehlt)
#
# Verwendung:
#   .\10_git_tag.ps1 -Channel stable
#   .\10_git_tag.ps1 -Channel beta
#   .\10_git_tag.ps1 -Channel stable -Push
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("stable", "beta")]
    [string]$Channel,

    [switch]$Push
)

. "$PSScriptRoot\_lib.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Git Tag ($Channel)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Step "Version lesen..."

$baseVersion = Get-AtlasVersion
Write-Ok "Basis-Version: $baseVersion"

# --- Tag-Name bestimmen ---

Write-Step "Tag-Name bestimmen..."

$tagName = ""

if ($Channel -eq "stable") {
    $tagName = "v$baseVersion"
}
elseif ($Channel -eq "beta") {
    $prefix = "v$baseVersion-beta."

    git fetch --tags 2>&1 | Out-Null

    $existingTags = git tag --list "$prefix*" 2>&1
    $highestN = 0

    if ($existingTags) {
        foreach ($t in $existingTags) {
            $t = $t.Trim()
            if ($t -match "-beta\.(\d+)$") {
                $n = [int]$Matches[1]
                if ($n -gt $highestN) { $highestN = $n }
            }
        }
    }

    $nextN = $highestN + 1
    $tagName = "${prefix}${nextN}"
}

Write-Ok "Tag: $tagName"

# --- Idempotenz-Check (nur fuer stable) ---

if ($Channel -eq "stable") {
    $existsLocal = git tag --list $tagName 2>&1
    if ($existsLocal.Trim() -eq $tagName) {
        Write-Ok "Tag '$tagName' existiert bereits (idempotent)"

        if ($Push.IsPresent) {
            Write-Info "Pushe existierenden Tag..."
            git push origin $tagName 2>&1 | Out-Null
            Write-Ok "Tag gepusht"
        }
        exit 0
    }
}

# --- Tag erstellen ---

Write-Step "Tag erstellen..."

git tag -a $tagName -m "ATLAS release $tagName" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Tag-Erstellung fehlgeschlagen"
    exit 1
}
Write-Ok "Tag erstellt: $tagName"

# --- Optional: Push ---

if ($Push.IsPresent) {
    Write-Step "Tag auf Remote pushen..."
    git push origin $tagName 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Tag-Push fehlgeschlagen"
        exit 1
    }
    Write-Ok "Tag gepusht: $tagName"
}

Write-Host ""
Write-Host "TAG=$tagName"
