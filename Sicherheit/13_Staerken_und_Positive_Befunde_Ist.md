# 13 — Staerken und Positive Befunde (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## Kategorie: Datenbank-Sicherheit

### POS-001: Prepared Statements durchgaengig

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Nahezu alle SQL-Queries verwenden PDO Prepared Statements mit Parameter-Binding. Die `Database` Klasse erzwingt parameterisierte Queries. Prepared-Statement-Emulation ist deaktiviert (`PDO::ATTR_EMULATE_PREPARES => false`). |
| Evidenz | `api/lib/db.php:21` (Emulation off), `api/lib/db.php:35, 44, 54, 63` (prepare+execute). Alle Endpoint-Dateien verwenden `Database::query()` mit `$params`. |
| Abdeckung | ~98% (2 Dateien mit Int-Cast + Interpolation fuer LIMIT/OFFSET) |

### POS-002: UTF-8 Charset (utf8mb4)

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Die Datenbank-Verbindung verwendet `utf8mb4`, was Unicode vollstaendig unterstuetzt und Encoding-basierte Injection-Angriffe verhindert. |
| Evidenz | `api/lib/db.php:22` |

---

## Kategorie: Authentifizierung

### POS-003: Bcrypt mit Cost Factor 12

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Benutzer-Passwoerter werden mit bcrypt (Cost 12) gehasht. Dies bietet starken Schutz gegen Brute-Force auf gestohlene Hashes. |
| Evidenz | `api/lib/crypto.php:110-113` |

### POS-004: Timing-safe Vergleiche

| Aspekt | Detail |
|--------|--------|
| Beschreibung | JWT-Signaturen, API-Keys und Passwort-Verifikationen verwenden `hash_equals()` fuer timing-safe Vergleiche. Dies verhindert Timing-Side-Channel-Angriffe. |
| Evidenz | `api/lib/jwt.php:50` (JWT), `api/incoming_scans.php:67` (API-Key), `api/lib/crypto.php:119` (bcrypt via password_verify). |

### POS-005: Timing-Schutz bei unbekanntem User

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Bei Login mit unbekanntem Benutzernamen wird eine Dummy-Passwort-Verifikation durchgefuehrt. Dies verhindert Username-Enumeration ueber Antwortzeiten. |
| Evidenz | `api/auth.php:74` |

### POS-006: Server-seitige Session-Validierung

| Aspekt | Detail |
|--------|--------|
| Beschreibung | JWT-Tokens werden nicht nur client-seitig validiert, sondern auch gegen eine server-seitige `sessions` Tabelle geprueft. Bei jedem API-Call wird die Session-Gueltigkeit und der User-Status (is_active, is_locked) neu verifiziert. |
| Evidenz | `api/lib/jwt.php:103-127` |

### POS-007: Session-Invalidierung bei kritischen Aktionen

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Alle Sessions eines Users werden automatisch invalidiert bei: Passwort-Aenderung, Account-Sperrung, Account-Deaktivierung. |
| Evidenz | `api/admin.php:292` (Password), `api/admin.php:324` (Lock), `api/admin.php:375` (Deaktivierung) |

---

## Kategorie: Verschluesselung

### POS-008: AES-256-GCM fuer Credentials

| Aspekt | Detail |
|--------|--------|
| Beschreibung | VU-Credentials und E-Mail-Credentials werden mit AES-256-GCM verschluesselt in der Datenbank gespeichert. GCM bietet Authenticated Encryption (Vertraulichkeit + Integritaet). Random IV (12 Bytes) pro Verschluesselung. |
| Evidenz | `api/lib/crypto.php:9` (AES-256-GCM), `api/lib/crypto.php:20` (Random IV), `api/credentials.php:135`, `api/email_accounts.php:147` |

---

## Kategorie: Datei-Operationen

### POS-009: Atomic File Operations

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Datei-Uploads verwenden ein Staging-Pattern: Dateien werden zunaechst in eine temporaere Datei geschrieben und dann per `rename()` an den Zielort verschoben. Dies verhindert partielle Dateien bei Absturz. |
| Evidenz | `api/documents.php:430-545` (Upload), `api/incoming_scans.php:146-238` (Scan) |

### POS-010: Dateiname-Sanitization und Path-Traversal-Schutz

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Dateinamen werden durchgaengig mit `basename()` und regex-Sanitization gereinigt. Path-Traversal-Zeichen (`../`, `..\\`) werden entfernt. Dies gilt fuer alle Upload-Wege: Dokument-Upload, Scan-Upload, Release-Upload. |
| Evidenz | `api/documents.php:411-412`, `api/incoming_scans.php:115, 376-397`, `src/services/zip_handler.py:279-284`, `src/services/msg_handler.py:133-140` |

### POS-011: SHA256-Hash fuer Duplikat-Erkennung

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Jedes hochgeladene Dokument erhaelt einen SHA256-Hash. Duplikate werden automatisch erkannt und visuell markiert (Warn-Icon in der Tabelle). |
| Evidenz | `api/documents.php:447` (Hash), `api/documents.php:489-513` (Duplikat-Check), `src/ui/archive_boxes_view.py` (UI-Anzeige) |

---

## Kategorie: Zugriffskontrolle

### POS-012: Granulares Permission-System (10 Permissions)

| Aspekt | Detail |
|--------|--------|
| Beschreibung | 10 einzeln zuweisbare Permissions fuer verschiedene Funktionsbereiche. Server-seitige Durchsetzung via `requirePermission()` Middleware. Admin hat automatisch alle Permissions. |
| Evidenz | `api/lib/permissions.php:106-126` |

### POS-013: Admin-Selbstschutz

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Administratoren koennen sich nicht selbst sperren oder loeschen. Dies verhindert versehentlichen vollstaendigen Admin-Verlust. |
| Evidenz | `api/admin.php:313` (Self-Lock-Protection), `api/admin.php:368` (Self-Delete-Protection) |

### POS-014: Permission-Denial-Logging

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Fehlgeschlagene Permission-Pruefungen werden im Activity-Log protokolliert (Status: "denied"). Dies ermoeglicht die Erkennung von unauthorisierten Zugriffsversuchen. |
| Evidenz | `api/lib/permissions.php:111-120` |

---

## Kategorie: Audit und Logging

### POS-015: Umfassendes Activity-Logging

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Nahezu alle sicherheitsrelevanten Aktionen werden in der `activity_log` Tabelle protokolliert: Login-Versuche (Erfolg und Fehlschlag), Dokumenten-Operationen, Admin-Aktionen, VU-Credential-Zugriffe, AI-Key-Zugriffe. Jeder Eintrag enthaelt IP-Adresse und User-Agent. |
| Evidenz | `api/lib/activity_logger.php`, Nutzung in allen Endpoint-Dateien |

### POS-016: Non-Blocking Audit-Logging

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Das Activity-Logging ist non-blocking implementiert: Fehler im Logging verhindern nicht die eigentliche Operation. Dies stellt die Verfuegbarkeit sicher. |
| Evidenz | `api/lib/activity_logger.php:56-59` (try/catch, error_log) |

---

## Kategorie: Auto-Update

### POS-017: SHA256-Verifikation fuer Installer

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Heruntergeladene Installer-EXEs werden vor der Ausfuehrung mit SHA256 verifiziert. Bei Hash-Mismatch wird die Datei geloescht und die Installation abgebrochen. |
| Evidenz | `src/services/update_service.py:164-174` |

---

## Kategorie: BiPRO-Integration

### POS-018: XML-Escaping in SOAP-Requests

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Alle Benutzereingaben (Username, Password, Consumer-ID, Shipment-ID) werden vor dem Einfuegen in SOAP-XML per `_escape_xml()` escaped. Die Funktion deckt 5 XML-Entities ab (&, <, >, ", '). |
| Evidenz | `src/bipro/transfer_service.py:531-538` (_escape_xml), Nutzung in `transfer_service.py:549-550, 567-568, 754, 850, 863, 1243, 1257` |

### POS-019: TLS-Verifikation aktiv

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Alle HTTPS-Verbindungen (API, BiPRO, OpenRouter, Updates) verwenden `verify=True` als Standard. TLS-Zertifikate werden gegen das System-CA-Bundle verifiziert. |
| Evidenz | `src/api/client.py:253` (API), `src/bipro/transfer_service.py:262` (BiPRO), `src/services/update_service.py:144` (Updates) |

### POS-020: PDF-Magic-Byte-Validierung

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Nach MTOM-Extraktion wird geprueft ob Dateien mit Content-Type `application/pdf` tatsaechlich `%PDF` Magic-Bytes enthalten. Warnung bei Diskrepanz. |
| Evidenz | `src/bipro/transfer_service.py` (Post-MTOM-Validation) |

---

## Kategorie: Scan-Upload (Power Automate)

### POS-021: Timing-safe API-Key-Vergleich

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Der Scan-Upload-Endpoint verwendet `hash_equals()` fuer den API-Key-Vergleich. Dies verhindert Timing-basierte Key-Extraktion. |
| Evidenz | `api/incoming_scans.php:67` |

### POS-022: MIME-Whitelist und Base64-Strict

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Scan-Uploads werden gegen eine MIME-Whitelist (PDF, JPG, PNG) geprueft. Base64-Dekodierung im Strict-Modus lehnt ungueltige Eingaben ab. |
| Evidenz | `api/incoming_scans.php:111-112` (MIME), `api/incoming_scans.php:122` (Base64 strict) |

---

## Kategorie: Konfiguration

### POS-023: config.php doppelt geschuetzt

| Aspekt | Detail |
|--------|--------|
| Beschreibung | Die sensible `config.php` ist durch drei Schichten geschuetzt: (1) `.gitignore` schliesst sie aus dem Repository aus, (2) Root-.htaccess blockiert HTTP-Zugriff, (3) API-.htaccess blockiert HTTP-Zugriff zusaetzlich. |
| Evidenz | `.gitignore:119`, `BiPro-Webspace Spiegelung Live/.htaccess:11-14`, `api/.htaccess:35-38` |

### POS-024: display_errors deaktiviert

| Aspekt | Detail |
|--------|--------|
| Beschreibung | PHP `display_errors` ist in der Produktion deaktiviert. Fehlermeldungen werden nicht an den Client gesendet. Exception-Handler geben generische Fehlermeldungen zurueck. |
| Evidenz | `api/config.php:13` (display_errors=0), `api/index.php:203-209` (generische Fehler) |

---

## Kategorie: SmartScan

### POS-025: Idempotenz-Schutz gegen Doppelversand

| Aspekt | Detail |
|--------|--------|
| Beschreibung | SmartScan-Versand verwendet eine `client_request_id` zur Idempotenz-Pruefung. Innerhalb eines 10-Minuten-Fensters wird der gleiche Request nicht zweimal ausgefuehrt. |
| Evidenz | `api/smartscan.php:380-398` |

### POS-026: E-Mail-Credentials verschluesselt

| Aspekt | Detail |
|--------|--------|
| Beschreibung | SMTP/IMAP-Credentials werden mit AES-256-GCM verschluesselt in der Datenbank gespeichert und nur bei Bedarf entschluesselt. |
| Evidenz | `api/email_accounts.php:147` (encrypt), `api/email_accounts.php:313, 423` (decrypt bei Nutzung) |

---

## Statistik

| Kategorie | Anzahl Positive Befunde |
|-----------|------------------------|
| Datenbank-Sicherheit | 2 |
| Authentifizierung | 5 |
| Verschluesselung | 1 |
| Datei-Operationen | 3 |
| Zugriffskontrolle | 3 |
| Audit und Logging | 2 |
| Auto-Update | 1 |
| BiPRO-Integration | 3 |
| Scan-Upload | 2 |
| Konfiguration | 2 |
| SmartScan | 2 |
| **Gesamt** | **26** |
