# ============================================================================
# ATLAS Governance - Release Upload + Gate-Validierung + Aktivierung
# ============================================================================
# Laedt einen Installer auf den Server, fuehrt die 7-Gate-Validierung aus
# und aktiviert das Release (optional als mandatory).
#
# Verwendung:
#   .\07_upload_release.ps1 -Token $token -Channel beta
#   .\07_upload_release.ps1 -Token $token -Channel stable -Mandatory
#   .\07_upload_release.ps1 -Token $token -Channel beta -InstallerPath "...\setup.exe" -Version "2.3.0-beta.1"
#
# Ohne -InstallerPath / -Version wird .last_build gelesen (von 06_build_installer.ps1).
#
# Flow:
#   1. Upload (POST /admin/releases)       -> Status: pending
#   2. Validieren (POST /validate)          -> Status: validated / blocked
#   3. Aktivieren (PUT status=active)       -> Status: active
#   4. Optional: Mandatory (PUT mandatory)  -> Status: mandatory
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [string]$Token,

    [ValidateSet("stable", "beta")]
    [string]$Channel = "stable",

    [string]$InstallerPath = "",
    [string]$Version = "",
    [string]$ReleaseNotes = "",

    [switch]$Mandatory,

    [int]$GateRetries = 3,
    [int]$GateRetryDelay = 10
)

. "$PSScriptRoot\_lib.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Release Upload ($Channel)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Build-Info laden ---

if ($InstallerPath -eq "" -or $Version -eq "") {
    $buildInfoFile = Join-Path $PSScriptRoot ".last_build"
    if (-not (Test-Path $buildInfoFile)) {
        Write-Err "Kein -InstallerPath/-Version angegeben und .last_build nicht gefunden."
        Write-Info "Fuehre zuerst 06_build_installer.ps1 aus."
        exit 1
    }

    $buildInfo = Get-Content $buildInfoFile -Raw | ConvertFrom-Json

    if ($InstallerPath -eq "") { $InstallerPath = $buildInfo.installer }
    if ($Version -eq "") { $Version = $buildInfo.version }
}

if (-not (Test-Path $InstallerPath)) {
    Write-Err "Installer-Datei nicht gefunden: $InstallerPath"
    exit 1
}

$fileSizeMB = [math]::Round((Get-Item $InstallerPath).Length / 1MB, 2)

Write-Info "Version:    $Version"
Write-Info "Channel:    $Channel"
Write-Info "Installer:  $InstallerPath ($fileSizeMB MB)"
Write-Info "Mandatory:  $($Mandatory.IsPresent)"

# --- 1. Upload ---

Write-Step "Installer hochladen..."

$formFields = @{
    version       = $Version
    channel       = $Channel
    release_notes = $ReleaseNotes
}

Write-Info "Upload laeuft... (kann bei grossen Dateien mehrere Minuten dauern)"

$uploadResult = Invoke-AtlasUpload `
    -Endpoint "/admin/releases" `
    -Token $Token `
    -FormFields $formFields `
    -FilePath $InstallerPath

if (-not $uploadResult -or -not $uploadResult.success) {
    Write-Err "Upload fehlgeschlagen"
    if ($uploadResult.message) { Write-Info "Server: $($uploadResult.message)" }
    exit 1
}

$releaseId = $uploadResult.data.id
Write-Ok "Upload erfolgreich (Release ID: $releaseId, Status: pending)"

# --- 2. Gate-Validierung ---

Write-Step "Gate-Validierung starten (7 Gates)..."

$gatesPassed = $false
for ($attempt = 1; $attempt -le $GateRetries; $attempt++) {

    Write-Info "Validierungsversuch $attempt/$GateRetries ..."

    $validateResult = Invoke-AtlasApi `
        -Endpoint "/admin/releases/$releaseId/validate" `
        -Method POST `
        -Token $Token

    if (-not $validateResult) {
        Write-Warn "Validierungs-API nicht erreichbar"
        if ($attempt -lt $GateRetries) {
            Write-Info "Warte ${GateRetryDelay}s vor erneutem Versuch..."
            Start-Sleep -Seconds $GateRetryDelay
            continue
        }
        Write-Err "Validierung nach $GateRetries Versuchen fehlgeschlagen"
        exit 1
    }

    if ($validateResult.data.status -eq "validated") {
        $gatesPassed = $true
        Write-Ok "Alle Gates bestanden!"

        if ($validateResult.data.gate_report) {
            $report = $validateResult.data.gate_report
            if ($report -is [string]) { $report = $report | ConvertFrom-Json }
            Write-Info "Gate-Report:"
            foreach ($gate in $report.gates.PSObject.Properties) {
                $status = $gate.Value.status
                $color = if ($status -eq "passed") { "Green" } elseif ($status -eq "skipped") { "Gray" } else { "Red" }
                Write-Host "    [$status] $($gate.Name)" -ForegroundColor $color
            }
            Save-GateReport -Report $report -Version $Version -Channel $Channel -Passed $true
        }
        break
    }
    elseif ($validateResult.data.status -eq "blocked") {
        Write-Warn "Gates nicht bestanden (Status: blocked)"

        if ($validateResult.data.gate_report) {
            $report = $validateResult.data.gate_report
            if ($report -is [string]) { $report = $report | ConvertFrom-Json }
            Write-Info "Gate-Report:"
            foreach ($gate in $report.gates.PSObject.Properties) {
                $status = $gate.Value.status
                $color = if ($status -eq "passed") { "Green" } elseif ($status -eq "skipped") { "Gray" } else { "Red" }
                Write-Host "    [$status] $($gate.Name): $($gate.Value.details)" -ForegroundColor $color
            }
            Save-GateReport -Report $report -Version $Version -Channel $Channel -Passed $false
        }

        if ($attempt -lt $GateRetries) {
            Write-Info "Warte ${GateRetryDelay}s vor erneutem Versuch..."
            Start-Sleep -Seconds $GateRetryDelay
        }
    }
}

if (-not $gatesPassed) {
    Write-Err "Gate-Validierung fehlgeschlagen. Release bleibt im Status 'blocked'."
    Write-Info "Release ID: $releaseId -- kann manuell im Admin-Bereich geprueft werden."
    exit 1
}

# --- 3. Aktivieren ---

Write-Step "Release aktivieren..."

$activateResult = Invoke-AtlasApi `
    -Endpoint "/admin/releases/$releaseId" `
    -Method PUT `
    -Token $Token `
    -Body @{ status = "active" }

if (-not $activateResult -or -not $activateResult.success) {
    Write-Err "Aktivierung fehlgeschlagen"
    if ($activateResult.message) { Write-Info "Server: $($activateResult.message)" }
    exit 1
}
Write-Ok "Release aktiviert (Status: active)"

# --- 4. Optional: Mandatory ---

if ($Mandatory.IsPresent) {
    Write-Step "Release als MANDATORY markieren..."

    $mandatoryResult = Invoke-AtlasApi `
        -Endpoint "/admin/releases/$releaseId" `
        -Method PUT `
        -Token $Token `
        -Body @{ status = "mandatory" }

    if (-not $mandatoryResult -or -not $mandatoryResult.success) {
        Write-Err "Mandatory-Markierung fehlgeschlagen"
        if ($mandatoryResult.message) { Write-Info "Server: $($mandatoryResult.message)" }
        exit 1
    }
    Write-Ok "Release ist MANDATORY -- alle Clients muessen updaten"
}

# --- Ergebnis ---

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Release Upload abgeschlossen" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Release ID: $releaseId" -ForegroundColor White
Write-Host "  Version:    $Version" -ForegroundColor White
Write-Host "  Channel:    $Channel" -ForegroundColor White
Write-Host "  Status:     $(if ($Mandatory.IsPresent) { 'mandatory' } else { 'active' })" -ForegroundColor White
Write-Host ""

# Release-ID fuer nachfolgende Skripte speichern
$releaseId | Out-File -FilePath (Join-Path $PSScriptRoot ".last_release_id") -NoNewline -Encoding UTF8
