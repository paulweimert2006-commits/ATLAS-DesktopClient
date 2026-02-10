# 07 — Server, Deployment, Webspace (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 7.1 Webserver-Konfiguration

### Hosting

| Aspekt | IST-Zustand |
|--------|-------------|
| Hoster | Strato |
| Typ | Shared Hosting (kein Root-Zugriff) |
| Webserver | Apache (vermutet, .htaccess funktioniert) |
| PHP-Version | 7.4+ (UNVERIFIZIERT — nur aus Doku) |
| Domain | `acencia.info` |
| HTTPS | Ja (UNVERIFIZIERT ob HTTP→HTTPS Redirect erzwungen) |

### .htaccess Konfiguration

#### Root `.htaccess` (`BiPro-Webspace Spiegelung Live/.htaccess`)

| Regel | Wirkung | Evidenz |
|-------|---------|---------|
| `Options -Indexes` | Directory-Listing deaktiviert | Zeile 5 |
| `AddDefaultCharset UTF-8` | UTF-8 Standard-Encoding | Zeile 8 |
| `config.php` Block | Direkter HTTP-Zugriff auf config.php verboten | Zeilen 11-14 |
| Hidden Files Block | Zugriff auf `.`-Dateien verboten | Zeilen 17-20 |

#### API `.htaccess` (`BiPro-Webspace Spiegelung Live/api/.htaccess`)

| Regel | Wirkung | Evidenz |
|-------|---------|---------|
| PHP Upload-Max | 250 MB | Zeilen 6-7 |
| PHP Post-Max | 260 MB | Zeile 8 |
| PHP Execution Time | 600 Sekunden | Zeilen 10-11 |
| PHP Memory Limit | 300 MB | Zeilen 13-14 |
| PHP Max Input Vars | 10000 | Zeilen 16-17 |
| PHP Max Input Time | 300 Sekunden | Zeilen 18-19 |
| RewriteEngine On | URL-Rewriting aktiv | Zeile 22 |
| RewriteRule | Alles nach `index.php` routen | Zeilen 27-32 |
| `config.php` Block | Zusaetzlicher Schutz (doppelt) | Zeilen 35-38 |

### PHP-Konfiguration

#### `.user.ini` (`BiPro-Webspace Spiegelung Live/api/.user.ini`)

| Einstellung | Wert | Evidenz |
|-------------|------|---------|
| `upload_max_filesize` | 250M | Zeile 6 |
| `post_max_size` | 260M | Zeile 8 |
| `max_execution_time` | 600 | Zeile 10 |
| `memory_limit` | 300M | Zeile 12 |
| `max_input_time` | 300 | Zeile 14 |

**Anmerkung:** Die gleichen Limits sind in `.htaccess`, `.user.ini` und `php.ini` definiert (Dreifach-Konfiguration fuer Strato-Kompatibilitaet).

### Fehlende Webserver-Konfiguration

| Aspekt | Status |
|--------|--------|
| Security Headers | **Nicht konfiguriert** (weder in .htaccess noch in PHP) |
| HSTS | **Nicht konfiguriert** |
| CSP | **Nicht konfiguriert** |
| X-Frame-Options | **Nicht konfiguriert** |
| X-Content-Type-Options | **Nicht konfiguriert** |
| Rate-Limiting | **Nicht konfiguriert** (weder mod_ratelimit noch PHP) |
| IP-Whitelisting | **Nicht konfiguriert** (fuer Admin-Endpoints) |
| Fail2Ban / WAF | **Nicht verfuegbar** (Shared Hosting) |

## 7.2 Deployment-Prozess

### Server-Deployment (PHP)

| Aspekt | IST-Zustand |
|--------|-------------|
| Methode | Ordner-Synchronisierung (lokal → Strato FTP) |
| Trigger | Automatisch bei Datei-Aenderung |
| Review-Prozess | **Nicht vorhanden** |
| Staging-Umgebung | **Nicht vorhanden** |
| Rollback | Manuell (Git + Re-Sync) |
| Blue-Green/Canary | **Nicht vorhanden** |
| Downtime | Zero-Downtime (Datei-Replacement) |
| DB-Migrationen | Manuell (PHP-Scripts in `setup/` ausfuehren) |

**Risiko:** Jede lokale Aenderung wird sofort live. Kein Code-Review, kein Test-Gate, kein Staging.

**Evidenz:** `AGENTS.md` Zeile 10-21

### Desktop-Deployment

| Aspekt | IST-Zustand |
|--------|-------------|
| Build-Tool | PyInstaller + Inno Setup | 
| Build-Script | `build.bat` |
| Hash-Verifikation | SHA256-Datei wird generiert |
| Code-Signing | **Nicht vorhanden** |
| Distribution | Admin laed EXE via Admin-Panel hoch |
| Auto-Update | Ja (optional/pflicht via UpdateService) |

**Evidenz:** `build.bat`, `src/services/update_service.py`

## 7.3 Umgebungs-Trennung

| Umgebung | Vorhanden | Details |
|----------|-----------|---------|
| Development | Ja | Lokale Python-Umgebung, `python run.py` |
| Testing | Teilweise | `scripts/run_checks.py`, keine Integration-Tests |
| Staging | **Nein** | Kein Staging-Server |
| Production | Ja | Strato Webspace (direkt synchronisiert) |

**Risiko:** Es gibt keine Trennung zwischen Entwicklung und Produktion fuer den Server-Code. Lokale Aenderungen werden direkt live.

## 7.4 Datei-Storage auf Server

| Verzeichnis | Zweck | Web-Zugaenglich | Sync |
|-------------|-------|-----------------|------|
| `api/` | PHP-Code | Ja (via Router) | Ja |
| `dokumente/` | Dokument-Storage | Nein (nur via API) | Nein |
| `releases/` | Installer-EXEs | Nein (nur via API) | Nein |
| `setup/` | DB-Migrationen | Ja (HTTP-zugaenglich!) | Ja |

**Risiko:** Das `setup/` Verzeichnis ist synchronisiert und enthaelt PHP-Migrationsskripte. Diese sind potentiell ueber HTTP aufrufbar, da kein `.htaccess`-Schutz fuer `setup/` existiert.

**Evidenz:** `AGENTS.md` Zeile 10-21, `BiPro-Webspace Spiegelung Live/setup/`

## 7.5 Datenbank-Server

| Aspekt | IST-Zustand |
|--------|-------------|
| Server | `database-5019508812.webspace-host.com` |
| DB-Name | `dbs15252975` |
| Verbindung | PDO (MySQLi-kompatibel) |
| Charset | `utf8mb4` |
| TLS | UNVERIFIZIERT (vermutlich intern bei Strato) |
| Backup | UNVERIFIZIERT (Strato-Managed) |

**Evidenz:** `api/lib/db.php`, `api/config.php` (gitignored)

## 7.6 Error-Handling (Produktion)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| `display_errors` | `0` (deaktiviert) | `api/config.php:13` |
| `DEBUG_MODE` | `false` (Produktion) | `api/config.php` |
| Error-Logging | `error_log()` (PHP default) | Diverse PHP-Dateien |
| Exception-Handling | try/catch im Router mit generischer Fehlermeldung | `api/index.php:203-209` |
| API-Version | Im Health-Check exponiert | `api/index.php:41` |

**Anmerkung:** Die API-Version wird im `/status`-Endpoint zurueckgegeben (`API_VERSION` Konstante). Dies koennte fuer Angreifer nuetzliche Versionsinformationen liefern.
