# 06 — Input Validation und Datenfluss (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 6.1 Server-seitige Input-Validierung

### Dokument-Upload (`api/documents.php`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Dateiname-Sanitization | `basename()` + `preg_replace` (Sonderzeichen entfernen) | `api/documents.php:411-412` |
| Dateigroesse | `MAX_UPLOAD_SIZE` Check | `api/documents.php:403` |
| MIME-Type-Pruefung | **Optional** (nicht erzwungen bei normalem Upload) | `api/documents.php:408` |
| Magic-Byte-Validierung | **Nicht vorhanden** (keine Dateiinhalt-Pruefung) | Kein Code |
| Path-Traversal-Schutz | `basename()` entfernt Verzeichnis-Pfade | `api/documents.php:411` |
| SHA256-Hash | Berechnet nach Upload | `api/documents.php:447` |
| Duplikat-Erkennung | Hash-Vergleich gegen bestehende Dokumente | `api/documents.php:489-513` |
| Atomic Write | Staging-Datei → `rename()` | `api/documents.php:430-545` |

### Scan-Upload (`api/incoming_scans.php`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| API-Key-Auth | `hash_equals()` (timing-safe) | `api/incoming_scans.php:67` |
| Pflichtfelder | `fileName`, `contentBase64` | `api/incoming_scans.php:103` |
| MIME-Type-Whitelist | Nur PDF, JPG, PNG erlaubt | `api/incoming_scans.php:111-112` |
| Extension-Pruefung | Doppelte Pruefung: Content-Type + Dateiendung | `api/incoming_scans.php:326-364` |
| Dateiname-Sanitization | `basename()` + regex + Path-Traversal-Check | `api/incoming_scans.php:115, 376-397` |
| Base64-Dekodierung | Strict Mode (`base64_decode($data, true)`) | `api/incoming_scans.php:122` |
| Groessenlimit | 50 MB | `api/incoming_scans.php:131-138` |
| SHA256-Hash | Berechnet nach Dekodierung | `api/incoming_scans.php` |
| Atomic Write | Staging → `rename()` | `api/incoming_scans.php:146-238` |

### Release-Upload (`api/releases.php`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Admin-Only | `requireAdmin()` | `api/releases.php:179` |
| Version-Validierung | SemVer Regex | `api/releases.php:279` |
| Dateigroesse | `MAX_RELEASE_SIZE` (250 MB) | `api/releases.php:310` |
| SHA256-Hash | Berechnet nach Upload | `api/releases.php:325` |
| Duplikat-Check | Version-Uniqueness in DB | `api/releases.php:284-290` |
| MIME-Type-Pruefung | **Nicht vorhanden** | Kein Code fuer EXE-Validierung |
| Code-Signing-Pruefung | **Nicht vorhanden** | Kein Authenticode-Check |

### GDV-Operationen (`api/gdv.php`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Document-ID-Validierung | **Nicht als Integer validiert** | `api/gdv.php:18` |
| Dateiinhalt-Validierung | Encoding-Erkennung (CP1252, Latin-1, UTF-8) | `api/gdv.php:379-395` |
| SQL LIMIT/OFFSET | `(int)` Cast, dann String-Interpolation | `api/gdv.php:255-263` |
| Datei-Groessenlimit | **Nicht vorhanden** (`file_get_contents` ohne Limit) | `api/gdv.php:139` |

## 6.2 Client-seitige Input-Verarbeitung

### ZIP-Extraktion (`src/services/zip_handler.py`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Rekursionstiefe | Max 3 Ebenen | `src/services/zip_handler.py:20-21` |
| Dateiname-Sanitization | `_sanitize_filename()` entfernt Path-Separatoren | `src/services/zip_handler.py:279-284` |
| Passwort-Entschluesselung | Passwoerter aus DB + Fallback auf Hardcoded-Liste | `src/services/zip_handler.py:215-276` |
| Per-File-Groessenlimit | **Nicht vorhanden** | Kein Size-Check pro extrahierter Datei |
| Kumulatives Groessenlimit | **Nicht vorhanden** | Kein Tracking der Gesamtgroesse |
| Temp-Verzeichnis | `tempfile.mkdtemp()` mit Prefix | `src/services/zip_handler.py:74` |
| Zip-Bomb-Schutz | **Nur Rekursionslimit, kein Groessenschutz** | Keine Size-Validierung |

### MSG-Extraktion (`src/services/msg_handler.py`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Dateiendung-Check | `.msg` Extension | `src/services/msg_handler.py:31-33` |
| Dateiname-Sanitization | `_sanitize_filename()` | `src/services/msg_handler.py:133-140` |
| Attachment-Groessenlimit | **Nicht vorhanden** | Kein Size-Check |
| Temp-Verzeichnis | `tempfile.mkdtemp()` | `src/services/msg_handler.py:58` |
| Error-Handling | Fehler bei PDF-Unlock werden verschluckt | `src/services/msg_handler.py:102-110` |

### PDF-Entsperrung (`src/services/pdf_unlock.py`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Extension-Check | `.pdf` vor Verarbeitung | `src/services/pdf_unlock.py:121` |
| Passwortquelle | API (Session-Cache) + Fallback Hardcoded | `src/services/pdf_unlock.py:42-94` |
| Thread-Safety | `threading.Lock()` fuer Cache | `src/services/pdf_unlock.py:38-39` |
| Temp-File | `tempfile.mkstemp()` | `src/services/pdf_unlock.py:155` |
| Temp-Cleanup | Nur bei Exception (nicht im Normalfall) | `src/services/pdf_unlock.py:155-161` |

### Drag&Drop-Upload (`src/ui/main_hub.py`)

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Permission-Check | `documents_upload` vor Upload | `src/ui/main_hub.py:818-823` |
| Dateisammlung | Rekursiv bei Ordnern, Hidden Files ausgeschlossen | `src/ui/main_hub.py:974-986` |
| Dateivalidierung (Client) | **Keine Typ-/Groessenvalidierung** | Kein Code |
| Outlook COM | `win32com.client.GetActiveObject("Outlook.Application")` | `src/ui/main_hub.py:899` |
| Outlook-Filename-Sanitization | `_sanitize_outlook_filename()` | `src/ui/main_hub.py:964-972` |

## 6.3 Datenfluss-Analyse

### Unkontrollierte Datenfluesse

| Von | Nach | Daten | Validierung |
|-----|------|-------|-------------|
| BiPRO VU | Desktop-App | PDFs, GDV-Dateien | PDF-Magic-Byte-Check, sonst keine Validierung |
| Desktop-App | OpenRouter API | PDF-Textinhalt (2-5 Seiten) | Keine PII-Filterung |
| Desktop-App | PHP API | Beliebige Dateien | Server-seitig: basename() + Duplikat-Check |
| Power Automate | PHP API | PDF/JPG/PNG (Base64) | MIME-Whitelist, Groessenlimit, Sanitization |
| IMAP-Server | PHP Staging | E-Mail-Anhaenge | Server: IMAP-Staging, Client: ZIP/MSG/PDF-Pipeline |

### PII-Datenfluesse

| Quelle | Ziel | Datentyp | Schutz |
|--------|------|----------|--------|
| GDV-Dateien | UI (Partner-View) | Namen, Adressen, Geburtstage, IBANs | Nur Anzeige, keine Persistierung |
| PDFs | OpenRouter API (extern) | PDF-Text (kann PII enthalten) | HTTPS, aber Daten bei Drittanbieter |
| VU-Credentials | BiPRO-Endpunkte | Username, Passwort | TLS, XML-Escaping |
| User-Passwoerter | MySQL | bcrypt Hash | Einweg-Hash |
| E-Mail-Credentials | MySQL | AES-256-GCM | Verschluesselt |
| VU-Credentials | MySQL | AES-256-GCM | Verschluesselt |
| PDF/ZIP-Passwoerter | MySQL | **Klartext** | Keine Verschluesselung |

## 6.4 Datei-Upload-Zusammenfassung

### Upload-Typen und Sicherheitskontrollen

| Upload-Typ | Typ-Pruefung | Groessenlimit | Sanitization | Atomic Write | Path-Traversal |
|------------|-------------|---------------|--------------|--------------|----------------|
| Button-Upload | Nein (server-side) | Server (MAX_UPLOAD_SIZE) | Server (basename+regex) | Ja | Ja |
| Drag&Drop | Nein | Server | Server | Ja | Ja |
| Scan-Upload | MIME-Whitelist | 50 MB | basename+regex+strict | Ja | Ja |
| Release-Upload | Nein | 250 MB | Nein (Filename generiert) | `move_uploaded_file()` | N/A (generiert) |
| IMAP-Anhang | Nein | Nein | Server-Staging | Ja | Ja |

### Owner/Tenant-Pruefung

| Aspekt | IST-Zustand | Evidenz |
|--------|-------------|---------|
| Multi-Tenant | Nein (alle User teilen sich alle Dokumente) | Kein Tenant-Feld in documents-Tabelle |
| Dokument-Ownership | Nein (kein Owner-Feld) | `api/documents.php` |
| Zugriffsschutz | Nur via Permissions (nicht pro Dokument) | `api/lib/permissions.php` |

**Anmerkung:** Das System ist fuer ein kleines Team (2-5 Personen) konzipiert. Alle authentifizierten Benutzer mit der entsprechenden Permission haben Zugriff auf alle Dokumente. Es gibt keine dokumentenbasierte Zugriffskontrolle.
