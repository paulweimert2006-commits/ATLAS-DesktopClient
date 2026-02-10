# 02 — Architektur (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 2.1 Architektur-Ueberblick

Das System besteht aus drei Schichten:

1. **Desktop-App** (Python/PySide6) — Client auf Windows
2. **PHP REST API** (Custom Router) — Strato Shared Hosting
3. **MySQL 8.0** — Strato Datenbank-Server

Zusaetzlich kommuniziert die Desktop-App direkt mit:
4. **BiPRO SOAP-Services** — Versicherer-Endpunkte (Degenia, VEMA, 47 SmartAdmin-VUs)
5. **OpenRouter API** — KI-Klassifikation (GPT-4o/GPT-4o-mini)

## 2.2 Datenfluss-Diagramm

```
Desktop-App (Python/PySide6)
    |
    |-- HTTPS/REST --> PHP API (acencia.info/api/)
    |                     |
    |                     +--> MySQL (database-5019508812.webspace-host.com)
    |                     |
    |                     +--> Dateisystem (dokumente/, releases/)
    |
    |-- HTTPS/SOAP --> BiPRO VU-Endpunkte (Degenia, VEMA, SmartAdmin)
    |                     |
    |                     +--> STS Token Service (BiPRO 410)
    |                     +--> Transfer Service (BiPRO 430)
    |
    |-- HTTPS/REST --> OpenRouter API (KI-Klassifikation)

Externe Systeme:
    Power Automate --> POST /api/incoming-scans (API-Key)
    IMAP-Server <-- PHP Polling (email_accounts.php)
    SMTP-Server <-- PHPMailer (SmartScan-Versand)
```

## 2.3 Schichten-Architektur (Desktop)

### UI Layer
- `src/ui/main_hub.py` — Navigation, Drag&Drop, Close-Schutz
- `src/ui/bipro_view.py` — BiPRO-Datenabruf, Mail-Import
- `src/ui/archive_boxes_view.py` — Dokumentenarchiv, SmartScan
- `src/ui/admin_view.py` — Admin-Panel (10 Panels)
- `src/ui/login_dialog.py` — Login-Dialog
- `src/ui/main_window.py` — GDV-Editor

**Evidenz:** `src/ui/` Verzeichnis

### API Client Layer
- `src/api/client.py` — Base-Client mit JWT, Retry, HTTPS
- `src/api/auth.py` — Login, Token-Refresh, Token-Persistenz
- `src/api/documents.py` — Dokument-CRUD, Bulk-Ops
- `src/api/smartscan.py` — SmartScan + E-Mail-Konten
- `src/api/vu_connections.py` — VU-Verbindungen + Credentials

**Evidenz:** `src/api/` Verzeichnis

### Services Layer
- `src/services/document_processor.py` — KI-Klassifikation
- `src/services/update_service.py` — Auto-Update (Download, Verify, Install)
- `src/services/pdf_unlock.py` — PDF-Entsperrung
- `src/services/zip_handler.py` — ZIP-Entpackung
- `src/services/data_cache.py` — Caching + Auto-Refresh

**Evidenz:** `src/services/` Verzeichnis

### BiPRO Layer
- `src/bipro/transfer_service.py` — SOAP Client (STS + Transfer)
- `src/bipro/bipro_connector.py` — Verbindungsabstraktion
- `src/bipro/rate_limiter.py` — Adaptive Rate Limiter
- `src/api/smartadmin_auth.py` — SmartAdmin-Auth fuer 47 VUs

**Evidenz:** `src/bipro/` Verzeichnis

## 2.4 Schichten-Architektur (Server)

### Router
- `api/index.php` — URL-Routing, Exception-Handling

### Endpoint-Handler
- `api/auth.php` — Login/Logout/Verify
- `api/documents.php` — Dokument-CRUD + Bulk
- `api/gdv.php` — GDV-Records
- `api/credentials.php` — VU-Credentials (verschluesselt)
- `api/admin.php` — User-Verwaltung
- `api/sessions.php` — Session-Management
- `api/smartscan.php` — SmartScan Settings + Send
- `api/email_accounts.php` — E-Mail-Konten + IMAP
- `api/releases.php` — Release-Management
- `api/incoming_scans.php` — Externer Scan-Upload
- `api/passwords.php` — PDF/ZIP-Passwoerter

### Library Layer
- `api/lib/db.php` — PDO-Wrapper mit Prepared Statements
- `api/lib/jwt.php` — JWT Sign/Verify + Session-Check
- `api/lib/crypto.php` — AES-256-GCM + bcrypt
- `api/lib/permissions.php` — RBAC-Middleware
- `api/lib/activity_logger.php` — Audit-Trail
- `api/lib/response.php` — JSON-Response-Helpers

**Evidenz:** `BiPro-Webspace Spiegelung Live/api/` und `api/lib/`

## 2.5 Authentifizierungs-Architektur

```
Client                          Server
  |                               |
  |-- POST /auth/login ---------> |
  |   (username, password)        |
  |                               |-- bcrypt verify
  |                               |-- Session in DB anlegen
  |                               |-- JWT generieren (HS256, 8h)
  |<-- JWT Token + User-Daten --- |
  |                               |
  |-- Bearer {JWT} in Header ---> |
  |                               |-- JWT Signatur pruefen (hash_equals)
  |                               |-- Expiry pruefen
  |                               |-- Session in DB pruefen (aktiv?)
  |                               |-- User-Status pruefen (active, not locked)
  |<-- Response ------------------|
```

**Evidenz:** `api/auth.php`, `api/lib/jwt.php`

## 2.6 Verschluesselungs-Architektur

| Daten | Methode | Ort | Evidenz |
|-------|---------|-----|---------|
| User-Passwoerter | bcrypt (Cost 12) | MySQL | `api/lib/crypto.php:110-113` |
| VU-Credentials | AES-256-GCM (MASTER_KEY) | MySQL | `api/credentials.php:135` |
| E-Mail-Credentials | AES-256-GCM (MASTER_KEY) | MySQL | `api/email_accounts.php:147` |
| JWT-Signatur | HMAC-SHA256 (JWT_SECRET) | HTTP Header | `api/lib/jwt.php:26` |
| PDF/ZIP-Passwoerter | **Klartext** | MySQL | `api/passwords.php:44` |
| Session-Token | SHA256 Hash | MySQL | `api/lib/jwt.php:102` |

## 2.7 Datei-Storage-Architektur

| Storage | Pfad | Zugriff | Evidenz |
|---------|------|---------|---------|
| Dokumente | `dokumente/` auf Server | Nur via API (nicht web-zugaenglich) | `api/documents.php` |
| Releases | `releases/` auf Server | Download via API + offentlich | `api/releases.php` |
| Vorschau-Cache | `%TEMP%/bipro_preview_cache/` lokal | Nur Desktop-App | `src/services/data_cache.py` |
| Zertifikate | `%APPDATA%/ACENCIA ATLAS/certs/` | Nur Desktop-App, unverschluesselt | `src/config/certificates.py:20-30` |
| JWT-Token | `~/.bipro_gdv_token.json` | Nur Desktop-App, Klartext | `src/api/auth.py:295-305` |
| Logs | `logs/bipro_gdv.log` lokal | Nur Desktop-App | `src/main.py:49-79` |

## 2.8 Thread-Architektur (Desktop)

Die Desktop-App nutzt QThread-Worker fuer Hintergrund-Operationen:

| Worker | Datei | Zweck |
|--------|-------|-------|
| `ParallelDownloadManager` | `bipro_view.py` | BiPRO-Downloads (ThreadPoolExecutor, max 10) |
| `MailImportWorker` | `bipro_view.py` | IMAP-Import (ThreadPoolExecutor, max 4) |
| `ProcessingWorker` | `archive_boxes_view.py` | KI-Dokumentenverarbeitung |
| `SmartScanWorker` | `archive_boxes_view.py` | E-Mail-Versand via SmartScan |
| `BoxDownloadWorker` | `archive_boxes_view.py` | Box-Download (ZIP/Ordner) |
| `DropUploadWorker` | `main_hub.py` | Drag&Drop Upload |
| `MultiUploadWorker` | `archive_boxes_view.py` | Button-Upload |
| `UpdateCheckWorker` | `main_hub.py` | Periodischer Update-Check (30 Min) |
| `DelayedCostWorker` | `archive_boxes_view.py` | OpenRouter-Kosten (90s Delay) |

**Thread-Safety:** SharedTokenManager mit Double-Checked Locking (`transfer_service.py`), DataCache mit `threading.Lock()` (`data_cache.py:100-101`).

**Evidenz:** Jeweilige Dateien
