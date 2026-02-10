# 10 — Abhaengigkeiten und Lizenzen (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 10.1 Python-Dependencies (Produktion)

### `requirements.txt`

| Package | Versionierung | Bekannte Sicherheitsrisiken | Lizenz |
|---------|--------------|----------------------------|--------|
| `PySide6>=6.6.0` | Minimum, kein Maximum | UNVERIFIZIERT | LGPL v3 |
| `requests>=2.31.0` | Minimum, kein Maximum | UNVERIFIZIERT | Apache 2.0 |
| `cryptography>=41.0.0` | Minimum, kein Maximum | UNVERIFIZIERT | Apache 2.0 / BSD |
| `PyMuPDF>=1.23.0` | Minimum, kein Maximum | UNVERIFIZIERT | AGPL v3 |
| `pyjks>=20.0.0` | Minimum, kein Maximum | UNVERIFIZIERT | MIT |
| `openpyxl>=3.1.0` | Minimum, kein Maximum | UNVERIFIZIERT | MIT |
| `extract-msg>=0.50.0` | Minimum, kein Maximum | UNVERIFIZIERT | GPL v3 |
| `pywin32>=306` | Minimum, kein Maximum (nur Windows) | UNVERIFIZIERT | PSF |
| `pyzipper>=0.3.6` | Minimum, kein Maximum | UNVERIFIZIERT | MIT |
| `pyinstaller>=6.0.0` | Minimum, kein Maximum | UNVERIFIZIERT | GPL v2 (mit Ausnahme) |

**Evidenz:** `requirements.txt` (Root)

### Lizenz-Kompatibilitaet

| Lizenz | Packages | Kompatibilitaet mit Closed-Source |
|--------|----------|----------------------------------|
| LGPL v3 | PySide6 | Ja (dynamisches Linking) |
| AGPL v3 | PyMuPDF | **Problematisch** (AGPL erfordert Quellcode-Offenlegung bei Netzwerk-Nutzung) |
| GPL v3 | extract-msg | **Problematisch** (GPL erfordert GPL-kompatible Lizenz fuer abgeleitete Werke) |
| GPL v2+ | PyInstaller | Ja (Bootloader-Ausnahme fuer bundled Apps) |
| Apache 2.0 | requests, cryptography | Ja |
| MIT | pyjks, openpyxl, pyzipper | Ja |
| PSF | pywin32 | Ja |

**Risiko:** PyMuPDF (AGPL v3) und extract-msg (GPL v3) haben Copyleft-Lizenzen. Bei Distribution als Closed-Source-EXE muss die Lizenz-Kompatibilitaet geprueft werden.

**Status:** UNVERIFIZIERT — Keine Lizenz-Analyse im Projekt dokumentiert.

## 10.2 Python-Dependencies (Entwicklung)

### `requirements-dev.txt`

| Package | Versionierung | Lizenz |
|---------|--------------|--------|
| `pytest>=7.0.0` | Minimum | MIT |
| `ruff>=0.1.0` | Minimum | MIT |

**Evidenz:** `requirements-dev.txt` (Root)

## 10.3 PHP-Dependencies

### Manuell verwaltete Libraries

| Library | Version | Ort | Lizenz |
|---------|---------|-----|--------|
| PHPMailer | v6.9.3 | `api/lib/PHPMailer/` (3 Dateien) | LGPL v2.1 |

**Evidenz:** `BiPro-Webspace Spiegelung Live/api/lib/PHPMailer/`

### Fehlende Dependency-Management-Tools

| Aspekt | IST-Zustand |
|--------|-------------|
| Composer | **Nicht vorhanden** |
| `composer.json` | **Nicht vorhanden** |
| `composer.lock` | **Nicht vorhanden** |
| Automatische Updates | **Nicht vorhanden** |

**Anmerkung:** Alle PHP-Libraries sind manuell in `api/lib/` platziert. Es gibt kein automatisches Dependency-Management fuer PHP.

## 10.4 Lockfiles

| Lockfile | Vorhanden | Evidenz |
|----------|-----------|---------|
| `requirements.txt` (pinned) | **Nein** (nur `>=` Versionen) | `requirements.txt` |
| `pip freeze` / `pip.lock` | **Nein** | Nicht im Repository |
| `composer.lock` | **Nein** | Nicht im Repository |
| `package-lock.json` | N/A (kein Node.js) | - |

**Risiko:** Ohne Lockfiles ist der Build nicht deterministisch. Verschiedene Installationszeitpunkte koennen unterschiedliche Versionen produzieren. Dies ist ein Supply-Chain-Risiko.

## 10.5 Dependency-Audit

### pip-audit

**Status:** Nicht ausgefuehrt. `pip-audit` ist nicht in den Dependencies.

### npm audit

**Status:** N/A (kein Node.js-Projekt)

### composer audit

**Status:** N/A (kein Composer konfiguriert)

### Bekannte Schwachstellen

**Status:** UNVERIFIZIERT — Kein automatisierter Dependency-Audit vorhanden. Keine CVE-Pruefung dokumentiert.

## 10.6 Transitive Dependencies

### Python

Die `>=` Versionierung bedeutet, dass transitive Dependencies ebenfalls nicht fixiert sind.

Beispiel: `PySide6>=6.6.0` zieht `shiboken6`, `PySide6-Essentials`, `PySide6-Addons` mit jeweils eigenen Versionen nach.

**Status:** UNVERIFIZIERT — Keine Analyse der transitiven Dependencies.

### PHP

PHPMailer v6.9.3 hat keine externen Dependencies (standalone).

## 10.7 Update-Praxis

| Aspekt | IST-Zustand |
|--------|-------------|
| Automatische Dependency-Updates | **Nicht vorhanden** (kein Dependabot, Renovate, etc.) |
| Manuelle Updates | UNVERIFIZIERT (kein Prozess dokumentiert) |
| Security-Advisories | **Nicht abonniert** |
| PHP-Version-Updates | Strato-Managed (nicht kontrollierbar) |
| Python-Version-Updates | Manuell (Build-Umgebung) |

## 10.8 Zusammenfassung

| Kategorie | Anzahl | Status |
|-----------|--------|--------|
| Python Produktions-Dependencies | 10 | Alle `>=`, keine Lockfile |
| Python Dev-Dependencies | 2 | Alle `>=`, keine Lockfile |
| PHP Libraries | 1 (PHPMailer) | Manuell verwaltet, v6.9.3 |
| Lockfiles | 0 | Keine vorhanden |
| Dependency-Audits | 0 | Nie ausgefuehrt |
| Lizenz-Konflikte (potentiell) | 2 | PyMuPDF (AGPL), extract-msg (GPL) |
