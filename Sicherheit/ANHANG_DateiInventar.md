# ANHANG — Datei-Inventar

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## Ignorierte Build-Pfade

Folgende Pfade wurden vom Audit ausgeschlossen (Build-Artefakte):
- `build/`, `dist/`, `__pycache__/`
- `Output/*.exe`
- `node_modules/`, `vendor/`
- `.venv/`, `venv/`

---

## Datei-Inventar

### Root-Verzeichnis

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `run.py` | Code | Entry Point | Hoch | Minimal (importiert src.main) |
| `VERSION` | Config | Zentrale Versionsdatei (1.6.0) | Mittel | Keine Secrets |
| `requirements.txt` | Config | Produktions-Dependencies | Hoch | Supply-Chain-Risiko (>=) |
| `requirements-dev.txt` | Config | Dev-Dependencies (pytest, ruff) | Niedrig | Nur Entwicklung |
| `.gitignore` | Config | Git-Ausschlussregeln | Hoch | Schliesst config.php aus |
| `build.bat` | Build | Haupt-Build-Script (PyInstaller+Inno) | Mittel | Keine Secrets |
| `build_debug.bat` | Build | Debug-Build | Niedrig | - |
| `build_simple.bat` | Build | Einfacher Build | Niedrig | - |
| `0_release.bat` | Build | Release-Workflow | Niedrig | - |
| `TEST_EXE.bat` | Build | EXE-Test | Niedrig | - |
| `release.ps1` | Build | PowerShell Release | Niedrig | - |
| `installer.iss` | Build | Inno Setup Konfiguration | Mittel | Install-Pfade |
| `version_info.txt` | Build | Version-Metadaten | Niedrig | - |
| `AGENTS.md` | Doku | Projekt-Dokumentation | Hoch | Enthaelt Architektur-Details |
| `README.md` | Doku | Projekt-Readme | Niedrig | - |
| `LICENSE.txt` | Doku | Lizenz | Niedrig | - |
| `BUILD_README.md` | Doku | Build-Anleitung | Niedrig | - |
| `RELEASE_HOWTO.md` | Doku | Release-Prozess | Niedrig | - |
| `RELEASE_FEATURES_HISTORY.txt` | Doku | Feature-Historie | Niedrig | - |
| `BIPRO_STATUS.md` | Doku | BiPRO-Integrationsstatus | Mittel | Enthaelt Endpoint-Details |
| `GDV- Daten Dokumentation.txt` | Doku | GDV-Format-Doku | Niedrig | - |
| `degenia_wsdl.xml` | Config | Degenia WSDL | Mittel | Endpoint-Informationen |

### Python Source (`src/`)

#### API Layer (`src/api/`)

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `src/api/client.py` | Code | Base API Client (~514 Zeilen) | Hoch | JWT-Token-Handling, HTTPS, Retry |
| `src/api/auth.py` | Code | Auth Client (~324 Zeilen) | Kritisch | Login, Token-Speicherung, Refresh |
| `src/api/documents.py` | Code | Dokument-API (~869 Zeilen) | Hoch | Upload/Download, Bulk-Ops |
| `src/api/admin.py` | Code | Admin-API Client | Mittel | Admin-Operationen |
| `src/api/gdv_api.py` | Code | GDV-API Client | Mittel | GDV-Parsing |
| `src/api/openrouter.py` | Code | OpenRouter KI (~1760 Zeilen) | Hoch | API-Key-Handling, KI-Klassifikation |
| `src/api/passwords.py` | Code | Passwort-API Client | Hoch | PDF/ZIP-Passwoerter |
| `src/api/processing_history.py` | Code | History-API Client | Niedrig | Audit-Trail |
| `src/api/releases.py` | Code | Releases-API Client | Mittel | Auto-Update |
| `src/api/smartadmin_auth.py` | Code | SmartAdmin Auth (~640 Zeilen) | Hoch | SAML-Token, 47 VUs |
| `src/api/smartscan.py` | Code | SmartScan + Email API | Mittel | E-Mail-Versand |
| `src/api/vu_connections.py` | Code | VU-Verbindungen (~427 Zeilen) | Hoch | Credential-Abruf |
| `src/api/xml_index.py` | Code | XML-Index Client | Niedrig | - |

#### BiPRO Layer (`src/bipro/`)

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `src/bipro/transfer_service.py` | Code | BiPRO SOAP Client (~1334 Zeilen) | Kritisch | STS-Token, Zertifikate, MTOM, XML |
| `src/bipro/bipro_connector.py` | Code | Verbindungsabstraktion (~397 Zeilen) | Hoch | Credential-Weitergabe |
| `src/bipro/rate_limiter.py` | Code | Adaptive Rate Limiter (~343 Zeilen) | Niedrig | DoS-Schutz |
| `src/bipro/categories.py` | Code | Kategorie-Mapping | Niedrig | - |

#### Services Layer (`src/services/`)

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `src/services/document_processor.py` | Code | Dokumenten-Klassifikation (~1524 Zeilen) | Hoch | KI-Integration, Temp-Files |
| `src/services/data_cache.py` | Code | Cache-Service (~592 Zeilen) | Mittel | Thread-Safety, Memory |
| `src/services/update_service.py` | Code | Auto-Update (~237 Zeilen) | Kritisch | EXE-Download, SHA256, Install |
| `src/services/pdf_unlock.py` | Code | PDF-Entsperrung (~183 Zeilen) | Kritisch | Hardcoded Passwoerter |
| `src/services/zip_handler.py` | Code | ZIP-Extraktion (~297 Zeilen) | Hoch | Zip-Bomb, Path-Traversal |
| `src/services/msg_handler.py` | Code | MSG-Extraktion (~153 Zeilen) | Mittel | Attachment-Extraktion |
| `src/services/atomic_ops.py` | Code | Atomic File Operations | Mittel | SHA256, Safe-Write |

#### UI Layer (`src/ui/`)

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `src/ui/main_hub.py` | Code | Navigation + DragDrop (~1145 Zeilen) | Hoch | Drop-Upload, Outlook COM, Close-Schutz |
| `src/ui/bipro_view.py` | Code | BiPRO UI (~4900 Zeilen) | Hoch | Download-Manager, Mail-Import |
| `src/ui/archive_boxes_view.py` | Code | Archiv-UI (~5380 Zeilen) | Hoch | SmartScan, Upload, Vorschau |
| `src/ui/archive_view.py` | Code | Legacy-Archiv + PDF-Viewer | Mittel | PDF-Edit, subprocess |
| `src/ui/admin_view.py` | Code | Admin-Panel (~4000 Zeilen) | Hoch | User-/Session-/Release-Verwaltung |
| `src/ui/login_dialog.py` | Code | Login-Dialog | Hoch | Passwort-Masking, Token |
| `src/ui/update_dialog.py` | Code | Update-Dialog | Mittel | Pflicht-Update-Modus |
| `src/ui/main_window.py` | Code | GDV-Editor (~1060 Zeilen) | Mittel | Datenbearbeitung |
| `src/ui/gdv_editor_view.py` | Code | GDV-Editor View (~648 Zeilen) | Mittel | - |
| `src/ui/partner_view.py` | Code | Partner-Uebersicht | Mittel | PII-Anzeige |
| `src/ui/settings_dialog.py` | Code | Einstellungen (~350 Zeilen) | Mittel | Zertifikat-Import |
| `src/ui/toast.py` | Code | Toast-System + ProgressToast | Niedrig | - |
| `src/ui/user_detail_view.py` | Code | Detail-Ansicht | Niedrig | - |
| `src/ui/styles/tokens.py` | Code | Design-Tokens (~977 Zeilen) | Niedrig | - |

#### Config Layer (`src/config/`)

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `src/config/certificates.py` | Code | Zertifikat-Manager (~291 Zeilen) | Hoch | PFX/P12, X.509 |
| `src/config/processing_rules.py` | Code | Verarbeitungsregeln | Niedrig | BiPRO-Codes |
| `src/config/smartadmin_endpoints.py` | Code | 47 VU-Endpunkte (~640 Zeilen) | Mittel | Endpoint-URLs |
| `src/config/vu_endpoints.py` | Code | VU-Endpunkte | Mittel | - |

#### Sonstige Python

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `src/main.py` | Code | App-Init (~312 Zeilen) | Hoch | Logging, Version, Mutex |
| `src/parser/gdv_parser.py` | Code | GDV-Parser | Mittel | File-I/O |
| `src/layouts/gdv_layouts.py` | Code | Satzart-Definitionen | Niedrig | - |
| `src/domain/models.py` | Code | Domain-Klassen | Niedrig | - |
| `src/domain/mapper.py` | Code | Domain-Mapping | Niedrig | - |
| `src/i18n/de.py` | Code | i18n (~910 Keys) | Niedrig | - |

#### Tests

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `src/tests/run_smoke_tests.py` | Test | Smoke-Tests (~363 Zeilen) | Mittel | Stabilitaet |
| `src/tests/test_smoke.py` | Test | pytest Smoke-Tests (~456 Zeilen) | Mittel | - |
| `src/tests/test_stability.py` | Test | Stabilitaets-Tests (~196 Zeilen) | Mittel | Deadlock, Thread-Safety |
| `testdata/sample.gdv` | Test | Test-GDV-Datei | Niedrig | - |
| `testdata/test_roundtrip.py` | Test | Roundtrip-Test (~192 Zeilen) | Niedrig | - |
| `testdata/create_testdata.py` | Test | Testdaten-Generator | Niedrig | - |
| `scripts/run_checks.py` | Test | Minimal-CI (~67 Zeilen) | Niedrig | - |

### PHP Backend (`BiPro-Webspace Spiegelung Live/`)

#### API-Dateien

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `api/index.php` | Code | Haupt-Router | Kritisch | Routing, CORS, Error-Handling |
| `api/config.php` | Config | Credentials + Secrets | Kritisch | DB-Pass, Master-Key, JWT-Secret, API-Keys |
| `api/auth.php` | Code | Authentifizierung | Kritisch | Login, JWT, Password-Verify |
| `api/documents.php` | Code | Dokument-Verwaltung | Kritisch | Upload, Download, Move, Archive |
| `api/gdv.php` | Code | GDV-Operationen | Hoch | SQL-LIMIT-Interpolation |
| `api/credentials.php` | Code | VU-Credentials | Kritisch | Verschluesselung/Entschluesselung |
| `api/admin.php` | Code | Admin-Verwaltung | Hoch | User-CRUD, Permissions |
| `api/sessions.php` | Code | Session-Verwaltung | Hoch | Session-Kill |
| `api/activity.php` | Code | Activity-Log | Mittel | SQL-LIMIT-Interpolation |
| `api/processing_history.php` | Code | Processing-History | Niedrig | Audit-Trail |
| `api/releases.php` | Code | Release-Verwaltung | Hoch | File-Upload, Download |
| `api/ai.php` | Code | KI-Key-Endpoint | Kritisch | API-Key-Exposition |
| `api/smartscan.php` | Code | SmartScan E-Mail | Hoch | SMTP-Versand, Credentials |
| `api/email_accounts.php` | Code | E-Mail-Konten | Hoch | IMAP/SMTP, Verschluesselung |
| `api/passwords.php` | Code | Passwort-Verwaltung | Kritisch | Klartext-Passwoerter in DB |
| `api/incoming_scans.php` | Code | Scan-Upload | Hoch | API-Key-Auth, File-Upload |
| `api/shipments.php` | Code | Lieferungen | Mittel | BiPRO-Daten |
| `api/xml_index.php` | Code | XML-Index | Niedrig | - |

#### Library-Dateien

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `api/lib/db.php` | Code | DB-Verbindung | Kritisch | PDO, Prepared Statements |
| `api/lib/jwt.php` | Code | JWT-Implementierung | Kritisch | Token-Sign/Verify, Session-Check |
| `api/lib/crypto.php` | Code | Kryptographie | Kritisch | AES-256-GCM, bcrypt |
| `api/lib/response.php` | Code | Response-Helpers | Mittel | Error-Handling |
| `api/lib/permissions.php` | Code | RBAC-Middleware | Hoch | Permission-Checks |
| `api/lib/activity_logger.php` | Code | Activity-Logging | Mittel | Audit-Trail |
| `api/lib/PHPMailer/*.php` | Lib | PHPMailer v6.9.3 (3 Dateien) | Mittel | SMTP-Versand |

#### Konfiguration

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `.htaccess` (Root) | Config | Directory-Listing, config.php-Schutz | Hoch | Access-Control |
| `api/.htaccess` | Config | URL-Rewriting, PHP-Limits | Hoch | Upload-Limits, config.php-Schutz |
| `api/.user.ini` | Config | PHP-Konfiguration | Mittel | Upload/Memory-Limits |
| `api/php.ini` | Config | PHP-Konfiguration | Mittel | Upload/Memory-Limits |

#### Migrations

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `setup/005_add_box_columns.php` | Migration | Box-System | Niedrig | - |
| `setup/006_add_bipro_category.php` | Migration | BiPRO-Kategorie | Niedrig | - |
| `setup/007_add_is_archived.php` | Migration | Archiv-Flag | Niedrig | - |
| `setup/008_add_box_type_falsch.php` | Migration | Box-Type-Fix | Niedrig | - |
| `setup/010_smartscan_email.php` | Migration | SmartScan (7 Tabellen) | Mittel | E-Mail-System |
| `setup/011_fix_smartscan_schema.php` | Migration | Schema-Fix | Niedrig | - |
| `setup/012_add_documents_history_permission.php` | Migration | History-Permission | Niedrig | - |
| `setup/create_processing_history.sql` | Migration | Processing-History | Niedrig | - |

### Sonstige Verzeichnisse

| Pfad | Typ | Zweck | Relevanz | Sicherheitsbezug |
|------|-----|-------|----------|------------------|
| `docs/ARCHITECTURE.md` | Doku | Architektur-Doku | Niedrig | - |
| `docs/DEVELOPMENT.md` | Doku | Entwicklungs-Doku | Niedrig | - |
| `docs/DOMAIN.md` | Doku | Domain-Doku | Niedrig | - |
| `docs/BIPRO_ENDPOINTS.md` | Doku | BiPRO-Endpoints | Mittel | Endpoint-Details |
| `docs/ui/UX_RULES.md` | Doku | UI-Regeln | Niedrig | - |
| `tools/decrypt_iwm_password.py` | Tool | IWM-Passwort-Entschluesselung | Mittel | Analyse-Tool |
| `Audit/` | Doku | Audit-Dokumente (7 Dateien) | Niedrig | - |
| `Bugs/` | Doku | Bug-Analysen (6 Dateien) | Niedrig | - |
| `Kontext/` | Doku | Kontext-Analysen (9 Dateien) | Niedrig | - |
| `STABILITY_UPGRADE/` | Doku | Upgrade-Reports (7 Dateien) | Niedrig | - |

---

## Statistik

| Kategorie | Anzahl |
|-----------|--------|
| Python-Dateien (src/) | ~63 |
| PHP-API-Dateien | 18 |
| PHP-Library-Dateien | 6 |
| PHP-Migrationen | 8 |
| Konfigurationsdateien | ~8 |
| Build-Skripte | 5 Batch + 1 PowerShell |
| Test-Dateien | 5 |
| Dokumentation | ~15 |
| **Sicherheitskritisch** | **~25 Dateien** |
