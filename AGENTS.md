# AGENTS.md
# ACENCIA ATLAS -- Desktop Client

> **Version**: 3.4.0
> Detaillierte Dokumentation liegt im privaten Submodule `ATLAS_private - Doku - Backend/`.

---

## Projekt-Steckbrief

| Feld | Wert |
|------|------|
| **Name** | ACENCIA ATLAS |
| **Typ** | Python-Desktop-App (PySide6/Qt) |
| **Entry Point** | `python run.py` |
| **Version** | Siehe `VERSION`-Datei im Root |

---

## Coding Standards

### Sprache & Style
- **Python**: PEP 8, Type Hints, Google-Style Docstrings
- **Variablen/Funktionen**: Englisch
- **Kommentare/Docstrings**: Deutsch OK
- **UI-Texte**: MUESSEN aus `src/i18n/de.py` stammen -- keine Hardcoded Strings

### Verbotene Patterns
- **KEINE modalen Popups**: `QMessageBox.information/warning/critical` sind VERBOTEN. Stattdessen `ToastManager` aus `ui.toast` verwenden. Erlaubt: Nur `QMessageBox.question()` fuer sicherheitskritische Bestaetigungen.
- **Keine Secrets im Code**
- **Keine `print()`-Reste oder Debug-Ausgaben**

### Namenskonventionen
- **Klassen**: PascalCase (`ParsedRecord`, `GDVData`)
- **Funktionen/Variablen**: snake_case
- **Datumsanzeige**: DD.MM.YYYY in UI

### Error-Handling
- Fehler via `ToastManager` (nicht-blockierend)
- Logging: `logging` Standard-Library
- File-Logging: `logs/bipro_gdv.log` (RotatingFileHandler, 5 MB, 3 Backups)

---

## Git-Regeln

- **Branch-Strategie**: `main` (stable) / `beta` (beta) / `dev` (experimental)
- **Kein Direktcommit** auf `main` oder `dev`
- **Pipeline**: Feature-Branch -> dev -> beta -> main
- Pipeline-Skripte: siehe `ATLAS_private - Doku - Backend/governance/`

---

## Projektstruktur (oeffentlich)

```
src/                    Python Desktop-App
  ui/                   UI-Layer (PySide6)
  api/                  API-Client-Module
  bipro/                BiPRO SOAP Client
  services/             Business-Services
  parser/               GDV-Parser
  i18n/                 Internationalisierung
  tests/                Smoke-Tests
run.py                  Entry Point
VERSION                 Versionsdatei
requirements.txt        Dependencies
```

## Interne Dokumentation

Detaillierte Architektur, API-Docs, Security, Governance und Backend-Code
liegen im privaten Submodule:

```
ATLAS_private - Doku - Backend/     (Git Submodule, privat)
  docs/                             Kern- und Entwickler-Dokumentation
  governance/                       Pipeline-Skripte
  testdata/                         Testdaten
  BiPro-Webspace Spiegelung Live/   PHP REST-API Backend
  AGENTS.md                         Vollstaendige Agent-Instruktionen
```
