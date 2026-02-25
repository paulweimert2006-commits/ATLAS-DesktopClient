# ============================================================================
# ATLAS Governance - Rollback (Git + API)
# ============================================================================
# Zwei Modi:
#   1. Git-Rollback:  Branch auf einen Tag/Commit zuruecksetzen (Force-Push)
#   2. API-Rollback:  Release zurueckziehen (nutzt Withdraw mit Auto-Fallback)
#
# Verwendung:
#   .\11_rollback.ps1 -Mode git -GitBranch main -GitTarget v2.2.5
#   .\11_rollback.ps1 -Mode git -GitBranch beta -GitTarget abc1234
#   .\11_rollback.ps1 -Mode api -WithdrawReleaseId 42 -Token $token
#   .\11_rollback.ps1 -Mode both -GitBranch main -GitTarget v2.2.5 -WithdrawReleaseId 42 -Token $token
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("git", "api", "both")]
    [string]$Mode,

    [string]$GitBranch = "",
    [string]$GitTarget = "",

    [int]$WithdrawReleaseId = 0,
    [string]$Token = ""
)

. "$PSScriptRoot\_lib.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Red
Write-Host " ATLAS ROLLBACK ($Mode)" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red

# =========================================================================
# GIT-ROLLBACK
# =========================================================================

if ($Mode -in @("git", "both")) {
    if ($GitBranch -eq "" -or $GitTarget -eq "") {
        Write-Err "-GitBranch und -GitTarget sind erforderlich fuer Git-Rollback"
        Write-Info "Beispiel: .\11_rollback.ps1 -Mode git -GitBranch main -GitTarget v2.2.5"
        exit 1
    }

    Write-Step "Git-Rollback vorbereiten..."

    Write-Host ""
    Write-Host "  ACHTUNG: DESTRUKTIVE OPERATION" -ForegroundColor Red
    Write-Host "  Branch '$GitBranch' wird per FORCE PUSH auf '$GitTarget' zurueckgesetzt." -ForegroundColor Red
    Write-Host "  Alle nachfolgenden Commits gehen UNWIDERRUFLICH verloren!" -ForegroundColor Red
    Write-Host ""

    Write-Step "Aktuelle Situation..."
    git fetch --all --tags 2>&1 | Out-Null

    $currentHead = git log "origin/$GitBranch" -1 --oneline 2>&1
    Write-Info "Aktuell ($GitBranch): $currentHead"

    $targetInfo = git log $GitTarget -1 --oneline 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Ziel '$GitTarget' nicht gefunden (kein gültiger Tag/Commit)"
        exit 1
    }
    Write-Info "Ziel ($GitTarget):    $targetInfo"

    $commitsBetween = git rev-list --count "$GitTarget..origin/$GitBranch" 2>&1
    Write-Warn "$commitsBetween Commit(s) werden zurueckgesetzt"

    $proceed = Confirm-Action "Git-Rollback durchfuehren? Tippe 'ROLLBACK':" -RequiredInput "ROLLBACK"
    if (-not $proceed) { exit 0 }

    Write-Step "Git-Rollback ausfuehren..."

    git checkout $GitBranch 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Konnte nicht auf $GitBranch wechseln"
        exit 1
    }

    git reset --hard $GitTarget 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Reset auf $GitTarget fehlgeschlagen"
        exit 1
    }

    git push -f origin $GitBranch 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Force-Push auf $GitBranch fehlgeschlagen"
        exit 1
    }

    Write-Ok "Git-Rollback abgeschlossen: $GitBranch -> $GitTarget"
}

# =========================================================================
# API-ROLLBACK (Withdraw mit Auto-Fallback)
# =========================================================================

if ($Mode -in @("api", "both")) {
    if ($WithdrawReleaseId -eq 0) {
        Write-Err "-WithdrawReleaseId ist erforderlich fuer API-Rollback"
        exit 1
    }
    if ($Token -eq "") {
        Write-Warn "Kein Token angegeben. Interaktiver Login..."
        $Token = Invoke-AtlasLogin
    }

    Write-Step "API-Rollback vorbereiten..."

    $release = Invoke-AtlasApi `
        -Endpoint "/admin/releases/$WithdrawReleaseId" `
        -Method GET `
        -Token $Token

    if (-not $release) {
        Write-Err "Release $WithdrawReleaseId nicht gefunden"
        exit 1
    }

    $releaseData = if ($release.data) { $release.data } else { $release }
    Write-Info "Release: v$($releaseData.version) ($($releaseData.channel), Status: $($releaseData.status))"

    if ($releaseData.status -in @("withdrawn", "deprecated")) {
        Write-Warn "Release ist bereits $($releaseData.status). Nichts zu tun."
        exit 0
    }

    Write-Host ""
    Write-Host "  Das Release wird zurueckgezogen (withdrawn)." -ForegroundColor Yellow
    Write-Host "  Falls ein aelteres Release im selben Channel existiert," -ForegroundColor Yellow
    Write-Host "  wird es automatisch reaktiviert (Auto-Fallback)." -ForegroundColor Yellow
    Write-Host ""

    $proceed = Confirm-Action "Release $WithdrawReleaseId zurueckziehen?"
    if (-not $proceed) { exit 0 }

    Write-Step "Release zurueckziehen..."

    $withdrawResult = Invoke-AtlasApi `
        -Endpoint "/admin/releases/$WithdrawReleaseId/withdraw" `
        -Method POST `
        -Token $Token

    if (-not $withdrawResult -or -not $withdrawResult.success) {
        Write-Err "Withdraw fehlgeschlagen"
        if ($withdrawResult.message) { Write-Info "Server: $($withdrawResult.message)" }
        exit 1
    }

    Write-Ok "Release $WithdrawReleaseId zurueckgezogen"

    if ($withdrawResult.data.fallback_release_id) {
        Write-Ok "Auto-Fallback: Release $($withdrawResult.data.fallback_release_id) reaktiviert"
    }
    else {
        Write-Warn "Kein Fallback-Release gefunden. Kein aktives Release im Channel!"
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Rollback abgeschlossen" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
