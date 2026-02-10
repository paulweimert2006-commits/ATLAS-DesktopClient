@echo off
REM Vereinfachtes Build-Script mit besserer Fehlerbehandlung

echo ========================================
echo ACENCIA ATLAS - Einfacher Build
echo ========================================
echo.

REM Prüfe Python
echo Pruefe Python-Installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden!
    echo Bitte installiere Python 3.10+ von https://www.python.org/
    pause
    exit /b 1
)
python --version
echo.

REM Prüfe und installiere PyInstaller
echo Pruefe PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller nicht gefunden, installiere...
    python -m pip install pyinstaller
) else (
    echo PyInstaller ist installiert
)

REM Zeige PyInstaller Version
python -m PyInstaller --version
echo.

REM Alte Builds löschen
echo Raeume alte Builds auf...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul
echo OK
echo.

REM Build starten
echo Starte Build-Prozess...
echo (Das kann 2-5 Minuten dauern...)
echo.
python -m PyInstaller build_config.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ========================================
    echo BUILD FEHLGESCHLAGEN!
    echo ========================================
    echo.
    echo Moegliche Loesungen:
    echo.
    echo 1. PyInstaller neu installieren:
    echo    python -m pip uninstall pyinstaller -y
    echo    python -m pip install pyinstaller
    echo.
    echo 2. Fehlende Module installieren:
    echo    python -m pip install -r requirements.txt
    echo.
    echo 3. Manuell testen:
    echo    python -m PyInstaller --version
    echo    python run.py
    echo.
    echo 4. Log pruefen:
    echo    build\ACENCIA-ATLAS\warn-ACENCIA-ATLAS.txt
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD ERFOLGREICH!
echo ========================================
echo.
echo Die EXE wurde erstellt:
echo.
echo    dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe
echo.
echo Starte die App mit Doppelklick auf die EXE!
echo.

REM Frage ob die EXE gestartet werden soll
choice /c JN /m "Moechtest du die EXE jetzt testen"
if errorlevel 2 goto :skip_test
if errorlevel 1 (
    echo.
    echo Starte ACENCIA-ATLAS.exe...
    start "" "dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe"
    echo.
    echo Hinweis: Falls die App nicht startet, pruefe die Logs in:
    echo    dist\ACENCIA-ATLAS\_internal\
    echo.
)

:skip_test
echo.
echo ========================================
pause
