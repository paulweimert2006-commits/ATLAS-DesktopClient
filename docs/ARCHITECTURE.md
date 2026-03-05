# ARCHITECTURE.md - ACENCIA ATLAS Desktop Client

> **Stand**: 05.03.2026 | **Version**: 2.3.1

---

## System-Ueberblick

ACENCIA ATLAS ist eine Python-Desktop-App (PySide6/Qt) mit Clean Architecture,
die ueber eine REST-API mit einem PHP-Backend auf Hetzner Cloud kommuniziert.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ACENCIA ATLAS Gesamtsystem                       │
│                                                                     │
│  ┌────────────────────┐  HTTPS/JWT  ┌──────────────────────────┐   │
│  │  Desktop-App        │◄──────────►│  Hetzner Cloud (CCX13)   │   │
│  │  (PySide6/Python)   │            │                          │   │
│  │                     │            │  ┌──────────────────┐    │   │
│  │  - Core (MainHub)   │            │  │  Nginx           │    │   │
│  │  - Provision        │            │  │  (HTTPS, HTTP/2) │    │   │
│  │  - Workforce        │            │  └────────┬─────────┘    │   │
│  │  - Admin            │            │           │              │   │
│  └────────────────────┘            │  ┌────────▼─────────┐    │   │
│                                     │  │  PHP 8.3 FPM     │    │   │
│  ┌────────────────────┐            │  │  REST API         │    │   │
│  │  Web-Admin-Panel    │◄──────────►│  │  (~48 Endpoints)  │    │   │
│  │  (Vanilla JS SPA)   │  HTTPS/JWT │  └────────┬─────────┘    │   │
│  └────────────────────┘            │           │              │   │
│                                     │  ┌────────▼─────────┐    │   │
│  ┌────────────────────┐            │  │  MySQL 8.0        │    │   │
│  │  HR-Provider APIs   │            │  │  (~63 Tabellen)   │    │   │
│  │  (Personio, HRworks)│◄──────────►│  └──────────────────┘    │   │
│  └────────────────────┘  Desktop   │                          │   │
│                          direkt    │  Volume 100 GB           │   │
│  ┌────────────────────┐            │  /mnt/atlas-volume/      │   │
│  │  BiPRO SOAP APIs    │            │  (Dokumente, Releases,   │   │
│  │  (Degenia, VEMA)    │◄──────────►│   Backups)              │   │
│  └────────────────────┘  Desktop   └──────────────────────────┘   │
│                          direkt                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Clean Architecture (Desktop-App)

Die Desktop-App folgt einer strikten Schichtenarchitektur:

```
┌──────────────────────────────────────────────────────┐
│                    UI Layer (PySide6)                  │
│  app_router.py → dashboard_screen.py                  │
│  main_hub.py → bipro_view, archive_boxes_view, ...    │
│  provision_hub.py → 10 Panels                         │
│  workforce_hub.py → 7 Panels                          │
│  admin_shell.py → 17 Panels                           │
├──────────────────────────────────────────────────────┤
│                  Presenter Layer (MVP)                 │
│  archive/archive_presenter.py                         │
│  provision/ (8 Presenter)                             │
├──────────────────────────────────────────────────────┤
│                  Use Case Layer                       │
│  archive/ (~15 Use Cases: Upload, Download, Move...) │
│  provision/ (~10 Use Cases: Load, Import, Match...)  │
├──────────────────────────────────────────────────────┤
│                  Domain Layer                         │
│  archive/entities.py, rules.py, classifier.py         │
│  provision/entities.py, interfaces.py                 │
├──────────────────────────────────────────────────────┤
│               Infrastructure Layer                    │
│  api/ (provision_repository.py)                       │
│  archive/ (document_repo, pdf, ai, smartscan, hash)  │
│  cache/ (provision_cache.py)                          │
│  storage/ (local_storage.py)                          │
│  threading/ (archive_workers, freeze_detector)        │
├──────────────────────────────────────────────────────┤
│                  API Client Layer                      │
│  client.py (Basis-HTTP-Client, JWT, Retry)            │
│  auth.py, documents.py, provision.py, messages.py     │
│  admin.py, xempus.py, bipro_events.py, smartscan.py  │
│  openrouter/ (KI-Integration)                         │
│  workforce/api_client.py (HR-Endpoints)               │
├──────────────────────────────────────────────────────┤
│                  Services Layer                        │
│  document_processor.py (KI-Klassifikation)            │
│  data_cache.py, provision_import.py, xempus_parser.py │
│  global_heartbeat.py, update_service.py               │
│  workforce/services/ (Sync, Delta, Export, Trigger)   │
└──────────────────────────────────────────────────────┘
```

### Abhaengigkeitsrichtung

UI → Presenter → Use Case → Domain ← Infrastructure

Die Domain-Schicht hat **keine Abhaengigkeiten** nach aussen.
Infrastructure implementiert die Interfaces aus der Domain-Schicht.

---

## Module (Hauptbereiche)

### 1. Core-Modul (MainHub)

**Navigation**: Sidebar mit Eintraegen fuer Mitteilungszentrale, BiPRO, Archiv, GDV-Editor, Admin, Chat.

```
MainHub (QWidget)
├── Sidebar (NavButtons)
├── QStackedWidget
│   ├── [0] MessageCenterView    - Mitteilungen + Releases
│   ├── [1] BiPROView            - BiPRO-Datenabruf
│   ├── [2] ArchiveBoxesView     - Dokumentenarchiv mit Box-System
│   ├── [3] GDVEditorView        - GDV-Editor
│   ├── [4] ProvisionView        - (optional, Link zu Ledger)
│   ├── [5] AdminShell           - (optional, nur Admins)
│   └── [6] ChatView             - 1:1 Chat
└── NotificationPoller (QTimer, 30s)
```

### 2. Provision-Modul (ProvisionHub)

**Zugriff**: `provision_access` oder `provision_manage` Berechtigung erforderlich.

```
ProvisionHub (QWidget)
├── Sidebar (10 Eintraege)
├── QStackedWidget
│   ├── [0] DashboardPanel       - KPI-Karten, Berater-Ranking
│   ├── [1] PerformancePanel     - Performance-Metriken
│   ├── [2] ImportPanel          - VU-Listen + Xempus Import
│   ├── [3] ZuordnungPanel       - Vermittler-Zuordnung
│   ├── [4] XempusPanel          - Xempus-Beratungen
│   ├── [5] FreeCommissionPanel  - Freie Provisionen
│   ├── [6] ClearancePanel       - Klaerung
│   ├── [7] VerteilPanel         - Verteilungsschluessel
│   ├── [8] AuszahlungenPanel    - Abrechnungen + PDF-Export
│   └── [9] SettingsPanel        - Provision-Einstellungen
└── Presenter-Schicht (8 Presenter)
```

### 3. Workforce-Modul (WorkforceHub)

**Zugriff**: `hr.view` Berechtigung erforderlich. Trigger: zusaetzlich `hr.triggers`.

```
WorkforceHub (QWidget)
├── Sidebar (7 Eintraege)
├── QStackedWidget
│   ├── [0] EmployersView        - Arbeitgeber CRUD + Credentials
│   ├── [1] EmployeesView        - Mitarbeiter (paginiert, Suche)
│   ├── [2] ExportsView          - SCS-Exporte (Upload/Download)
│   ├── [3] SnapshotsView        - HR-Snapshots
│   ├── [4] StatsView            - Statistiken
│   ├── [5] TriggersView         - Trigger-Verwaltung
│   └── [6] SmtpView             - SMTP-Konfiguration
└── Worker-Threads (Sync, Delta, Export, Stats)
```

### 4. Admin-Modul (AdminShell)

**Zugriff**: Nur fuer Admins (`account_type = 'admin'`).

17 Panels in 5 Sektionen: Verwaltung (4), Monitoring (3), Verarbeitung (4), E-Mail (4), System (2).

---

## Routing

### AppRouter (Top-Level)

```
AppRouter (QMainWindow + QStackedWidget)
├── [0] DashboardScreen          - Startbildschirm mit Modul-Kacheln
├── [1] MainHub                  - Core-Modul (Lazy Load)
├── [2] ProvisionHub             - Provision-Modul (Lazy Load)
└── [3] WorkforceHub             - Workforce-Modul (Lazy Load)
```

**Signals**: `module_requested(str)`, `back_requested`, `logout_requested`

**Kein URL-basiertes Routing** -- Navigation ueber `QStackedWidget.setCurrentIndex()` und Qt Signals.

---

## Datenfluss-Diagramme

### Login-Flow

```
LoginDialog                    APIClient                   PHP Backend
    │                              │                            │
    ├─ login(user, pass) ─────────►│                            │
    │                              ├─ POST /auth/login ────────►│
    │                              │                            ├─ JWT generieren
    │                              │◄─ { token, user } ────────┤
    │                              ├─ set_token(jwt)            │
    │◄─ AuthState ────────────────┤                            │
    │                              │                            │
    ├─ (bei "Angemeldet bleiben")  │                            │
    │   save_token() ──────────────► keyring / TOKEN_FILE       │
```

### Dokumenten-Upload mit KI-Klassifikation

```
ArchiveBoxesView           DocumentProcessor            API / Backend
    │                           │                            │
    ├─ upload(files) ──────────►│                            │
    │                           ├─ POST /documents (upload) ─►│
    │                           │◄─ { id, filename } ────────┤
    │                           │                            │
    │                           ├─ extract_text(pdf)         │
    │                           ├─ classify(text) ───────────► OpenRouter/OpenAI
    │                           │◄─ { category, confidence } ┤
    │                           │                            │
    │                           ├─ PUT /documents/{id}       │
    │                           │   { box, ai_name } ────────►│
    │                           │◄─ OK ─────────────────────┤
    │◄─ refresh_view() ────────┤                            │
```

### HR Delta-Export-Flow

```
WorkforceHub               SyncService/DeltaService       API / Providers
    │                           │                              │
    ├─ sync_employer(id) ──────►│                              │
    │                           ├─ GET /hr/employers/{id}/     │
    │                           │   credentials (decrypted) ───►│ PHP
    │                           │◄─ { api_key, ... } ─────────┤
    │                           │                              │
    │                           ├─ provider.fetch_employees() ─► Personio/HRworks
    │                           │◄─ [employees] ──────────────┤
    │                           │                              │
    │                           ├─ GET /hr/employers/{id}/     │
    │                           │   snapshots/latest ──────────► PHP
    │                           │◄─ { snapshot_data } ────────┤
    │                           │                              │
    │                           ├─ delta_service.compare()     │
    │                           ├─ export_service.generate_xlsx()│
    │                           │                              │
    │                           ├─ POST /hr/snapshots ─────────► PHP
    │                           ├─ POST /hr/exports ───────────► PHP
    │                           │                              │
    │                           ├─ trigger_service.evaluate()  │
    │                           │   (E-Mail via smtplib,       │
    │                           │    API via requests)         │
    │                           │                              │
    │                           ├─ POST /hr/trigger-runs ──────► PHP
    │◄─ result ────────────────┤                              │
```

---

## State Management

ATLAS verwendet **kein** zentrales State-Management-Framework. State wird ueber klassische OOP-Patterns verwaltet:

| Mechanismus | Verwendung |
|-------------|------------|
| **Qt Signals/Slots** | Event-Propagation zwischen Komponenten |
| **MVP-Pattern** | Presenter halten View-State, Views zeigen ihn an |
| **APIClient Singleton** | Eine Instanz pro App, haelt Token und Session |
| **QSettings** | Persistente Einstellungen (Font, Sprache, letzte Abrufe) |
| **GlobalHeartbeat** | Polling alle 5s: Session-Pruefung, Benachrichtigungen, System-Status |

---

## Threading-Modell

Alle langandauernden Operationen laufen in Hintergrund-Threads:

| Worker | Basis | Verwendung |
|--------|-------|------------|
| BiPRO-Worker (6) | `QThread` | STS-Auth, listShipments, getShipment, ... |
| Archive-Worker | `QRunnable` / `ThreadPoolExecutor` | Upload, Download, KI-Verarbeitung |
| Provision-Worker | `QThread` | Import, Match, Split-Berechnung |
| Workforce-Worker | `QThread` | Sync, Delta-Export, Stats |
| NotificationPoller | `QTimer` (30s) | Benachrichtigungs-Polling |
| GlobalHeartbeat | `QTimer` (5s) | Session-Pruefung |
| UpdateCheckWorker | `QTimer` (30min) | Auto-Update-Pruefung |

**Regel**: Kein blockierender Code auf dem Main-Thread. Alle API-Calls und Dateioperationen muessen in Worker-Threads.

---

## Sicherheit

### Authentifizierung
- JWT-Token (Login via `POST /auth/login`)
- Auto-Login via keyring (Windows Credential Manager / DPAPI) oder Fallback-Datei
- Token-Refresh bei 401 (transparent, `_request_with_retry`)
- Forced Logout bei Session-Ende oder Sperrung

### Berechtigungssystem
- `account_type`: `admin` oder `user`
- Standard-Rechte: Admins haben alle (ausser Provision/HR)
- Provision-Rechte: `provision_access`, `provision_manage` (explizit)
- HR-Rechte: `hr.view`, `hr.sync`, `hr.export`, `hr.triggers`, `hr.admin` (explizit)
- Web-Admin-Panel: `is_super_admin` fuer Server-Management-Panels

### Verschluesselung
- Credentials in DB: AES-256-GCM (PHP `Crypto`-Klasse)
- Token-Datei: `chmod 0600` (Fallback)
- SSL/TLS fuer alle API-Kommunikation

---

## Datei-Referenz (Wichtigste Dateien)

| Datei | Beschreibung |
|-------|-------------|
| `run.py` | Entry Point (Desktop-App oder Background-Updater) |
| `src/main.py` | Qt-Anwendung, Single-Instance, Login, AppRouter |
| `src/ui/app_router.py` | Top-Level-Routing (Dashboard, Core, Ledger, Workforce) |
| `src/ui/main_hub.py` | Hauptfenster mit Sidebar und Views |
| `src/api/client.py` | Basis-HTTP-Client mit JWT und Retry |
| `src/api/auth.py` | Login/Logout, User-Model, Permissions |
| `src/services/document_processor.py` | KI-Klassifikation Pipeline |
| `src/services/global_heartbeat.py` | Session-Pruefung + Benachrichtigungen |
| `src/workforce/api_client.py` | HR-API-Client (30+ Methoden) |
| `src/i18n/de.py` | Deutsche UI-Texte (~2600 Keys) |
| `src/ui/styles/tokens.py` | Design-Tokens (Farben, Fonts, Spacing) |
| `VERSION` | Zentrale Versionsdatei |
