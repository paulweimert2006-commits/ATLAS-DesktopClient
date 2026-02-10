# 03 — Verifikationsergebnisse

| SV-ID | Test | Ergebnis | Methode | Notiz |
|-------|------|----------|---------|-------|
| SV-001 | Keine hardcoded Passwords | PASS | grep TQMakler/555469899/dfvprovision → 0 Treffer | Git-History behalten, Rotation empfohlen |
| SV-002 | Security Headers vorhanden | PASS | Code-Review: 7 Headers in send_security_headers() | Server-Test nach Deploy noetig |
| SV-003 | Rate-Limiter implementiert | PASS | Code-Review: check/record/reset in auth.php | DB-Migration 013 muss ausgefuehrt werden |
| SV-004 | API-Key nicht am Client | PASS | _ensure_api_key() gibt "proxy-mode", ai.php hat POST /ai/classify | GET /ai/key → HTTP 410 |
| SV-005 | Token-Schutz | PASS | keyring-Import + chmod Fallback in auth.py | keyring muss installiert sein |
| SV-006 | Passwoerter verschluesselt | PASS | Crypto::encrypt() in Create/Update, decrypt() in Read | Migration 014 muss laufen |
| SV-007 | Zip-Bomb-Limit | PASS | MAX_TOTAL=500MB, MAX_SINGLE=100MB, ValueError bei Ueberschreitung | Normale ZIPs unbeeintraechtigt |
| SV-008 | PEM-Cleanup | PASS | atexit-Handler registriert, chmod 0600 gesetzt | Windows: chmod begrenzt |
| SV-009 | Deployment-Doku | PASS | docs/DEPLOYMENT.md existiert | Prozess-Disziplin noetig |
| SV-010 | Cert chmod | PASS | stat.S_IRUSR/S_IWUSR nach copy2() | Windows: begrenzt |
| SV-011 | Lockfile vorhanden | PASS | requirements-lock.txt generiert, obere Grenzen in requirements.txt | Manuelles Update noetig |
| SV-012 | Keine String-Interpolation | PASS | grep 'LIMIT $\|LIMIT {' → 0 Treffer | Defense-in-Depth |
| SV-013 | PII-Redaktion | PASS | redact_pii() in ai.php: Email, IBAN, Phone | False Positives moeglich |
| SV-014 | Responses gekuerzt | PASS | 500→200 (STS), 1000→200 (Acknowledge) | Debugging weiterhin moeglich |
| SV-015 | Proxy konfigurierbar | PASS | BIPRO_USE_SYSTEM_PROXY env var | Default: aus (abwaertskompatibel) |
| SV-016 | Pinning vorbereitet | PASS | PINNED_CERT_HASHES Array, ssl/urllib3 Imports | Hash muss befuellt werden |
| SV-017 | Code-Signing | NA | BLOCKED: Zertifikat noetig | Kosten: ~100-300 EUR/Jahr |
| SV-018 | setup/ geschuetzt | PASS | .htaccess mit "Require all denied" | Server-Test nach Deploy |
| SV-019 | Log-Cleanup aktiv | PASS | LogCleanup::maybePurge() in index.php | 1% Wahrscheinlichkeit, 90 Tage |
| SV-020 | HKDF | NA | BLOCKED: DB-Migration noetig | Wartungsfenster erforderlich |
| SV-021 | MIME-Whitelist | PASS | 13 erlaubte Typen, HTTP 415 bei Verstoss | application/octet-stream fuer GDV |
| SV-022 | composer.json | PASS | Datei vorhanden mit PHPMailer | Strato: ggf. manuelles Update |
| SV-023 | Version nicht exponiert | PASS | 'version' aus /status Response entfernt | Kein Breaking Change |
| SV-024 | Temp-Cleanup | PASS | try/finally mit temp_path=None | Strukturelles Refactoring |
| SV-025 | Fehler geloggt | PASS | logger.warning statt pass | MSG-Verarbeitung bricht nicht ab |
| SV-026 | CRL/OCSP dokumentiert | PASS | docs/SECURITY.md | Risiko: Gering |
| SV-027 | Lizenzen dokumentiert | PASS | docs/SECURITY.md (PyMuPDF AGPL, extract-msg GPL) | Rechtsberatung empfohlen |
| SV-028 | Monitoring | NA | BLOCKED: Externer Dienst | UptimeRobot empfohlen |
| SV-029 | MySQL-SSL | NA | BLOCKED: Strato-Pruefung | Dokumentiert in SECURITY.md |
| SV-030 | Security-Tests | PASS | test_security.py mit 7 Testklassen | Pytest-Integration |
