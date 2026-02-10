# ANHANG — Checkliste Coverage

Coverage-Tabelle: Jeder Befund mit zugeordnetem Test und Testtyp.

| SV-ID | M-ID | T-ID | Testtyp | Beschreibung | Automatisierbar |
|-------|------|------|---------|-------------|----------------|
| SV-001 | M-001 | T-001 | Code-Grep + Regression | Keine hardcoded Passwords, PDF-Unlock funktioniert | ✅ Ja |
| SV-002 | M-002 | T-002 | HTTP-Header-Pruefung | Security Headers in Response vorhanden | ✅ Ja (curl) |
| SV-003 | M-003 | T-003 | Funktional + Regression | Rate-Limiting bei 6. Versuch, Reset nach Erfolg | ✅ Ja |
| SV-004 | M-004 | T-004 | Funktional + Negativ | Proxy-Klassifikation funktioniert, GET /ai/key → 404 | ✅ Ja |
| SV-005 | M-005 | T-005 | Datei/Keyring-Pruefung | Token nicht als Klartext-Datei | ⚠️ Teilweise |
| SV-006 | M-006 | T-006 | DB-Query + Funktional | Verschluesselte Werte in DB, Entschluesselung korrekt | ✅ Ja |
| SV-007 | M-007 | T-007 | Funktional + Negativ | Zip-Bomb → ValueError, Normale ZIP → Erfolg | ✅ Ja |
| SV-008 | M-008 | T-008 | Datei-Pruefung | Keine PEM-Reste nach Cleanup, Permissions 0o600 | ⚠️ Teilweise |
| SV-009 | M-009 | T-009 | Dokumentation | Deployment-Checkliste vorhanden | ❌ Manuell |
| SV-010 | M-010 | T-010 | Datei/Keyring-Pruefung | Zertifikate nicht als Klartext | ⚠️ Teilweise |
| SV-011 | M-011 | T-011 | Datei-Pruefung | Lockfile vorhanden, Versionen gepinnt | ✅ Ja |
| SV-012 | M-012 | T-012 | Code-Grep + Funktional | Keine String-Interpolation fuer LIMIT/OFFSET | ✅ Ja |
| SV-013 | M-013 | T-013 | Funktional | PII-Redaktion in Proxy aktiv | ✅ Ja |
| SV-014 | M-014 | T-014 | Log-Pruefung | DEBUG-Logs ohne vollstaendige PII | ⚠️ Teilweise |
| SV-015 | M-015 | T-015 | Funktional | Proxy-Konfiguration wirkt | ⚠️ Env-abhaengig |
| SV-016 | M-016 | T-016 | Funktional + Negativ | Pinning blockiert falsches Zertifikat | ⚠️ Teilweise |
| SV-017 | M-017 | T-017 | Build-Pruefung | Authenticode-Signatur vorhanden | ✅ Ja |
| SV-018 | M-018 | T-018 | HTTP-Pruefung | setup/ gibt 403 | ✅ Ja (curl) |
| SV-019 | M-019 | T-019 | DB-Query | Alte Eintraege geloescht nach Cleanup | ✅ Ja |
| SV-020 | M-020 | T-020 | Funktional | HKDF-Derivation, bestehende Daten lesbar | ✅ Ja |
| SV-021 | M-021 | T-021 | Funktional + Negativ | .exe → 415, .pdf → Erfolg | ✅ Ja |
| SV-022 | M-022 | T-022 | Datei-Pruefung | composer.json + lock vorhanden | ✅ Ja |
| SV-023 | M-023 | T-023 | HTTP-Pruefung | Kein "version" in /status Response | ✅ Ja (curl) |
| SV-024 | M-024 | T-024 | Datei-Pruefung | Kein Temp-File nach Fehler | ✅ Ja |
| SV-025 | M-025 | T-025 | Log-Pruefung | Warning im Log bei Fehler | ✅ Ja |
| SV-026 | M-026 | T-026 | Dokumentation | SECURITY.md enthaelt CRL/OCSP-Abschnitt | ❌ Manuell |
| SV-027 | M-027 | T-027 | Dokumentation | LICENSES.md vorhanden | ❌ Manuell |
| SV-028 | M-028 | T-028 | Externer Dienst | Uptime-Monitor meldet Ausfall | ❌ Manuell |
| SV-029 | M-029 | T-029 | DB-Query + Doku | SSL-Status dokumentiert | ❌ Manuell |
| SV-030 | M-030 | T-030 | Pytest | test_security.py besteht | ✅ Ja |

## Statistik

| Testtyp | Anzahl | Anteil |
|---------|--------|--------|
| Voll automatisierbar | 18 | 60% |
| Teilweise automatisierbar | 6 | 20% |
| Nur manuell | 6 | 20% |
| **Gesamt** | **30** | **100%** |

## Empfohlene Automatisierung

### In `src/tests/test_security.py` (Pytest):
- T-001: Code-Grep auf hardcoded Passwords
- T-007: Zip-Bomb-Schutz
- T-011: Lockfile existiert
- T-012: Code-Grep LIMIT/OFFSET
- T-024: Temp-File-Cleanup
- T-025: MSG-Fehler-Logging
- T-030: Meta-Test (dieser Test selbst existiert)

### In `scripts/deploy_check.py` (Pre-Deploy):
- T-002: curl Security Headers
- T-018: curl setup/ → 403
- T-023: curl /status ohne Version

### In CI/CD (zukuenftig):
- T-003: Rate-Limiting Integration-Test
- T-004: OpenRouter-Proxy Integration-Test
- T-006: DB-Verschluesselung
- T-021: MIME-Whitelist
