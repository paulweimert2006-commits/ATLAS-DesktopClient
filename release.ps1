# ============================================================================
# ACENCIA ATLAS - Automatisches Release-Script
# ============================================================================
#
# Dieses Script:
#   1. Liest die aktuelle Version und zaehlt automatisch hoch (Patch)
#   2. Fragt nach Release Notes
#   3. Fragt nach Admin-Zugangsdaten
#   4. Baut die App (PyInstaller + Inno Setup + SHA256)
#   5. Laedt den Installer auf den Server hoch
#   6. Erstellt den Release-Eintrag in der Datenbank
#
# Voraussetzungen:
#   - Python 3.10+ mit PyInstaller
#   - Inno Setup 6 installiert
#   - Internetzugang fuer API-Upload
#   - Admin-Account auf acencia.info
#
# ============================================================================

param(
    [string]$IncrementType = "patch"  # patch (default), minor, major
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Farb-Hilfsfunktionen
function Write-Step   { param($msg) Write-Host "`n[$script:stepNum/8] $msg" -ForegroundColor Cyan; $script:stepNum++ }
function Write-Ok     { param($msg) Write-Host "  OK - $msg" -ForegroundColor Green }
function Write-Warn   { param($msg) Write-Host "  WARNUNG: $msg" -ForegroundColor Yellow }
function Write-Err    { param($msg) Write-Host "  FEHLER: $msg" -ForegroundColor Red }
function Write-Info   { param($msg) Write-Host "  $msg" -ForegroundColor Gray }

$script:stepNum = 1

# API-Konfiguration
$API_BASE = "https://acencia.info/api"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ACENCIA ATLAS - Release Automation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# SCHRITT 1: Version lesen und hochzaehlen
# ============================================================================
Write-Step "Version ermitteln und hochzaehlen..."

$versionFile = Join-Path $PSScriptRoot "VERSION"
if (-not (Test-Path $versionFile)) {
    Write-Err "VERSION-Datei nicht gefunden!"
    exit 1
}

$currentVersion = (Get-Content $versionFile -Raw).Trim()
Write-Info "Aktuelle Version: $currentVersion"

# Version parsen
if ($currentVersion -notmatch '^(\d+)\.(\d+)\.(\d+)') {
    Write-Err "Ungueltige Version in VERSION-Datei: $currentVersion"
    exit 1
}

$major = [int]$Matches[1]
$minor = [int]$Matches[2]
$patch = [int]$Matches[3]

# Hochzaehlen
switch ($IncrementType.ToLower()) {
    "major" { $major++; $minor = 0; $patch = 0 }
    "minor" { $minor++; $patch = 0 }
    "patch" { $patch++ }
    default { $patch++ }
}

$nextVersion = "$major.$minor.$patch"
Write-Info "Naechste Version: $nextVersion ($IncrementType-Increment)"
Write-Host ""

$confirm = Read-Host "  Version $nextVersion verwenden? [J/n] oder neue Version eingeben"
if ($confirm -eq "n" -or $confirm -eq "N") {
    Write-Host "  Abgebrochen." -ForegroundColor Yellow
    exit 0
}
if ($confirm -ne "" -and $confirm -ne "j" -and $confirm -ne "J" -and $confirm -ne "y" -and $confirm -ne "Y") {
    # Benutzereingabe als Version interpretieren
    $nextVersion = $confirm.Trim()
}

# SemVer-Validierung
if ($nextVersion -notmatch '^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$') {
    Write-Err "Ungueltige Version: $nextVersion (erwartet: X.Y.Z)"
    exit 1
}

# Version in Datei schreiben (UTF-8 OHNE BOM - wichtig fuer Python-Kompatibilitaet!)
[System.IO.File]::WriteAllText($versionFile, $nextVersion, (New-Object System.Text.UTF8Encoding $false))
Write-Ok "VERSION-Datei auf $nextVersion aktualisiert"

# Auch i18n/de.py aktualisieren falls APP_VERSION dort existiert
# (aktuell nicht der Fall, aber sicher ist sicher)


# ============================================================================
# SCHRITT 2: Release Notes abfragen (mit automatischem Header + History)
# ============================================================================
Write-Step "Release Notes eingeben..."

# Fester Header-Text
$releaseHeader = @"
Willkommen bei ACENCIA ATLAS.
Der Datenkern fuer Versicherungsprofis. Automatisierter BiPRO-Datenabruf, zentrales Dokumentenarchiv mit KI-Klassifikation und GDV-Editor - alles in einer Anwendung. Entwickelt fuer Teams, optimiert für Effizienz.
"@ 

$separator = "----------------------------------------------------------------"

# History-Datei lesen (bisherige Features)
$historyFile = Join-Path $PSScriptRoot "RELEASE_FEATURES_HISTORY.txt"
$existingFeatures = @()
if (Test-Path $historyFile) {
    $existingFeatures = Get-Content $historyFile -Encoding UTF8 | Where-Object { $_.Trim() -ne "" }
    Write-Info "Bisherige Features geladen: $($existingFeatures.Count) Eintraege"
} else {
    Write-Warn "Keine History-Datei gefunden, erstelle neue..."
}

Write-Host ""
Write-Host "  Geben Sie die NEUEN Features fuer dieses Release ein." -ForegroundColor Gray
Write-Host "  Format: - Feature-Beschreibung (ein Feature pro Zeile)" -ForegroundColor Gray
Write-Host "  Leere Zeile zum Beenden:" -ForegroundColor Gray
Write-Host ""

$newNotesLines = @()
while ($true) {
    $line = Read-Host "  "
    if ([string]::IsNullOrEmpty($line)) { break }
    # Sicherstellen, dass jede Zeile mit "- " beginnt
    if (-not $line.StartsWith("- ")) {
        $line = "- $line"
    }
    $newNotesLines += $line
}

if ($newNotesLines.Count -eq 0) {
    Write-Warn "Keine neuen Features eingegeben!"
    $newNotesSection = "- Release $nextVersion"
} else {
    $newNotesSection = $newNotesLines -join "`n"
    Write-Ok "$($newNotesLines.Count) neue Feature(s) erfasst"
}

# Vollstaendige Release Notes zusammenbauen
# Format: Header + Trennlinie + NEUE Notes + Trennlinie + ALTE Features
$releaseNotes = @"
$releaseHeader
$separator
$newNotesSection
$separator
$($existingFeatures -join "`n")
"@

# Vorschau anzeigen
Write-Host ""
Write-Host "  --- Vorschau der Release Notes ---" -ForegroundColor Cyan
Write-Host $releaseNotes -ForegroundColor Gray
Write-Host "  --- Ende Vorschau ---" -ForegroundColor Cyan
Write-Host ""

$confirmNotes = Read-Host "  Release Notes so verwenden? [J/n]"
if ($confirmNotes -eq "n" -or $confirmNotes -eq "N") {
    Write-Host "  Abgebrochen." -ForegroundColor Yellow
    exit 0
}

# Neue Features zur History-Datei hinzufuegen (am ANFANG, damit neueste oben stehen)
$updatedHistory = @()
$updatedHistory += $newNotesLines
$updatedHistory += $existingFeatures
[System.IO.File]::WriteAllLines($historyFile, $updatedHistory, [System.Text.Encoding]::UTF8)
Write-Ok "Feature-History aktualisiert ($($updatedHistory.Count) Eintraege)"


# ============================================================================
# SCHRITT 3: Admin-Zugangsdaten und Login
# ============================================================================
Write-Step "Am Server anmelden..."

$username = Read-Host "  Admin-Benutzername"
$securePassword = Read-Host "  Admin-Passwort" -AsSecureString

# SecureString in Klartext (fuer API-Login noetig)
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

# Login via API
try {
    $loginBody = @{
        username = $username
        password = $plainPassword
    } | ConvertTo-Json -Compress

    $loginResponse = Invoke-RestMethod `
        -Uri "$API_BASE/auth/login" `
        -Method POST `
        -Body $loginBody `
        -ContentType "application/json; charset=utf-8"

    if (-not $loginResponse.success) {
        Write-Err "Login fehlgeschlagen: $($loginResponse.message)"
        exit 1
    }

    $token = $loginResponse.data.token
    $loginUser = $loginResponse.data.user

    # Admin-Check
    if ($loginUser.account_type -ne "admin") {
        Write-Err "Nur Administratoren koennen Releases erstellen!"
        exit 1
    }

    Write-Ok "Angemeldet als '$($loginUser.username)' (Admin)"
} catch {
    Write-Err "Login fehlgeschlagen: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) {
        $errDetail = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($errDetail.message) { Write-Err $errDetail.message }
    }
    exit 1
} finally {
    # Passwort aus Speicher loeschen
    $plainPassword = $null
}


# ============================================================================
# SCHRITT 4: Version in Build-Dateien aktualisieren
# ============================================================================
Write-Step "Build-Dateien aktualisieren..."

# version_info.txt aktualisieren
$nextVersion -match '^(\d+)\.(\d+)\.(\d+)' | Out-Null
$vMajor = $Matches[1]
$vMinor = $Matches[2]
$vPatch = $Matches[3]

$versionInfoPath = Join-Path $PSScriptRoot "version_info.txt"
if (Test-Path $versionInfoPath) {
    $content = Get-Content $versionInfoPath -Raw
    $content = $content -replace 'filevers=\([\d, ]+\)', "filevers=($vMajor, $vMinor, $vPatch, 0)"
    $content = $content -replace 'prodvers=\([\d, ]+\)', "prodvers=($vMajor, $vMinor, $vPatch, 0)"
    $content = $content -replace "FileVersion', u'[\d.]+'"  , "FileVersion', u'$nextVersion.0'"
    $content = $content -replace "ProductVersion', u'[\d.]+'"  , "ProductVersion', u'$nextVersion.0'"
    Set-Content $versionInfoPath $content -NoNewline
    Write-Ok "version_info.txt auf $nextVersion aktualisiert"
}

# installer.iss aktualisieren
$issPath = Join-Path $PSScriptRoot "installer.iss"
if (Test-Path $issPath) {
    $content = Get-Content $issPath -Raw
    $content = $content -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$nextVersion`""
    Set-Content $issPath $content -NoNewline
    Write-Ok "installer.iss auf $nextVersion aktualisiert"
}


# ============================================================================
# SCHRITT 5: PyInstaller Build
# ============================================================================
Write-Step "App mit PyInstaller bauen..."

# Alte Builds aufraeumen
$buildDir = Join-Path $PSScriptRoot "build"
$distDir = Join-Path $PSScriptRoot "dist"
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }
if (Test-Path $distDir) { Remove-Item $distDir -Recurse -Force }
Write-Info "Alte Build-Verzeichnisse bereinigt"

# PyInstaller pruefen
$pyInstallerCheck = pip show pyinstaller 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Info "PyInstaller nicht gefunden, installiere..."
    pip install pyinstaller
}

# Build starten
Write-Info "PyInstaller laeuft... (dies kann einige Minuten dauern)"
$specFile = Join-Path $PSScriptRoot "build_config.spec"

$buildProcess = Start-Process -FilePath "python" `
    -ArgumentList "-m PyInstaller `"$specFile`" --clean --noconfirm" `
    -WorkingDirectory $PSScriptRoot `
    -NoNewWindow -Wait -PassThru

if ($buildProcess.ExitCode -ne 0) {
    Write-Err "PyInstaller Build fehlgeschlagen! (Exit-Code: $($buildProcess.ExitCode))"
    exit 1
}

# Pruefen ob EXE existiert
$exePath = Join-Path $PSScriptRoot "dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe"
if (-not (Test-Path $exePath)) {
    Write-Err "Build-Ergebnis nicht gefunden: $exePath"
    exit 1
}

Write-Ok "PyInstaller Build erfolgreich"


# ============================================================================
# SCHRITT 6: Installer mit Inno Setup erstellen
# ============================================================================
Write-Step "Installer mit Inno Setup erstellen..."

$innoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $innoPath)) {
    Write-Err "Inno Setup 6 nicht gefunden unter: $innoPath"
    Write-Err "Bitte installieren: https://jrsoftware.org/isdl.php"
    exit 1
}

# Output-Verzeichnis sicherstellen
$outputDir = Join-Path $PSScriptRoot "Output"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

$innoProcess = Start-Process -FilePath $innoPath `
    -ArgumentList "`"$issPath`"" `
    -WorkingDirectory $PSScriptRoot `
    -NoNewWindow -Wait -PassThru

if ($innoProcess.ExitCode -ne 0) {
    Write-Err "Inno Setup fehlgeschlagen! (Exit-Code: $($innoProcess.ExitCode))"
    exit 1
}

# Installer umbenennen mit Version
$setupGeneric = Join-Path $outputDir "ACENCIA-ATLAS-Setup.exe"
$setupVersioned = Join-Path $outputDir "ACENCIA-ATLAS-Setup-$nextVersion.exe"

if (Test-Path $setupGeneric) {
    if (Test-Path $setupVersioned) { Remove-Item $setupVersioned -Force }
    Move-Item $setupGeneric $setupVersioned
    Write-Ok "Installer erstellt: ACENCIA-ATLAS-Setup-$nextVersion.exe"
} else {
    Write-Err "Installer-Datei nicht gefunden: $setupGeneric"
    exit 1
}


# ============================================================================
# SCHRITT 7: SHA256-Hash generieren
# ============================================================================
Write-Step "SHA256-Hash berechnen..."

$sha256 = (Get-FileHash $setupVersioned -Algorithm SHA256).Hash.ToLower()
$sha256File = Join-Path $outputDir "ACENCIA-ATLAS-Setup-$nextVersion.sha256"
Set-Content $sha256File $sha256 -NoNewline -Encoding UTF8

$fileSize = (Get-Item $setupVersioned).Length
$fileSizeMB = [math]::Round($fileSize / 1MB, 2)

Write-Ok "SHA256: $sha256"
Write-Info "Dateigroesse: $fileSizeMB MB"


# ============================================================================
# SCHRITT 8: Auf Server hochladen
# ============================================================================
Write-Step "Release auf Server hochladen..."

Write-Info "Lade hoch: ACENCIA-ATLAS-Setup-$nextVersion.exe ($fileSizeMB MB)..."

try {
    # .NET HttpClient mit MultipartFormDataContent (sauberes Multipart-Handling)
    Add-Type -AssemblyName System.Net.Http

    $httpClient = New-Object System.Net.Http.HttpClient
    $httpClient.Timeout = [System.TimeSpan]::FromSeconds(600)
    $httpClient.DefaultRequestHeaders.Add("Authorization", "Bearer $token")

    $multipart = New-Object System.Net.Http.MultipartFormDataContent

    # Form-Felder hinzufuegen
    $multipart.Add([System.Net.Http.StringContent]::new($nextVersion, [System.Text.Encoding]::UTF8), "version")
    $multipart.Add([System.Net.Http.StringContent]::new("stable", [System.Text.Encoding]::UTF8), "channel")
    $multipart.Add([System.Net.Http.StringContent]::new($releaseNotes, [System.Text.Encoding]::UTF8), "release_notes")

    # Datei hinzufuegen
    $fileStream = [System.IO.File]::OpenRead($setupVersioned)
    $fileContent = New-Object System.Net.Http.StreamContent($fileStream)
    $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new("application/octet-stream")
    $multipart.Add($fileContent, "file", "ACENCIA-ATLAS-Setup-$nextVersion.exe")

    # Upload ausfuehren
    Write-Info "Upload laeuft... (dies kann bei grossen Dateien mehrere Minuten dauern)"
    $response = $httpClient.PostAsync("$API_BASE/admin/releases", $multipart).GetAwaiter().GetResult()
    $responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

    # Stream und Client aufraeumen
    $fileStream.Dispose()
    $multipart.Dispose()
    $httpClient.Dispose()

    if ($response.IsSuccessStatusCode) {
        $responseJson = $responseBody | ConvertFrom-Json
        if ($responseJson.success) {
            Write-Ok "Release erfolgreich auf Server hochgeladen!"
        } else {
            Write-Err "Server-Antwort: $($responseJson.message)"
            exit 1
        }
    } else {
        Write-Err "Upload fehlgeschlagen: HTTP $([int]$response.StatusCode) $($response.ReasonPhrase)"
        # Versuche Server-Fehlermeldung zu parsen
        try {
            $errJson = $responseBody | ConvertFrom-Json
            if ($errJson.message) { Write-Err "Server: $($errJson.message)" }
        } catch {
            if ($responseBody.Length -lt 500) { Write-Info "Response: $responseBody" }
        }
        Write-Host ""
        Write-Warn "Die Installer-Datei wurde lokal erstellt und kann manuell hochgeladen werden:"
        Write-Info "  Datei: $setupVersioned"
        Write-Info "  Ueber: Admin-Bereich > Verwaltung > Releases > Neues Release"
        exit 1
    }
} catch {
    Write-Err "Upload fehlgeschlagen: $($_.Exception.Message)"
    Write-Host ""
    Write-Warn "Die Installer-Datei wurde lokal erstellt und kann manuell hochgeladen werden:"
    Write-Info "  Datei: $setupVersioned"
    Write-Info "  Ueber: Admin-Bereich > Verwaltung > Releases > Neues Release"
    exit 1
}


# ============================================================================
# ZUSAMMENFASSUNG
# ============================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Release $nextVersion erfolgreich!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Version:      $nextVersion" -ForegroundColor White
Write-Host "  Channel:      stable" -ForegroundColor White
Write-Host "  Status:       active (optional)" -ForegroundColor White
Write-Host "  Dateigroesse: $fileSizeMB MB" -ForegroundColor White
Write-Host "  SHA256:       $sha256" -ForegroundColor White
Write-Host ""
Write-Host "  Lokale Datei: $setupVersioned" -ForegroundColor Gray
Write-Host "  SHA256-Datei: $sha256File" -ForegroundColor Gray
Write-Host ""
Write-Host "  Naechste Schritte:" -ForegroundColor Yellow
Write-Host "    - Release in der Verwaltung pruefen" -ForegroundColor Gray
Write-Host "    - Optional: Status auf 'mandatory' setzen" -ForegroundColor Gray
Write-Host "    - Optional: Mindestversion festlegen" -ForegroundColor Gray
Write-Host ""
