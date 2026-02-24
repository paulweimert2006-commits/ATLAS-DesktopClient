@echo off
REM ============================================
REM ACENCIA ATLAS - Release Automation
REM ============================================
REM
REM Erstellt automatisch ein neues Release:
REM   - Version hochzaehlen (Patch)
REM   - App bauen (PyInstaller + Inno Setup)
REM   - Auf Server hochladen
REM
REM Optionen:
REM   0_release.bat              Patch-Increment (0.9.8 -> 0.9.9)
REM   0_release.bat minor        Minor-Increment (0.9.8 -> 0.10.0)
REM   0_release.bat major        Major-Increment (0.9.8 -> 1.0.0)
REM
REM ============================================

set INCREMENT_TYPE=%1
if "%INCREMENT_TYPE%"=="" set INCREMENT_TYPE=patch

echo.
echo ACENCIA ATLAS - Release Automation
echo ============================================
echo Increment: %INCREMENT_TYPE%
echo.

REM PowerShell-Script ausfuehren (Execution Policy umgehen)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0release.ps1" -IncrementType %INCREMENT_TYPE%

echo.
if %ERRORLEVEL% NEQ 0 (
    echo Release-Erstellung fehlgeschlagen!
    echo.
)
pause
