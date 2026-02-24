# ACENCIA ATLAS - Build Anleitung

Erstelle eine standalone Windows .EXE mit Installer für die ACENCIA ATLAS Desktop-App.

## Voraussetzungen

### 1. Python-Dependencies installieren
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 2. (Optional) Inno Setup für Installer
Für einen professionellen Windows-Installer:
- Download: https://jrsoftware.org/isdl.php
- Installiere Inno Setup 6 (kostenlos)

## Schnellstart: EXE erstellen

### Windows (einfach)
Doppelklick auf `build.bat` - fertig!

### Manuell
```bash
# Alte Builds löschen
rmdir /s /q build dist

# EXE erstellen
pyinstaller build_config.spec --clean --noconfirm

# Fertig! Die EXE liegt in:
dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe
```

## Installer erstellen (optional)

Wenn Inno Setup installiert ist:

```bash
# 1. Erst die EXE bauen
pyinstaller build_config.spec --clean --noconfirm

# 2. Dann den Installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# Fertig! Der Installer liegt in:
Output\ACENCIA-ATLAS-Setup.exe
```

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `build_config.spec` | PyInstaller-Konfiguration |
| `version_info.txt` | Windows Version Info |
| `build.bat` | Automatisches Build-Script |
| `installer.iss` | Inno Setup Installer-Config |

## Was wird gepackt?

- Python-Runtime (eingebettet)
- PySide6 (Qt-Framework)
- Alle Dependencies (requests, PyMuPDF, openpyxl, etc.)
- Deine komplette `src/` Verzeichnisstruktur
- Qt-Plugins und DLLs

**Größe:** ~80-120 MB (komprimiert im Installer: ~40 MB)

## Performance

Die EXE startet **deutlich schneller** als `python run.py`:
- ❌ Mit Python: ~3-5 Sekunden (Python-Startup + Import aller Module)
- ✅ Mit EXE: ~1-2 Sekunden (alles vorkompiliert)

## Troubleshooting

### Problem: "ModuleNotFoundError" beim Start der EXE
**Lösung:** Fehlende Module in `build_config.spec` → `hiddenimports` hinzufügen

### Problem: Qt-Plugins nicht gefunden
**Lösung:** PySide6-Daten werden automatisch gesammelt via `collect_data_files('PySide6')`

### Problem: EXE zu groß (>200 MB)
**Lösung:** 
1. Prüfe `excludes` in `build_config.spec` - unnötige Module ausschließen
2. UPX-Kompression ist aktiviert (`upx=True`)
3. Inno Setup komprimiert nochmal (~50% Reduktion)

### Problem: Antivirus meldet Virus
**Lösung:** False Positive bei PyInstaller-EXEs (üblich)
- Windows Defender: Ausnahme hinzufügen
- Oder: Code-Signing-Zertifikat verwenden (kostenpflichtig)

## Distribution

### Nur EXE verteilen
Kopiere den gesamten Ordner `dist\ACENCIA-ATLAS\` auf andere PCs.
**Vorteil:** Keine Installation nötig, portable.

### Installer verteilen
Verteile `Output\ACENCIA-ATLAS-Setup.exe`.
**Vorteile:**
- Professionelle Installation in Programme-Ordner
- Desktop-Icon
- Startmenü-Eintrag
- Saubere Deinstallation

## Icon

Das App-Icon liegt unter `src/ui/assets/icon.ico` und wird automatisch in den Build eingebunden.

## Updates verteilen (empfohlen)

Fuer neue Releases den automatisierten Workflow nutzen:

```
0_release.bat
```

Das Script:
1. Zaehlt die Version automatisch hoch (VERSION-Datei)
2. Aktualisiert version_info.txt und installer.iss
3. Baut die App (PyInstaller + Inno Setup)
4. Laedt den Installer auf den Server hoch
5. Erstellt den Release-Eintrag in der Datenbank

Nutzer erhalten das Update automatisch (Auto-Update-System seit v0.9.9).

Siehe `RELEASE_HOWTO.md` fuer Details.

---

## Support

Bei Problemen:
- Logs prüfen: `dist\ACENCIA-ATLAS\_internal\`
- PyInstaller-Doku: https://pyinstaller.org/en/stable/
- Inno Setup-Doku: https://jrsoftware.org/ishelp/

**Wichtig:** Die EXE verbindet sich mit `https://acencia.info/api/` - Server muss erreichbar sein!
