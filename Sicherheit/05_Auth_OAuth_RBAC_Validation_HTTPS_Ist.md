# 05 — Auth, OAuth, RBAC, Validation, HTTPS (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 5.1 Authentication

### Login-Mechanismus

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Methode | Username + Passwort via HTTPS POST | `api/auth.php:67-70` |
| Passwort-Hashing | bcrypt, Cost Factor 12 | `api/lib/crypto.php:110-113` |
| Passwort-Verifikation | `password_verify()` (bcrypt-native) | `api/lib/crypto.php:119` |
| Timing-Schutz | Dummy-Verify bei unbekanntem User | `api/auth.php:74` |
| Account-Status-Pruefung | `is_active` und `is_locked` validiert | `api/auth.php:90-98` |
| Fehlgeschlagene Logins | Activity-Log mit IP und User-Agent | `api/auth.php:77-85, 91-92, 95-97, 101-102` |
| Rate-Limiting | **Nicht vorhanden** | Kein Code gefunden |
| Account-Lockout | **Nicht automatisch** (nur manuell durch Admin) | `api/admin.php` (Lock-Funktion) |
| Passwort-Mindestlaenge | 8 Zeichen | `api/admin.php:180, 284` |
| Passwort-Komplexitaet | **Nicht vorhanden** (nur Laenge) | `api/admin.php:180` |

### Token-Handling (JWT)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Algorithmus | HMAC-SHA256 (HS256) | `api/lib/jwt.php:15, 26` |
| Signatur-Verifikation | `hash_equals()` (timing-safe) | `api/lib/jwt.php:50` |
| Expiry | 8 Stunden (28800 Sekunden) | `api/config.php` (JWT_EXPIRY) |
| Refresh-Mechanismus | **Nicht vorhanden** (Token laeuft ab, Re-Login noetig) | Kein Refresh-Endpoint |
| Token-Extraktion | Bearer Token aus Authorization Header | `api/lib/jwt.php:72-81` |
| Token-Revocation | Server-seitig via Session-Tabelle | `api/lib/jwt.php:103-127` |
| Token-Speicherung (Client) | Im Memory + optional Klartext-Datei | `src/api/auth.py:295-305` |
| Token-Datei | `~/.bipro_gdv_token.json` | `src/api/auth.py:60-61` |
| Token-Datei-Permissions | **Keine expliziten Permissions gesetzt** | `src/api/auth.py:302, 311` |

### Session-Management

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Session-Storage | MySQL `sessions` Tabelle | `api/lib/jwt.php:103-127` |
| Session-Inhalt | Token-Hash, User-ID, IP, User-Agent, Expiry | `api/lib/jwt.php:154-189` |
| Token-Hash | SHA256 des JWT-Tokens | `api/lib/jwt.php:102, 155` |
| Session-Validierung | Bei jedem API-Call (JWT + Session-Check) | `api/lib/jwt.php:103-109` |
| User-Status-Recheck | Bei jedem API-Call (is_active, is_locked) | `api/lib/jwt.php:117-127` |
| Session-Invalidierung | Bei Logout, Password-Change, Lock, Deaktivierung | `api/auth.php`, `api/admin.php:292, 324, 375` |
| Admin Session-Kill | Einzeln und Bulk (alle Sessions eines Users) | `api/sessions.php` |
| Activity-Throttle | Session-Activity nur alle 60s aktualisiert | `api/lib/jwt.php:131` |

## 5.2 OAuth

**Status:** OAuth ist NICHT implementiert. Es gibt keinen OAuth-Provider, keinen OAuth-Flow und keine OAuth-Tokens.

## 5.3 RBAC (Role-Based Access Control)

### Rollen-Modell

| Rolle | Definition | Evidenz |
|-------|-----------|---------|
| `admin` | Vollzugriff (alle Permissions automatisch) | `api/lib/permissions.php:19-21` |
| `user` | Granulare Permissions (einzeln zuweisbar) | `api/lib/permissions.php:23-28` |

### Permissions (10 Stueck)

| Permission | Schuetzt | Evidenz |
|------------|----------|---------|
| `vu_connections_manage` | VU-Verbindungen CRUD, Credential-Entschluesselung | `api/credentials.php:23` |
| `bipro_fetch` | BiPRO-Lieferungen abrufen | `api/shipments.php:19` |
| `documents_manage` | Dokument-Update, Move, Archive, Replace, Colors | `api/documents.php` |
| `documents_delete` | Dokument-Loeschung | `api/documents.php` |
| `documents_upload` | Dokument-Upload | `api/documents.php` |
| `documents_download` | Dokument-Download | `api/documents.php` |
| `documents_process` | KI-Verarbeitung, AI-Key-Abruf | `api/ai.php:17` |
| `documents_history` | Dokument-Historie einsehen | `api/documents.php` |
| `gdv_edit` | GDV-Datensaetze bearbeiten | `api/gdv.php:22-32` |
| `smartscan_send` | SmartScan E-Mail-Versand | `api/smartscan.php:86-98` |

### Permission-Durchsetzung

| Ort | Methode | Evidenz |
|-----|---------|---------|
| PHP-Server | `requirePermission($key)` Middleware | `api/lib/permissions.php:106-126` |
| PHP-Server | `requireAdmin()` Middleware | `api/lib/permissions.php:128+` |
| Python-Client | `has_permission()` auf User-Objekt (UI-Guards) | `src/api/auth.py` (User-Model) |

**Anmerkung:** Die Client-seitigen Permission-Guards (deaktivierte Buttons) sind reine UI-Komfortfunktionen. Die eigentliche Durchsetzung erfolgt server-seitig.

### Permission-Speicherung

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| DB-Tabelle | `user_permissions` (user_id, permission_key) | `api/lib/permissions.php:23-28` |
| Vergabe | Nur durch Admin (POST /admin/users) | `api/admin.php` |
| Caching | **Nicht vorhanden** (DB-Query pro Check) | `api/lib/permissions.php:23-28` |
| Denial-Logging | Permission-Verweigerungen werden geloggt | `api/lib/permissions.php:111-120` |

## 5.4 Validation (Server-seitig)

### Input-Validierung in PHP

| Endpoint | Validierung | Evidenz |
|----------|------------|---------|
| `auth/login` | Username + Password Pflichtfelder | `api/auth.php:67-70` |
| `documents` Upload | Dateiname sanitized, Groessencheck | `api/documents.php:403-412` |
| `incoming-scans` | MIME-Whitelist, Base64-strict, Filename-Sanitize, Groesse | `api/incoming_scans.php:103-138` |
| `admin/users` | Username-Laenge, Passwort-Mindestlaenge (8), account_type Whitelist | `api/admin.php:178-189` |
| `admin/passwords` | Typ-Whitelist (pdf/zip), Pflichtfelder | `api/passwords.php:127-129` |
| `releases` Upload | Version SemVer-Regex, Dateigroesse, Duplikat-Check | `api/releases.php:279-310` |

### SQL-Injection-Schutz

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| PDO Prepared Statements | Standard fuer alle Queries | `api/lib/db.php:35, 44, 54, 63` |
| Emulation deaktiviert | `PDO::ATTR_EMULATE_PREPARES => false` | `api/lib/db.php:21` |
| LIMIT/OFFSET | `(int)` Cast in 2 Dateien, direkte Interpolation | `api/gdv.php:255-263`, `api/activity.php:108-127` |
| Alle anderen Dateien | Korrekte Parameterisierung | Alle PHP-Endpoints |

**Detail zu LIMIT/OFFSET:**
- `gdv.php:255-263`: `$limit = min((int)($_GET['limit'] ?? 1000), 5000)` → `LIMIT $limit OFFSET $offset` (Interpolation nach Int-Cast)
- `activity.php:108-127`: `$perPage = min(200, max(1, (int)($_GET['per_page'] ?? 50)))` → `LIMIT {$perPage} OFFSET {$offset}` (Interpolation nach Int-Cast)
- Andere Dateien (smartscan.php, processing_history.php, email_accounts.php, xml_index.php) verwenden `LIMIT ? OFFSET ?` mit Parametern

## 5.5 HTTPS / TLS

### Server-seitig

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| HTTPS | Ja (acencia.info) | Domain-Konfiguration |
| HTTP → HTTPS Redirect | UNVERIFIZIERT (Strato-Konfiguration) | Nicht im Code sichtbar |
| HSTS-Header | **Nicht gesetzt** | Kein `Strict-Transport-Security` in PHP |
| TLS-Version | UNVERIFIZIERT (Strato-Managed) | Shared Hosting, nicht konfigurierbar |
| Zertifikat | UNVERIFIZIERT (Strato-Managed) | Vermutlich Let's Encrypt |

### Client-seitig (Python)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| TLS-Verifikation (API) | `verify=True` (Standard) | `src/api/client.py:253, 289, 324` |
| TLS-Verifikation (BiPRO) | `verify=True` | `src/bipro/transfer_service.py:262` |
| TLS-Verifikation (Update) | `verify=True` | `src/services/update_service.py:144` |
| Certificate-Pinning | **Nicht vorhanden** | Kein Code |
| Proxy-Einstellung (BiPRO) | Komplett deaktiviert | `src/bipro/transfer_service.py:72-75, 264` |
| CA-Bundle | System-Standard | Kein Custom-Bundle |
| TLS-Version-Restriction | Keine (System-Default) | Kein Code |
| Cipher-Restriction | Keine (System-Default) | Kein Code |

### MySQL-Verbindung

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Verschluesselung | UNVERIFIZIERT | Kein `ssl` Parameter in PDO-Verbindung (`api/lib/db.php`) |
| TLS-Erzwingung | UNVERIFIZIERT | Strato Shared Hosting, DB-Server intern |

## 5.6 Security Headers

| Header | IST-Zustand | Evidenz |
|--------|-------------|---------|
| `Strict-Transport-Security` | **Nicht gesetzt** | Kein `header()` in PHP |
| `X-Frame-Options` | **Nicht gesetzt** | Kein `header()` in PHP |
| `X-Content-Type-Options` | **Nicht gesetzt** | Kein `header()` in PHP |
| `Content-Security-Policy` | **Nicht gesetzt** | Kein `header()` in PHP |
| `X-XSS-Protection` | **Nicht gesetzt** | Kein `header()` in PHP |
| `Referrer-Policy` | **Nicht gesetzt** | Kein `header()` in PHP |
| `Content-Type` | `application/json; charset=utf-8` (API-Responses) | `api/lib/response.php:13` |
| `Cache-Control` | `no-cache, must-revalidate` (nur bei Downloads) | `api/documents.php:624` |

## 5.7 CORS

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| OPTIONS Preflight | Gibt HTTP 200 zurueck | `api/index.php:14-17` |
| `Access-Control-Allow-Origin` | **Nicht gesetzt** | Kein CORS-Header in PHP |
| `Access-Control-Allow-Methods` | **Nicht gesetzt** | Kein CORS-Header in PHP |
| `Access-Control-Allow-Headers` | **Nicht gesetzt** | Kein CORS-Header in PHP |
| `Access-Control-Allow-Credentials` | **Nicht gesetzt** | Kein CORS-Header in PHP |

**Anmerkung:** Da die App ein Desktop-Client ist (nicht Browser-basiert), sind CORS-Header fuer den Hauptanwendungsfall nicht relevant. Die fehlende Konfiguration ist primaer fuer den Fall relevant, dass die API von einer Web-Anwendung genutzt wuerde.
