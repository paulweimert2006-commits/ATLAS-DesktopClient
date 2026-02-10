@echo off
setlocal enabledelayedexpansion
REM Build-Script für ACENCIA ATLAS
REM Erstellt eine standalone Windows EXE mit versioniertem Installer

echo ========================================
echo ACENCIA ATLAS - Build Process
echo ========================================
echo.

REM 0. Version aus zentraler VERSION-Datei lesen
if not exist "VERSION" (
    echo FEHLER: VERSION-Datei nicht gefunden!
    echo Erstelle eine VERSION-Datei mit dem Inhalt z.B. "0.9.8"
    pause
    exit /b 1
)
set /p APP_VERSION=<VERSION
echo Version: %APP_VERSION%
echo.

REM 1. Alte Builds löschen
echo [1/7] Räume alte Builds auf...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo OK
echo.

REM 2. PyInstaller installieren (falls nicht vorhanden)
echo [2/7] Prüfe PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller nicht gefunden, installiere...
    pip install pyinstaller
) else (
    echo PyInstaller bereits installiert
)
echo.

REM 3. Version in version_info.txt aktualisieren
echo [3/7] Aktualisiere version_info.txt...
REM Version in Komma-Format konvertieren (0.9.8 -> 0, 9, 8, 0)
for /f "tokens=1-3 delims=.-" %%a in ("%APP_VERSION%") do (
    set V_MAJOR=%%a
    set V_MINOR=%%b
    set V_PATCH=%%c
)
if not defined V_PATCH set V_PATCH=0

powershell -Command "$content = Get-Content 'version_info.txt' -Raw; $content = $content -replace 'filevers=\([\d, ]+\)', ('filevers=(%V_MAJOR%, %V_MINOR%, %V_PATCH%, 0)'); $content = $content -replace 'prodvers=\([\d, ]+\)', ('prodvers=(%V_MAJOR%, %V_MINOR%, %V_PATCH%, 0)'); $content = $content -replace \"FileVersion', u'[\d.]+'\", (\"FileVersion', u'%APP_VERSION%.0'\"); $content = $content -replace \"ProductVersion', u'[\d.]+'\", (\"ProductVersion', u'%APP_VERSION%.0'\"); Set-Content 'version_info.txt' $content -NoNewline"
echo OK - version_info.txt auf %APP_VERSION% aktualisiert
echo.

REM 4. Version in installer.iss aktualisieren
echo [4/7] Aktualisiere installer.iss...
powershell -Command "(Get-Content 'installer.iss') -replace '#define MyAppVersion \".*\"', '#define MyAppVersion \"%APP_VERSION%\"' | Set-Content 'installer.iss'"
echo OK - installer.iss auf %APP_VERSION% aktualisiert
echo.

REM 5. Build mit PyInstaller
echo [5/7] Erstelle EXE mit PyInstaller...
echo.
python -m PyInstaller build_config.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo FEHLER beim Build!
    echo.
    echo Troubleshooting:
    echo 1. PyInstaller neu installieren: pip uninstall pyinstaller ^&^& pip install pyinstaller
    echo 2. Python neu starten: Schliesse alle Python-Prozesse
    echo 3. Manuell testen: python -m PyInstaller --version
    echo.
    pause
    exit /b 1
)
echo OK
echo.

REM 6. Installer erstellen (wenn Inno Setup vorhanden)
echo [6/7] Erstelle Installer...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    if errorlevel 1 (
        echo WARNUNG: Installer-Erstellung fehlgeschlagen!
    ) else (
        echo OK - Installer erstellt
        
        REM Installer umbenennen mit Version
        if exist "Output\ACENCIA-ATLAS-Setup.exe" (
            if exist "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe" del "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe"
            move "Output\ACENCIA-ATLAS-Setup.exe" "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe" >nul
            echo     Umbenannt zu: ACENCIA-ATLAS-Setup-%APP_VERSION%.exe
        )
    )
) else (
    echo HINWEIS: Inno Setup nicht gefunden, ueberspringe Installer-Erstellung
    echo          Installiere Inno Setup 6 von: https://jrsoftware.org/isdl.php
)
echo.

REM 7. SHA256-Hash generieren
echo [7/7] Generiere SHA256-Hash...
if exist "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe" (
    certutil -hashfile "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe" SHA256 > "Output\sha256_temp.txt" 2>nul
    REM Zweite Zeile der certutil-Ausgabe ist der Hash
    for /f "skip=1 tokens=*" %%h in ('certutil -hashfile "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe" SHA256') do (
        if not defined SHA_HASH set "SHA_HASH=%%h"
    )
    echo %SHA_HASH% > "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.sha256"
    del "Output\sha256_temp.txt" 2>nul
    echo OK - SHA256: %SHA_HASH%
) else (
    echo HINWEIS: Keine Installer-Datei zum Hashen gefunden
)
echo.

REM Fertig
echo ========================================
echo Build abgeschlossen!
echo ========================================
echo.
echo   Version:   %APP_VERSION%
if exist "Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe" (
    echo   Installer: Output\ACENCIA-ATLAS-Setup-%APP_VERSION%.exe
    echo   SHA256:    %SHA_HASH%
)
echo   EXE:       dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe
echo.
echo Naechste Schritte:
echo   1. Testen: dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe
echo   2. Im Admin-Bereich der App neues Release hochladen
echo.
pause
