# 02 — Aenderungsliste

Alle Code-Aenderungen mit Bezug zum Security-Befund.

| SV-ID | Datei | Aenderung | Typ |
|-------|-------|-----------|-----|
| SV-001 | src/services/pdf_unlock.py | Fallback-Passwoerter-Listen entfernt, Warning-Log statt Fallback | Entfernung |
| SV-001 | AGENTS.md | Klartext-Passwoerter aus Dokumentation entfernt | Entfernung |
| SV-002 | api/lib/response.php | Neue Funktion `send_security_headers()` | Hinzufuegung |
| SV-002 | api/index.php | Aufruf `send_security_headers()` | Aenderung |
| SV-003 | api/lib/rate_limiter.php | Neue Datei: RateLimiter Klasse | Neue Datei |
| SV-003 | api/auth.php | Rate-Limiting Integration (check/record/reset) | Aenderung |
| SV-003 | setup/013_rate_limits.php | DB-Migration: rate_limits Tabelle | Neue Datei |
| SV-004 | api/ai.php | Komplett neu: Proxy statt Key-Ausgabe | Rewrite |
| SV-004 | src/api/openrouter.py | _openrouter_request() ueber Proxy, get_credits() ueber Proxy | Aenderung |
| SV-005 | src/api/auth.py | keyring-Integration + chmod Fallback fuer Token | Aenderung |
| SV-005 | requirements.txt | keyring>=24.0.0,<26.0.0 hinzugefuegt | Aenderung |
| SV-006 | api/passwords.php | Crypto::encrypt() bei Create/Update, decrypt() bei Read | Aenderung |
| SV-006 | setup/014_encrypt_passwords.php | Migration: Klartext → AES-256-GCM | Neue Datei |
| SV-007 | src/services/zip_handler.py | MAX_TOTAL_UNCOMPRESSED_SIZE + MAX_SINGLE_FILE_SIZE | Aenderung |
| SV-008 | src/bipro/transfer_service.py | atexit-Handler + _temp_pem_files Tracking + chmod 0600 | Aenderung |
| SV-009 | docs/DEPLOYMENT.md | Deployment-Checkliste | Neue Datei |
| SV-010 | src/config/certificates.py | chmod 0600 nach shutil.copy2() | Aenderung |
| SV-011 | requirements.txt | Obere Versionsgrenzen | Aenderung |
| SV-011 | requirements-lock.txt | Lockfile generiert | Neue Datei |
| SV-012 | api/gdv.php | LIMIT/OFFSET als ? Parameter | Aenderung |
| SV-012 | api/activity.php | LIMIT/OFFSET als ? Parameter | Aenderung |
| SV-013 | api/ai.php | redact_pii() und redact_pii_in_messages() | Hinzufuegung |
| SV-014 | src/bipro/transfer_service.py | Response-Logs auf 200 Zeichen gekuerzt | Aenderung |
| SV-015 | src/bipro/transfer_service.py | BIPRO_USE_SYSTEM_PROXY Env-Variable | Aenderung |
| SV-016 | src/services/update_service.py | PINNED_CERT_HASHES Infrastruktur | Hinzufuegung |
| SV-018 | setup/.htaccess | Require all denied | Neue Datei |
| SV-019 | api/lib/log_cleanup.php | LogCleanup Klasse | Neue Datei |
| SV-019 | api/index.php | Probabilistischer Cleanup-Trigger | Aenderung |
| SV-021 | api/documents.php | MIME-Type-Whitelist (13 Typen, HTTP 415) | Aenderung |
| SV-022 | composer.json | PHP-Dependencies dokumentiert | Neue Datei |
| SV-023 | api/index.php | version aus /status entfernt | Aenderung |
| SV-024 | src/services/pdf_unlock.py | try/finally mit temp_path=None Pattern | Aenderung |
| SV-025 | src/services/msg_handler.py | logger.warning statt pass | Aenderung |
| SV-026 | docs/SECURITY.md | CRL/OCSP Dokumentation | Neue Datei |
| SV-027 | docs/SECURITY.md | Lizenz-Dokumentation | Ergaenzung |
| SV-029 | docs/SECURITY.md | MySQL-SSL Dokumentation | Ergaenzung |
| SV-030 | src/tests/test_security.py | 7 Security-Testklassen | Neue Datei |
