@echo off
REM Test-Script für die erstellte EXE

echo ========================================
echo ACENCIA ATLAS - EXE Test
echo ========================================
echo.

REM Prüfe ob EXE existiert
if not exist "dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe" (
    echo FEHLER: EXE nicht gefunden!
    echo.
    echo Bitte erst build_simple.bat ausfuehren.
    pause
    exit /b 1
)

echo EXE gefunden: dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe
echo.

REM Größe anzeigen
for %%A in ("dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe") do echo Groesse: %%~zA Bytes (~%%~zA / 1048576 = MB)
echo.

echo Starte EXE...
echo.
echo Falls die App nicht startet:
echo 1. Pruefe Windows Defender (False Positive moeglich)
echo 2. Starte als Administrator
echo 3. Pruefe Logs in: dist\ACENCIA-ATLAS\_internal\
echo.

start "" "dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe"

echo.
echo EXE wurde gestartet!
echo Falls Fehler auftreten, siehst du sie im Log.
echo.
pause
