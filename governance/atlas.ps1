# ============================================================================
# ATLAS Governance - Zentraler Orchestrator
# ============================================================================
#
# Einheitlicher Entry-Point fuer alle Governance-Operationen.
# Kann von der Kommandozeile, aus Cursor oder aus CI/CD genutzt werden.
#
# Verwendung:
#   .\atlas.ps1 -Action health
#   .\atlas.ps1 -Action cleanup
#   .\atlas.ps1 -Action reset
#   .\atlas.ps1 -Action beta-flow -BumpType minor
#   .\atlas.ps1 -Action stable-flow
#   .\atlas.ps1 -Action full -SkipBuild
#   .\atlas.ps1 -Action health -Json
#   .\atlas.ps1 -Action status
#
# Aktionen:
#   verify-env    Umgebung pruefen (Tools, Git, etc.)
#   health        Systemzustand pruefen (Git, API, Branches, Releases)
#   status        Schnellstatus: Branch, Version, offene PRs, Divergenz
#   cleanup       Alle Feature-Branches loeschen
#   reset         beta + dev auf main zuruecksetzen
#   bump          Version erhoehen (patch/minor/major)
#   tag           Git-Tag erstellen (stable/beta)
#   pr            Pull Request erstellen (-Base, -Head)
#   wait-ci       CI-Checks abwarten (-PRNumber)
#   merge         PR mergen (-PRNumber)
#   build         Installer bauen
#   upload        Release hochladen + Gates + Aktivierung
#   deprecate     Alte Releases auf deprecated setzen
#   changelog     Release Notes aus PR-History generieren
#   rollback      Git- oder API-Rollback
#   beta-flow     Kompletter Beta-Release-Flow (dev -> beta)
#   stable-flow   Kompletter Stable-Release-Flow (beta -> main)
#   full          Kompletter Governance-Zyklus (Cleanup + Reset + Beta + Stable)
#
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(
        "verify-env", "health", "status",
        "cleanup", "reset",
        "bump", "tag",
        "pr", "wait-ci", "merge",
        "build", "upload", "deprecate",
        "changelog", "rollback",
        "beta-flow", "stable-flow", "full"
    )]
    [string]$Action,

    # Globale Flags
    [switch]$Json,
    [switch]$Force,
    [switch]$SkipBuild,

    # Auth (non-interaktiv, fuer Agents/CI)
    [string]$Token = "",

    # Version
    [ValidateSet("major", "minor", "patch")]
    [string]$BumpType = "patch",
    [string]$Version = "",

    # PR
    [string]$Base = "",
    [string]$Head = "",
    [string]$Title = "",
    [string]$PRNumber = "",

    # Release
    [ValidateSet("stable", "beta")]
    [string]$Channel = "stable",
    [string]$ReleaseNotes = "",

    # Tag
    [switch]$Push,

    # CI
    [int]$CheckInterval = 15,
    [int]$CheckTimeout = 600,

    # Rollback
    [string]$GitBranch = "",
    [string]$GitTarget = "",
    [ValidateSet("git", "api", "both")]
    [string]$RollbackMode = "git",
    [int]$WithdrawReleaseId = 0,

    # Changelog
    [string]$SinceTag = "",
    [string]$OutputFile = ""
)

. "$PSScriptRoot\_lib.ps1"

if ($Json) { Set-GovernanceMode -Json }

$readOnlyActions = @("verify-env", "health", "status", "changelog", "wait-ci")
$needsLock = $Action -notin $readOnlyActions

if ($needsLock) {
    Enter-GovernanceLock -Action $Action
}

try {

$startTime = Get-Date

if (-not $Json) {
    Write-Host ""
    Write-Host "  ATLAS Governance" -ForegroundColor Cyan -NoNewline
    Write-Host " | " -NoNewline
    Write-Host "$Action" -ForegroundColor White
    Write-Host ""
}

# =========================================================================
# Action-Dispatch
# =========================================================================

$exitCode = 0

switch ($Action) {

    # --- Diagnostik ---

    "verify-env" {
        $args = @{}
        if ($Json) { $args["Json"] = $true }
        & "$PSScriptRoot\12_verify_env.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "health" {
        $args = @{}
        if ($Json) { $args["Json"] = $true }
        if ($Token -ne "") { $args["Token"] = $Token }
        & "$PSScriptRoot\13_healthcheck.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "status" {
        $currentBranch = git branch --show-current 2>&1
        $version = Get-AtlasVersion
        Invoke-GitSilent fetch --all --prune

        $devAhead = git rev-list --count "origin/beta..origin/dev" 2>&1
        $betaAhead = git rev-list --count "origin/main..origin/beta" 2>&1

        $openPrs = (gh pr list --state open --json number 2>&1 | ConvertFrom-Json).Count

        $extraBranches = @(git branch -r 2>&1 |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -notmatch "HEAD" } |
            ForEach-Object { $_ -replace "^origin/", "" } |
            Where-Object { $_ -notin @("main", "beta", "dev") }).Count

        if ($Json) {
            @{
                action           = "status"
                branch           = $currentBranch.Trim()
                version          = $version
                dev_ahead_beta   = [int]$devAhead
                beta_ahead_main  = [int]$betaAhead
                open_prs         = $openPrs
                feature_branches = $extraBranches
            } | ConvertTo-Json
        }
        else {
            Write-Host "  Branch:           $($currentBranch.Trim())" -ForegroundColor White
            Write-Host "  Version:          $version" -ForegroundColor White
            Write-Host "  dev -> beta:      $devAhead Commit(s) voraus" -ForegroundColor $(if ([int]$devAhead -gt 0) { "Yellow" } else { "Green" })
            Write-Host "  beta -> main:     $betaAhead Commit(s) voraus" -ForegroundColor $(if ([int]$betaAhead -gt 0) { "Yellow" } else { "Green" })
            Write-Host "  Offene PRs:       $openPrs" -ForegroundColor $(if ($openPrs -gt 0) { "Yellow" } else { "Green" })
            Write-Host "  Feature-Branches: $extraBranches" -ForegroundColor $(if ($extraBranches -gt 0) { "Yellow" } else { "Green" })
        }
    }

    # --- Einzelaktionen ---

    "cleanup" {
        $args = @{}
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\01_cleanup_branches.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "reset" {
        $args = @{}
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\02_reset_branches.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "bump" {
        $args = @{ Action = "bump"; Type = $BumpType }
        if ($Version -ne "") { $args = @{ Action = "set"; Version = $Version } }
        & "$PSScriptRoot\09_version_bump.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "tag" {
        $args = @{ Channel = $Channel }
        if ($Push) { $args["Push"] = $true }
        & "$PSScriptRoot\10_git_tag.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "pr" {
        if ($Base -eq "" -or $Head -eq "") {
            Write-Err "PR benoetigt -Base und -Head Parameter"
            Write-Info "Beispiel: .\atlas.ps1 -Action pr -Base beta -Head dev"
            exit 1
        }
        $args = @{ Base = $Base; Head = $Head }
        if ($Title -ne "") { $args["Title"] = $Title }
        & "$PSScriptRoot\03_create_pr.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "wait-ci" {
        $args = @{ Interval = $CheckInterval; Timeout = $CheckTimeout }
        if ($PRNumber -ne "") { $args["PRNumber"] = $PRNumber }
        & "$PSScriptRoot\04_wait_for_checks.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "merge" {
        $args = @{}
        if ($PRNumber -ne "") { $args["PRNumber"] = $PRNumber }
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\05_merge_pr.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "build" {
        $args = @{}
        if ($Version -ne "") { $args["Version"] = $Version }
        & "$PSScriptRoot\06_build_installer.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "upload" {
        $authToken = $Token
        if ($authToken -eq "") {
            Write-Info "Login erforderlich fuer Upload..."
            $authToken = Invoke-AtlasLogin
        }

        $args = @{ Token = $authToken; Channel = $Channel }
        if ($ReleaseNotes -ne "") { $args["ReleaseNotes"] = $ReleaseNotes }
        if ($Channel -eq "stable") { $args["Mandatory"] = $true }
        & "$PSScriptRoot\07_upload_release.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "deprecate" {
        $authToken = $Token
        if ($authToken -eq "") {
            Write-Info "Login erforderlich fuer Deprecate..."
            $authToken = Invoke-AtlasLogin
        }

        $args = @{ Token = $authToken }
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\08_deprecate_releases.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "changelog" {
        $args = @{}
        if ($SinceTag -ne "") { $args["SinceTag"] = $SinceTag }
        if ($OutputFile -ne "") { $args["OutputFile"] = $OutputFile }
        if ($Json) { $args["Json"] = $true }
        & "$PSScriptRoot\14_changelog_from_pr.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "rollback" {
        $args = @{ Mode = $RollbackMode }
        if ($GitBranch -ne "") { $args["GitBranch"] = $GitBranch }
        if ($GitTarget -ne "") { $args["GitTarget"] = $GitTarget }
        if ($WithdrawReleaseId -gt 0) { $args["WithdrawReleaseId"] = $WithdrawReleaseId }
        if ($Token -ne "") { $args["Token"] = $Token }
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\11_rollback.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    # --- Flows ---

    "beta-flow" {
        $args = @{
            BumpType      = $BumpType
            CheckInterval = $CheckInterval
            CheckTimeout  = $CheckTimeout
        }
        if ($ReleaseNotes -ne "") { $args["ReleaseNotes"] = $ReleaseNotes }
        if ($SkipBuild) { $args["SkipBuild"] = $true }
        if ($Token -ne "") { $args["Token"] = $Token }
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\flow_beta_release.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "stable-flow" {
        $args = @{
            CheckInterval = $CheckInterval
            CheckTimeout  = $CheckTimeout
        }
        if ($ReleaseNotes -ne "") { $args["ReleaseNotes"] = $ReleaseNotes }
        if ($SkipBuild) { $args["SkipBuild"] = $true }
        if ($Token -ne "") { $args["Token"] = $Token }
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\flow_stable_release.ps1" @args
        $exitCode = $LASTEXITCODE
    }

    "full" {
        $args = @{
            BumpType      = $BumpType
            CheckInterval = $CheckInterval
            CheckTimeout  = $CheckTimeout
        }
        if ($ReleaseNotes -ne "") { $args["ReleaseNotes"] = $ReleaseNotes }
        if ($SkipBuild) { $args["SkipBuild"] = $true }
        if ($Token -ne "") { $args["Token"] = $Token }
        if ($Force) { $args["Force"] = $true }
        & "$PSScriptRoot\flow_full_governance.ps1" @args
        $exitCode = $LASTEXITCODE
    }
}

# =========================================================================
# State speichern + Abschluss
# =========================================================================

$duration = (Get-Date) - $startTime

Save-GovernanceState @{
    last_action  = $Action
    exit_code    = $exitCode
    duration_sec = [math]::Round($duration.TotalSeconds, 1)
    version      = (Get-AtlasVersion)
}

if (-not $Json) {
    Write-Host ""
    Write-Host "  Dauer: $([math]::Round($duration.TotalSeconds, 1))s" -ForegroundColor Gray
    Write-Host ""
}

exit $exitCode

} finally {
    if ($needsLock) { Exit-GovernanceLock }
}
