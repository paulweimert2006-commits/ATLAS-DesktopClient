# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# ACENCIA ATLAS - PyInstaller Build-Konfiguration
# =============================================================================
#
# Verwendung:
#   python -m PyInstaller build_config.spec --clean --noconfirm
#
# Oder automatisch via:
#   build.bat          (nur Build)
#   0_release.bat      (Build + Upload auf Server)
#
# =============================================================================

import os
import sys

block_cipher = None

PROJECT_DIR = os.path.abspath(os.path.dirname(SPEC))

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# PySide6: Qt-Plugins, Translations, Platform-Dateien
pyside6_datas = collect_data_files('PySide6')

# tiktoken: Encoding-Dateien (BPE-Tabellen fuer Token-Zaehlung)
tiktoken_datas = collect_data_files('tiktoken')

# certifi: CA-Zertifikatbundle (HTTPS-Verbindungen via requests/urllib3)
certifi_datas = collect_data_files('certifi')

# keyring: Backend-Module dynamisch geladen
keyring_imports = collect_submodules('keyring.backends')

a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        # Zentrale Versionsdatei (geladen via sys._MEIPASS in main.py)
        ('VERSION', '.'),

        # App-Icon (fuer QIcon zur Laufzeit)
        ('src/ui/assets/icon.ico', 'ui/assets'),

        # Fonts (falls .ttf/.otf Dateien im Ordner liegen)
        ('src/ui/assets/fonts', 'ui/assets/fonts'),

        # Externe Bibliotheks-Daten
        *pyside6_datas,
        *tiktoken_datas,
        *certifi_datas,
    ],
    hiddenimports=[
        # ---- PySide6 ----
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',

        # ---- HTTP / Netzwerk ----
        'requests',
        'requests.adapters',
        'urllib3',

        # ---- PDF (PyMuPDF) ----
        'fitz',
        'fitz._fitz',
        'fitz.fitz',

        # ---- Excel ----
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.workbook',
        'openpyxl.reader.excel',
        'openpyxl.writer.excel',

        # ---- E-Mail / MSG ----
        'extract_msg',
        'olefile',

        # ---- ZIP (AES-256) ----
        'pyzipper',

        # ---- Windows COM (Outlook) ----
        'win32com',
        'win32com.client',
        'pythoncom',
        'pywintypes',

        # ---- Token-Zaehlung ----
        'tiktoken',
        'tiktoken.core',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',

        # ---- Kryptographie ----
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.serialization',
        'cryptography.hazmat.primitives.serialization.pkcs12',
        'cryptography.hazmat.backends',

        # ---- Keyring ----
        'keyring',
        *keyring_imports,

        # ---- JKS-Zertifikate ----
        'jks',

        # ---- Logging ----
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
        'tkinter',
        'unittest',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ACENCIA-ATLAS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='src/ui/assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ACENCIA-ATLAS',
)
