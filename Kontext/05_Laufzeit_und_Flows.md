# 05 - Laufzeit und Flows

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Anwendungsstart

```
python run.py
    -> sys.path.insert(src/)
    -> from main import main
    -> main():
        1. QApplication erstellen
        2. setup_logging() -> RotatingFileHandler (logs/bipro_gdv.log, 5 MB, 3 Backups)
        3. load_embedded_fonts() -> Tenor Sans, Open Sans aus src/ui/assets/fonts/
        4. VERSION-Datei lesen -> APP_VERSION
        5. Single-Instance-Check (Windows Mutex)
        6. API-Server erreichbar? (APIClient.check_connection())
        7. LoginDialog anzeigen (modal)
            -> Benutzername + Passwort
            -> POST /auth/login -> JWT-Token
            -> User-Objekt mit Permissions
        8. Update-Check (synchron, nach Login)
            -> GET /updates/check?version=X&channel=stable
            -> Bei Update: UpdateDialog (optional/mandatory/deprecated)
        9. MainHub erstellen (Hauptfenster)
            -> Sidebar-Navigation (BiPRO, Archiv, GDV, Admin)
            -> Lazy Loading: Views werden erst bei Aufruf erstellt
            -> Update-Timer starten (30 Min Intervall)
            -> ToastManager initialisieren
       10. app.exec() -> Qt Event Loop
```

**Quelle:** `src/main.py`

---

## Login-Flow

```
LoginDialog.login_clicked()
    -> LoginWorker(QThread):
        1. POST /auth/login { username, password }
        2. Response: { success, token, user: { id, username, account_type, permissions } }
        3. Token in APIClient setzen
        4. User-Objekt erstellen (AuthAPI.User)
            -> account_type: 'administrator' oder 'benutzer'
            -> permissions: Liste von Permission-Strings
            -> has_permission(perm) -> bool
            -> is_admin -> bool
    -> Bei Erfolg: dialog.accept() -> MainHub starten
    -> Bei Fehler: Inline-Error-Label (kein Popup seit v1.0.7)
```

**Quelle:** `src/ui/login_dialog.py`, `src/api/auth.py`

---

## BiPRO-Abruf Flow

### Einzelne VU abrufen

```
BiPROView._on_connection_selected(vu):
    1. VU-Credentials vom Server laden
        -> GET /vu-connections/{id}/credentials
        -> AES-entschluesselt: Username + Password
    2. Lieferungen auflisten (FetchShipmentsWorker):
        -> TransferServiceClient._get_sts_token() [BiPRO 410]
        -> TransferServiceClient.list_shipments() [BiPRO 430]
        -> Tabelle fuellen (Kategorie, Datum, Status)
    3. Download (einzeln oder alle):
        a) Einzeln: DownloadShipmentWorker
        b) Alle: ParallelDownloadManager (ThreadPoolExecutor, max 10 Worker)
            -> SharedTokenManager: Ein STS-Token fuer alle Threads
            -> AdaptiveRateLimiter: Bei 429/503 automatisch drosseln
    4. Fuer jede Lieferung:
        -> getShipment() -> MTOM-Response parsen
        -> PDF-Magic-Byte-Validierung
        -> Archiv-Upload (POST /documents mit box_type=eingang)
    5. Nach Download: Automatische KI-Verarbeitung starten
```

### "Alle VUs abholen"

```
BiPROView._fetch_all_vus():
    1. Alle aktiven VU-Verbindungen ermitteln
    2. _vu_queue = [vu1, vu2, ...]
    3. _all_vus_mode = True
    4. _process_next_vu():
        a) Naechste VU aus Queue
        b) Credentials laden
        c) Lieferungen abrufen
        d) Alle herunterladen (ParallelDownloadManager)
        e) Bei Fehler/keine Lieferungen: Naechste VU
        f) Abschluss-Zusammenfassung
```

### IMAP Mail-Import

```
BiPROView._fetch_mails():
    1. MailImportWorker(QThread) starten
    2. Phase 1: IMAP-Poll (Server-seitig)
        -> POST /admin/email-accounts/{id}/poll
        -> Server pollt IMAP, speichert Attachments in Staging
    3. Phase 2: Pending Attachments verarbeiten
        -> GET /email-inbox/pending-attachments
        -> ThreadPoolExecutor (4 Worker, per-Thread API-Client)
        -> Fuer jeden Anhang:
            a) Attachment herunterladen
            b) ZIP? -> extract_zip_contents() (rekursiv, Passwort)
            c) MSG? -> extract_msg_attachments() (Anhaenge extrahieren)
            d) PDF? -> unlock_pdf_if_needed() (Passwort entfernen)
            e) Upload in Eingangsbox
            f) Als importiert markieren (PUT /email-inbox/attachments/{id}/imported)
    4. Toast-Benachrichtigung: ProgressToastWidget (zweiphasig)
```

**Quelle:** `src/ui/bipro_view.py`, `src/bipro/transfer_service.py`

---

## Dokumentenverarbeitungs-Flow

### Upload-Pipeline

```
Upload (Button, Drag & Drop, E-Mail-Anhang, Scan, BiPRO):
    1. Datei-Erkennung:
        a) ZIP -> extract_zip_contents() -> rekursive Verarbeitung (max 3 Ebenen)
        b) MSG -> extract_msg_attachments() -> Anhaenge in Eingang, MSG in Roh
        c) PDF -> unlock_pdf_if_needed() -> Passwort entfernen
        d) Sonstige -> direkt hochladen
    2. Upload: POST /documents { file, box_type=eingang }
    3. Server: SHA256-Hash berechnen, Duplikat-Check, Speichern
```

### Automatische Verarbeitung

```
ProcessingWorker -> DocumentProcessor.process_inbox():
    1. Alle Dokumente in Eingangsbox laden (status=pending)
    2. ThreadPoolExecutor (max 8 Worker):
        Fuer jedes Dokument:
        a) processing_status -> 'processing'
        b) Typ-Erkennung:
            - XML/XBRL -> Roh-Archiv
            - GDV-Endung (.gdv, .txt ohne PDF) -> GDV-Box
                -> GDV parsen: VU-Name + Datum aus 0001-Satz
            - BiPRO-Courtage-Code (300xxx) -> Courtage-Box
            - PDF -> KI-Klassifikation:
                Stufe 1: GPT-4o-mini (2 Seiten, ~200 Token)
                    -> Confidence: high/medium/low
                    -> Bei high/medium: Ergebnis verwenden
                Stufe 2: GPT-4o (5 Seiten) nur bei low
                    -> document_name fuer "Sonstige"
            - Sonstige -> Sonstige-Box
        c) Umbenennung (VU_Typ_Datum.pdf)
        d) processing_status -> 'completed'
    3. Kosten-Tracking:
        -> credits_before (vor Verarbeitung)
        -> DelayedCostWorker: 90s warten
        -> credits_after (nach Verarbeitung)
        -> batch_cost_update in processing_history
```

**Quelle:** `src/services/document_processor.py`, `src/api/openrouter.py`

---

## Smart!Scan-Versand Flow

```
Trigger: Toolbar-Button, Box-Sidebar-Kontextmenue, Dokument-Kontextmenue
    1. Bestaetigung per QMessageBox.question()
    2. SmartScanWorker(QThread):
        a) Settings laden (GET /smartscan/settings)
        b) Dokumente in Chunks aufteilen (max 10 pro Call)
        c) Fuer jeden Chunk:
            -> POST /smartscan/send
            -> Server: PHPMailer -> SMTP -> SCS-SmartScan
            -> Idempotenz: client_request_id (10 Min Fenster)
        d) Post-Send-Aktionen (konfigurierbar):
            -> Archivieren (POST /documents/archive)
            -> Umfaerben (POST /documents/colors)
    3. Toast-Benachrichtigung mit Ergebnis
```

**Quelle:** `src/ui/archive_boxes_view.py`, `BiPro-Webspace Spiegelung Live/api/smartscan.php`

---

## GDV-Editor Flow

```
1. Datei oeffnen (Menue oder Drag & Drop):
    -> parse_file(filepath):
        a) Encoding-Detection (CP1252, Latin-1, UTF-8)
        b) Jede Zeile (256 Bytes) parsen:
            - Position 1-4: Satzart
            - Position 256: Teildatensatz-Nr
            - Layout-Definition laden
            - Felder extrahieren
        c) ParsedFile zurueckgeben (records, errors, warnings)
    -> map_parsed_file_to_gdv_data() -> GDVData
    -> RecordTableWidget (Satzart-Uebersicht)
    -> UserDetailWidget (wichtige Felder, editierbar)
    -> ExpertDetailWidget (alle Felder)
    -> PartnerView (extrahierte Personen/Firmen)

2. Speichern:
    -> save_file(parsed_file, filepath):
        a) Fuer jeden Record: build_line_from_record()
        b) CP1252 Encoding
        c) 256 Bytes pro Zeile
```

**Quelle:** `src/parser/gdv_parser.py`, `src/ui/main_window.py`

---

## PDF-Bearbeitung Flow (v1.1.3)

```
1. Dokument doppelklicken -> PreviewDownloadWorker -> PDFViewerDialog
2. PDFViewerDialog:
    - QPdfView (Qt native) fuer Anzeige
    - PyMuPDF (fitz) fuer Manipulation
    - Thumbnail-Sidebar (QListWidget, 150px)
3. Bearbeitungsoptionen:
    a) Seite rechts drehen (90° CW)
    b) Seite links drehen (90° CCW)
    c) Seite loeschen (Bestaetigung, letzte Seite geschuetzt)
4. Speichern:
    -> PDFSaveWorker(QThread)
    -> POST /documents/{id}/replace (Multipart-Upload)
    -> Server: Datei ersetzen, content_hash + file_size neu berechnen
    -> Client: Vorschau-Cache + Historie-Cache invalidieren
```

**Quelle:** `src/ui/archive_view.py`

---

## Shutdown-Flow (v1.1.4)

```
MainHub.closeEvent(event):
    1. Blockierende Operationen pruefen:
        -> archive_view.get_blocking_operations()
        -> Prueft: _processing_worker, _delayed_cost_worker, _smartscan_worker
        -> Bei blockierend: Toast-Warnung, event.ignore(), RETURN
    2. Ungespeicherte GDV-Aenderungen:
        -> QMessageBox.question() -> bei "Nein": event.ignore(), RETURN
    3. Aufraeumen:
        -> BiPROView.cleanup() (Worker-Threads beenden)
        -> Update-Timer stoppen
        -> UpdateCheckWorker beenden
        -> DropUploadWorker beenden
    4. event.accept()
```

**Quelle:** `src/ui/main_hub.py`, `src/ui/archive_boxes_view.py`

---

## Thread-Uebersicht

### UI-Threads (QThread-Worker)

| Worker | Ort | Zweck |
|--------|-----|-------|
| FetchShipmentsWorker | bipro_view | Lieferungen auflisten |
| DownloadShipmentWorker | bipro_view | Einzelne Lieferung downloaden |
| ParallelDownloadManager | bipro_view | Parallele BiPRO-Downloads (max 10) |
| MailImportWorker | bipro_view | IMAP-Poll + Attachment-Import |
| ProcessingWorker | archive_boxes_view | KI-Dokumentenverarbeitung |
| DelayedCostWorker | archive_boxes_view | 90s Wartezeit fuer Guthaben-Abfrage |
| SmartScanWorker | archive_boxes_view | Smart!Scan E-Mail-Versand |
| MultiUploadWorker | archive_boxes_view | Multi-File-Upload (ZIP/MSG/PDF) |
| MultiDownloadWorker | archive_boxes_view | Multi-File-Download |
| BoxDownloadWorker | archive_boxes_view | Ganze Box herunterladen |
| PreviewDownloadWorker | archive_boxes_view | Vorschau mit Cache |
| DocumentHistoryWorker | archive_boxes_view | Dokument-Historie laden |
| CreditsWorker | archive_boxes_view | OpenRouter-Guthaben |
| CostStatsWorker | archive_boxes_view | Kosten-Statistiken |
| BoxStatsWorker | archive_boxes_view | Box-Zaehler |
| DocumentMoveWorker | archive_boxes_view | Dokumente verschieben |
| CacheDocumentLoadWorker | archive_boxes_view | Cache-Refresh |
| PDFSaveWorker | archive_view | Bearbeitetes PDF speichern |
| UpdateCheckWorker | main_hub | Periodischer Update-Check |
| DropUploadWorker | main_hub | Drag & Drop Upload |
| LoginWorker | login_dialog | Login-Request |
| DownloadWorker | update_dialog | Update-Download |
| ~15 Admin-Worker | admin_view | Daten laden fuer Admin-Panels |

### Thread-Sicherheitsma ssnahmen

| Mechanismus | Ort | Beschreibung |
|-------------|-----|--------------|
| `SharedTokenManager` | transfer_service | Double-Checked Locking fuer STS-Token |
| `_auth_refresh_lock` | client.py | Non-blocking acquire gegen Deadlock |
| `ThreadPoolExecutor` | document_processor | max 8 Worker fuer KI-Verarbeitung |
| `ThreadPoolExecutor` | bipro_view/MailImport | max 4 Worker fuer Attachment-Upload |
| `pause_count` | data_cache | Counter-basierte Auto-Refresh-Pause |
| `_is_worker_running()` | archive_boxes_view | RuntimeError-sicherer Worker-Check |
| Per-Thread API-Client | MailImportWorker | Eigener APIClient pro Upload-Thread |
