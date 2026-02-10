# 08 — Secrets, Keys, Config (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 8.1 Hardcoded Secrets im Code

### Python-Code

| Ort | Secret-Typ | Wert (Auszug) | Evidenz |
|-----|------------|---------------|---------|
| `src/services/pdf_unlock.py:23-28` | PDF-Passwoerter | `TQMakler37`, `TQMakler2021`, `555469899`, `dfvprovision` | Fallback-Passwoerter im Klartext |
| `src/services/pdf_unlock.py:30-35` | ZIP-Passwoerter | Identische 4 Passwoerter | Fallback-Passwoerter im Klartext |
| `src/api/client.py` | API-Base-URL | `https://acencia.info/api` | Oeffentlich, kein Secret |

**Anmerkung:** Die Passwoerter in `pdf_unlock.py` sind als Fallback gedacht, falls die API nicht verfuegbar ist. Sie werden auch in `AGENTS.md:639` dokumentiert.

### PHP-Code

| Ort | Secret-Typ | Evidenz |
|-----|------------|---------|
| `api/config.php` | DB-Credentials (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`) | Zeilen 19-22 |
| `api/config.php` | `MASTER_KEY` (AES-256-GCM Schluessel) | Zeile 35 |
| `api/config.php` | `JWT_SECRET` (JWT-Signatur) | Zeile 42 |
| `api/config.php` | `OPENROUTER_API_KEY` (externer AI-Dienst) | Zeile 55 |
| `api/config.php` | `SCAN_API_KEY` (Power Automate) | Zeile 63 |

**Schutz:** `config.php` ist per `.gitignore` vom Repository ausgeschlossen und per `.htaccess` vor direktem HTTP-Zugriff geschuetzt (2 Ebenen).

### Dokumentation

| Ort | Secret-Typ | Evidenz |
|-----|------------|---------|
| `AGENTS.md:639` | PDF-Passwoerter namentlich erwaehnt | "Seed-Daten: 4 bekannte PDF-Passwoerter" |
| `AGENTS.md:1268` | Portal-Passwort `ACA555` erwaehnt | Als "funktioniert nicht fuer API" dokumentiert |
| `BIPRO_STATUS.md:35` | Gleiches Portal-Passwort | Debugging-Hinweis |

## 8.2 .env Handling

| Aspekt | IST-Zustand |
|--------|-------------|
| `.env` Dateien | **Nicht vorhanden** |
| `.env.example` | **Nicht vorhanden** |
| Environment Variables | **Nicht verwendet** |
| Secret-Management | Alle Secrets in `config.php` (PHP-Konstanten) |

**Anmerkung:** Das Projekt verwendet keine Environment Variables. Alle Server-Secrets sind in `config.php` als PHP-Konstanten definiert. Diese Datei ist per `.gitignore` ausgeschlossen.

## 8.3 .gitignore Analyse

### Sicherheitsrelevante Ausschluesse

| Pattern | Zweck | Effektiv |
|---------|-------|----------|
| `BiPro-Webspace Spiegelung Live/api/config.php` | DB-Credentials, Master-Key, JWT-Secret, API-Keys | Ja |
| `neuer API KEY/` | API-Key-Dateien | Ja |
| `logs/`, `*.log` | Log-Dateien (koennten PII enthalten) | Ja |
| `Echte daten Beispiel/` | Echte personenbezogene Daten | Ja |
| `bipro_preview_cache/` | Vorschau-Cache (temporaere PDFs) | Ja |
| `outlook_temp_*/` | Outlook-Temp-Dateien | Ja |
| `Output/*.exe` | Build-Artefakte | Ja |

**Evidenz:** `.gitignore` (137 Zeilen)

### Potentielle Luecken

| Risiko | Detail |
|--------|--------|
| `AGENTS.md` im Repository | Enthaelt Passwoerter (`TQMakler37`, etc.) und Architektur-Details |
| `BIPRO_STATUS.md` im Repository | Enthaelt Portal-Passwort-Hinweis (`ACA555`) |
| `degenia_wsdl.xml` im Repository | Enthaelt WSDL-Endpoint-Details |
| `tools/decrypt_iwm_password.py` im Repository | Passwort-Entschluesselungs-Tool |
| `testdata/` im Repository | Enthaelt nur Beispieldaten (kein echtes Risiko lt. Kommentar in .gitignore) |

## 8.4 Zugriffsrechte

### Server-Dateien

| Datei/Ordner | Schutz | Evidenz |
|-------------|--------|---------|
| `config.php` | `.htaccess` Block (2 Ebenen) + `.gitignore` | Root- und API-.htaccess |
| `dokumente/` | Nicht web-zugaenglich (nur via API) | Kein direkter HTTP-Pfad |
| `releases/` | Nicht web-zugaenglich (nur via API) | Kein direkter HTTP-Pfad |
| `setup/` | **Potentiell web-zugaenglich** (synchronisiert, kein .htaccess) | AGENTS.md: "setup ist synchronisiert" |

### Client-Dateien

| Datei/Ordner | Schutz | Evidenz |
|-------------|--------|---------|
| `~/.bipro_gdv_token.json` | **Keine expliziten Permissions** | `src/api/auth.py:302, 311` |
| `%APPDATA%/ACENCIA ATLAS/certs/` | **Keine Verschluesselung** | `src/config/certificates.py:20-30` |
| `%TEMP%/bipro_preview_cache/` | OS-Temp-Verzeichnis | Standard-Permissions |
| `logs/bipro_gdv.log` | Im Projekt-Verzeichnis | Standard-Permissions |

## 8.5 API-Key-Exposition

### OpenRouter API-Key

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Speicherung | In `config.php` auf Server | `api/config.php:55` |
| Abruf | `GET /ai/key` mit `documents_process` Permission | `api/ai.php:17, 58` |
| Uebertragung | Im JSON-Response an Client | `api/ai.php:58` |
| Client-Nutzung | Direkter Aufruf an OpenRouter API | `src/api/openrouter.py` |

**Risiko:** Der API-Key wird an den Desktop-Client uebertragen. Jeder authentifizierte Benutzer mit `documents_process` Permission kann den Key extrahieren und eigenstaendig nutzen.

### Scan API-Key

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Speicherung | In `config.php` auf Server | `api/config.php:63` |
| Nutzung | `X-API-Key` Header bei Scan-Upload | `api/incoming_scans.php:67` |
| Vergleich | `hash_equals()` (timing-safe) | `api/incoming_scans.php:67` |
| Rotation | **Nicht vorgesehen** (statischer Key) | Kein Rotations-Code |

## 8.6 Verschluesselung

### Verschluesselung at Rest

| Daten | Methode | Key | Evidenz |
|-------|---------|-----|---------|
| VU-Credentials | AES-256-GCM | MASTER_KEY (SHA256-Hash) | `api/lib/crypto.php:100-103`, `api/credentials.php:135` |
| E-Mail-Credentials | AES-256-GCM | MASTER_KEY (SHA256-Hash) | `api/email_accounts.php:147` |
| User-Passwoerter | bcrypt (Cost 12) | N/A (Hash) | `api/lib/crypto.php:110` |
| JWT-Signatur | HMAC-SHA256 | JWT_SECRET | `api/lib/jwt.php:26` |
| PDF/ZIP-Passwoerter | **Klartext** | N/A | `api/passwords.php:44` |
| Zertifikate (Client) | **Klartext auf Disk** | N/A | `src/config/certificates.py:203-204` |
| JWT-Token (Client) | **Klartext JSON-Datei** | N/A | `src/api/auth.py:295-305` |

### Key-Derivation

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Methode | `hash('sha256', MASTER_KEY)` | `api/lib/crypto.php:100-103` |
| Key-Rotation | **Nicht vorgesehen** | Kein Rotations-Code |
| Key-Separation | **Nicht vorhanden** (ein Key fuer alle Verschluesselungen) | Gleicher MASTER_KEY |
| HKDF | **Nicht verwendet** | Einfacher SHA256-Hash |

### Verschluesselung in Transit

| Verbindung | Methode | Evidenz |
|-----------|---------|---------|
| Client → PHP API | HTTPS (TLS, verify=True) | `src/api/client.py` |
| Client → BiPRO VUs | HTTPS (TLS, verify=True) | `src/bipro/transfer_service.py:262` |
| Client → OpenRouter | HTTPS | `src/api/openrouter.py` |
| PHP → MySQL | UNVERIFIZIERT | `api/lib/db.php` (kein SSL-Parameter) |
| PHP → SMTP | TLS/SSL (PHPMailer) | `api/smartscan.php` |
| PHP → IMAP | TLS/SSL | `api/email_accounts.php` |

## 8.7 Temporaere Private Keys

| Ort | Typ | Lebensdauer | Cleanup | Evidenz |
|-----|-----|-------------|---------|---------|
| `transfer_service.py` | PEM-Dateien (Private Keys aus PFX) | Session-Dauer | `close()` Methode | `src/bipro/transfer_service.py:342-367, 1300-1313` |

**Risiko:** Unverschluesselte Private Keys werden als temporaere Dateien auf Disk geschrieben. Cleanup erfolgt in `close()`, aber bei Crash/Absturz bleiben die Dateien bestehen.
