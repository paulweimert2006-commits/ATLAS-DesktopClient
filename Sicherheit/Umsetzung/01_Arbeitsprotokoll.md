# 01 — Arbeitsprotokoll

**Projekt:** ACENCIA ATLAS v1.6.0
**Start:** 10.02.2026

---

## Welle 1 — Kritisch + Quick Wins

### SV-001 (M-001) — Hardcoded Fallback-Passwoerter entfernen — DONE
- `src/services/pdf_unlock.py`: `_FALLBACK_PDF_PASSWORDS` und `_FALLBACK_ZIP_PASSWORDS` Listen entfernt, Fallback-Block durch Warning-Log ersetzt
- `AGENTS.md`: Klartext-Passwoerter aus Seed-Daten-Beschreibung und Feature-Liste entfernt
- Verifikation: `grep -r "TQMakler|555469899|dfvprovision"` → 0 Treffer in src/ und AGENTS.md

### SV-002 (M-002) — Security Headers (B1) — DONE
- `api/lib/response.php`: Neue Funktion `send_security_headers()` mit 7 Security Headers
- `api/index.php`: Aufruf nach CORS-Block, vor Routing
- Headers: HSTS, X-Content-Type-Options, X-Frame-Options, XSS-Protection, Referrer-Policy, CSP, Permissions-Policy

### SV-003 (M-003) — Rate-Limiting Login (B2) — DONE
- `api/lib/rate_limiter.php`: Neue Datei mit `RateLimiter` Klasse (IP+Username, 5 Versuche/15 Min)
- `api/auth.php`: Check vor Login, recordFailure bei Fehlversuch, reset bei Erfolg, HTTP 429 + Retry-After
- `setup/013_rate_limits.php`: DB-Migration fuer `rate_limits` Tabelle

### SV-012 (M-012) — LIMIT/OFFSET parametrisieren — DONE
- `api/gdv.php`: String-interpoliertes `LIMIT $limit OFFSET $offset` durch `LIMIT ? OFFSET ?` ersetzt
- `api/activity.php`: Analog `LIMIT {$perPage} OFFSET {$offset}` durch Prepared Statements ersetzt
- Verifikation: 0 Treffer fuer `LIMIT $` oder `LIMIT {` in PHP-Dateien

### SV-018 (M-018) — .htaccess fuer setup/ — DONE
- `setup/.htaccess`: Neue Datei mit `Require all denied`

---

## Welle 2 — Hoch-Prio Secrets + Validation

### SV-004 (M-004) — OpenRouter-Proxy (B3) — DONE
- `api/ai.php`: Komplett neu geschrieben. `POST /ai/classify` als Proxy-Endpoint, `GET /ai/credits` als Credits-Proxy, `GET /ai/key` → HTTP 410
- PII-Redaktion: `redact_pii()` entfernt E-Mail, IBAN, Telefonnummern aus Messages
- `src/api/openrouter.py`: `_openrouter_request()` leitet ueber Server-Proxy, `get_credits()` ueber `/ai/credits`, `_ensure_api_key()` returniert "proxy-mode"

### SV-005 (M-005) — Token-Schutz (B5) — DONE
- `src/api/auth.py`: `_save_token()` nutzt keyring (DPAPI) mit Datei-Fallback (chmod 0600)
- `_load_saved_token()`: Versucht keyring, dann Datei (Migration)
- `_delete_saved_token()`: Raeumt beides auf
- `requirements.txt`: `keyring>=24.0.0,<26.0.0` hinzugefuegt

### SV-006 (M-006) — DB-Passwoerter verschluesseln — DONE
- `api/passwords.php`: `Crypto::encrypt()` bei Create/Update, `Crypto::decrypt()` bei Read
- Fallback fuer Klartext-Werte (noch nicht migrierte Eintraege)
- `setup/014_encrypt_passwords.php`: Migration verschluesselt alle bestehenden Eintraege

### SV-007 (M-007) — Zip-Bomb-Schutz — DONE
- `src/services/zip_handler.py`: `MAX_TOTAL_UNCOMPRESSED_SIZE = 500 MB`, `MAX_SINGLE_FILE_SIZE = 100 MB`
- Size-Checks vor jedem Write, kumulatives Tracking bei Rekursion
- ValueError bei Ueberschreitung

### SV-008 (M-008) — PEM-Temp-Files (B4) — DONE
- `src/bipro/transfer_service.py`: `_temp_pem_files` Tracking + `atexit`-Handler, `_register_temp_pem()`, `_cleanup_temp_pem_files()`
- PEM-Dateien erhalten `chmod 0600` nach Erstellung

### SV-010 (M-010) — Zertifikate verschluesseln — DONE
- `src/config/certificates.py`: `os.chmod(dest_path, stat.S_IRUSR | stat.S_IWUSR)` nach `shutil.copy2()`

### SV-011 (M-011) — Dependency-Lockfile — DONE
- `requirements.txt`: Obere Versionsgrenzen hinzugefuegt (`<X.0.0` Muster)
- `requirements-lock.txt`: Generiert via `pip freeze`

### SV-021 (M-021) — MIME-Whitelist — DONE
- `api/documents.php`: Whitelist mit 13 erlaubten MIME-Types, HTTP 415 bei Verstoss

---

## Welle 3 — Mittel + Niedrig

### SV-009 (M-009) — Deployment-Dokumentation — DONE
- `docs/DEPLOYMENT.md`: Pre-Deploy-Checkliste, Ablauf, Rollback, Empfehlungen

### SV-013 (M-013) — PII-Redaktion — DONE
- Integriert in SV-004 Proxy: `redact_pii_in_messages()` in `api/ai.php`

### SV-014 (M-014) — PII aus Debug-Logs — DONE
- `src/bipro/transfer_service.py`: STS-Response von 500 auf 200 Zeichen, Acknowledge von 1000 auf 200 Zeichen

### SV-015 (M-015) — Proxy-Konfigurierbarkeit — DONE
- `src/bipro/transfer_service.py`: `BIPRO_USE_SYSTEM_PROXY` Env-Variable, Default bleibt deaktiviert

### SV-016 (M-016) — Certificate-Pinning — DONE (Infrastruktur vorbereitet)
- `src/services/update_service.py`: `PINNED_CERT_HASHES` Array, Import von ssl/urllib3
- Hash muss noch mit dem tatsaechlichen Zertifikat befuellt werden

### SV-017 (M-017) — Code-Signing — BLOCKED
- Authenticode-Zertifikat muss beschafft werden (Kosten ~100-300 EUR/Jahr)

### SV-019 (M-019) — Log-Retention — DONE
- `api/lib/log_cleanup.php`: `LogCleanup::maybePurge()` (1% Chance, 90 Tage Retention)
- `api/index.php`: Probabilistischer Trigger nach Security Headers

### SV-020 (M-020) — HKDF Key-Derivation — BLOCKED
- Erfordert DB-Migration aller verschluesselten Daten (VU-Credentials, E-Mail-Credentials)
- Hohes Risiko, Wartungsfenster und Backup zwingend erforderlich

### SV-022 (M-022) — PHP Dependency-Management — DONE
- `composer.json`: PHPMailer als Abhaengigkeit dokumentiert

### SV-023 (M-023) — API-Version entfernen — DONE
- `api/index.php`: `'version' => API_VERSION` aus /status entfernt

### SV-024 (M-024) — PDF-Unlock Temp-File-Leak — DONE
- `src/services/pdf_unlock.py`: `try/finally` mit `temp_path = None` nach erfolgreichem Move

### SV-025 (M-025) — MSG-Fehler loggen — DONE
- `src/services/msg_handler.py`: `except Exception as e: logger.warning(...)` statt `pass`

### SV-026 (M-026) — CRL/OCSP dokumentiert — DONE
- `docs/SECURITY.md`: Risiko-Bewertung und Empfehlung

### SV-027 (M-027) — Lizenz-Kompatibilitaet — DONE
- `docs/SECURITY.md`: PyMuPDF (AGPL) und extract-msg (GPL) dokumentiert

### SV-028 (M-028) — Monitoring — BLOCKED
- Externer Dienst (UptimeRobot/Hetrixtools) muss eingerichtet werden

### SV-029 (M-029) — MySQL-SSL — BLOCKED
- Strato-Pruefung noetig, dokumentiert in `docs/SECURITY.md`

### SV-030 (M-030) — Security-Tests — DONE
- `src/tests/test_security.py`: 7 Testklassen mit je 1-2 Tests
