# 11 — Testbarkeit und Reproduzierbarkeit (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 11.1 Vorhandene Tests

### Smoke-Tests (standalone)

| Datei | Framework | Tests | Zweck |
|-------|-----------|-------|-------|
| `src/tests/run_smoke_tests.py` | Kein (standalone) | 8 Test-Klassen | Kann ohne pytest ausgefuehrt werden |

**Test-Klassen:**
1. PDF-Validierung (Enum-Status)
2. GDV-Fallback (Konstanten)
3. Atomic Operations (SHA256, Integrity, Write)
4. Document State Machine (Status-Uebergaenge)
5. Document Dataclass (Felder, Defaults)
6. Processing History (Dataclass)
7. XML Index (Dataclass)
8. Import-Tests (Modul-Verfuegbarkeit)

**Evidenz:** `src/tests/run_smoke_tests.py` (~363 Zeilen)

### pytest-Tests

| Datei | Framework | Tests | Zweck |
|-------|-----------|-------|-------|
| `src/tests/test_smoke.py` | pytest | 7 Klassen | Erweiterte Smoke-Tests |
| `src/tests/test_stability.py` | pytest | 9 Tests | Stabilitaets-Regression |

**test_stability.py Tests:**
1. APIClient-Erstellung
2. Auth-Refresh (Deadlock-Schutz) — `acquire(blocking=False)`
3. Retry-Mechanismus
4. Exponential Backoff
5. Parser Roundtrip
6. DataCache Thread-Safety
7. SharedTokenManager Struktur
8. Import-Kette
9. Domain-Mapping

**Evidenz:** `src/tests/test_stability.py` (~196 Zeilen)

### Roundtrip-Test

| Datei | Zweck |
|-------|-------|
| `testdata/test_roundtrip.py` | GDV: Laden → Editieren → Speichern → Neu laden → Vergleichen |

**Evidenz:** `testdata/test_roundtrip.py` (~192 Zeilen)

### Minimal-CI Script

| Datei | Zweck |
|-------|-------|
| `scripts/run_checks.py` | Fuehrt ruff (optional) und pytest aus |

**Evidenz:** `scripts/run_checks.py` (~67 Zeilen)

## 11.2 Fehlende Tests

| Bereich | Status | Auswirkung |
|---------|--------|------------|
| UI-Komponenten | Nicht vorhanden | Keine Regression fuer UI-Aenderungen |
| PHP API Endpoints | Nicht vorhanden | Keine serverseitige Test-Coverage |
| BiPRO SOAP-Client | Nicht vorhanden (braucht Live-Verbindung) | Integration nur manuell testbar |
| KI-Klassifikation | Nicht vorhanden | Klassifikationslogik nicht regressionsgetestet |
| Security-Tests | Nicht vorhanden | Keine automatisierte Sicherheitspruefung |
| E2E-Tests | Nicht vorhanden | Kein End-to-End-Workflow-Test |
| Load-Tests | Nicht vorhanden | Keine Performance-Baseline |
| File-Upload-Tests | Nicht vorhanden | Upload-Sicherheit nicht automatisiert getestet |

## 11.3 Test-Coverage

**Belegbar:** Keine Coverage-Messung konfiguriert. Kein `coverage`-Tool in den Dependencies.

**Geschaetzt (basierend auf Test-Analyse):**
- Core-Domain (Dataclasses, State-Machine): ~60-70%
- Parser: ~40% (nur Roundtrip)
- API-Client: ~10% (nur Struktur/Import)
- Services: ~5% (nur Imports)
- UI: 0%
- PHP-Backend: 0%
- BiPRO: 0%

**Status:** UNVERIFIZIERT — Keine automatische Coverage-Messung vorhanden.

## 11.4 CI/CD

| Aspekt | Status |
|--------|--------|
| CI-Pipeline | **Nicht vorhanden** |
| CD-Pipeline | **Nicht vorhanden** |
| Automatische Tests bei Commit | **Nein** |
| Automatische Tests bei PR | **Nein** |
| Linter-Integration | Manuell (`ruff` in requirements-dev.txt) |
| Pre-Commit-Hooks | **Nicht vorhanden** |

**Build-Prozess:** Manuell via `build.bat` → PyInstaller → Inno Setup → SHA256-Hash.

**Deploy-Prozess:** Automatisch via Ordner-Synchronisierung (Strato). Keine Review-Gates.

**Evidenz:** Keine `.github/workflows/`, `.gitlab-ci.yml`, oder Jenkinsfile gefunden.

## 11.5 Reproduzierbarkeit

### Desktop-Build

| Schritt | Befehl | Reproduzierbar |
|---------|--------|----------------|
| Dependencies | `pip install -r requirements.txt` | Bedingt (>=, keine Lockfile) |
| Start | `python run.py` | Ja |
| Build | `build.bat` | Ja (Windows, PyInstaller + Inno Setup) |
| Tests | `python scripts/run_checks.py` | Ja |

**Problem:** Keine `pip freeze` / `pip-lock` vorhanden. Verschiedene Developer koennten unterschiedliche Versionen erhalten.

### Server-Deployment

| Schritt | Methode | Reproduzierbar |
|---------|---------|----------------|
| Code-Deploy | Ordner-Sync → Strato | Ja (automatisch) |
| DB-Migration | Manuell PHP-Scripts ausfuehren | Bedingt (kein Migrations-Runner) |
| PHP-Dependencies | Manuell in `api/lib/` | Bedingt (kein Composer) |

**Evidenz:** `BiPro-Webspace Spiegelung Live/setup/` (8 Migrationen)
