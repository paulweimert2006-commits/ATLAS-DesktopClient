# 12 — Schwachstellen und Fehlverhalten (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## Schweregrad-Definitionen

| Schweregrad | Definition |
|-------------|-----------|
| **Kritisch** | Sofortige Ausnutzung moeglich, schwerer Schaden |
| **Hoch** | Ausnutzung wahrscheinlich, signifikanter Schaden |
| **Mittel** | Ausnutzung moeglich, moderater Schaden |
| **Niedrig** | Geringe Auswirkung, Defense-in-Depth |

---

## Kritische Befunde

### SV-001: Hardcoded Passwoerter im Quellcode

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Kritisch** |
| Kategorie | Secrets |
| Ort | `src/services/pdf_unlock.py:23-35` |
| Beschreibung | Vier PDF/ZIP-Passwoerter (`TQMakler37`, `TQMakler2021`, `555469899`, `dfvprovision`) sind als Fallback-Werte im Quellcode hartcodiert. Die gleichen Passwoerter sind in `AGENTS.md:639` namentlich dokumentiert. |
| Evidenz | `src/services/pdf_unlock.py` Zeilen 23-28 (PDF) und 30-35 (ZIP) |
| Status | Offen |

### SV-002: Fehlende Security Headers

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Kritisch** |
| Kategorie | Server-Config |
| Ort | `BiPro-Webspace Spiegelung Live/api/index.php` (global) |
| Beschreibung | Keine Security Headers gesetzt: Kein `Strict-Transport-Security`, kein `X-Frame-Options`, kein `X-Content-Type-Options`, kein `Content-Security-Policy`, kein `X-XSS-Protection`, kein `Referrer-Policy`. Die API ist somit anfaellig fuer Clickjacking, MIME-Sniffing und fehlende HSTS-Durchsetzung. |
| Evidenz | Grep ueber alle PHP-Dateien: Kein `header('X-Frame-Options')` etc. gefunden. Einzige `header()` Calls sind Content-Type und Content-Disposition. |
| Status | Offen |

### SV-003: Kein Rate-Limiting auf Login-Endpoint

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Kritisch** |
| Kategorie | Auth |
| Ort | `BiPro-Webspace Spiegelung Live/api/auth.php`, `api/index.php` |
| Beschreibung | Der Login-Endpoint (`POST /auth/login`) hat kein Rate-Limiting. Brute-Force-Angriffe auf Passwoerter sind ohne Einschraenkung moeglich. Es gibt kein automatisches Account-Lockout nach fehlgeschlagenen Versuchen. |
| Evidenz | Kein Rate-Limiting-Code in `auth.php` oder `index.php`. Kein `mod_ratelimit` in `.htaccess`. |
| Status | Offen |

### SV-004: OpenRouter API-Key an Client exponiert

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Kritisch** |
| Kategorie | Secrets |
| Ort | `BiPro-Webspace Spiegelung Live/api/ai.php:58` |
| Beschreibung | Der OpenRouter API-Key wird ueber `GET /ai/key` im JSON-Response an den Desktop-Client uebertragen. Jeder authentifizierte Benutzer mit `documents_process` Permission kann den Key extrahieren und eigenstaendig nutzen, was unkontrollierte Kosten verursachen kann. |
| Evidenz | `api/ai.php:58`: `json_success(['key' => OPENROUTER_API_KEY, ...])` |
| Status | Offen |

---

## Hohe Befunde

### SV-005: JWT-Token im Klartext auf Disk

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Hoch** |
| Kategorie | Secrets |
| Ort | `src/api/auth.py:295-305` |
| Beschreibung | Bei "Angemeldet bleiben" wird der JWT-Token als Klartext-JSON in `~/.bipro_gdv_token.json` gespeichert. Keine expliziten Datei-Permissions (0600) werden gesetzt. Andere Benutzer auf dem gleichen System koennten den Token lesen. |
| Evidenz | `src/api/auth.py:302` (write), `src/api/auth.py:311` (read). Kein `os.chmod()` Aufruf. |
| Status | Offen |

### SV-006: PDF/ZIP-Passwoerter in DB im Klartext

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Hoch** |
| Kategorie | Secrets |
| Ort | `BiPro-Webspace Spiegelung Live/api/passwords.php:44` |
| Beschreibung | Die `known_passwords` DB-Tabelle speichert PDF- und ZIP-Passwoerter im Klartext (`password_value` Spalte). Alle authentifizierten Benutzer koennen ueber `GET /passwords` die Klartext-Werte abrufen. Keine Verschluesselung mit `Crypto::encrypt()`. |
| Evidenz | `api/passwords.php:44` (SELECT password_value), `api/passwords.php:49` (oeffentlicher Endpoint). |
| Status | Offen |

### SV-007: Kein Zip-Bomb-Schutz (kein kumulatives Groessenlimit)

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Hoch** |
| Kategorie | Input-Validation |
| Ort | `src/services/zip_handler.py:99-149` |
| Beschreibung | ZIP-Extraktion hat eine maximale Rekursionstiefe (3 Ebenen), aber kein kumulatives Groessenlimit. Ein komprimiertes ZIP mit vielen kleinen Dateien oder einem einzelnen grossen komprimierten File koennte den verfuegbaren Speicher/Disk fuellen. |
| Evidenz | `src/services/zip_handler.py:20-21` (nur Rekursionslimit), kein Size-Tracking in `extract_zip_contents()`. |
| Status | Offen |

### SV-008: Temporaere PEM-Dateien mit Private Keys

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Hoch** |
| Kategorie | Secrets |
| Ort | `src/bipro/transfer_service.py:342-367` |
| Beschreibung | Private Keys aus PFX-Zertifikaten werden als unverschluesselte temporaere PEM-Dateien auf Disk geschrieben. Cleanup erfolgt in `close()`, aber bei Crash oder Absturz bleiben die Dateien bestehen. |
| Evidenz | `src/bipro/transfer_service.py:342-367` (PEM-Write), `src/bipro/transfer_service.py:1300-1313` (Cleanup in close()). |
| Status | Offen |

### SV-009: Keine Umgebungs-Trennung (Dev = Prod)

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Hoch** |
| Kategorie | Deployment |
| Ort | `BiPro-Webspace Spiegelung Live/` (Ordner-Sync) |
| Beschreibung | Der PHP-Code wird per Ordner-Sync direkt auf den Produktionsserver deployed. Kein Staging, kein Code-Review-Gate, kein Test-Gate. Jede lokale Aenderung ist sofort live. |
| Evidenz | `AGENTS.md:10-21` (Live-Synchronisierung). Keine CI/CD-Konfiguration vorhanden. |
| Status | Offen |

### SV-010: Zertifikate unverschluesselt auf Disk

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Hoch** |
| Kategorie | Secrets |
| Ort | `src/config/certificates.py:203-204` |
| Beschreibung | Client-Zertifikate (PFX/P12/JKS) werden unverschluesselt in `%APPDATA%/ACENCIA ATLAS/certs/` gespeichert. Kein Schutz durch OS-Keychain oder Verschluesselung. |
| Evidenz | `src/config/certificates.py:203-204` (shutil.copy2). |
| Status | Offen |

### SV-011: Keine Dependency-Lockfiles

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Hoch** |
| Kategorie | Supply-Chain |
| Ort | `requirements.txt` |
| Beschreibung | Alle Python-Dependencies verwenden `>=` Versionierung ohne obere Grenze. Keine Lockfile vorhanden. Build ist nicht deterministisch. Verschiedene Installationszeitpunkte koennen unterschiedliche (potentiell kompromittierte) Versionen installieren. |
| Evidenz | `requirements.txt`: Alle 10 Eintraege mit `>=`. |
| Status | Offen |

---

## Mittlere Befunde

### SV-012: SQL LIMIT/OFFSET per String-Interpolation

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | SQL-Injection |
| Ort | `api/gdv.php:255-263`, `api/activity.php:108-127` |
| Beschreibung | LIMIT und OFFSET Werte werden per `(int)` gecastet und dann per String-Interpolation in SQL eingefuegt (`LIMIT $limit OFFSET $offset`), statt als Prepared-Statement-Parameter. Der Int-Cast verhindert Injection, aber es verletzt Defense-in-Depth. Andere Dateien (smartscan.php, processing_history.php, etc.) verwenden korrekt `LIMIT ? OFFSET ?`. |
| Evidenz | `api/gdv.php:263`, `api/activity.php:127`. |
| Status | Offen |

### SV-013: PII-Daten an externen Dienst (OpenRouter)

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Datenschutz |
| Ort | `src/api/openrouter.py`, `src/services/document_processor.py` |
| Beschreibung | PDF-Textinhalt (2-5 Seiten, bis zu 5000 Zeichen) wird an die OpenRouter API (extern) gesendet. Dieser Text kann personenbezogene Daten enthalten (Namen, Adressen, Versicherungsnummern). DSGVO-Konformitaet ist UNVERIFIZIERT. |
| Evidenz | `src/services/document_processor.py` (Text-Extraktion), `src/api/openrouter.py` (API-Calls). |
| Status | Offen |

### SV-014: Potentielle PII in Debug-Logs

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Datenschutz |
| Ort | `src/bipro/transfer_service.py:616-617, 814, 1147` |
| Beschreibung | Bei DEBUG-Log-Level koennten Versicherungsschein-Nummern, STS-Responses und Transfer-Responses in Log-Dateien landen. Im Standard-Level (INFO) nicht aktiv, aber bei Debugging moeglich. |
| Evidenz | `transfer_service.py:1147` (Versicherungsschein-Nr), `transfer_service.py:616` (STS-Response 500 Zeichen), `transfer_service.py:814` (Response 2000 Zeichen). |
| Status | Offen |

### SV-015: Proxy komplett deaktiviert

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Netzwerk |
| Ort | `src/bipro/transfer_service.py:72-75, 264` |
| Beschreibung | Alle Proxy-Umgebungsvariablen werden geloescht und Proxies explizit deaktiviert (`trust_env=False`). In Unternehmensumgebungen mit Proxy-Pflicht werden Sicherheitskontrollen (Firewall, DLP, IDS) umgangen. |
| Evidenz | `transfer_service.py:72-74` (env clear), `transfer_service.py:264` (proxies=empty). |
| Status | Offen |

### SV-016: Kein Certificate-Pinning

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | TLS |
| Ort | `src/api/client.py`, `src/bipro/transfer_service.py`, `src/services/update_service.py` |
| Beschreibung | TLS-Verifikation ist aktiv (`verify=True`), aber kein Certificate-Pinning implementiert. Ein Angreifer mit einem gueltigen CA-signierten Zertifikat koennte einen MITM-Angriff durchfuehren. Besonders kritisch fuer den Auto-Update-Kanal. |
| Evidenz | Kein Pinning-Code in der gesamten Codebasis. |
| Status | Offen |

### SV-017: Kein Code-Signing fuer Installer

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Supply-Chain |
| Ort | `build.bat`, `src/services/update_service.py` |
| Beschreibung | Die Installer-EXE wird nicht digital signiert (kein Authenticode). SHA256-Verifikation findet statt, aber der Hash kommt vom gleichen Server wie die EXE. Ein kompromittierter Server koennte Hash und EXE gleichzeitig aendern. |
| Evidenz | Kein Code-Signing in `build.bat`. SHA256 aber vorhanden (`build.bat`, `update_service.py:164-174`). |
| Status | Offen |

### SV-018: Setup-Verzeichnis potentiell web-zugaenglich

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Server-Config |
| Ort | `BiPro-Webspace Spiegelung Live/setup/` |
| Beschreibung | Das `setup/` Verzeichnis wird synchronisiert und enthaelt PHP-Migrationsskripte. Es ist kein `.htaccess`-Schutz fuer dieses Verzeichnis vorhanden. Die Migrationen koennten ueber HTTP aufrufbar sein. |
| Evidenz | `AGENTS.md:16` ("setup ist synchronisiert"), kein `.htaccess` in `setup/`. |
| Status | UNVERIFIZIERT (nicht live getestet) |

### SV-019: Unbegrenzte Activity-Log-Retention

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Datenschutz / Performance |
| Ort | `BiPro-Webspace Spiegelung Live/api/lib/activity_logger.php` |
| Beschreibung | Die `activity_log` Tabelle waechst unbegrenzt (kein Cleanup, keine Retention-Policy). Sie enthaelt IP-Adressen und User-Agents (DSGVO-relevant). Bei hoher Aktivitaet Auswirkung auf DB-Performance. |
| Evidenz | Kein DELETE/TRUNCATE fuer activity_log in der Codebasis. |
| Status | Offen |

### SV-020: Einfache Key-Derivation (SHA256 statt HKDF)

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Kryptographie |
| Ort | `BiPro-Webspace Spiegelung Live/api/lib/crypto.php:100-103` |
| Beschreibung | Der AES-256-GCM Schluessel wird durch einfaches `hash('sha256', MASTER_KEY)` abgeleitet, nicht durch HKDF oder PBKDF2. Ein einzelner Key wird fuer alle Verschluesselungen verwendet (VU-Credentials, E-Mail-Credentials). Keine Key-Separation, keine Key-Rotation. |
| Evidenz | `api/lib/crypto.php:100-103`. |
| Status | Offen |

### SV-021: Keine MIME-Type-Validierung bei normalem Upload

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Mittel** |
| Kategorie | Input-Validation |
| Ort | `BiPro-Webspace Spiegelung Live/api/documents.php:408` |
| Beschreibung | Beim normalen Dokument-Upload wird keine MIME-Type-Whitelist erzwungen (im Gegensatz zum Scan-Upload, der PDF/JPG/PNG erzwingt). Beliebige Dateitypen koennen hochgeladen werden. |
| Evidenz | `api/documents.php:408` (MIME-Type optional). |
| Status | Offen |

---

## Niedrige Befunde

### SV-022: Kein PHP Dependency-Management

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | Supply-Chain |
| Ort | `BiPro-Webspace Spiegelung Live/api/lib/` |
| Beschreibung | PHP-Libraries (PHPMailer) werden manuell verwaltet. Kein Composer, kein `composer.lock`. Updates muessen manuell durchgefuehrt werden. |
| Evidenz | Kein `composer.json` im Repository. |
| Status | Offen |

### SV-023: API-Version im Health-Check exponiert

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | Information-Disclosure |
| Ort | `BiPro-Webspace Spiegelung Live/api/index.php:40-44` |
| Beschreibung | Der `/status` Endpoint gibt die API-Version zurueck. Dies koennte fuer Angreifer nuetzliche Versionsinformationen liefern. |
| Evidenz | `api/index.php:42`: `'version' => API_VERSION`. |
| Status | Offen |

### SV-024: Temp-File-Leak bei PDF-Unlock

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | Resource-Management |
| Ort | `src/services/pdf_unlock.py:155-161` |
| Beschreibung | Temporaere Dateien bei PDF-Unlock werden nur im Exception-Handler bereinigt, nicht im Normalfall. Bei bestimmten Code-Pfaden koennten Temp-Dateien zurueckbleiben. |
| Evidenz | `src/services/pdf_unlock.py:155` (mkstemp), `src/services/pdf_unlock.py:161` (nur Exception-Cleanup). |
| Status | Offen |

### SV-025: Fehler bei MSG-Extraktion werden verschluckt

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | Error-Handling |
| Ort | `src/services/msg_handler.py:102-110` |
| Beschreibung | Fehler bei PDF-Unlock waehrend MSG-Extraktion werden abgefangen und ignoriert. Der Benutzer erhaelt keine Benachrichtigung ueber fehlgeschlagene Einzelverarbeitungen. |
| Evidenz | `src/services/msg_handler.py:109` (Exception silently caught). |
| Status | Offen |

### SV-026: Keine CRL/OCSP-Pruefung fuer Zertifikate

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | TLS |
| Ort | `src/config/certificates.py`, `src/bipro/transfer_service.py` |
| Beschreibung | Client-Zertifikate werden nicht gegen Revocation-Listen (CRL) oder OCSP geprueft. Ein zurueckgerufenes Zertifikat koennte weiterhin verwendet werden. |
| Evidenz | Kein CRL/OCSP-Code in der Codebasis. |
| Status | Offen |

### SV-027: Potentielle Lizenz-Konflikte (AGPL/GPL)

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | Compliance |
| Ort | `requirements.txt` |
| Beschreibung | PyMuPDF (AGPL v3) und extract-msg (GPL v3) haben Copyleft-Lizenzen. Bei Distribution als Closed-Source-EXE muss die Lizenz-Kompatibilitaet geprueft werden. |
| Evidenz | PyMuPDF: AGPL v3, extract-msg: GPL v3 (Lizenz-Dateien der Packages). |
| Status | UNVERIFIZIERT |

### SV-028: Kein Monitoring und Alerting

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | Monitoring |
| Ort | Gesamtsystem |
| Beschreibung | Kein Server-Monitoring, kein APM, kein Error-Alerting, keine Log-Aggregation, keine Anomalie-Erkennung. Sicherheitsvorfaelle koennten unbemerkt bleiben. |
| Evidenz | Kein Monitoring-Code oder -Konfiguration im Repository. |
| Status | Offen |

### SV-029: MySQL-Verbindung ohne nachweisbare TLS-Verschluesselung

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | TLS |
| Ort | `BiPro-Webspace Spiegelung Live/api/lib/db.php` |
| Beschreibung | Die PDO-Verbindung zur MySQL-Datenbank enthaelt keinen SSL-Parameter. Die Verbindung koennte unverschluesselt sein (bei Strato Shared Hosting vermutlich intern, aber nicht verifizierbar). |
| Evidenz | `api/lib/db.php:16-22` (kein `PDO::MYSQL_ATTR_SSL_CA`). |
| Status | UNVERIFIZIERT |

### SV-030: Keine automatischen Tests fuer Security

| Aspekt | Detail |
|--------|--------|
| Schweregrad | **Niedrig** |
| Kategorie | Testing |
| Ort | `src/tests/` |
| Beschreibung | Keine Security-spezifischen Tests vorhanden. Keine Tests fuer: SQL-Injection, Path-Traversal, Auth-Bypass, Rate-Limiting, Input-Validation. Vorhandene Tests decken nur funktionale Aspekte ab. |
| Evidenz | `src/tests/test_smoke.py`, `src/tests/test_stability.py` (nur funktionale Tests). |
| Status | Offen |

---

## Statistik

| Schweregrad | Anzahl |
|-------------|--------|
| Kritisch | 4 |
| Hoch | 7 |
| Mittel | 10 |
| Niedrig | 9 |
| **Gesamt** | **30** |
