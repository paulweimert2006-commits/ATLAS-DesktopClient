# ACENCIA ATLAS - Architektur und Dateistruktur

**Letzte Aktualisierung:** 24. Februar 2026

---

## Systemarchitektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ACENCIA ATLAS                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Desktop-App (PySide6/Qt)              Strato Webspace                       │
│ ├── UI Layer                          ├── PHP REST API (26 Dateien)         │
│ │   ├── main_hub.py (Navigation)      │   ├── auth.php (JWT)               │
│ │   ├── message_center_view.py        │   ├── documents.php (Archiv)       │
│ │   ├── chat_view.py                  │   ├── provision.php (GF-Bereich)   │
│ │   ├── bipro_view.py                 │   ├── xempus.php (Insight Engine)  │
│ │   ├── archive_boxes_view.py         │   ├── ai.php (KI-Proxy)           │
│ │   ├── gdv_editor_view.py            │   ├── smartscan.php               │
│ │   ├── admin/ (15 Panels)            │   └── ... (20 weitere)            │
│ │   ├── provision/ (8 Panels)         │                                     │
│ │   └── toast.py                      ├── MySQL Datenbank (~40 Tabellen)   │
│ ├── API Clients                       ├── Dokumente-Storage (/dokumente/)  │
│ │   ├── client.py (Base)              └── Releases-Storage (/releases/)    │
│ │   ├── documents.py                                                        │
│ │   ├── provision.py                                                        │
│ │   └── ... (18 weitere)                                                    │
│ ├── BiPRO SOAP Client                                                       │
│ │   ├── transfer_service.py                                                 │
│ │   └── workers.py                                                          │
│ ├── Services Layer                                                           │
│ │   ├── document_processor.py                                               │
│ │   ├── provision_import.py                                                 │
│ │   └── ... (11 weitere)                                                    │
│ └── Parser Layer                                                             │
│     ├── gdv_parser.py                                                       │
│     └── gdv_layouts.py                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Datenfluesse:                                                                │
│ 1. Desktop ←→ PHP-API ←→ MySQL/Dateien (Archiv, Auth, Provisionen)         │
│ 2. Desktop → BiPRO SOAP → Versicherer (STS-Token + Transfer)               │
│ 3. Desktop ←→ PHP-API → OpenRouter/OpenAI (KI-Proxy)                       │
│ 4. SharePoint → PHP-API → MySQL (Power Automate Scans)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Python-Dateien (Desktop-App) - Vollstaendige Liste

### `src/` (Root)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `__init__.py` | 18 | Package-Init |
| `main.py` | 334 | Qt-App Initialisierung, Update-Check nach Login, APP_VERSION aus VERSION |

### `src/api/` (API-Clients, 21 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `client.py` | 523 | Base-Client mit JWT, Retry, Auto-Refresh |
| `documents.py` | 1.111 | Document-Modell, Upload/Download, Bulk-Ops, ATLAS-Suche, Duplikate |
| `provision.py` | 859 | ProvisionAPI (40+ Methoden), 11 Dataclasses (Employee, Contract, Commission...) |
| `auth.py` | 390 | Login/Logout, User-Model mit Permissions |
| `smartadmin_auth.py` | 640 | SmartAdmin-SAML-Auth fuer 47 VUs |
| `smartscan.py` | 502 | SmartScan + EmailAccounts API |
| `vu_connections.py` | 427 | VU-Verbindungen CRUD |
| `xempus.py` | 377 | Xempus Insight Engine API (Chunked Import, CRUD, Stats, Diff) |
| `processing_history.py` | 371 | Verarbeitungs-Audit-Trail |
| `xml_index.py` | 259 | XML-Rohdaten-Index |
| `admin.py` | 241 | Admin-Nutzerverwaltung |
| `gdv_api.py` | 229 | GDV-Dateien server-seitig parsen/speichern |
| `releases.py` | 171 | Release-Verwaltung + Update-Check |
| `chat.py` | 152 | 1:1 Chat-Nachrichten |
| `messages.py` | 143 | System-/Admin-Mitteilungen |
| `processing_settings.py` | 133 | KI-Klassifikations-Einstellungen |
| `ai_providers.py` | 120 | KI-Provider-Verwaltung (OpenRouter/OpenAI) |
| `model_pricing.py` | 117 | Modell-Preise + Request-Historie |
| `document_rules.py` | 94 | Dokumenten-Regeln (Duplikate, leere Seiten) |
| `passwords.py` | ~100 | PDF/ZIP-Passwoerter aus DB |

### `src/api/openrouter/` (KI-Integration, 6 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `classification.py` | 749 | Zweistufige KI-Klassifikation (Triage + Detail) |
| `client.py` | 253 | HTTP-Client mit Semaphore fuer Rate-Limiting |
| `ocr.py` | 244 | Vision-OCR fuer Bild-PDFs |
| `utils.py` | 188 | Keyword-Hints, Text-Aufbereitung |
| `models.py` | 170 | Dataclasses (ClassificationResult, etc.) |
| `__init__.py` | 49 | Package-Exports |

### `src/bipro/` (BiPRO SOAP, 7 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `transfer_service.py` | 1.330 | BiPRO 410 STS + 430 Transfer, SharedTokenManager |
| `workers.py` | 1.339 | 5 QThread-Worker (Fetch, Download, Ack, MailImport, ParallelDL) |
| `bipro_connector.py` | 397 | SmartAdmin vs. Standard Verbindungsabstraktion |
| `rate_limiter.py` | 343 | AdaptiveRateLimiter (HTTP 429/503) |
| `mtom_parser.py` | 283 | MTOM/XOP-Response-Parser (Multipart-MIME) |
| `categories.py` | 155 | BiPRO-Kategorie-Code zu Name Mapping |

### `src/config/` (Konfiguration, 6 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `vu_endpoints.py` | 641 | VU-spezifische BiPRO-Endpunkte |
| `processing_rules.py` | 600 | BiPRO-Code → Box-Mapping, Verarbeitungsregeln |
| `smartadmin_endpoints.py` | 490 | SmartAdmin VU-Endpunkte (47 Versicherer) |
| `certificates.py` | 298 | PFX/P12 Zertifikat-Manager |
| `ai_models.py` | 58 | Modell-Definitionen pro Provider |

### `src/domain/` (Datenmodelle, 4 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `models.py` | 623 | GDV-Domain (ParsedFile, ParsedRecord, GDVField) |
| `mapper.py` | 513 | GDV-Feldwert-Zuordnungen (Anrede, Sparte, etc.) |
| `xempus_models.py` | 375 | 9 Xempus-Dataclasses (Employer, Consultation, etc.) |

### `src/i18n/` (Uebersetzungen)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `de.py` | 2.119 | ~1.400 deutsche UI-Texte (alle GROSSBUCHSTABEN_KEYS) |

### `src/services/` (Business-Logik, 13 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `document_processor.py` | ~2.300 | KI-Klassifikation, Verarbeitung, Regeln, Kosten |
| `provision_import.py` | 738 | VU/Xempus Excel-Parser, Normalisierung |
| `xempus_parser.py` | 404 | Xempus 5-Sheet Excel-Parser |
| `zip_handler.py` | 320 | ZIP-Entpackung (AES-256, rekursiv) |
| `update_service.py` | 249 | Auto-Update (Check, Download, Verify, Install) |
| `atomic_ops.py` | 214 | SHA256, Staging, Safe-Write |
| `empty_page_detector.py` | 191 | 4-Stufen Leere-Seiten-Erkennung |
| `pdf_unlock.py` | 169 | PDF-Passwort-Entsperrung (dynamisch aus DB) |
| `cost_calculator.py` | 164 | tiktoken Token-Zaehlung + Kostenberechnung |
| `msg_handler.py` | 155 | Outlook .msg Anhaenge extrahieren |
| `early_text_extract.py` | 149 | Text sofort nach Upload extrahieren |
| `image_converter.py` | 73 | Bild → PDF Konvertierung (PyMuPDF) |
| `data_cache.py` | ~300 | DataCacheService (Auto-Refresh, Thread-safe) |

### `src/ui/` (Hauptfenster, ~13 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `bipro_view.py` | ~3.530 | BiPRO-UI, VU-Verwaltung, Signal-Handling |
| `main_hub.py` | 1.529 | Haupt-Navigation, Drag&Drop, NotificationPoller, Schliess-Schutz |
| `partner_view.py` | 1.165 | Partner-Uebersicht (Firmen/Personen) |
| `main_window.py` | 1.072 | GDV-Editor Hauptfenster |
| `chat_view.py` | 876 | Vollbild-Chat (Conversation-Liste + Nachrichten) |
| `message_center_view.py` | 639 | Mitteilungszentrale (3 Kacheln) |
| `gdv_editor_view.py` | 598 | GDV-Editor View (RecordTable + Editor) |
| `toast.py` | 598 | ToastManager + ToastWidget + ProgressToast |
| `user_detail_view.py` | 515 | Benutzerfreundliche GDV-Detail-Ansicht |
| `settings_dialog.py` | 417 | Einstellungen (Zertifikate) |
| `update_dialog.py` | 361 | Update-Dialog (3 Modi) |
| `login_dialog.py` | 288 | Login mit Auto-Login + Cache-Wipe |

### `src/ui/admin/` (Admin-Bereich, 21 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `admin_shell.py` | 390 | Shell mit Sidebar + QStackedWidget + Lazy Loading |
| `dialogs.py` | 723 | 6 Dialog-Klassen + AdminNavButton |
| `workers.py` | 190 | 8 Admin-Worker-Klassen |
| `panels/user_management.py` | 323 | Nutzerverwaltung |
| `panels/sessions.py` | 216 | Session-Management |
| `panels/passwords.py` | 414 | Passwort-Verwaltung |
| `panels/activity_log.py` | 286 | Aktivitaetslog |
| `panels/ai_costs.py` | 578 | KI-Kosten + Einzelne Requests |
| `panels/releases.py` | 455 | Release-Verwaltung |
| `panels/ai_classification.py` | 654 | KI-Pipeline + Prompt-Editor |
| `panels/ai_providers.py` | 335 | KI-Provider (OpenRouter/OpenAI) |
| `panels/model_pricing.py` | 308 | Modell-Preise |
| `panels/document_rules.py` | 274 | Dokumenten-Regeln |
| `panels/email_accounts.py` | 237 | E-Mail-Konten |
| `panels/smartscan_settings.py` | 321 | SmartScan-Einstellungen |
| `panels/smartscan_history.py` | 251 | SmartScan-Historie |
| `panels/email_inbox.py` | 322 | E-Mail-Posteingang |
| `panels/messages.py` | 286 | Admin-Mitteilungen |

### `src/ui/archive/` (Dokumentenarchiv, 4 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `archive_boxes_view.py` | ~5.645 | Box-UI, QTableView/Model, SmartScan, Duplikate, ATLAS Index, Historie |
| `archive_view.py` | ~2.674 | Legacy-View + PDFViewerDialog + DuplicateCompareDialog |
| `workers.py` | 901 | 16 QThread-Worker (Cache, Upload, Download, Processing, etc.) |

### `src/ui/provision/` (Provisionsmanagement, 12 Dateien)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `xempus_insight_panel.py` | 1.209 | 4-Tab Xempus-Analyse (Arbeitgeber, Stats, Import, Status-Mapping) |
| `zuordnung_panel.py` | 915 | Klaerfaelle + MatchContractDialog + Reverse-Matching |
| `provisionspositionen_panel.py` | 883 | Master-Detail mit FilterChips, PillBadges, VU-Vermittler |
| `widgets.py` | 821 | 9 Shared Widgets (PillBadge, DonutChart, KpiCard, etc.) |
| `auszahlungen_panel.py` | 639 | StatementCards, Status-Workflow, Export |
| `verteilschluessel_panel.py` | 608 | Modell-Karten + Mitarbeiter-Tabelle |
| `dashboard_panel.py` | 576 | 4 KPI-Karten, DonutChart, Berater-Ranking |
| `xempus_panel.py` | 488 | Xempus-Beratungen-Liste |
| `abrechnungslaeufe_panel.py` | 478 | Import + Batch-Historie |
| `settings_panel.py` | 341 | Gefahrenzone (Reset mit 3s-Countdown) |
| `provision_hub.py` | 328 | Hub mit Sidebar + 8 Panels |

### `src/ui/styles/` (Design)

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `tokens.py` | 1.090 | ACENCIA Design-Tokens, Farben, Fonts, Pill-Colors, Rich-Tooltips |

---

## PHP-Dateien (Server-Backend) - Vollstaendige Liste

### `BiPro-Webspace Spiegelung Live/api/`

| Datei | Zeilen | Zweck |
|-------|--------|-------|
| `provision.php` | 2.289 | Provisionsmanagement (Split-Engine, Auto-Matching, 32 Routes) |
| `documents.php` | 1.748 | Dokumentenarchiv (CRUD, Bulk-Ops, Suche, Duplikate, Historie) |
| `xempus.php` | 1.360 | Xempus Insight Engine (4-Phasen-Import, CRUD, Stats, Diff) |
| `smartscan.php` | 1.229 | SmartScan (Settings, Send, Chunk, Historie) |
| `email_accounts.php` | 1.028 | E-Mail-Konten (SMTP/IMAP, Polling, Inbox) |
| `processing_history.php` | 589 | Verarbeitungs-Audit-Trail + Kosten-Historie |
| `releases.php` | 514 | Release-Verwaltung + Update-Check |
| `incoming_scans.php` | 425 | Scan-Upload (Power Automate, API-Key-Auth) |
| `ai.php` | 427 | KI-Proxy (OpenRouter/OpenAI Routing, PII-Redaktion, Kosten) |
| `admin.php` | 407 | Nutzerverwaltung (nur Admins) |
| `chat.php` | 400 | 1:1 Chat (Conversations, Messages, Read) |
| `gdv.php` | 399 | GDV-Operationen |
| `processing_settings.php` | 384 | KI-Klassifikations-Einstellungen |
| `credentials.php` | 318 | VU-Verbindungen (Credentials verschluesselt) |
| `ai_providers.php` | 298 | KI-Provider-Keys (AES-256-GCM) |
| `model_pricing.php` | 298 | Modell-Preise + Request-Logging |
| `passwords.php` | 298 | PDF/ZIP-Passwoerter |
| `index.php` | 297 | API-Router (alle Routes) |
| `auth.php` | 279 | Login/Logout/JWT-Token |
| `messages.php` | 252 | System-/Admin-Mitteilungen |
| `xml_index.php` | 247 | XML-Rohdaten-Index |
| `activity.php` | 227 | Aktivitaetslog-Endpunkte |
| `shipments.php` | 229 | BiPRO-Lieferungen |
| `document_rules.php` | 210 | Dokumenten-Regeln Settings |
| `sessions.php` | 174 | Session-Management |
| `notifications.php` | 109 | Polling-Endpoint (Unread-Counts) |

### `BiPro-Webspace Spiegelung Live/api/lib/`

| Datei | Zweck |
|-------|-------|
| `permissions.php` | Permission-Middleware (requirePermission, requireAdmin) |
| `activity_logger.php` | Zentrales Activity-Logging |
| `db.php` | Datenbank-Verbindung |
| `response.php` | JSON-Response-Helpers |
| `PHPMailer/` | PHPMailer v6.9.3 (3 Dateien: PHPMailer.php, SMTP.php, Exception.php) |

---

## DB-Migrationen (19 Skripte)

| Nr. | Datei | Zweck |
|-----|-------|-------|
| 005 | `add_box_columns.php` | Box-Spalten fuer Dokumentenarchiv |
| 006 | `add_bipro_category.php` | BiPRO-Kategorie-Spalte |
| 007 | `add_is_archived.php` | Archivierungs-Flag |
| 008 | `add_box_type_falsch.php` | Box "falsch" (Admin-Umlagerung) |
| 010 | `smartscan_email.php` | 7 Tabellen fuer E-Mail-System |
| 011 | `fix_smartscan_schema.php` | Schema-Fix SmartScan |
| 012 | `add_documents_history_permission.php` | documents_history Berechtigung |
| 013 | `rate_limits.php` | Rate-Limiting Tabelle |
| 014 | `encrypt_passwords.php` | Passwort-Verschluesselung |
| 015 | `message_center.php` | 4 Tabellen fuer Mitteilungen + Chat |
| 016 | `empty_page_detection.php` | empty_page_count Spalten |
| 017 | `document_ai_data.php` | document_ai_data Tabelle |
| 018 | `content_duplicate_detection.php` | content_duplicate_of_id |
| 024 | `provision_matching_v2.php` | VN-Normalisierung, Indizes, UNIQUE |
| 025 | `provision_indexes.php` | 8 operative Indizes |
| 026 | `vsnr_renormalize.php` | VSNR: Alle Nullen entfernen |
| 027 | `reset_provision_data.php` | Reset-Funktion fuer Gefahrenzone |
| 028 | `xempus_complete.php` | 9 neue xempus_* Tabellen |
| 029 | `provision_role_permissions.php` | provision_access + provision_manage |

---

## Wichtige Sonstige Dateien

| Datei | Zweck |
|-------|-------|
| `run.py` | Start-Script (`python run.py`) |
| `VERSION` | Zentrale Versionsdatei (aktuell: 2.2.0) |
| `requirements.txt` | 13 Python-Abhaengigkeiten |
| `AGENTS.md` | Agent-Dokumentation (Single Source of Truth) |
| `docs/ARCHITECTURE.md` | Architektur-Dokumentation |
| `docs/DOMAIN.md` | Datenmodell-Dokumentation |
| `docs/DEVELOPMENT.md` | Entwicklungs-Richtlinien |
| `docs/BIPRO_ENDPOINTS.md` | BiPRO VU-Endpunkte |
| `docs/ui/UX_RULES.md` | Verbindliche UI-Regeln (keine modalen Popups) |
| `testdata/sample.gdv` | GDV-Testdatei |
| `src/tests/run_smoke_tests.py` | 11 Smoke-Tests |
| `logs/bipro_gdv.log` | Laufzeit-Log (Rotation 5 MB, 3 Backups) |
| `installer.iss` | Inno Setup Installer-Script |
