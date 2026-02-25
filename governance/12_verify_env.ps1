# ============================================================================
# ATLAS Governance - Umgebung verifizieren
# ============================================================================
# Prueft ob alle erforderlichen Tools installiert und erreichbar sind.
#
# Verwendung:
#   .\12_verify_env.ps1
#   .\12_verify_env.ps1 -IncludeBuildTools   # Auch Inno Setup + PyInstaller
#
# Exit-Codes:
#   0 = Alles OK
#   1 = Mindestens ein Tool fehlt
# ============================================================================

param(
    [switch]$IncludeBuildTools,
    [switch]$Json
)

. "$PSScriptRoot\_lib.ps1"

if ($Json) { Set-GovernanceMode -Json }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Umgebungs-Pruefung" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$allOk = $true
$results = @{}

# --- Pflicht-Tools ---

$requiredTools = @(
    @{ Name = "git";    Cmd = "git --version";    Desc = "Git" }
    @{ Name = "gh";     Cmd = "gh --version";     Desc = "GitHub CLI" }
    @{ Name = "python"; Cmd = "python --version";  Desc = "Python" }
)

Write-Step "Pflicht-Tools pruefen..."

foreach ($tool in $requiredTools) {
    $found = Get-Command $tool.Name -ErrorAction SilentlyContinue
    if ($found) {
        $versionOutput = & $tool.Name --version 2>&1 | Select-Object -First 1
        Write-Ok "$($tool.Desc): $versionOutput"
        $results[$tool.Name] = @{ status = "ok"; version = "$versionOutput" }
    }
    else {
        Write-Err "$($tool.Desc) ($($tool.Name)) nicht gefunden!"
        $results[$tool.Name] = @{ status = "missing" }
        $allOk = $false
    }
}

# --- Git-Repository ---

Write-Step "Git-Repository pruefen..."

$gitRoot = git rev-parse --show-toplevel 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Ok "Git-Repository: $gitRoot"
    $results["git_repo"] = @{ status = "ok"; path = "$gitRoot" }

    $remoteUrl = git remote get-url origin 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Remote origin: $remoteUrl"
        $results["git_remote"] = @{ status = "ok"; url = "$remoteUrl" }
    }
    else {
        Write-Err "Kein Remote 'origin' konfiguriert"
        $results["git_remote"] = @{ status = "missing" }
        $allOk = $false
    }
}
else {
    Write-Err "Nicht in einem Git-Repository!"
    $results["git_repo"] = @{ status = "missing" }
    $allOk = $false
}

# --- GitHub CLI Auth ---

Write-Step "GitHub CLI Authentifizierung pruefen..."

$ghAuth = gh auth status 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Ok "GitHub CLI authentifiziert"
    $results["gh_auth"] = @{ status = "ok" }
}
else {
    Write-Err "GitHub CLI nicht authentifiziert! Fuehre 'gh auth login' aus."
    $results["gh_auth"] = @{ status = "missing" }
    $allOk = $false
}

# --- VERSION-Datei ---

Write-Step "VERSION-Datei pruefen..."

$projectRoot = if ($gitRoot -and $LASTEXITCODE -eq 0) { $gitRoot.Trim() } else { $PSScriptRoot | Split-Path }
$versionFile = Join-Path $projectRoot "VERSION"
if (Test-Path $versionFile) {
    $ver = (Get-Content $versionFile -Raw).Trim()
    if ($ver -match '^\d+\.\d+\.\d+') {
        Write-Ok "VERSION: $ver"
        $results["version"] = @{ status = "ok"; value = $ver }
    }
    else {
        Write-Err "VERSION-Datei hat ungueltiges Format: $ver"
        $results["version"] = @{ status = "invalid"; value = $ver }
        $allOk = $false
    }
}
else {
    Write-Err "VERSION-Datei nicht gefunden: $versionFile"
    $results["version"] = @{ status = "missing" }
    $allOk = $false
}

# --- Optionale Build-Tools ---

if ($IncludeBuildTools) {
    Write-Step "Build-Tools pruefen..."

    $pyInstallerCheck = pip show pyinstaller 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "PyInstaller installiert"
        $results["pyinstaller"] = @{ status = "ok" }
    }
    else {
        Write-Warn "PyInstaller nicht installiert (wird bei Build automatisch installiert)"
        $results["pyinstaller"] = @{ status = "missing" }
    }

    $innoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path $innoPath) {
        Write-Ok "Inno Setup 6 gefunden"
        $results["inno_setup"] = @{ status = "ok"; path = $innoPath }
    }
    else {
        Write-Err "Inno Setup 6 nicht gefunden: $innoPath"
        $results["inno_setup"] = @{ status = "missing" }
        $allOk = $false
    }
}

# --- Ergebnis ---

Write-Host ""
if ($allOk) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Umgebung OK - alle Voraussetzungen erfuellt" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host " Umgebung NICHT vollstaendig!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

Write-JsonResult -Action "verify-env" -Success $allOk -Data $results

if (-not $allOk) { exit 1 }
