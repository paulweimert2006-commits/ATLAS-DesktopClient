# 09 — Logging, Auditing, Monitoring (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 9.1 Server-seitiges Logging

### Activity-Logger (`api/lib/activity_logger.php`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Implementierung | Zentrale `ActivityLogger` Klasse | `api/lib/activity_logger.php` |
| Storage | MySQL `activity_log` Tabelle | `api/lib/activity_logger.php:45-55` |
| Non-Blocking | Logging-Fehler blockieren nicht die Operation | `api/lib/activity_logger.php:56-59` |

**Geloggte Felder:**
| Feld | Inhalt | Evidenz |
|------|--------|---------|
| `user_id` | Authentifizierter User (nullable) | Zeile 28 |
| `username` | Benutzername | Zeile 29 |
| `action_category` | auth, document, bipro, vu_connection, gdv, admin, system, ai | Zeile 30 |
| `action` | Spezifische Aktion (login, upload, download, delete, etc.) | Zeile 31 |
| `entity_type` | document, user, vu_connection, shipment, etc. | Zeile 32 |
| `entity_id` | ID des betroffenen Objekts | Zeile 33 |
| `description` | Menschenlesbare Beschreibung | Zeile 34 |
| `details` | Strukturierte Details (JSON) | Zeile 35 |
| `ip_address` | `$_SERVER['REMOTE_ADDR']` | Zeile 42 |
| `user_agent` | Truncated auf 512 Zeichen | Zeile 43 |
| `status` | success, error, denied | Zeile 37 |
| `duration_ms` | Dauer der Operation | Zeile 38 |
| `created_at` | Zeitstempel | Automatisch |

### Geloggte Aktionen nach Kategorie

| Kategorie | Geloggte Aktionen | Evidenz |
|-----------|-------------------|---------|
| `auth` | login_success, login_failed (username, ip, reason), logout, token_verify | `api/auth.php` |
| `document` | upload, download, delete, move, archive, unarchive, color_change, rename, classify, file_replaced | `api/documents.php` |
| `admin` | user_create, user_update, user_lock, user_unlock, user_delete, password_change | `api/admin.php` |
| `system` | session_kill, session_kill_all | `api/sessions.php` |
| `ai` | ai_key_access | `api/ai.php:47-55` |
| `bipro` | shipment_create, shipment_list | `api/shipments.php` |
| `vu_connection` | credential_access, vu_create, vu_update, vu_delete | `api/credentials.php` |
| `smartscan` | job_created, email_sent | `api/smartscan.php` |

### PHP Error-Logging

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| `error_log()` | Verwendet fuer Fehler und Warnungen | Diverse PHP-Dateien |
| `display_errors` | Deaktiviert (`0`) | `api/config.php:13` |
| `DEBUG_MODE` | `false` in Produktion | `api/config.php` |
| Log-Ziel | UNVERIFIZIERT (Strato Standard-PHP-Error-Log) | Shared Hosting |

## 9.2 Client-seitiges Logging (Python)

### Logging-Setup (`src/main.py:49-79`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Framework | Python `logging` (Standard-Library) | `src/main.py:49` |
| Level | `INFO` (Standard) | `src/main.py:55` |
| Format | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | `src/main.py:57` |
| Console-Handler | Ja | `src/main.py:59-61` |
| File-Handler | `RotatingFileHandler` | `src/main.py:64-71` |
| Rotation | 5 MB Max, 3 Backups | `src/main.py:67-68` |
| Encoding | UTF-8 | `src/main.py:69` |
| Log-Datei | `logs/bipro_gdv.log` | `src/main.py:52` |

### Log-Inhalte nach Modul

| Modul | Log-Level | Inhalte | PII-Risiko |
|-------|-----------|---------|------------|
| `transfer_service.py` | DEBUG/INFO/WARN/ERROR | Token-Details, MTOM-Parsing, Requests | **Ja** (Versicherungsschein-Nr bei DEBUG) |
| `bipro_view.py` | INFO/WARN/ERROR | Download-Progress, Fehler | Niedrig |
| `archive_boxes_view.py` | INFO/WARN/ERROR | Processing, Cache, SmartScan | Niedrig |
| `document_processor.py` | INFO/ERROR | Klassifikation, Kosten | Niedrig |
| `openrouter.py` | INFO/WARN/ERROR | API-Calls, Klassifikation | Mittel (Dokumentnamen) |
| `data_cache.py` | INFO/DEBUG | Cache-Operationen | Niedrig |
| `update_service.py` | INFO/ERROR | Update-Check, Download | Niedrig |
| `client.py` | INFO/WARN/ERROR | API-Requests, Retries | Mittel (URLs mit IDs) |

### PII in Logs (Potentielle Befunde)

| Datei | PII-Typ | Log-Level | Evidenz |
|-------|---------|-----------|---------|
| `src/bipro/transfer_service.py:1147` | Versicherungsschein-Nr | DEBUG | Metadata-Extraktion aus XML |
| `src/bipro/transfer_service.py:616-617` | STS-Response (500 Zeichen) | DEBUG/ERROR | Koennte Credentials enthalten |
| `src/bipro/transfer_service.py:814` | Transfer-Response (2000 Zeichen) | DEBUG | Koennte Vertragsdaten enthalten |

**Anmerkung:** Im Standard-Level `INFO` werden diese DEBUG-Meldungen nicht ausgegeben. Bei Aktivierung von DEBUG-Logging koennten PII-Daten in Log-Dateien landen.

## 9.3 Audit-Trails

### Login-Versuche

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Erfolgreiche Logins | Geloggt (user_id, ip, user_agent) | `api/auth.php:108-110` |
| Fehlgeschlagene Logins | Geloggt (username, ip, reason) | `api/auth.php:77-85, 91-97, 101-102` |
| Login-Gruende | unknown_user, account_inactive, account_locked, invalid_password | `api/auth.php` |
| IP-Tracking | Ja (`$_SERVER['REMOTE_ADDR']`) | `api/lib/activity_logger.php:42` |

### Datenaenderungen

| Aenderungstyp | Geloggt | Details |
|---------------|---------|---------|
| Dokument-Upload | Ja | Filename, Size, Box, Source-Type |
| Dokument-Download | Ja | Document-ID |
| Dokument-Loeschung | Ja | Document-ID, Filename |
| Dokument-Verschieben | Ja | Source-Box, Target-Box (pro Dokument) |
| Dokument-Archivierung | Ja | Bulk oder Einzel |
| Dokument-Farbmarkierung | Ja | Color-Value |
| Dokument-Umbenennung | Ja | Old/New Name |
| KI-Klassifikation | Ja | Box-Type, Confidence, Model |
| PDF-Datei-Ersetzung | Ja | Old/New Hash, Old/New Size |

### Admin-Aktionen

| Aktion | Geloggt | Details |
|--------|---------|---------|
| User-Erstellung | Ja | Username, Account-Type, Permissions |
| User-Aenderung | Ja | Changed Fields |
| User-Sperrung | Ja | Target-User-ID |
| User-Entsperrung | Ja | Target-User-ID |
| User-Deaktivierung | Ja | Target-User-ID |
| Passwort-Aenderung | Ja | Target-User-ID (nicht das Passwort) |
| Session-Kill | Ja | Session-ID, Target-User |
| Permission-Aenderung | Ja | User-ID, Permissions |

## 9.4 Monitoring

| Aspekt | IST-Zustand |
|--------|-------------|
| Server-Monitoring | **Nicht vorhanden** (kein Uptime-Monitoring) |
| APM (Application Performance Monitoring) | **Nicht vorhanden** |
| Error-Alerting | **Nicht vorhanden** (keine Benachrichtigung bei Fehlern) |
| Log-Aggregation | **Nicht vorhanden** (Logs nur lokal) |
| Metriken-Sammlung | **Nicht vorhanden** |
| Health-Check | Vorhanden (`GET /status`), aber nicht aktiv ueberwacht |
| Security-Monitoring | **Nicht vorhanden** (keine Anomalie-Erkennung) |
| Brute-Force-Detection | **Nicht vorhanden** |

## 9.5 Log-Retention

| Log-Typ | Retention | Evidenz |
|---------|-----------|---------|
| Python Client-Logs | 5 MB * 4 = max. 20 MB (Rotation) | `src/main.py:67-68` |
| PHP Error-Logs | UNVERIFIZIERT (Strato-Standard) | Shared Hosting |
| Activity-Log (DB) | **Unbegrenzt** (kein Cleanup) | Keine Retention-Policy in Code |
| Session-Log (DB) | Abgelaufene Sessions bleiben bestehen | Kein Cleanup-Job |

**Risiko:** Die `activity_log` Tabelle waechst unbegrenzt. Bei hoher Aktivitaet koennte dies zu Performance-Problemen fuehren. Ausserdem enthaelt sie IP-Adressen und User-Agents, was DSGVO-relevant sein koennte.
