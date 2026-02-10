@echo off
REM Debug-Build mit Konsolenfenster (für Fehlersuche)

echo ========================================
echo ACENCIA ATLAS - DEBUG Build
echo ========================================
echo.
echo WICHTIG: Dieser Build zeigt ein Konsolenfenster
echo fuer Debugging-Zwecke.
echo.

REM Alte Builds löschen
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist" rmdir /s /q "dist" 2>nul

REM Debug-Build (mit Konsole)
echo Erstelle DEBUG-Build...
python -m PyInstaller ^
    --clean ^
    --noconfirm ^
    --name ACENCIA-ATLAS-Debug ^
    --console ^
    --onedir ^
    --paths src ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtPdf ^
    --hidden-import requests ^
    --hidden-import openpyxl ^
    --hidden-import fitz ^
    --collect-data PySide6 ^
    run.py

if errorlevel 1 (
    echo.
    echo BUILD FEHLGESCHLAGEN!
    echo Pruefe die Fehlermeldungen oben.
    pause
    exit /b 1
)

echo.
echo ========================================
echo DEBUG-BUILD ERFOLGREICH!
echo ========================================
echo.
echo Die DEBUG-EXE liegt in:
echo    dist\ACENCIA-ATLAS-Debug\
echo.
echo Diese Version zeigt alle Python-Fehlermeldungen
echo im Konsolenfenster an.
echo.
pause
