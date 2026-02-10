# 07 - Build, Run, Test, Deployment

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Installation (Entwicklungsumgebung)

### Voraussetzungen

| Komponente | Version | Hinweis |
|------------|---------|---------|
| Python | 3.10+ | Getestet mit 3.10, 3.11 |
| pip | aktuell | - |
| Git | aktuell | - |
| Windows | 10/11 | Fuer pywin32 (Outlook-COM) |

### Setup

```bash
cd "X:\projekte\5510_GDV Tool V1"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # optional: Tests + Linting
```

---

## Anwendung starten

### Standard-Start

```bash
python run.py
```

### Mit Debug-Logging

```bash
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from src.main import main; main()"
```

### Login

- Benutzername: `admin` (oder zugewiesener Account)
- Passwort: Vom Administrator vergeben
- Server muss erreichbar sein: `https://acencia.info/api/`

---

## Tests

### Smoke-Tests

```bash
cd "X:\projekte\5510_GDV Tool V1"
python -m pytest src/tests/test_stability.py -v
```

11 Tests: Parser-Import, API-Client-Import, Deadlock-Verifikation, etc.

### Erweiterte Tests

```bash
python -m pytest src/tests/test_smoke.py -v
```

Umfangreichere Tests: PDF-Validierung, GDV-Fallback, Atomare Operationen, Document State Machine.

### Checks-Script

```bash
python scripts/run_checks.py
```

Fuehrt Lint + Tests in einem Durchlauf aus.

### Manuelle Tests

| Test | Vorgehen |
|------|----------|
| BiPRO-Abruf | App starten, Degenia-Verbindung waehlen, Lieferungen abrufen |
| KI-Klassifikation | PDF hochladen (Upload-Button), Verarbeitung starten |
| GDV-Editor | `testdata/sample.gdv` oeffnen, Felder bearbeiten, speichern |
| Drag & Drop | PDF aus Explorer auf App-Fenster ziehen |
| Smart!Scan | Dokument auswaehlen, Smart!Scan im Kontextmenue |
| Mail-Import | "Mails abholen" im BiPRO-Bereich klicken |

---

## Server-Synchronisierung

### Live-Sync (WinSCP oder aehnlich)

| Lokal | Remote |
|-------|--------|
| `BiPro-Webspace Spiegelung Live/` | Strato Webspace `/BiPro/` |

### Synchronisations-Regeln

| Ordner | Synchronisiert | Grund |
|--------|----------------|-------|
| `api/` | Ja | PHP-Code |
| `setup/` | Ja | Migrations-Skripte |
| `dokumente/` | **NEIN** | Server-Dokumentenspeicher |
| `releases/` | **NEIN** | Installer-EXEs fuer Updates |

**VORSICHT:** Geloeschte lokale Dateien werden auch auf dem Server geloescht!

### DB-Migrationen ausfuehren

```
https://acencia.info/setup/{dateiname}.php?token=BiPro2025Setup!
```

Nach erfolgreicher Ausfuehrung: Datei loeschen!

Aktuelle Migrationen:
- `008_add_box_type_falsch.php` - ENUM-Erweiterung
- `010_smartscan_email.php` - E-Mail-System (7 Tabellen)
- `011_fix_smartscan_schema.php` - Schema-Korrektur
- `012_add_documents_history_permission.php` - Neue Permission

---

## Packaging (Build)

### build.bat

```batch
build.bat
```

Schritte:
1. VERSION-Datei lesen (aktuell: 1.6.0)
2. Alte Build-Artefakte loeschen
3. PyInstaller pruefen/installieren
4. `version_info.txt` aktualisieren (Windows-Versionsinformationen)
5. `installer.iss` Version aktualisieren
6. PyInstaller-Build (`build_config.spec`)
7. Inno Setup Installer erstellen (falls installiert)
8. SHA256-Hash generieren (`Output/ACENCIA-ATLAS-Setup-{version}.exe.sha256`)

### Artefakte

| Artefakt | Pfad | Beschreibung |
|----------|------|--------------|
| EXE | `dist/ACENCIA-ATLAS/ACENCIA-ATLAS.exe` | Standalone-Anwendung |
| Installer | `Output/ACENCIA-ATLAS-Setup-{version}.exe` | Inno Setup Installer |
| SHA256 | `Output/ACENCIA-ATLAS-Setup-{version}.exe.sha256` | Hash-Datei fuer Verifikation |

### Installer (Inno Setup)

| Einstellung | Wert |
|-------------|------|
| AppId | `{8F9D5E3A-1234-5678-9ABC-DEF012345678}` |
| AppMutex | `ACENCIA_ATLAS_SINGLE_INSTANCE` |
| CloseApplications | force |
| Default Install Dir | `{autopf}\ACENCIA ATLAS` |
| Silent-Install | Unterstuetzt (`/SILENT /NORESTART`) |

---

## Auto-Update System (v0.9.9+)

### Update-Check

| Zeitpunkt | Methode |
|-----------|---------|
| Nach Login | Synchron (blockierend) |
| Periodisch | Alle 30 Minuten (UpdateCheckWorker) |

### Ablauf

```
1. GET /updates/check?version={current}&channel=stable
2. Server vergleicht Version -> Response mit Update-Info
3. UpdateDialog anzeigen:
    a) Optional: "Jetzt installieren" / "Spaeter"
    b) Pflicht: Kein Schliessen, App blockiert
    c) Veraltet: Warnung bei deprecated
4. Download: Installer-EXE herunterladen
5. SHA256-Verifikation
6. Installation: Inno Setup Silent Install
7. App neu starten
```

### Release-Verwaltung (Admin)

| Feld | Beschreibung |
|------|--------------|
| version | Versions-String (Semver) |
| channel | stable, beta, internal |
| status | active, mandatory, deprecated, withdrawn |
| min_version | Versionen darunter = Pflicht-Update |
| sha256_hash | Hash der Installer-EXE |
| download_count | Anzahl Downloads |

---

## Debugging

### Log-Dateien

| Pfad | Beschreibung |
|------|--------------|
| `logs/bipro_gdv.log` | Hauptlog (RotatingFileHandler, 5 MB, 3 Backups) |
| Konsole | Zusaetzliche Ausgabe bei Debug-Level |

### Typische Probleme

| Problem | Loesung |
|---------|---------|
| Umlaute falsch | Encoding nicht CP1252, Pruefe `parsed_file.encoding` |
| Felder falsch geparst | Layout in `gdv_layouts.py` pruefen (1-basiert!) |
| BiPRO "keine Lieferungen" | VEMA: API-Credentials verwenden, nicht Portal-Passwort |
| STS kein Token | Portal-Passwort funktioniert nicht fuer API |
| PDF-Vorschau leer | PySide6 >= 6.4 benoetigt |
| API "Unauthorized" | JWT abgelaufen, neu anmelden |
| processing_history 500 | Imports in PHP pruefen (lib/db.php, lib/response.php) |
| Verarbeitung langsam | processing_history Fehler mit Retries, Log pruefen |
| PDFs falsch klassifiziert | Keyword-Hints pruefen, _build_keyword_hints() |
| Deadlock bei Token-Refresh | _try_auth_refresh() nutzt non-blocking acquire |
| RuntimeError C++ deleted | _is_worker_running() nutzt try/except |
| BiPRO Downloads korrupt | MTOM-Parser + PDF-Reparatur (PyMuPDF) |
| Datetime-Fehler | timezone.utc verwenden (nicht naive datetimes) |

---

## Vorschau-Cache

| Aspekt | Details |
|--------|---------|
| Pfad | `%TEMP%/bipro_preview_cache/` |
| Strategie | Einmal downloaden, danach instant aus Cache |
| Invalidierung | Bei PDF-Bearbeitung (Replace) wird Cache geloescht |
| Cleanup | Manuell oder bei Neuinstallation |
