# 04 - Code-Struktur und Moduluebersicht

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Ordnerstruktur

```
5510_GDV Tool V1/
├── run.py                          # Entry Point
├── VERSION                         # Zentrale Versionsdatei (1.6.0)
├── AGENTS.md                       # Projekt-Dokumentation fuer Agents
├── README.md                       # Projekt-README
├── requirements.txt                # Produktions-Abhaengigkeiten
├── requirements-dev.txt            # Dev-Abhaengigkeiten (pytest, ruff)
├── build.bat                       # PyInstaller + Inno Setup Build
├── build_config.spec               # PyInstaller-Konfiguration
├── installer.iss                   # Inno Setup Script
│
├── src/
│   ├── main.py                     # App-Initialisierung, Login, Single-Instance
│   ├── api/                        # REST API Clients (~5.800 Zeilen)
│   │   ├── client.py               # Basis-HTTP-Client mit JWT/Retry
│   │   ├── auth.py                 # Login/Verify/Logout, User-Model
│   │   ├── documents.py            # Dokumenten-CRUD, Box-Ops, Bulk-Ops
│   │   ├── openrouter.py           # KI-Klassifikation (zweistufig)
│   │   ├── smartscan.py            # SmartScan + EmailAccounts API
│   │   ├── admin.py                # Admin-API (Nutzer, Sessions)
│   │   ├── passwords.py            # Passwort-Verwaltung (PDF/ZIP)
│   │   ├── releases.py             # Auto-Update API
│   │   ├── processing_history.py   # Audit-Trail + Kosten
│   │   ├── vu_connections.py       # VU-Verbindungsverwaltung
│   │   ├── smartadmin_auth.py      # SmartAdmin SAML-Auth
│   │   ├── gdv_api.py              # GDV-Server-Operationen
│   │   └── xml_index.py            # XML-Index-API
│   │
│   ├── bipro/                      # BiPRO SOAP Clients (~2.400 Zeilen)
│   │   ├── transfer_service.py     # BiPRO 410 STS + 430 Transfer
│   │   ├── bipro_connector.py      # Connector-Abstraktion
│   │   ├── rate_limiter.py         # AdaptiveRateLimiter
│   │   └── categories.py           # Kategorie-Code Mapping
│   │
│   ├── services/                   # Business-Logik (~3.400 Zeilen)
│   │   ├── document_processor.py   # Parallele KI-Verarbeitung
│   │   ├── data_cache.py           # Singleton-Cache + Auto-Refresh
│   │   ├── msg_handler.py          # MSG-Extraktion (Outlook)
│   │   ├── zip_handler.py          # ZIP-Entpackung (AES-256)
│   │   ├── pdf_unlock.py           # PDF-Passwortschutz entfernen
│   │   ├── update_service.py       # Auto-Update Service
│   │   └── atomic_ops.py           # Atomare Datei-Operationen
│   │
│   ├── ui/                         # GUI (~21.500 Zeilen)
│   │   ├── main_hub.py             # Navigation, Drag & Drop, Schliess-Schutz
│   │   ├── bipro_view.py           # BiPRO UI + ParallelDL + MailImport
│   │   ├── archive_boxes_view.py   # Box-Archiv + SmartScan + Historie
│   │   ├── archive_view.py         # PDF-Viewer + Spreadsheet-Viewer
│   │   ├── admin_view.py           # 10 Admin-Panels
│   │   ├── gdv_editor_view.py      # GDV-Editor Wrapper
│   │   ├── main_window.py          # GDV Tabelle + Detail
│   │   ├── partner_view.py         # Partner-Ansicht
│   │   ├── user_detail_view.py     # Benutzer-Ansicht
│   │   ├── toast.py                # Toast-System + ProgressToast
│   │   ├── update_dialog.py        # Update-Dialog
│   │   ├── login_dialog.py         # Login-Dialog
│   │   ├── settings_dialog.py      # Einstellungen + Zertifikate
│   │   ├── styles/
│   │   │   ├── tokens.py           # ACENCIA Design-System (~976 Z.)
│   │   │   └── __init__.py
│   │   └── assets/
│   │       ├── icon.ico            # App-Icon
│   │       └── logo.png            # App-Logo
│   │
│   ├── config/                     # Konfiguration
│   │   ├── processing_rules.py     # Verarbeitungsregeln + BiPRO-Codes
│   │   ├── vu_endpoints.py         # ~40 bekannte VU-Endpunkte
│   │   ├── smartadmin_endpoints.py # SmartAdmin-VU-Konfigurationen
│   │   └── certificates.py         # Zertifikats-Manager
│   │
│   ├── parser/
│   │   └── gdv_parser.py           # Fixed-Width Parser
│   │
│   ├── layouts/
│   │   └── gdv_layouts.py          # Satzart-Definitionen
│   │
│   ├── domain/
│   │   ├── models.py               # GDVData, Contract, Customer, etc.
│   │   └── mapper.py               # ParsedRecord -> Domain
│   │
│   ├── i18n/
│   │   └── de.py                   # ~910 deutsche UI-Texte
│   │
│   └── tests/
│       ├── test_stability.py       # 11 Smoke-Tests
│       ├── test_smoke.py           # Weitere Tests
│       └── run_smoke_tests.py      # Test-Runner
│
├── BiPro-Webspace Spiegelung Live/ # LIVE mit Strato synchronisiert!
│   ├── api/
│   │   ├── index.php               # API-Router (~400 Z.)
│   │   ├── auth.php                # Login/Logout/Verify
│   │   ├── documents.php           # Dokumenten-Endpunkte
│   │   ├── admin.php               # Nutzerverwaltung
│   │   ├── smartscan.php           # SmartScan-Versand
│   │   ├── email_accounts.php      # E-Mail + IMAP
│   │   ├── passwords.php           # Passwoerter
│   │   ├── releases.php            # Auto-Update
│   │   ├── sessions.php            # Session-Verwaltung
│   │   ├── activity.php            # Aktivitaetslog
│   │   ├── processing_history.php  # Audit-Trail
│   │   ├── incoming_scans.php      # Scan-Upload (API-Key)
│   │   ├── credentials.php         # VU-Verbindungen
│   │   ├── shipments.php           # BiPRO-Lieferungen
│   │   ├── gdv.php                 # GDV-Operationen
│   │   ├── ai.php                  # OpenRouter Key
│   │   ├── config.php              # DB-Creds, Secrets (SENSIBEL!)
│   │   ├── .htaccess               # URL-Rewrite + Schutz
│   │   └── lib/
│   │       ├── permissions.php     # Permission-Middleware
│   │       ├── activity_logger.php # Zentrales Logging
│   │       └── PHPMailer/          # PHPMailer v6.9.3 (3 Dateien)
│   │
│   ├── setup/                      # DB-Migrationen
│   │   ├── 008_add_box_type_falsch.php
│   │   ├── 010_smartscan_email.php
│   │   ├── 011_fix_smartscan_schema.php
│   │   └── 012_add_documents_history_permission.php
│   │
│   ├── dokumente/                  # NICHT synchronisiert! Server-only
│   └── releases/                   # NICHT synchronisiert! Server-only
│
├── testdata/                       # GDV-Testdateien
├── docs/                           # Technische Dokumentation
├── Kontext/                        # Dieses Verzeichnis
└── logs/                           # Logfiles (RotatingFileHandler)
```

---

## Kernmodule im Detail

### `src/main.py` (~309 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | App-Initialisierung, Login, Update-Check |
| Funktion `main()` | QApplication erstellen, Fonts laden, LoginDialog, MainHub |
| `_read_app_version()` | Liest VERSION-Datei, Fallback "0.0.0" |
| `ForcedLogoutHandler` | Erzwingt Logout bei 401er-Antworten |
| Single-Instance | Windows Mutex `ACENCIA_ATLAS_SINGLE_INSTANCE` |
| Update-Check | Nach Login synchron, dann periodisch (30 Min) |

### `src/ui/main_hub.py` (~1145 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | Hauptfenster, Navigation, Drag & Drop, Schliess-Schutz |
| `MainHub` | QMainWindow mit Sidebar (BiPRO, Archiv, GDV, Admin) |
| `NavButton` | Custom-Button fuer Sidebar-Navigation |
| `UpdateCheckWorker` | QThread fuer periodischen Update-Check (30 Min) |
| `DropUploadWorker` | QThread fuer Drag & Drop Upload |
| `closeEvent()` | Prueft `get_blocking_operations()`, dann ungespeicherte GDV-Aenderungen |
| `_show_admin()` | Versteckt Haupt-Sidebar, zeigt Admin-Vollbild |
| `_leave_admin()` | Zeigt Haupt-Sidebar wieder |
| `dragEnterEvent()` / `dropEvent()` | Globales Drag & Drop + Outlook-Direct-Drop |
| `_extract_outlook_emails()` | COM-Automation (pywin32) fuer Outlook-Mails |

### `src/ui/bipro_view.py` (~4950 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | BiPRO-Datenabruf UI, Lieferungen, Downloads, Mail-Import |
| `BiPROView` | Haupt-Widget mit VU-Auswahl, Toolbar, Lieferungstabelle |
| `FetchShipmentsWorker` | QThread fuer listShipments |
| `DownloadShipmentWorker` | QThread fuer Einzeldownload |
| `ParallelDownloadManager` | QThread mit ThreadPoolExecutor (max 10 Worker) |
| `MailImportWorker` | QThread: IMAP-Poll + Attachments verarbeiten (ZIP/MSG/PDF) |
| `BiPROProgressOverlay` | Fortschritts-UI fuer Parallel-Downloads |
| `AddConnectionDialog` | Dialog: Neue VU-Verbindung erstellen |
| `EditConnectionDialog` | Dialog: VU-Verbindung bearbeiten |
| `_fetch_all_vus()` | "Alle VUs abholen" - sequentielle Verarbeitung |
| `_fetch_mails()` | "Mails abholen" - IMAP via MailImportWorker |
| `mime_to_extension()` | MIME-Type zu Dateiendung Mapping |

### `src/ui/archive_boxes_view.py` (~5380 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | Dokumentenarchiv mit Box-System, zentrale Archiv-UI |
| `ArchiveBoxesView` | Haupt-Widget mit Sidebar + Tabelle + Historie-Panel |
| `BoxSidebar` | Box-Navigation mit Live-Zaehler + Kontextmenue |
| `DraggableDocumentTable` | Tabelle mit Drag & Drop zwischen Boxen |
| `DocumentHistoryPanel` | Seitenpanel mit farbcodierten Historie-Eintraegen |
| `DocumentHistoryWorker` | QThread fuer Historie-Laden mit Cache |
| `ProcessingWorker` | QThread fuer DocumentProcessor |
| `DelayedCostWorker` | QThread: 90s warten, dann Guthaben abrufen |
| `SmartScanWorker` | QThread fuer Smart!Scan-Versand (Chunking) |
| `MultiUploadWorker` | QThread fuer Multi-File-Upload (MSG/ZIP/PDF-Pipeline) |
| `MultiDownloadWorker` | QThread fuer Multi-File-Download |
| `BoxDownloadWorker` | QThread fuer ganze Box als ZIP/Ordner |
| `PreviewDownloadWorker` | QThread fuer Vorschau-Download mit Cache |
| `CreditsWorker` | QThread fuer OpenRouter-Guthaben |
| `CostStatsWorker` | QThread fuer Kosten-Statistiken |
| `get_blocking_operations()` | Liste blockierender Worker fuer Schliess-Schutz |
| `_setup_shortcuts()` | 10 Tastenkuerzel (F2, Entf, Strg+A/D/F/U, etc.) |

### `src/ui/admin_view.py` (~4000 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | 10 Admin-Panels in 3 Sektionen |
| Layout | Vertikale Sidebar links, QStackedWidget rechts |
| VERWALTUNG | Panel 0: Nutzerverwaltung, 1: Sessions, 2: Passwoerter |
| MONITORING | Panel 3: Aktivitaetslog, 4: KI-Kosten, 5: Releases |
| E-MAIL | Panel 6: E-Mail-Konten, 7: SmartScan-Settings, 8: SmartScan-Historie, 9: IMAP-Inbox |
| Worker-Klassen | LoadUsersWorker, LoadSessionsWorker, LoadPasswordsWorker, LoadActivityWorker, LoadCostDataWorker, LoadReleasesWorker, UploadReleaseWorker, etc. |

### `src/api/client.py` (~513 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | Basis-HTTP-Client fuer alle API-Aufrufe |
| `APIClient` | JWT-Token-Management, Session-basiert |
| `_request_with_retry()` | Retry bei 429, 500, 502, 503, 504 mit exp. Backoff |
| `_try_auth_refresh()` | JWT Auto-Refresh bei 401, Deadlock-Schutz (non-blocking) |
| `upload_file()` | Multipart-Upload mit Fortschritt |
| `download_file()` | Streaming-Download mit filename_override |
| Thread-Sicherheit | `_auth_refresh_lock` (threading.Lock) |

### `src/bipro/transfer_service.py` (~1519 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | BiPRO 410 STS + 430 Transfer Client |
| `TransferServiceClient` | SOAP-Client (Raw XML, kein zeep) |
| `SharedTokenManager` | Thread-sicheres Token-Management, Double-Checked Locking |
| `_get_sts_token()` | STS-Token holen (BiPRO 410) |
| `list_shipments()` | Lieferungen auflisten (VU-spezifisch) |
| `get_shipment()` | Lieferung herunterladen (MTOM/XOP) |
| `_parse_mtom_response()` | MTOM-Parser mit PDF-Magic-Byte-Validierung |
| `_detect_vema()` | VEMA-Erkennung anhand Endpoint-URL |

### `src/api/openrouter.py` (~1878 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | KI-Klassifikation zweistufig |
| `OpenRouterClient` | Stufe 1: GPT-4o-mini, Stufe 2: GPT-4o (bei low Confidence) |
| `_build_keyword_hints()` | Lokaler Keyword-Scanner fuer Konflikte |
| `classify_sparte_with_date()` | Haupt-Klassifikations-Methode |
| `_classify_sparte_request()` | Stufe 1: Schnelle Triage |
| `_classify_sparte_detail()` | Stufe 2: Detail-Klassifikation |
| `slug_de()` | Sichere Dateinamen-Generierung (Umlaute, Sonderzeichen) |
| `_safe_json_loads()` | Robustes JSON-Parsing (Fence-Stripping) |

### `src/services/data_cache.py` (~589 Zeilen)

| Aspekt | Beschreibung |
|--------|--------------|
| Zweck | Singleton-Cache fuer Dokumente/Verbindungen |
| `DataCacheService` | QObject mit Signalen (docs_loaded, stats_updated) |
| `get_documents()` | Alle Dokumente laden (1 API-Call), lokal filtern |
| `_compute_stats_from_cache()` | BoxStats client-seitig berechnen |
| `pause_auto_refresh()` | Waehrend Downloads/Verarbeitung pausieren |
| `resume_auto_refresh()` | Nach Operation fortsetzen (Counter-basiert) |

---

## PHP API Struktur

### Route-Registrierung (`index.php`)

| Auth | Ressource | Endpunkte |
|------|-----------|-----------|
| Keine | auth/login, auth/logout | Login, Logout |
| Keine | updates/check | Update-Pruefung |
| Keine | releases/download/{id} | Release-Download |
| JWT | documents/* | CRUD, Bulk, Upload, Historie, Replace |
| JWT | gdv/* | Parse, Records, Export |
| JWT | vu-connections/* | CRUD, Credentials, Test |
| JWT | shipments/* | List, Get, Acknowledge |
| JWT | ai/key | OpenRouter-Key |
| JWT | passwords | Aktive Passwoerter (Public) |
| JWT | processing_history/* | Audit-Trail, Kosten |
| JWT | smartscan/* | Settings, Send, Jobs |
| JWT | email-inbox/* | Mails, Attachments |
| Admin | admin/users/* | Nutzerverwaltung |
| Admin | admin/releases/* | Release-Verwaltung |
| Admin | admin/passwords/* | Passwort-Verwaltung |
| Admin | admin/email-accounts/* | E-Mail-Konten |
| Admin | sessions/* | Session-Verwaltung |
| Admin | activity/* | Aktivitaetslog |
| API-Key | incoming-scans | Scan-Upload (Power Automate) |

### Berechtigungen (10 Stueck)

| Permission | Beschreibung |
|------------|--------------|
| vu_connections_manage | VU-Verbindungen verwalten |
| bipro_fetch | BiPRO-Lieferungen abrufen |
| documents_manage | Dokumente verschieben, umbenennen, archivieren |
| documents_delete | Dokumente loeschen |
| documents_upload | Dokumente hochladen |
| documents_download | Dokumente herunterladen |
| documents_process | KI-Verarbeitung starten |
| documents_history | Dokument-Historie einsehen |
| gdv_edit | GDV-Datensaetze bearbeiten |
| smartscan_send | Smart!Scan E-Mails versenden |
