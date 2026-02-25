# ============================================================================
# ATLAS Governance - Build Installer
# ============================================================================
# Baut die ATLAS-App (PyInstaller + Inno Setup) und erzeugt SHA256-Hash.
# Extrahiert aus release.ps1 -- kann eigenstaendig oder vom Orchestrator genutzt werden.
#
# Verwendung:
#   .\06_build_installer.ps1                    # Version aus VERSION-Datei
#   .\06_build_installer.ps1 -Version "2.3.0"  # Explizite Version
#
# Output:
#   Installer:  Output\ACENCIA-ATLAS-Setup-<VERSION>.exe
#   SHA256:     Output\ACENCIA-ATLAS-Setup-<VERSION>.sha256
# ============================================================================

param(
    [string]$Version = ""
)

. "$PSScriptRoot\_lib.ps1"

$projectRoot = Get-ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Build Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Version ermitteln ---

Write-Step "Version ermitteln..."

if ($Version -eq "") {
    $Version = Get-AtlasVersion
}

if ($Version -notmatch '^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$') {
    Write-Err "Ungueltige Version: $Version (erwartet: X.Y.Z oder X.Y.Z-suffix)"
    exit 1
}

Write-Ok "Version: $Version"

# --- Version in Komponentenform ---

$Version -match '^(\d+)\.(\d+)\.(\d+)' | Out-Null
$vMajor = $Matches[1]
$vMinor = $Matches[2]
$vPatch = $Matches[3]

# --- Build-Dateien aktualisieren ---

Write-Step "Build-Dateien aktualisieren..."

$versionInfoPath = Join-Path $projectRoot "version_info.txt"
if (Test-Path $versionInfoPath) {
    $content = Get-Content $versionInfoPath -Raw
    $content = $content -replace 'filevers=\([\d, ]+\)', "filevers=($vMajor, $vMinor, $vPatch, 0)"
    $content = $content -replace 'prodvers=\([\d, ]+\)', "prodvers=($vMajor, $vMinor, $vPatch, 0)"
    $content = $content -replace "FileVersion', u'[\d.]+'"  , "FileVersion', u'$Version.0'"
    $content = $content -replace "ProductVersion', u'[\d.]+'"  , "ProductVersion', u'$Version.0'"
    Set-Content $versionInfoPath $content -NoNewline
    Write-Ok "version_info.txt auf $Version aktualisiert"
}

$issPath = Join-Path $projectRoot "installer.iss"
if (Test-Path $issPath) {
    $content = Get-Content $issPath -Raw
    $content = $content -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$Version`""
    Set-Content $issPath $content -NoNewline
    Write-Ok "installer.iss auf $Version aktualisiert"
}

# --- Alte Builds aufraeumen ---

Write-Step "Alte Build-Verzeichnisse bereinigen..."

$buildDir = Join-Path $projectRoot "build"
$distDir = Join-Path $projectRoot "dist"
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
if (Test-Path $distDir) { Remove-Item $distDir -Recurse -Force }
Write-Ok "Bereinigt"

# --- PyInstaller ---

Write-Step "PyInstaller Build starten..."

$pyInstallerCheck = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Info "PyInstaller nicht gefunden, installiere..."
    pip install pyinstaller
}

$specFile = Join-Path $projectRoot "build_config.spec"
if (-not (Test-Path $specFile)) {
    Write-Err "build_config.spec nicht gefunden: $specFile"
    exit 1
}

Write-Info "PyInstaller laeuft... (kann einige Minuten dauern)"
$buildProcess = Start-Process -FilePath "python" `
    -ArgumentList "-m PyInstaller `"$specFile`" --clean --noconfirm" `
    -WorkingDirectory $projectRoot `
    -NoNewWindow -Wait -PassThru

if ($buildProcess.ExitCode -ne 0) {
    Write-Err "PyInstaller Build fehlgeschlagen! (Exit-Code: $($buildProcess.ExitCode))"
    exit 1
}

$exePath = Join-Path $projectRoot "dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe"
if (-not (Test-Path $exePath)) {
    Write-Err "Build-Ergebnis nicht gefunden: $exePath"
    exit 1
}
Write-Ok "PyInstaller Build erfolgreich"

# --- Inno Setup Installer ---

Write-Step "Installer mit Inno Setup erstellen..."

$innoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $innoPath)) {
    Write-Err "Inno Setup 6 nicht gefunden unter: $innoPath"
    Write-Info "Installation: https://jrsoftware.org/isdl.php"
    exit 1
}

$outputDir = Join-Path $projectRoot "Output"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$innoProcess = Start-Process -FilePath $innoPath `
    -ArgumentList "`"$issPath`"" `
    -WorkingDirectory $projectRoot `
    -NoNewWindow -Wait -PassThru

if ($innoProcess.ExitCode -ne 0) {
    Write-Err "Inno Setup fehlgeschlagen! (Exit-Code: $($innoProcess.ExitCode))"
    exit 1
}

$setupGeneric = Join-Path $outputDir "ACENCIA-ATLAS-Setup.exe"
$setupVersioned = Join-Path $outputDir "ACENCIA-ATLAS-Setup-$Version.exe"

if (Test-Path $setupGeneric) {
    if (Test-Path $setupVersioned) { Remove-Item $setupVersioned -Force }
    Move-Item $setupGeneric $setupVersioned
    Write-Ok "Installer: ACENCIA-ATLAS-Setup-$Version.exe"
}
else {
    Write-Err "Installer-Datei nicht gefunden: $setupGeneric"
    exit 1
}

# --- SHA256-Hash ---

Write-Step "SHA256-Hash berechnen..."

$sha256 = (Get-FileHash $setupVersioned -Algorithm SHA256).Hash.ToLower()
$sha256File = Join-Path $outputDir "ACENCIA-ATLAS-Setup-$Version.sha256"
Set-Content $sha256File $sha256 -NoNewline -Encoding UTF8

$fileSize = (Get-Item $setupVersioned).Length
$fileSizeMB = [math]::Round($fileSize / 1MB, 2)

Write-Ok "SHA256: $sha256"
Write-Info "Dateigroesse: $fileSizeMB MB"

# --- Ergebnis ---

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Build abgeschlossen" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Version:    $Version" -ForegroundColor White
Write-Host "  Installer:  $setupVersioned" -ForegroundColor White
Write-Host "  SHA256:     $sha256" -ForegroundColor White
Write-Host "  Groesse:    $fileSizeMB MB" -ForegroundColor White
Write-Host ""

# Pfade fuer nachfolgende Skripte in Datei schreiben
$buildInfo = @{
    version       = $Version
    installer     = $setupVersioned
    sha256        = $sha256
    file_size     = $fileSize
    file_size_mb  = $fileSizeMB
}
$buildInfo | ConvertTo-Json | Out-File -FilePath (Join-Path $PSScriptRoot ".last_build") -Encoding UTF8
Write-Info "Build-Info gespeichert in .last_build"
