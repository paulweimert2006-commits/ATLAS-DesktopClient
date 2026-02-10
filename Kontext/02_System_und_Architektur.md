# 02 - System und Architektur

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Systemuebersicht

ACENCIA ATLAS ist eine **4-Schichten-Architektur** mit Desktop-Client, Server-Backend, externen Diensten und lokalen Dateien:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Desktop-App (PySide6/Qt)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  UI Layer (~21.500 Zeilen)                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐ ┌─────────────────┐  │
│  │ main_hub.py  │ │bipro_view.py │ │archive_boxes_  │ │ admin_view.py   │  │
│  │ Navigation   │ │ BiPRO-Abruf  │ │ view.py        │ │ 10 Admin-Panels │  │
│  │ Drag & Drop  │ │ MailImport   │ │ Box-System     │ │ Sidebar-Nav     │  │
│  │ Schliess-    │ │ ParallelDL   │ │ Smart!Scan     │ │                 │  │
│  │ Schutz       │ │ "Alle VUs"   │ │ PDF-Bearbeitung│ │                 │  │
│  │ toast.py     │ │              │ │ Dok-Historie   │ │                 │  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬─────────┘ └───────┬─────────┘  │
│         └────────────────┴────────────────┴────────────────────┘            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Service Layer (~12.000 Zeilen)                                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐ ┌─────────────┐  │
│  │  API Clients    │ │  BiPRO Client   │ │  Services    │ │  Parser     │  │
│  │  (src/api/)     │ │  (src/bipro/)   │ │              │ │(src/parser/)│  │
│  │  ~5.800 Zeilen  │ │  ~2.400 Zeilen  │ │  ~3.400 Z.   │ │  ~750 Z.   │  │
│  │  client, docs,  │ │  transfer_svc,  │ │  data_cache,  │ │  gdv_parser │  │
│  │  openrouter,    │ │  rate_limiter,  │ │  doc_proc,    │ │  gdv_layouts│  │
│  │  smartscan,     │ │  categories     │ │  pdf_unlock,  │ │             │  │
│  │  admin, passwd  │ │                 │ │  zip_handler, │ │             │  │
│  │                 │ │                 │ │  msg_handler  │ │             │  │
│  └────────┬────────┘ └────────┬────────┘ └──────┬───────┘ └──────┬──────┘  │
└───────────┼───────────────────┼─────────────────┼────────────────┼─────────┘
            │                   │                 │                │
            ▼                   ▼                 ▼                ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
│  Strato Webspace │ │  Versicherer     │ │  OpenRouter  │ │  Lokales FS  │
│  PHP REST API    │ │  BiPRO Services  │ │  KI (GPT-4o) │ │  GDV-Dateien │
│  MySQL + Files   │ │  (Degenia, VEMA) │ │  Klassifik.  │ │  Temp-Cache  │
│  ~20 Endpunkte   │ │                  │ │              │ │              │
└──────────────────┘ └──────────────────┘ └──────────────┘ └──────────────┘
```

---

## Schichten im Detail

### 1. UI Layer (`src/ui/`)

| Komponente | Datei | Zeilen | Beschreibung |
|------------|-------|--------|--------------|
| MainHub | `main_hub.py` | ~1145 | Navigation, Drag & Drop Upload, Schliess-Schutz, Update-Check |
| BiPROView | `bipro_view.py` | ~4950 | VU-Verbindungen, ParallelDownloadManager, MailImportWorker, "Alle VUs abholen" |
| ArchiveBoxesView | `archive_boxes_view.py` | ~5380 | Box-System, Smart!Scan, PDF-Bearbeitung, Dokument-Historie, Duplikat-Spalte, Tastenkuerzel, Schliess-Schutz |
| AdminView | `admin_view.py` | ~4000 | 10 Panels in 3 Sektionen (Verwaltung, Monitoring, E-Mail), vertikale Sidebar |
| ToastManager | `toast.py` | ~558 | Toast-Benachrichtigungen (success/error/warning/info) + ProgressToast |
| GDVEditorView | `gdv_editor_view.py` | ~597 | GDV-Dateien bearbeiten |
| MainWindow | `main_window.py` | ~1060 | GDV-Editor Hauptfenster mit Tabelle + Detail |
| PartnerView | `partner_view.py` | ~1138 | Firmen/Personen-Uebersicht |
| PDFViewerDialog | `archive_view.py` | ~1957 | PDF-Vorschau mit Bearbeitung (Drehen, Loeschen, Speichern) |
| UpdateDialog | `update_dialog.py` | ~360 | Auto-Update (optional/mandatory/deprecated) |
| LoginDialog | `login_dialog.py` | ~270 | JWT-Authentifizierung |

**Design-System:** ACENCIA Corporate Identity via `src/ui/styles/tokens.py` (~976 Zeilen)
- Primaer: #001f3d (dunkel), Akzent: #fa9939 (orange)
- Tenor Sans (Headlines), Open Sans (Body)
- 8 Dokumenten-Farbmarkierungen, Box-Farben

### 2. API Clients (`src/api/`)

| Klasse | Datei | Zeilen | Beschreibung |
|--------|-------|--------|--------------|
| APIClient | `client.py` | ~513 | Basis-HTTP-Client mit JWT, Retry (exp. Backoff), Deadlock-Schutz |
| DocumentsAPI | `documents.py` | ~864 | CRUD, Bulk-Ops, Farben, Historie, Datei-Ersetzung |
| OpenRouterClient | `openrouter.py` | ~1878 | Zweistufige KI-Klassifikation, Keyword-Hints, OCR |
| SmartScanAPI | `smartscan.py` | ~501 | SmartScan-Versand + EmailAccounts-CRUD |
| AdminAPI | `admin.py` | ~241 | Nutzerverwaltung (Admin) |
| PasswordsAPI | `passwords.py` | ~152 | PDF/ZIP-Passwoerter (Public + Admin CRUD) |
| ReleasesAPI | `releases.py` | ~156 | Auto-Update (Admin CRUD + Public Check) |
| ProcessingHistoryAPI | `processing_history.py` | ~370 | Audit-Trail, Kosten-Historie |
| AuthAPI | `auth.py` | ~323 | Login/Logout/Verify, User-Model mit Permissions |
| VUConnectionsAPI | `vu_connections.py` | ~426 | VU-Verbindungsverwaltung |

### 3. BiPRO Client (`src/bipro/`)

| Klasse | Datei | Zeilen | Beschreibung |
|--------|-------|--------|--------------|
| TransferServiceClient | `transfer_service.py` | ~1519 | BiPRO 410 STS + 430 Transfer, MTOM/XOP, Multi-VU |
| SharedTokenManager | `transfer_service.py` | (enthalten) | Thread-sicheres Token-Management, Double-Checked Locking |
| AdaptiveRateLimiter | `rate_limiter.py` | ~342 | Dynamische Rate-Anpassung bei 429/503 |

### 4. Services (`src/services/`)

| Klasse | Datei | Zeilen | Beschreibung |
|--------|-------|--------|--------------|
| DocumentProcessor | `document_processor.py` | ~1515 | Parallele Verarbeitung (ThreadPoolExecutor), KI-Klassifikation |
| DataCacheService | `data_cache.py` | ~589 | Singleton-Cache, Auto-Refresh mit pause/resume |
| MsgExtractResult | `msg_handler.py` | ~152 | Outlook .msg Anhaenge extrahieren |
| ZipExtractResult | `zip_handler.py` | ~288 | ZIP entpacken (AES-256, rekursiv) |
| pdf_unlock | `pdf_unlock.py` | ~182 | PDF-Passwortschutz entfernen (Passwoerter aus DB) |
| UpdateService | `update_service.py` | ~236 | Auto-Update Check + Download + Install |

### 5. Parser Layer

| Klasse | Datei | Zeilen | Beschreibung |
|--------|-------|--------|--------------|
| gdv_parser | `parser/gdv_parser.py` | ~750 | Fixed-Width Parser (CP1252, 256 Bytes/Zeile) |
| gdv_layouts | `layouts/gdv_layouts.py` | ~506 | Satzart-Definitionen als Metadaten |

### 6. Domain Layer

| Klasse | Datei | Zeilen | Beschreibung |
|--------|-------|--------|--------------|
| models | `domain/models.py` | ~622 | GDVData, Contract, Customer, Risk, Coverage, Enums |
| mapper | `domain/mapper.py` | ~475 | ParsedRecord -> Domain-Objekt Mapping |

---

## Datenflüsse

### 1. BiPRO-Abruf (inkl. Mail-Import)

```
VU auswaehlen -> STS-Token holen (BiPRO 410) -> listShipments (BiPRO 430)
    -> Tabelle fuellen -> Download (parallel, max 10 Worker) -> MTOM parsen
    -> Archiv-Upload -> KI-Verarbeitung (automatisch)

ODER: "Mails abholen" -> IMAP-Poll (Server) -> Attachments downloaden
    -> ZIP/MSG/PDF-Pipeline -> Eingangsbox -> KI-Verarbeitung
```

### 2. Dokumentenverarbeitung

```
Eingangsbox -> DocumentProcessor (ThreadPoolExecutor, 8 Worker)
    -> XML? -> Roh-Archiv
    -> GDV-Endung? -> GDV-Box (mit VU/Datum aus Datei)
    -> BiPRO-Courtage-Code? -> Courtage-Box
    -> PDF? -> KI-Klassifikation:
        Stufe 1: GPT-4o-mini (2 Seiten, Confidence-Scoring)
        Stufe 2: GPT-4o (5 Seiten) nur bei low Confidence
    -> Sach/Leben/Kranken/Courtage/Sonstige Box
    -> Umbenennung: VU_Typ_Datum.pdf
```

### 3. GDV-Editor

```
Datei oeffnen -> parse_file() -> ParsedFile
    -> map_parsed_file_to_gdv_data() -> GDVData
    -> RecordTableWidget + UserDetailWidget + PartnerView
```

### 4. Smart!Scan

```
Dokumente auswaehlen -> SmartScanWorker (QThread)
    -> Chunking (max 10 Docs/Call) -> POST /smartscan/send
    -> PHPMailer -> SMTP -> SCS-SmartScan
    -> Post-Send: Archivieren + Umfaerben (optional)
```

---

## Externe Systeme

| System | Protokoll | Auth | Beschreibung |
|--------|-----------|------|--------------|
| Strato Webspace | HTTPS REST | JWT Bearer | PHP API + MySQL + Dateispeicher |
| BiPRO Degenia | HTTPS SOAP | STS-Token | Lieferungen abrufen |
| BiPRO VEMA | HTTPS SOAP | STS-Token (VEMA-spezifisch) | Lieferungen abrufen |
| OpenRouter | HTTPS REST | Bearer Token | GPT-4o/4o-mini KI-Klassifikation |
| Power Automate | HTTPS REST | API-Key (X-API-Key) | Scan-Upload von SharePoint |

---

## Kommunikation

| Verbindung | Protokoll | Auth |
|------------|-----------|------|
| Desktop <-> PHP API | HTTPS REST | JWT Bearer Token |
| Desktop <-> BiPRO | HTTPS SOAP | STS-Token (BiPRO 410) |
| Desktop <-> OpenRouter | HTTPS REST | Bearer Token |
| PHP API <-> MySQL | TCP | Credentials in config.php |
| PHP API <-> IMAP | TLS | IMAP-Credentials (AES-256-GCM verschluesselt) |
| PHP API <-> SMTP | TLS | SMTP-Credentials (AES-256-GCM verschluesselt) |
| Power Automate -> PHP API | HTTPS | API-Key Header |
