# 01 — Systemuebersicht

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0 ("Der Datenkern.")
**Auditor:** Automatisierter Security Audit (Agent)

---

## 1.1 Projekttyp

| Eigenschaft | Wert |
|-------------|------|
| Typ | Desktop-Anwendung + Server-Backend (Hybrid) |
| Desktop | Python 3.10+ mit PySide6 (Qt6) |
| Server | PHP 7.4+ REST API auf Strato Shared Hosting |
| Datenbank | MySQL 8.0 |
| Packaging | PyInstaller (Windows EXE) |
| Installer | Inno Setup (Silent Install) |

## 1.2 Zweck und Datenklassifikation

**Primaerer Zweck:** Automatisierter BiPRO-Datenabruf von Versicherungsunternehmen, zentrales Dokumentenarchiv, GDV-Datensatz-Editor.

**Verarbeitete Datenarten:**
- Personenbezogene Daten (DSGVO-relevant): Namen, Adressen, Geburtsdaten
- Finanzdaten: IBANs, Bankverbindungen, Versicherungsbeitraege
- Versicherungsdaten: Versicherungsschein-Nummern, Vertragsdaten, Sparten
- Geschaeftsdaten: Courtage-/Provisionsabrechnungen
- Authentifizierungsdaten: BiPRO-Credentials, SMTP/IMAP-Credentials
- Dokumente: PDFs, GDV-Dateien, Excel-Dateien, E-Mail-Anhaenge

**Nutzerkreis:** 2-5 Versicherungsvermittler (internes Team)

## 1.3 Tech-Stack

### Desktop-App (Python)

| Komponente | Bibliothek | Version |
|------------|-----------|---------|
| GUI Framework | PySide6 | >=6.6.0 |
| HTTP Client | requests | >=2.31.0 |
| Kryptographie | cryptography | >=41.0.0 |
| PDF-Verarbeitung | PyMuPDF (fitz) | >=1.23.0 |
| JKS-Zertifikate | pyjks | >=20.0.0 |
| Excel-Lesen | openpyxl | >=3.1.0 |
| MSG-Parsing | extract-msg | >=0.50.0 |
| Windows COM | pywin32 | >=306 |
| ZIP (AES-256) | pyzipper | >=0.3.6 |
| Packaging | pyinstaller | >=6.0.0 |

**Evidenz:** `requirements.txt` (Root)

### Server-API (PHP)

| Komponente | Details |
|------------|---------|
| Sprache | PHP 7.4+ |
| Framework | Kein Framework, Custom Router |
| Datenbank | PDO mit Prepared Statements |
| JWT | Custom-Implementierung (HMAC-SHA256) |
| Verschluesselung | AES-256-GCM (Custom `Crypto` Klasse) |
| E-Mail-Versand | PHPMailer v6.9.3 |
| Hosting | Strato Shared Webspace |

**Evidenz:** `BiPro-Webspace Spiegelung Live/api/lib/` (db.php, jwt.php, crypto.php, PHPMailer/)

### Infrastruktur

| Eigenschaft | Wert |
|-------------|------|
| Domain | `https://acencia.info/` |
| API Base | `https://acencia.info/api/` |
| DB Server | `database-5019508812.webspace-host.com` |
| DB Name | `dbs15252975` |
| Webserver | Apache (Strato Shared Hosting) |
| Sync-Methode | Lokaler Ordner ↔ Strato FTP (Echtzeit) |

**Evidenz:** `AGENTS.md`, Zeile 23-30 (Server-Infrastruktur)

## 1.4 Zielumgebung

| Umgebung | Details |
|----------|---------|
| Entwicklung | Windows 10/11, lokale Python-Umgebung |
| Produktion (Desktop) | Windows 10/11, Inno-Setup-Installer |
| Produktion (Server) | Strato Shared Hosting (kein Root-Zugriff) |
| CI/CD | Nicht vorhanden (manueller Build via `build.bat`) |
| Staging | Nicht vorhanden (direkt auf Produktion) |

## 1.5 Start- und Build-Hinweise

| Aktion | Befehl/Datei |
|--------|-------------|
| App starten | `python run.py` |
| Build (Installer) | `build.bat` (PyInstaller + Inno Setup) |
| Tests | `python scripts/run_checks.py` oder `pytest src/tests/` |
| Version | `VERSION` Datei (aktuell: `1.6.0`) |

**Evidenz:** `run.py`, `build.bat`, `scripts/run_checks.py`, `VERSION`

## 1.6 Live-Synchronisierung (Sicherheitsrelevant)

Der Ordner `BiPro-Webspace Spiegelung Live/` wird in Echtzeit mit dem Strato Webspace synchronisiert.

| Ordner | Synchronisiert | Sicherheitsrelevanz |
|--------|----------------|---------------------|
| `api/` | Ja | PHP-Code wird direkt deployed |
| `dokumente/` | **Nein** | Server-Dokumentenspeicher |
| `releases/` | **Nein** | Installer-EXE-Storage |
| `setup/` | Ja | Migrations-Skripte |

**Risiko:** Jede lokale Aenderung im `api/` Ordner wird sofort live. Kein Review-Prozess, kein Staging.

**Evidenz:** `AGENTS.md`, Zeile 10-21 (Live-Synchronisierung)
