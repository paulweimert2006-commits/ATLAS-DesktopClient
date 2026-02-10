# 02 — Massnahmenkatalog

**30 Massnahmen** fuer 30 Befunde aus dem Security Audit.

---

## Welle 1 — Kritisch + Quick Wins

---

### M-001: Hardcoded Fallback-Passwoerter entfernen

| Aspekt | Detail |
|--------|--------|
| Befund | SV-001 (Kritisch) |
| Cluster | A — Secrets im Code/Doku |
| Root Cause | Fallback-Liste als Safety-Net konzipiert, aber exposes Secrets im Quellcode |

**Fix:**
1. `src/services/pdf_unlock.py:23-35`: Beide Listen `_FALLBACK_PDF_PASSWORDS` und `_FALLBACK_ZIP_PASSWORDS` entfernen
2. In `get_known_passwords()` (Zeile 80-84): Den Fallback-Block entfernen. Wenn die API nicht erreichbar ist, leere Liste zurueckgeben und Fehler loggen
3. `AGENTS.md:639`: Die vier Klartext-Passwoerter (`TQMakler37`, `TQMakler2021`, `555469899`, `dfvprovision`) aus der Dokumentation entfernen
4. Git-History: Hinweis an Betreiber, dass die Passwoerter in der Git-History verbleiben und ggf. rotiert werden sollten

**Betroffene Dateien:**
- `src/services/pdf_unlock.py` (Zeilen 23-35, 80-84)
- `AGENTS.md` (Zeile ~639, Seed-Daten-Abschnitt)

**Verifikation:**
- `grep -r "TQMakler" .` liefert 0 Treffer (ausser Git-History)
- `grep -r "555469899" .` liefert 0 Treffer
- App startet, PDF-Unlock funktioniert wenn API erreichbar

**Risiko:** Wenn API nicht erreichbar, schlaegt PDF-Unlock fehl. Akzeptabel: Passwoerter sind in der DB.

---

### M-002: Security Headers einfuegen (Baustein B1)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-002 (Kritisch) |
| Cluster | B — Server-Haertung |
| Root Cause | Kein Security-Header-Layer in PHP-API |

**Fix:**
1. Neue Funktion `send_security_headers()` in `BiPro-Webspace Spiegelung Live/api/lib/response.php` hinzufuegen
2. Headers:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 0` (moderner Ansatz: CSP statt XSS-Filter)
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
3. Aufruf in `BiPro-Webspace Spiegelung Live/api/index.php` direkt nach CORS-Block (vor Routing, Zeile ~18)

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/lib/response.php` (neue Funktion)
- `BiPro-Webspace Spiegelung Live/api/index.php` (1 Aufruf-Zeile)

**Verifikation:**
- `curl -I https://acencia.info/api/status` zeigt alle Security Headers
- Desktop-App funktioniert weiterhin (Headers beeinflussen JSON-API nicht)

**Risiko:** Minimal. Headers sind fuer Browser-Clients relevant, Desktop-App ignoriert sie.

---

### M-003: Rate-Limiting fuer Login (Baustein B2)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-003 (Kritisch) |
| Cluster | B — Server-Haertung |
| Root Cause | Kein Brute-Force-Schutz auf Shared Hosting |

**Fix:**
1. Neue Datei `BiPro-Webspace Spiegelung Live/api/lib/rate_limiter.php`
2. DB-basierter Rate-Limiter (neue Tabelle `rate_limits` oder Nutzung von `activity_log`):
   - Tracking: IP + Username + Zeitstempel
   - Schwellwert: Max. 5 fehlgeschlagene Logins pro IP in 15 Minuten
   - Lockout: 15 Minuten nach Ueberschreitung
   - Cleanup: Abgelaufene Eintraege bei jedem Check entfernen
3. Einbindung in `auth.php` `handleLogin()` VOR `Database::queryOne()` (Zeile ~67)
4. Bei Lockout: HTTP 429 mit `Retry-After` Header
5. Erfolgreicher Login: Rate-Limit-Counter fuer diese IP zuruecksetzen

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/lib/rate_limiter.php` (neue Datei)
- `BiPro-Webspace Spiegelung Live/api/auth.php` (1-2 Aufrufe in handleLogin)
- DB: Neue Tabelle `rate_limits` (Migration-Script)

**Verifikation:**
- 6. Login-Versuch mit falschem Passwort → HTTP 429
- Erfolgreicher Login nach Lockout-Ablauf → HTTP 200
- Desktop-App zeigt verstaendliche Fehlermeldung bei HTTP 429

**Risiko:** Legitimate User bei geteilter IP (NAT) koennten gesperrt werden. Mitigiert durch Username-zusaetzliche Pruefung.

---

### M-012: LIMIT/OFFSET parametrisieren

| Aspekt | Detail |
|--------|--------|
| Befund | SV-012 (Mittel) |
| Cluster | B — Server-Haertung |
| Root Cause | Inkonsistenz: 2 von 8 Dateien nutzen String-Interpolation statt Prepared Statements |

**Fix:**
1. `api/gdv.php:255-263`: `LIMIT $limit OFFSET $offset` durch `LIMIT ? OFFSET ?` ersetzen und `$limit`, `$offset` zu `$params` Array hinzufuegen
2. `api/activity.php:120-127`: Analog `LIMIT {$perPage} OFFSET {$offset}` durch `LIMIT ? OFFSET ?` ersetzen

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/gdv.php` (Zeilen 255-264)
- `BiPro-Webspace Spiegelung Live/api/activity.php` (Zeilen 120-128)

**Verifikation:**
- `grep -n 'LIMIT \$\|LIMIT {' api/*.php` → 0 Treffer (alle parametrisiert)
- GDV-Pagination funktioniert weiterhin
- Activity-Log-Pagination funktioniert weiterhin

**Risiko:** Keines. Int-Cast bleibt als zusaetzliche Absicherung, Prepared Statement als Defense-in-Depth.

---

### M-018: .htaccess fuer setup/ Verzeichnis

| Aspekt | Detail |
|--------|--------|
| Befund | SV-018 (Mittel) |
| Cluster | B — Server-Haertung |
| Root Cause | Synchronisiertes Verzeichnis ohne Zugriffsschutz |

**Fix:**
1. Neue Datei `BiPro-Webspace Spiegelung Live/setup/.htaccess`:
   ```
   # Zugriff auf Migrations-Skripte verbieten
   Require all denied
   ```
2. Alternativ (falls Migrationen per HTTP ausgefuehrt werden muessen): IP-Whitelist
3. Besser: `setup/` aus der Sync-Konfiguration entfernen und Migrationen nur per SSH/SFTP ausfuehren

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/setup/.htaccess` (neue Datei)

**Verifikation:**
- `curl https://acencia.info/setup/migration_admin.php` → HTTP 403
- Sync-Konfiguration pruefen ob setup/ noch enthalten

**Risiko:** Keines. Migrationen werden einmalig ausgefuehrt und danach geloescht (laut AGENTS.md).

---

## Welle 2 — Hoch-Prio Secrets + Validation

---

### M-004: OpenRouter-Proxy (Baustein B3)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-004 (Kritisch) |
| Cluster | A — Secrets im Code/Doku |
| Root Cause | API-Key-Architektur sendet Secret an Client |

**Fix:**
1. Neuer PHP-Endpoint `POST /ai/classify` in `BiPro-Webspace Spiegelung Live/api/ai.php`:
   - Nimmt `document_id` und extrahierten Text entgegen
   - Server ruft OpenRouter API auf (cURL)
   - API-Key bleibt auf dem Server
   - Antwort wird an Client zurueckgegeben
2. `GET /ai/key` Endpoint entfernen oder deprecaten (Zugriff verweigern)
3. Python-Client `src/api/openrouter.py` anpassen:
   - Statt direkt OpenRouter aufzurufen: `POST /ai/classify` am eigenen Server aufrufen
   - `_classify_sparte_request()` und `_classify_sparte_detail()` umleiten
4. Optional: Rate-Limiting auf dem Proxy-Endpoint (max. N Calls pro Minute pro User)

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/ai.php` (neuer Endpoint, alter entfernen)
- `BiPro-Webspace Spiegelung Live/api/index.php` (Route hinzufuegen)
- `src/api/openrouter.py` (Client umleiten auf Proxy)

**Verifikation:**
- `GET /ai/key` → HTTP 404 oder 403
- KI-Klassifikation funktioniert weiterhin (ueber Proxy)
- API-Key nicht im Network-Traffic des Clients sichtbar

**Risiko:** Latenz-Erhoehung (~100-200ms pro Call durch Server-Hop). PHP-Timeout beachten (max_execution_time). Mitigiert durch asynchronen Worker im Client.

---

### M-005: Token-Datei mit OS-Schutz (Baustein B5)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-005 (Hoch) |
| Cluster | A — Secrets im Code/Doku |
| Root Cause | JWT-Token als Klartext-JSON ohne Datei-Permissions |

**Fix:**
1. `src/api/auth.py:302` (`_save_token`): Nach `write_text()` Datei-Permissions setzen:
   - Windows: `icacls` oder `win32security` (nur aktueller User)
   - Minimal: `os.chmod(path, 0o600)` (auf Windows begrenzt wirksam)
2. Langfristig (Baustein B5): `keyring` Library nutzen:
   - `keyring.set_password("acencia_atlas", "jwt_token", token_json)`
   - `keyring.get_password("acencia_atlas", "jwt_token")`
   - Nutzt Windows Credential Manager (DPAPI-geschuetzt)
3. Fallback: Wenn `keyring` nicht verfuegbar, aktuelles Datei-Verfahren mit `0o600`

**Betroffene Dateien:**
- `src/api/auth.py` (Zeilen 295-314: `_save_token`, `_load_saved_token`, `_delete_saved_token`)
- `requirements.txt` (ggf. `keyring>=24.0.0`)

**Verifikation:**
- Token wird nicht mehr als lesbare Datei auf Disk gespeichert
- "Angemeldet bleiben" funktioniert weiterhin nach App-Neustart
- Andere Benutzer auf dem System koennen Token nicht lesen

**Risiko:** `keyring` auf Windows erfordert `pywin32` (bereits als Abhaengigkeit vorhanden). Kein Risiko bei Fallback.

---

### M-006: Passwoerter in DB verschluesseln

| Aspekt | Detail |
|--------|--------|
| Befund | SV-006 (Hoch) |
| Cluster | A — Secrets im Code/Doku |
| Root Cause | `known_passwords.password_value` in Klartext gespeichert |

**Fix:**
1. `passwords.php` (oeffentlicher Endpoint, Zeile 43-49):
   - `SELECT password_value` → Werte nach SELECT mit `Crypto::decrypt()` entschluesseln
   - Fehlerhafte Entschluesselung (alte Klartext-Werte) abfangen und loggen
2. `passwords.php` (Admin-Endpoint):
   - `handleCreatePassword()`: `password_value` mit `Crypto::encrypt()` vor INSERT verschluesseln
   - `handleUpdatePassword()`: Analog bei UPDATE
   - `handleListPasswords()`: Werte beim Auslesen entschluesseln
3. Migration: Bestehende Klartext-Werte einmalig verschluesseln (Migration-Script)

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/passwords.php` (3-4 Stellen)
- `BiPro-Webspace Spiegelung Live/setup/` (neues Migrations-Script)

**Verifikation:**
- `SELECT password_value FROM known_passwords` zeigt nur verschluesselte Base64-Werte
- PDF/ZIP-Unlock funktioniert weiterhin (Entschluesselung transparent)
- Admin-Tab zeigt Passwoerter korrekt an (nach Entschluesselung)

**Risiko:** Migration muss korrekt laufen (Klartext → verschluesselt). Rollback: Werte sind idempotent entschluesselbar. Abhaengigkeit: M-001 muss zuerst abgeschlossen sein (kein Fallback mehr).

---

### M-007: Zip-Bomb-Schutz (kumulatives Groessenlimit)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-007 (Hoch) |
| Cluster | C — Input-Validation |
| Root Cause | Fehlende Defense-in-Depth bei ZIP-Extraktion |

**Fix:**
1. `src/services/zip_handler.py:20-21`: Neue Konstante `MAX_TOTAL_UNCOMPRESSED_SIZE = 500 * 1024 * 1024` (500 MB)
2. In `extract_zip_contents()`: Parameter `_total_size: int = 0` hinzufuegen
3. Vor `f.write(data)` (Zeile 122-123): `_total_size += len(data)` und Pruefung:
   ```python
   if _total_size > MAX_TOTAL_UNCOMPRESSED_SIZE:
       raise ValueError("Kumulatives Groessenlimit ueberschritten")
   ```
4. Bei rekursivem Aufruf (Zeile 131-133): `_total_size` weitergeben und Rueckgabewert aktualisieren
5. Optional: `MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024` (100 MB) pro Einzeldatei

**Betroffene Dateien:**
- `src/services/zip_handler.py` (Zeilen 20-21, 41-45, 99-149)

**Verifikation:**
- ZIP mit >500 MB unkomprimiertem Inhalt → ValueError
- Normale ZIPs (<500 MB) funktionieren weiterhin
- Rekursive ZIPs respektieren kumulatives Limit

**Risiko:** Keines bei vernuenftigem Limit. 500 MB ist grosszuegig fuer Versicherungsdokumente.

---

### M-008: PEM-Temp-Files absichern (Baustein B4)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-008 (Hoch) |
| Cluster | A — Secrets im Code/Doku |
| Root Cause | Private Keys als ungeschuetzte Temp-Files auf Disk |

**Fix:**
1. `src/bipro/transfer_service.py:342-367`: `tempfile.mkstemp()` durch `tempfile.NamedTemporaryFile(delete=False)` ersetzen mit explizitem Permissions-Set (`os.chmod(path, 0o600)`)
2. `atexit`-Handler registrieren der alle PEM-Temp-Files aufraeumt:
   ```python
   import atexit
   _temp_pem_files = []
   atexit.register(lambda: [os.unlink(f) for f in _temp_pem_files if os.path.exists(f)])
   ```
3. Cleanup in `close()` (Zeile 1300-1313) beibehalten als primaerer Cleanup
4. Optional: In-Memory-PEM ueber `requests` Adapter statt Temp-File (bevorzugt wenn machbar)

**Betroffene Dateien:**
- `src/bipro/transfer_service.py` (Zeilen 342-367, 1300-1313)

**Verifikation:**
- PEM-Dateien haben `0o600` Permissions nach Erstellung
- Nach App-Crash: `atexit`-Handler raeumt PEM-Files auf
- BiPRO-Verbindung mit Client-Zertifikat funktioniert weiterhin

**Risiko:** Minimal. `atexit` ist nicht 100% zuverlaessig bei SIGKILL, aber deutlich besser als Status Quo.

---

### M-010: Zertifikate verschluesseln (Baustein B5)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-010 (Hoch) |
| Cluster | A — Secrets im Code/Doku |
| Root Cause | PFX/P12-Dateien unverschluesselt in AppData |

**Fix:**
1. Baustein B5 (DPAPI/Keyring-Wrapper) nutzen:
   - Zertifikat-Bytes lesen → Base64 → `keyring.set_password("acencia_atlas", f"cert_{name}", b64_data)`
   - Laden: `keyring.get_password()` → Base64 → Bytes → tempfile fuer requests
2. Alternativ (einfacher): Zertifikat-Verzeichnis verschluesseln:
   - `os.chmod()` auf Verzeichnis und Dateien (0o700/0o600)
   - Windows: ACLs setzen (nur aktueller User)
3. `src/config/certificates.py:203-204`: Nach `shutil.copy2()` sofort `os.chmod(target, 0o600)`

**Betroffene Dateien:**
- `src/config/certificates.py` (Zeile 203-204 und Lade-Funktionen)
- Ggf. `src/bipro/transfer_service.py` (Zertifikat-Laden)

**Verifikation:**
- Zertifikat-Dateien haben restriktive Permissions
- BiPRO mit Client-Zertifikat funktioniert weiterhin
- Andere OS-Benutzer koennen Zertifikate nicht lesen

**Risiko:** Abhaengigkeit von B5. Fallback auf `chmod` wenn `keyring` nicht verfuegbar.

---

### M-011: Dependency-Lockfile erzeugen

| Aspekt | Detail |
|--------|--------|
| Befund | SV-011 (Hoch) |
| Cluster | E — Supply-Chain |
| Root Cause | `>=` ohne obere Grenze, keine deterministische Installation |

**Fix:**
1. `requirements.txt` anpassen: `>=` durch `==` mit konkreten aktuellen Versionen ersetzen
2. Alternativ: `pip freeze > requirements-lock.txt` ausfuehren und `requirements-lock.txt` committen
3. In `requirements.txt` obere Grenzen setzen: `PySide6>=6.6.0,<7.0.0` etc.
4. `build.bat` anpassen: `pip install -r requirements-lock.txt` statt `requirements.txt`
5. Dokumentation in README: "Fuer Entwicklung `requirements.txt`, fuer Build `requirements-lock.txt`"

**Betroffene Dateien:**
- `requirements.txt` (obere Grenzen setzen)
- `requirements-lock.txt` (neue Datei, gepinnte Versionen)
- `build.bat` (Lockfile referenzieren)

**Verifikation:**
- `pip install -r requirements-lock.txt` ist deterministisch
- Build auf frischem System liefert identische Abhaengigkeiten
- `pip-audit` zeigt keine bekannten CVEs (optional)

**Risiko:** Lockfile muss bei Updates manuell aktualisiert werden. Erhoehter Wartungsaufwand.

---

### M-021: MIME-Type-Whitelist fuer alle Uploads

| Aspekt | Detail |
|--------|--------|
| Befund | SV-021 (Mittel) |
| Cluster | C — Input-Validation |
| Root Cause | MIME-Check nur beim Scan-Upload, nicht beim normalen Upload |

**Fix:**
1. `BiPro-Webspace Spiegelung Live/api/documents.php:408`: MIME-Type-Whitelist einfuehren:
   - Erlaubte Typen: `application/pdf`, `image/jpeg`, `image/png`, `text/plain`, `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/xml`, `text/xml`, `application/zip`, `application/x-zip-compressed`, `application/octet-stream` (fuer .gdv/.dat)
2. Validierung vor dem Speichern (nicht erst nach Upload)
3. Fehlermeldung: HTTP 415 Unsupported Media Type

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/documents.php` (Upload-Handler)

**Verifikation:**
- Upload von .exe → HTTP 415
- Upload von .pdf, .csv, .xlsx, .gdv → Erfolg
- BiPRO-Upload (automatisch) funktioniert weiterhin

**Risiko:** Mittel. Muss alle aktuell genutzten Dateitypen abdecken. `application/octet-stream` als Catch-All fuer unbekannte Typen (GDV-Dateien haben oft keinen definierten MIME-Type).

---

## Welle 3 — Mittel + Niedrig

---

### M-009: Deployment-Prozess dokumentieren

| Aspekt | Detail |
|--------|--------|
| Befund | SV-009 (Hoch) |
| Cluster | G — Deployment/Testing/Monitoring |
| Root Cause | Kein Staging, kein Review-Gate |

**Fix:**
1. Deployment-Checkliste erstellen (`docs/DEPLOYMENT.md`):
   - Pre-Deploy: Smoke-Tests lokal ausfuehren
   - Pre-Deploy: PHP-Syntax-Check (`php -l`) auf allen geaenderten Dateien
   - Deploy: Sync-Tool mit Dry-Run-Option
   - Post-Deploy: API-Health-Check (`GET /status`)
2. Empfehlung fuer zukuenftigen Git-Branch-Workflow:
   - Feature-Branches → Pull Request → Review → Merge → Deploy
3. Empfehlung: WinSCP Sync mit "Compare only" Modus als Zwischenschritt

**Betroffene Dateien:**
- `docs/DEPLOYMENT.md` (neue Datei)
- Ggf. `scripts/deploy_check.bat` oder `scripts/deploy_check.py` (Pre-Deploy-Script)

**Verifikation:**
- Deployment-Checkliste existiert und ist im Repository
- Team kennt den Prozess

**Risiko:** Prozess-Massnahme, kein technischer Fix. Wirkung haengt von Disziplin ab.

---

### M-013: PII-Redaktion bei KI-Klassifikation

| Aspekt | Detail |
|--------|--------|
| Befund | SV-013 (Mittel) |
| Cluster | D — Datenschutz/PII |
| Root Cause | PDF-Textinhalt mit potentiellen PII an OpenRouter |

**Fix (2 Stufen):**
1. **Kurzfristig (mit M-004/B3):** Server-Proxy macht PII-Problem nicht schlimmer, aber zentralisiert den Zugriff → Log-Kontrolle moeglich
2. **Mittelfristig:** PII-Redaktion im Proxy:
   - Regex-basierte Erkennung von: E-Mail-Adressen, Telefonnummern, IBAN, Versicherungsschein-Nummern
   - Ersetzen durch Platzhalter (`[EMAIL]`, `[PHONE]`, `[IBAN]`, `[VS-NR]`)
   - Nur fuer den an OpenRouter gesendeten Text, nicht fuer das Ergebnis

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/ai.php` (im Proxy-Endpoint von B3)

**Verifikation:**
- Text an OpenRouter enthaelt keine E-Mail-Adressen, IBANs, Telefonnummern
- Klassifikation funktioniert weiterhin korrekt (PII sind nicht klassifikationsrelevant)

**Risiko:** Regex kann False Positives/Negatives haben. Vorsicht bei aggressiver Redaktion → KI-Qualitaet koennte leiden.

---

### M-014: PII aus Debug-Logs filtern

| Aspekt | Detail |
|--------|--------|
| Befund | SV-014 (Mittel) |
| Cluster | D — Datenschutz/PII |
| Root Cause | DEBUG-Level loggt Versicherungsschein-Nr und Responses |

**Fix:**
1. `src/bipro/transfer_service.py:1147`: Versicherungsschein-Nr maskieren:
   - Statt `f"VS-Nr: {vsn}"` → `f"VS-Nr: {vsn[:3]}***{vsn[-2:]}"`
2. `src/bipro/transfer_service.py:616`: STS-Response auf max. 200 Zeichen kuerzen und sensititve Felder reduzieren
3. `src/bipro/transfer_service.py:814`: Transfer-Response auf max. 500 Zeichen kuerzen
4. Genereller Review: Alle `logger.debug()` Aufrufe in `transfer_service.py` auf PII pruefen

**Betroffene Dateien:**
- `src/bipro/transfer_service.py` (3-5 Stellen)

**Verifikation:**
- `grep -n "debug.*response" src/bipro/transfer_service.py` → Alle Stellen gekuerzt
- DEBUG-Log enthaelt keine vollstaendigen Versicherungsschein-Nr oder Responses

**Risiko:** Keines. Debugging-Faehigkeit bleibt erhalten (gekuerzte Daten).

---

### M-015: Proxy-Konfigurierbarkeit

| Aspekt | Detail |
|--------|--------|
| Befund | SV-015 (Mittel) |
| Cluster | F — TLS/Netzwerk |
| Root Cause | Proxies explizit deaktiviert |

**Fix:**
1. `src/bipro/transfer_service.py:72-75`: Statt Proxy-Env-Vars loeschen → Konfigurierbare Option:
   - Neues Config-Attribut `use_system_proxy: bool = False`
   - Wenn `True`: System-Proxy nutzen (env vars beibehalten)
   - Wenn `False`: Wie bisher (env vars loeschen)
2. Default bleibt `False` (Abwaertskompatibilitaet)
3. UI-Einstellung: Optional in Settings-Dialog ergaenzen

**Betroffene Dateien:**
- `src/bipro/transfer_service.py` (Zeilen 72-75, 264)

**Verifikation:**
- Default-Verhalten unveraendert (kein Proxy)
- Mit `use_system_proxy=True`: System-Proxy wird genutzt
- BiPRO-Verbindung funktioniert in beiden Modi

**Risiko:** Gering. Default bleibt unveraendert. Proxy-Support ist optional.

---

### M-016: Certificate-Pinning fuer Update-Kanal

| Aspekt | Detail |
|--------|--------|
| Befund | SV-016 (Mittel) |
| Cluster | F — TLS/Netzwerk |
| Root Cause | Kein Pinning fuer kritischen Update-Download |

**Fix:**
1. `src/services/update_service.py`: SHA256-Fingerprint des acencia.info Zertifikats als Pin speichern
2. Vor Download: Zertifikat des Servers pruefen gegen gespeicherten Pin
3. Implementierung via `requests` + `urllib3` Custom-Adapter oder manueller SSL-Socket-Check
4. Pin-Rotation: 2 Pins speichern (aktuell + naechster) fuer Zertifikatwechsel

**Betroffene Dateien:**
- `src/services/update_service.py` (Download-Funktion)
- `src/config/` (Pin-Storage, ggf. eigene Datei)

**Verifikation:**
- Update-Download mit korrektem Zertifikat → Erfolg
- Update-Download mit falschem Zertifikat → Abbruch mit Fehlermeldung
- Zertifikat-Rotation moeglich ohne App-Update

**Risiko:** Pin-Rotation muss vor Zertifikatwechsel eingeplant werden. Sonst: Update-Kanal blockiert.

---

### M-017: Code-Signing fuer Installer

| Aspekt | Detail |
|--------|--------|
| Befund | SV-017 (Mittel) |
| Cluster | E — Supply-Chain |
| Root Cause | Kein Authenticode-Signing |

**Fix:**
1. Code-Signing-Zertifikat beschaffen (z.B. Sectigo, GlobalSign, ~100-300 EUR/Jahr)
2. `build.bat` erweitern: `signtool sign /f cert.pfx /p PASSWORD /t http://timestamp.digicert.com output.exe`
3. `src/services/update_service.py`: Vor Installation Authenticode-Signatur pruefen:
   - `subprocess.run(["powershell", "Get-AuthenticodeSignature", path])`
4. SHA256-Verifikation bleibt als zusaetzliche Schicht

**Betroffene Dateien:**
- `build.bat` (Signatur-Schritt)
- `src/services/update_service.py` (Signatur-Pruefung)

**Verifikation:**
- EXE zeigt "Herausgeber: ACENCIA" bei Rechtsklick → Eigenschaften → Digitale Signaturen
- Windows SmartScreen zeigt kein "Unbekannter Herausgeber"
- Manipulierte EXE → Signatur-Pruefung schlaegt fehl

**Risiko:** Kosten fuer Zertifikat. Zeitaufwand fuer Einrichtung. Erneuerung jaehrlich.

---

### M-019: Log-Retention-Policy

| Aspekt | Detail |
|--------|--------|
| Befund | SV-019 (Mittel) |
| Cluster | D — Datenschutz/PII |
| Root Cause | Unbegrenzte Speicherung von IP/User-Agent in activity_log |

**Fix:**
1. Neues Cleanup-Script `BiPro-Webspace Spiegelung Live/api/lib/log_cleanup.php`:
   - `DELETE FROM activity_log WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)`
   - Alternativ: IP-Adressen nach 30 Tagen anonymisieren (`UPDATE SET ip_address = 'anonymized'`)
2. Aufruf: Als Cron-Job (Strato Cronjob-Manager) oder als Hook in `index.php` mit probabilistischem Trigger (1% der Requests)
3. Konfigurierbare Retention: `config.php` → `LOG_RETENTION_DAYS = 90`

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/lib/log_cleanup.php` (neue Datei)
- `BiPro-Webspace Spiegelung Live/api/config.php` (Konstante)
- `BiPro-Webspace Spiegelung Live/api/index.php` (optionaler probabilistischer Trigger)

**Verifikation:**
- Activity-Log aelter als 90 Tage wird geloescht
- Admin-Ansicht funktioniert weiterhin (nur neuere Eintraege)
- DB-Groesse waechst nicht unbegrenzt

**Risiko:** Alte Audit-Daten gehen verloren. Muss mit Compliance-Anforderungen abgestimmt werden.

---

### M-020: HKDF Key-Derivation

| Aspekt | Detail |
|--------|--------|
| Befund | SV-020 (Mittel) |
| Cluster | F — TLS/Netzwerk |
| Root Cause | Einfaches `hash('sha256', MASTER_KEY)` statt HKDF |

**Fix:**
1. `BiPro-Webspace Spiegelung Live/api/lib/crypto.php:100-103`:
   - Ersetze `hash('sha256', MASTER_KEY, true)` durch PHP HKDF:
   ```php
   // PHP 8.1+: hash_hkdf()
   return hash_hkdf('sha256', MASTER_KEY, 32, 'acencia-atlas-encryption', '');
   ```
   - Fuer PHP 7.4: Eigene HKDF-Implementierung oder `hash_hmac`-basierte Ableitung
2. Optional: Key-Separation (verschiedene Keys fuer VU-Credentials vs. E-Mail-Credentials):
   - `info`-Parameter variieren: `'vu-credentials'`, `'email-credentials'`
3. **Migration**: Bestehende verschluesselte Daten muessen mit altem Key entschluesselt und mit neuem Key re-verschluesselt werden

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/lib/crypto.php` (Zeile 100-103)
- Ggf. Migrations-Script fuer Re-Verschluesselung

**Verifikation:**
- Bestehende verschluesselte VU-Credentials sind nach Migration lesbar
- Neue Verschluesselungen nutzen HKDF
- Key-Derivation ist kryptographisch korrekt

**Risiko:** Hoch wenn Migration fehlschlaegt → Daten nicht mehr entschluesselbar. Backup zwingend vor Migration. Rollback-Plan erforderlich.

---

### M-022: PHP Dependency-Management

| Aspekt | Detail |
|--------|--------|
| Befund | SV-022 (Niedrig) |
| Cluster | E — Supply-Chain |
| Root Cause | Manuelle Library-Verwaltung |

**Fix:**
1. `composer.json` erstellen mit PHPMailer als Abhaengigkeit
2. `composer install` lokal ausfuehren → `composer.lock` committen
3. `api/lib/PHPMailer/` durch `vendor/phpmailer/phpmailer/` ersetzen (Composer-Autoloader)
4. Alternativ (Strato-kompatibel): `composer.json` + `composer.lock` als Dokumentation, manuelles Update wenn Composer nicht auf Strato verfuegbar

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/composer.json` (neue Datei)
- `BiPro-Webspace Spiegelung Live/composer.lock` (neue Datei)
- `BiPro-Webspace Spiegelung Live/api/smartscan.php` (Include-Pfade anpassen)

**Verifikation:**
- PHPMailer ist durch Composer versioniert
- `composer audit` zeigt keine bekannten CVEs

**Risiko:** Strato Shared Hosting hat moeglicherweise keinen Composer-Zugang. Fallback: Lokal verwalten, vendor/ hochladen.

---

### M-023: API-Version aus Health-Check entfernen

| Aspekt | Detail |
|--------|--------|
| Befund | SV-023 (Niedrig) |
| Cluster | B — Server-Haertung |
| Root Cause | Information Disclosure |

**Fix:**
1. `BiPro-Webspace Spiegelung Live/api/index.php:40-44`: `'version' => API_VERSION` entfernen
2. Status-Response nur noch: `{'status': 'ok', 'timestamp': ...}`
3. Version nur fuer authentifizierte Admin-Requests verfuegbar machen (optional)

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/index.php` (Zeile 42)

**Verifikation:**
- `curl https://acencia.info/api/status` zeigt keine Version
- Desktop-App funktioniert (nutzt `/status` nicht fuer Versionsabfrage)

**Risiko:** Keines. Version ist fuer Client-Funktionalitaet nicht relevant.

---

### M-024: Temp-File-Leak bei PDF-Unlock beheben (Baustein B4)

| Aspekt | Detail |
|--------|--------|
| Befund | SV-024 (Niedrig) |
| Cluster | C — Input-Validation |
| Root Cause | `mkstemp` ohne garantiertes Cleanup |

**Fix:**
1. `src/services/pdf_unlock.py:155-166`: Refactoring zu `try/finally` mit garantiertem Cleanup:
   ```python
   temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
   os.close(temp_fd)
   try:
       doc.save(temp_path, encryption=fitz.PDF_ENCRYPT_NONE)
       doc.close()
       shutil.move(temp_path, file_path)
       temp_path = None  # Move erfolgreich, kein Cleanup noetig
   finally:
       if temp_path and os.path.exists(temp_path):
           os.unlink(temp_path)
   ```

**Betroffene Dateien:**
- `src/services/pdf_unlock.py` (Zeilen 155-166)

**Verifikation:**
- PDF-Unlock funktioniert weiterhin
- Nach Fehler: Keine verwaisten Temp-Dateien in TEMP
- Nach Erfolg: Temp-Datei ist weg (verschoben)

**Risiko:** Keines. Rein strukturelles Refactoring.

---

### M-025: Fehler bei MSG-Extraktion nicht verschlucken

| Aspekt | Detail |
|--------|--------|
| Befund | SV-025 (Niedrig) |
| Cluster | C — Input-Validation |
| Root Cause | Bare `except: pass` fuer PDF-Unlock-Fehler |

**Fix:**
1. `src/services/msg_handler.py:109-110`: Statt `except Exception: pass`:
   ```python
   except Exception as e:
       logger.warning(f"PDF-Unlock fuer MSG-Anhang '{filename}' fehlgeschlagen: {e}")
   ```
2. Optional: Fehlgeschlagene Anhaenge in `MsgExtractResult` als Warnung aufnehmen

**Betroffene Dateien:**
- `src/services/msg_handler.py` (Zeile 109-110)

**Verifikation:**
- PDF-Unlock-Fehler bei MSG-Extraktion werden geloggt
- MSG-Verarbeitung bricht nicht ab bei einzelnem Fehler

**Risiko:** Keines. Nur Logging-Verbesserung.

---

### M-026: CRL/OCSP-Hinweis dokumentieren

| Aspekt | Detail |
|--------|--------|
| Befund | SV-026 (Niedrig) |
| Cluster | F — TLS/Netzwerk |
| Root Cause | Keine Zertifikat-Revocation-Pruefung |

**Fix:**
1. Dokumentation in `docs/SECURITY.md`:
   - Beschreibung: Client-Zertifikate werden aktuell nicht gegen CRL/OCSP geprueft
   - Empfehlung: Manuelle Pruefung bei Zertifikat-Rotation
   - Risiko-Bewertung: Gering (Zertifikate werden nur intern zwischen Desktop und VU verwendet)
2. Optional (langfristig): `ssl.SSLContext` mit `check_hostname=True` und OCSP-Stapling

**Betroffene Dateien:**
- `docs/SECURITY.md` (neue Datei oder Ergaenzung)

**Verifikation:**
- Dokumentation vorhanden

**Risiko:** Keines. Nur Dokumentations-Massnahme.

---

### M-027: Lizenz-Kompatibilitaet pruefen

| Aspekt | Detail |
|--------|--------|
| Befund | SV-027 (Niedrig) |
| Cluster | E — Supply-Chain |
| Root Cause | AGPL/GPL-Abhaengigkeiten in Closed-Source-Distribution |

**Fix:**
1. Rechtsberatung einholen fuer PyMuPDF (AGPL) und extract-msg (GPL) Kompatibilitaet
2. Optionen:
   a. Kommerzielle Lizenz fuer PyMuPDF erwerben (verfuegbar bei Artifex)
   b. PyMuPDF durch Alternative ersetzen (z.B. `pypdf` MIT-lizenziert, aber weniger Features)
   c. Distribution als "Aggregation" argumentieren (rechtlich unsicher)
3. Dokumentation der Lizenz-Entscheidung in `docs/LICENSES.md`

**Betroffene Dateien:**
- `docs/LICENSES.md` (neue Datei)
- Ggf. `requirements.txt` (bei Library-Wechsel)

**Verifikation:**
- Lizenz-Dokumentation vorhanden
- Rechtliche Bewertung dokumentiert

**Risiko:** Abhaengig von rechtlicher Bewertung. Kein technisches Risiko.

---

### M-028: Monitoring einrichten

| Aspekt | Detail |
|--------|--------|
| Befund | SV-028 (Niedrig) |
| Cluster | G — Deployment/Testing/Monitoring |
| Root Cause | Kein Monitoring |

**Fix:**
1. Externer Uptime-Monitor (z.B. UptimeRobot, Hetrixtools, kostenlos):
   - URL: `https://acencia.info/api/status`
   - Intervall: 5 Minuten
   - Alert: E-Mail bei Ausfall
2. PHP Error-Logging in separate Datei:
   - `ini_set('error_log', __DIR__ . '/../logs/php_errors.log')`
   - Rotation ueber Strato oder manuell
3. Optional: Einfacher `/health` Endpoint der DB-Verbindung prueft

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/index.php` (ggf. Health-Endpoint)
- Externe Monitoring-Konfiguration

**Verifikation:**
- Uptime-Monitor meldet "Up"
- Bei absichtlichem Ausfall: Alert wird gesendet

**Risiko:** Keines. Nur Verbesserung.

---

### M-029: MySQL-Verbindung mit SSL pruefen

| Aspekt | Detail |
|--------|--------|
| Befund | SV-029 (Niedrig) |
| Cluster | F — TLS/Netzwerk |
| Root Cause | PDO ohne SSL-Parameter |

**Fix:**
1. Pruefen ob Strato MySQL SSL unterstuetzt: `SHOW VARIABLES LIKE 'have_ssl'`
2. Wenn ja: `db.php` anpassen:
   ```php
   $options[PDO::MYSQL_ATTR_SSL_CA] = '/path/to/ca.pem';
   $options[PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT] = true;
   ```
3. Wenn nein (Shared Hosting, internes Netzwerk): Dokumentieren als akzeptiertes Risiko
4. In `docs/SECURITY.md` dokumentieren

**Betroffene Dateien:**
- `BiPro-Webspace Spiegelung Live/api/lib/db.php` (Zeile 16-22)
- `docs/SECURITY.md` (Dokumentation)

**Verifikation:**
- `SHOW STATUS LIKE 'Ssl_cipher'` zeigt aktive Verschluesselung (wenn verfuegbar)
- API-Funktionalitaet unveraendert

**Risiko:** Strato-Shared-Hosting koennte SSL nicht unterstuetzen. Fallback: Dokumentieren.

---

### M-030: Security-Tests erstellen

| Aspekt | Detail |
|--------|--------|
| Befund | SV-030 (Niedrig) |
| Cluster | G — Deployment/Testing/Monitoring |
| Root Cause | Keine Security-spezifischen Tests |

**Fix:**
1. Neue Testdatei `src/tests/test_security.py`:
   - Test: Keine hardcoded Passwords im Code (`grep`-basiert)
   - Test: Security Headers in API-Response (wenn Test-Server verfuegbar)
   - Test: MIME-Type-Whitelist Enforcement
   - Test: Rate-Limiter Verhalten
   - Test: ZIP-Bomb wird abgelehnt (>500 MB)
   - Test: Temp-File-Cleanup nach PDF-Unlock
2. Integration in `scripts/run_checks.py`

**Betroffene Dateien:**
- `src/tests/test_security.py` (neue Datei)
- `scripts/run_checks.py` (Test-Suite erweitern)

**Verifikation:**
- `pytest src/tests/test_security.py` laeuft ohne Fehler
- Alle Security-Tests bestehen

**Risiko:** Keines. Nur Verbesserung der Testabdeckung.

---

## Zusammenfassung

| Welle | Massnahmen | IDs |
|-------|-----------|-----|
| 1 | 5 | M-001, M-002, M-003, M-012, M-018 |
| 2 | 8 | M-004, M-005, M-006, M-007, M-008, M-010, M-011, M-021 |
| 3 | 17 | M-009, M-013, M-014, M-015, M-016, M-017, M-019, M-020, M-022 bis M-030 |
| **Gesamt** | **30** | |
