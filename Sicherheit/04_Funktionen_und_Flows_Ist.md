# 04 — Funktionen und Flows (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 4.1 Login-Flow

```
1. User gibt Username + Passwort ein (login_dialog.py)
2. POST /auth/login (username, password) via HTTPS
3. Server: Username in DB suchen (parameterized query)
4. Server: User nicht gefunden → Dummy-Verify (Timing-Schutz) → 401
5. Server: User gefunden → is_active pruefen → is_locked pruefen
6. Server: password_verify(input, bcrypt_hash)
7. Server: Bei Erfolg → Session in DB anlegen → JWT generieren (HS256, 8h Expiry)
8. Server: Activity-Log: login_success oder login_failed
9. Client: JWT speichern (im Memory + optional in ~/.bipro_gdv_token.json)
10. Client: User-Objekt mit account_type + permissions speichern
```

**Sicherheitsrelevant:**
- Timing-safe Dummy-Verify bei unbekanntem User (`auth.php:74`)
- Bcrypt Cost 12 (`crypto.php:110`)
- Kein Rate-Limiting auf Login-Endpoint
- JWT-Token im Klartext auf Disk bei "Angemeldet bleiben"
- 8h Token-Expiry ohne Refresh-Mechanismus

**Evidenz:** `api/auth.php:67-112`, `src/api/auth.py:90-120`, `src/ui/login_dialog.py:189-252`

## 4.2 Dokument-Upload-Flow

```
1. User waehlt Dateien (Button-Upload, Drag&Drop, oder Outlook-Drop)
2. Client: Permission-Check (documents_upload)
3. Client: Fuer jede Datei:
   a. ZIP? → extract_zip_contents() (rekursiv, max 3 Ebenen)
   b. MSG? → extract_msg_attachments() (Anhaenge extrahieren)
   c. PDF? → unlock_pdf_if_needed() (Passwort entfernen)
4. Client: POST /documents (multipart/form-data)
5. Server: JWT validieren + Permission pruefen
6. Server: Dateiname sanitizen (basename + regex)
7. Server: SHA256-Hash berechnen
8. Server: Duplikat-Check (gleicher Hash in DB?)
9. Server: Atomic Write (Staging-Datei → rename zu Ziel)
10. Server: DB-Insert (mit box_type, source_type, content_hash)
11. Server: Activity-Log
12. Client: Toast-Benachrichtigung (ggf. mit Duplikat-Warnung)
```

**Sicherheitsrelevant:**
- ZIP-Extraktion: Max 3 Ebenen Rekursion, aber kein kumulatives Groessenlimit
- PDF-Unlock: Passwoerter aus DB + Fallback auf Hardcoded-Liste
- MIME-Type-Validierung nur teilweise (server-side bei Scans, nicht bei normalem Upload)
- Path-Traversal: `basename()` + regex Sanitization
- Atomic Write verhindert partielle Dateien

**Evidenz:** `src/ui/main_hub.py:818-860` (Drop), `src/ui/archive_boxes_view.py` (MultiUpload), `api/documents.php:388-592` (Upload-Handler)

## 4.3 BiPRO-Datenabruf-Flow

```
1. User waehlt VU-Verbindung oder "Alle VUs abholen"
2. Client: GET /credentials/{id}/decrypt → Entschluesselte Credentials
3. Client: STS-Token holen (BiPRO 410):
   a. SOAP-Request bauen (_escape_xml fuer Username/Password)
   b. POST zu VU STS-Endpoint (verify=True)
   c. Token extrahieren (SecurityContextToken)
4. Client: listShipments (BiPRO 430):
   a. SOAP-Request mit Token
   b. POST zu VU Transfer-Endpoint
   c. Lieferungen aus XML parsen
5. Client: Fuer jede Lieferung → getShipment:
   a. MTOM/XOP-Response parsen
   b. PDFs/GDVs aus Multipart extrahieren
   c. PDF-Magic-Byte-Validierung
   d. Automatisch in Dokumentenarchiv hochladen
6. Client: Optional acknowledgeShipment
```

**Sicherheitsrelevant:**
- Credentials werden entschluesselt ueber API abgerufen (HTTPS)
- XML-Injection: `_escape_xml()` schuetzt 5 Entities
- MTOM-Parsing: Binary-Parts mit Trailing CRLF/LF-Stripping
- TLS-Verifikation aktiv (`verify=True`)
- Proxy komplett deaktiviert (`trust_env=False`)
- SharedTokenManager: Thread-sicheres Token-Caching

**Evidenz:** `src/bipro/transfer_service.py:549-600` (STS), `src/bipro/transfer_service.py:766-867` (listShipments/getShipment)

## 4.4 KI-Dokumenten-Klassifikation-Flow

```
1. Trigger: Automatisch nach Upload oder manuell
2. Client: GET /ai/key → OpenRouter API-Key
3. Client: Fuer jedes Dokument:
   a. PDF herunterladen (temp)
   b. Text extrahieren (PyMuPDF, 2 Seiten, 3000 Zeichen)
   c. Optional: _build_keyword_hints() bei widersprüchlichen Keywords
   d. Stufe 1: GPT-4o-mini (schnell, guenstig)
      - Gibt box_type + confidence (high/medium/low)
   e. Bei low confidence → Stufe 2: GPT-4o (5 Seiten, 5000 Zeichen)
      - Gibt zusaetzlich document_name
   f. Dokument verschieben + umbenennen
4. Client: Kosten-Check (90s verzoegert, OpenRouter-Guthaben)
```

**Sicherheitsrelevant:**
- API-Key wird vom Server zum Client uebertragen
- PDF-Textinhalt wird an OpenRouter (extern) gesendet — PII-Risiko
- KI-Prompts koennen durch Dokumentinhalt beeinflusst werden (Prompt-Injection)
- Keyword-Hints reduzieren Fehlklassifikation

**Evidenz:** `src/api/openrouter.py` (~1760 Zeilen), `src/services/document_processor.py` (~1524 Zeilen), `api/ai.php`

## 4.5 SmartScan E-Mail-Versand-Flow

```
1. User waehlt Dokumente oder Box → Smart!Scan
2. Client: Permission-Check (smartscan_send)
3. Client: SmartScan-Settings laden (Zieladresse, Modi, Optionen)
4. Client: Bestaetigung per QMessageBox
5. Client: SmartScanWorker (QThread):
   a. Dokumente in Chunks (max 10 pro API-Call)
   b. POST /smartscan/send (mit client_request_id)
6. Server: Idempotenz-Check (client_request_id)
7. Server: E-Mail-Konto-Credentials entschluesseln
8. Server: PHPMailer: SMTP/TLS → Zieladresse
9. Server: Job + Items + Emails in DB loggen
10. Client: Post-Send-Aktionen (Archivieren, Umfaerben)
```

**Sicherheitsrelevant:**
- Idempotenz verhindert Doppelversand (10 Min Fenster)
- E-Mail-Credentials verschluesselt in DB (AES-256-GCM)
- SMTP mit TLS
- Keine Virus-Pruefung der Anhaenge
- Keine MIME-Type-Validierung der Anhaenge

**Evidenz:** `src/ui/archive_boxes_view.py` (SmartScanWorker), `api/smartscan.php`

## 4.6 Auto-Update-Flow

```
1. Trigger: Nach Login (synchron) + alle 30 Minuten (Hintergrund)
2. Client: GET /updates/check?version={current}&channel=stable
3. Server: Neueste passende Version ermitteln
4. Server: Response: version, sha256, download_url, is_mandatory
5. Client: UpdateDialog anzeigen (optional/pflicht/veraltet)
6. Client: EXE herunterladen (HTTPS, verify=True)
7. Client: SHA256-Hash verifizieren (lokal vs. Server-Hash)
8. Client: Bei Mismatch → Datei loeschen, Fehler anzeigen
9. Client: subprocess.Popen([installer, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
```

**Sicherheitsrelevant:**
- SHA256-Verifikation vor Ausfuehrung
- HTTPS fuer Download, aber kein Certificate-Pinning
- Silent Install (`/VERYSILENT`) — keine User-Bestaetigung bei Pflicht-Update
- Kein Code-Signing der EXE
- Oeffentlicher Download-Endpoint (kein JWT noetig)

**Evidenz:** `src/services/update_service.py:110-215`, `api/releases.php:130-165`

## 4.7 IMAP-Mail-Import-Flow

```
1. Trigger: "Mails abholen" Button in BiPRO-Bereich
2. Client: IMAP-Konto ermitteln (aus SmartScan-Settings)
3. Client: MailImportWorker (QThread):
   a. Phase 1: POST /email-accounts/{id}/poll-imap → Server pollt IMAP
   b. Server: IMAP-Verbindung (TLS), Mails abrufen, Anhaenge in Staging
   c. Phase 2: GET /email-accounts/inbox/pending-attachments
   d. Client: Fuer jeden Anhang:
      - Herunterladen
      - ZIP/MSG/PDF-Pipeline (entpacken, entsperren)
      - In Eingangsbox hochladen
   e. PUT /email-accounts/inbox/attachments/{id}/imported
4. Client: Toast mit Ergebnis
```

**Sicherheitsrelevant:**
- IMAP mit TLS/SSL
- Server-seitiges IMAP-Polling (Credentials bleiben auf Server)
- Client-seitige Attachment-Verarbeitung (ZIP, MSG, PDF)
- Parallele Uploads (ThreadPoolExecutor, 4 Worker)
- Per-Thread API-Client (thread-safe)

**Evidenz:** `src/ui/bipro_view.py` (MailImportWorker), `api/email_accounts.php`

## 4.8 Scan-Upload-Flow (Power Automate)

```
1. SharePoint-Flow erkennt neue Datei
2. Power Automate: POST /api/incoming-scans
   - Header: X-API-Key: {SCAN_API_KEY}
   - Body: { fileName, contentBase64, contentType, filePath }
3. Server: API-Key validieren (hash_equals, timing-safe)
4. Server: MIME-Type gegen Whitelist pruefen (PDF, JPG, PNG)
5. Server: Filename sanitizen (Path-Traversal-Schutz)
6. Server: Base64 dekodieren (strict mode)
7. Server: Atomic Write (Staging → rename)
8. Server: DB-Insert (source_type='scan', box_type='eingang')
9. Server: Activity-Log mit SharePoint-Pfad
```

**Sicherheitsrelevant:**
- Timing-safe API-Key-Vergleich (`hash_equals()`)
- MIME-Whitelist (nur PDF, JPG, PNG)
- Base64 strict mode
- 50 MB Limit
- Path-Traversal-Schutz (`basename()` + regex)
- Atomic Write

**Evidenz:** `api/incoming_scans.php:50-238`
