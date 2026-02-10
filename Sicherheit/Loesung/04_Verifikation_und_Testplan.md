# 04 — Verifikation und Testplan

Given/When/Then Tests + Negativ-Tests fuer alle 30 Massnahmen.

---

## Welle 1

### T-001: Hardcoded Passwoerter entfernt (M-001 / SV-001)

**Positiv-Test:**
```
Given: Quellcode nach M-001 Umsetzung
When:  grep -r "TQMakler" src/ AGENTS.md
Then:  0 Treffer
```

**Negativ-Test:**
```
Given: API-Server nicht erreichbar
When:  PDF-Upload mit passwortgeschuetzter PDF
Then:  PDF-Unlock schlaegt fehl mit verstaendlicher Fehlermeldung
       (KEIN Fallback auf hardcoded Passwoerter)
```

**Regressions-Test:**
```
Given: API-Server erreichbar, Passwoerter in DB
When:  PDF-Upload mit passwortgeschuetzter PDF (TQMakler37)
Then:  PDF wird erfolgreich entsperrt und hochgeladen
```

---

### T-002: Security Headers gesetzt (M-002 / SV-002)

**Positiv-Test:**
```
Given: API deployed mit B1 Middleware
When:  curl -I https://acencia.info/api/status
Then:  Response enthaelt:
       Strict-Transport-Security: max-age=31536000; includeSubDomains
       X-Content-Type-Options: nosniff
       X-Frame-Options: DENY
       Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
       Referrer-Policy: strict-origin-when-cross-origin
       Permissions-Policy: camera=(), microphone=(), geolocation=()
```

**Negativ-Test:**
```
Given: API mit Security Headers
When:  Desktop-App macht normalen API-Call (z.B. GET /documents)
Then:  App funktioniert fehlerfrei (Headers werden ignoriert)
```

---

### T-003: Rate-Limiting funktioniert (M-003 / SV-003)

**Positiv-Test:**
```
Given: Rate-Limiter deployed (B2), Schwellwert = 5
When:  6 POST /auth/login mit falschem Passwort von gleicher IP
Then:  Versuche 1-5: HTTP 401 (falsches Passwort)
       Versuch 6:   HTTP 429 mit Retry-After Header
```

**Negativ-Test (Lockout-Ablauf):**
```
Given: IP ist gesperrt (5 Fehlversuche)
When:  15 Minuten warten, dann erneuter Login-Versuch mit korrektem Passwort
Then:  HTTP 200 (Login erfolgreich)
```

**Negativ-Test (Reset nach Erfolg):**
```
Given: 3 Fehlversuche, dann erfolgreicher Login
When:  Erneuter Fehlversuch
Then:  Zaehler ist bei 1 (nicht bei 4), kein Lockout
```

**Desktop-App-Test:**
```
Given: Desktop-App, IP gesperrt
When:  Login-Versuch
Then:  Toast-Meldung: "Zu viele Anmeldeversuche. Bitte warten."
       (KEIN kryptischer Fehler)
```

---

### T-012: LIMIT/OFFSET parametrisiert (M-012 / SV-012)

**Positiv-Test:**
```
Given: gdv.php und activity.php mit Prepared-Statement LIMIT/OFFSET
When:  GET /gdv/records?limit=10&offset=0
Then:  10 Records zurueck, kein SQL-Fehler
```

**Code-Pruefung:**
```
Given: Alle PHP-Dateien in api/
When:  grep -n 'LIMIT \$\|LIMIT {' api/*.php
Then:  0 Treffer (alle parametrisiert)
```

---

### T-018: Setup-Verzeichnis geschuetzt (M-018 / SV-018)

**Positiv-Test:**
```
Given: .htaccess in setup/ deployed
When:  curl https://acencia.info/setup/migration_admin.php
Then:  HTTP 403 Forbidden
```

**Negativ-Test:**
```
Given: .htaccess in setup/ deployed
When:  API-Calls an normale Endpoints (z.B. GET /status)
Then:  Funktionieren weiterhin (kein Einfluss)
```

---

## Welle 2

### T-004: OpenRouter-Proxy funktioniert (M-004 / SV-004)

**Positiv-Test:**
```
Given: Proxy-Endpoint POST /ai/classify deployed
When:  KI-Verarbeitung eines PDF-Dokuments im Archiv
Then:  Dokument wird korrekt klassifiziert (courtage/sach/leben/kranken/sonstige)
```

**Negativ-Test (Key nicht exponiert):**
```
Given: GET /ai/key Endpoint entfernt
When:  curl https://acencia.info/api/ai/key -H "Authorization: Bearer <jwt>"
Then:  HTTP 404 oder 410 (kein API-Key in Response)
```

**PII-Redaktion (M-013):**
```
Given: PDF-Text enthaelt "max.mustermann@email.de" und "DE89370400440532013000"
When:  POST /ai/classify mit diesem Text
Then:  An OpenRouter gesendeter Text enthaelt "[EMAIL]" und "[IBAN]"
       Klassifikation funktioniert trotzdem korrekt
```

---

### T-005: JWT-Token sicher gespeichert (M-005 / SV-005)

**Positiv-Test (Keyring):**
```
Given: keyring installiert, Windows Credential Manager verfuegbar
When:  Login mit "Angemeldet bleiben"
Then:  Token in Windows Credential Manager gespeichert
       KEINE Datei ~/.bipro_gdv_token.json vorhanden
```

**Positiv-Test (Fallback):**
```
Given: keyring NICHT installiert
When:  Login mit "Angemeldet bleiben"
Then:  Token in %APPDATA%/ACENCIA ATLAS/secure/jwt_token.enc
       Datei hat nur User-Permissions (0o600)
```

**Regressions-Test:**
```
Given: Token gespeichert (Keyring oder Fallback)
When:  App neu starten
Then:  Auto-Login funktioniert (Token wird geladen und verifiziert)
```

---

### T-006: DB-Passwoerter verschluesselt (M-006 / SV-006)

**Positiv-Test:**
```
Given: Migration ausgefuehrt (Klartext → verschluesselt)
When:  SELECT password_value FROM known_passwords
Then:  Alle Werte sind Base64-kodierte verschluesselte Strings
       (KEIN "TQMakler37" im Klartext)
```

**Funktions-Test:**
```
Given: Passwoerter verschluesselt in DB
When:  GET /passwords?type=pdf (mit JWT)
Then:  Antwort enthaelt entschluesselte Klartext-Werte
       PDF-Unlock funktioniert damit
```

---

### T-007: Zip-Bomb wird abgelehnt (M-007 / SV-007)

**Positiv-Test:**
```
Given: ZIP-Handler mit kumulativem Limit (500 MB)
When:  Upload einer ZIP-Datei mit 600 MB unkomprimiertem Inhalt
Then:  ValueError: "Kumulatives Groessenlimit ueberschritten"
       Upload wird abgebrochen
```

**Negativ-Test (Normale ZIP):**
```
Given: ZIP-Handler mit Limit
When:  Upload einer normalen ZIP-Datei (10 MB, 5 PDFs)
Then:  Alle 5 PDFs erfolgreich extrahiert und hochgeladen
```

---

### T-008: PEM-Temp-Files abgesichert (M-008 / SV-008)

**Positiv-Test:**
```
Given: PEM-Files werden mit TempFileTracker registriert
When:  BiPRO-Verbindung mit Client-Zertifikat oeffnen und schliessen
Then:  Keine PEM-Files im TEMP-Verzeichnis zurueckgeblieben
```

**Crash-Test:**
```
Given: PEM-File registriert, App wird beendet (nicht per kill -9)
When:  atexit-Handler laeuft
Then:  PEM-File wird geloescht
```

**Permissions-Test:**
```
Given: PEM-File erstellt
When:  stat(pem_path)
Then:  Permissions sind 0o600 (nur Owner read/write)
```

---

### T-010: Zertifikate sicher gespeichert (M-010 / SV-010)

**Positiv-Test:**
```
Given: Zertifikat-Speicherung ueber secure_storage
When:  Neues PFX-Zertifikat importieren
Then:  Zertifikat in Keyring oder in %APPDATA%/.../secure/cert_*.enc
       NICHT als Klartext-PFX in certs/
```

**Regressions-Test:**
```
Given: Zertifikat gespeichert
When:  BiPRO-Verbindung mit diesem Zertifikat aufbauen
Then:  Verbindung erfolgreich
```

---

### T-011: Lockfile existiert (M-011 / SV-011)

**Positiv-Test:**
```
Given: requirements-lock.txt im Repository
When:  pip install -r requirements-lock.txt auf neuem System
Then:  Exakt gleiche Versionen installiert
```

**Code-Pruefung:**
```
Given: requirements.txt
When:  Pruefe Versionsangaben
Then:  Alle Eintraege haben obere Grenze (z.B. >=6.6.0,<7.0.0)
```

---

### T-021: MIME-Whitelist erzwingt Typen (M-021 / SV-021)

**Positiv-Test:**
```
Given: MIME-Whitelist in documents.php aktiv
When:  Upload einer .exe Datei
Then:  HTTP 415 Unsupported Media Type
```

**Negativ-Test (Erlaubte Typen):**
```
Given: Whitelist aktiv
When:  Upload von .pdf, .csv, .xlsx, .gdv, .xml
Then:  Alle erfolgreich hochgeladen
```

---

## Welle 3

### T-009: Deployment-Checkliste existiert (M-009 / SV-009)

```
Given: docs/DEPLOYMENT.md vorhanden
When:  Datei oeffnen
Then:  Enthaelt Pre-Deploy, Deploy, Post-Deploy Schritte
```

### T-013: PII-Redaktion aktiv (M-013 / SV-013)

```
Given: Proxy mit PII-Redaktion
When:  Text mit "max@example.com" an /ai/classify senden
Then:  OpenRouter erhaelt "[EMAIL]" statt der Adresse
```

### T-014: Debug-Logs ohne PII (M-014 / SV-014)

```
Given: transfer_service.py mit maskierter Ausgabe
When:  BiPRO-Abruf im DEBUG-Modus
Then:  Log enthaelt "VS-Nr: 123***99" statt voller Nummer
```

### T-015: Proxy konfigurierbar (M-015 / SV-015)

```
Given: use_system_proxy=True konfiguriert
When:  BiPRO-Request
Then:  System-Proxy-Einstellungen werden genutzt
```

### T-016: Certificate-Pinning aktiv (M-016 / SV-016)

```
Given: Pin fuer acencia.info gespeichert
When:  Update-Download mit korrektem Zertifikat
Then:  Download erfolgreich
```
```
Given: Pin fuer acencia.info gespeichert
When:  Update-Download mit falschem Zertifikat (MITM)
Then:  Download abgebrochen mit Sicherheitswarnung
```

### T-017: Installer signiert (M-017 / SV-017)

```
Given: Code-Signing-Zertifikat konfiguriert
When:  build.bat ausfuehren
Then:  Resultierende EXE hat gueltige Authenticode-Signatur
```

### T-019: Log-Retention aktiv (M-019 / SV-019)

```
Given: Retention-Policy 90 Tage
When:  Cleanup laeuft
Then:  activity_log Eintraege aelter 90 Tage sind geloescht
```

### T-020: HKDF Key-Derivation (M-020 / SV-020)

```
Given: crypto.php mit hash_hkdf()
When:  Neue VU-Credentials verschluesseln
Then:  Key wird mit HKDF abgeleitet (nicht mit einfachem SHA256)
```
```
Given: Migration ausgefuehrt
When:  Bestehende VU-Credentials entschluesseln
Then:  Entschluesselung erfolgreich mit neuem Key
```

### T-022: PHP Dependency-Management (M-022 / SV-022)

```
Given: composer.json + composer.lock vorhanden
When:  composer audit
Then:  Keine bekannten CVEs in PHPMailer
```

### T-023: API-Version entfernt (M-023 / SV-023)

```
Given: index.php ohne Version im Status
When:  curl https://acencia.info/api/status
Then:  Response enthaelt KEIN "version" Feld
```

### T-024: PDF-Temp-Cleanup garantiert (M-024 / SV-024)

```
Given: pdf_unlock.py mit try/finally
When:  PDF-Unlock mit absichtlichem Fehler
Then:  Temp-File ist aufgeraeumt (nicht im TEMP-Verzeichnis)
```

### T-025: MSG-Fehler geloggt (M-025 / SV-025)

```
Given: msg_handler.py mit Logging statt pass
When:  MSG-Extraktion mit fehlerhaftem PDF-Anhang
Then:  Log enthaelt Warnung mit Dateiname und Fehlergrund
```

### T-026: CRL/OCSP dokumentiert (M-026 / SV-026)

```
Given: docs/SECURITY.md vorhanden
When:  Nach "CRL" oder "OCSP" suchen
Then:  Dokumentation mit Risiko-Bewertung gefunden
```

### T-027: Lizenz-Dokumentation (M-027 / SV-027)

```
Given: docs/LICENSES.md vorhanden
When:  Datei pruefen
Then:  Enthaelt Bewertung von PyMuPDF (AGPL) und extract-msg (GPL)
```

### T-028: Monitoring aktiv (M-028 / SV-028)

```
Given: Externer Uptime-Monitor konfiguriert
When:  API absichtlich stoppen
Then:  Alert-Email innerhalb von 5 Minuten
```

### T-029: MySQL-SSL dokumentiert (M-029 / SV-029)

```
Given: DB-Verbindung geprueft
When:  SHOW STATUS LIKE 'Ssl_cipher' auf Strato
Then:  Ergebnis dokumentiert (SSL aktiv oder akzeptiertes Risiko)
```

### T-030: Security-Tests vorhanden (M-030 / SV-030)

```
Given: src/tests/test_security.py vorhanden
When:  pytest src/tests/test_security.py
Then:  Alle Tests bestehen:
       - test_no_hardcoded_passwords
       - test_zip_bomb_protection
       - test_temp_file_cleanup
       - test_mime_whitelist
```
