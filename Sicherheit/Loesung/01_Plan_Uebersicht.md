# 01 — Plan-Uebersicht

**Projekt:** ACENCIA ATLAS v1.6.0
**Plan-Datum:** 10.02.2026
**Grundlage:** Security Audit vom 10.02.2026 (30 Befunde)

---

## 1.1 Befund-Statistik

| Schweregrad | Anzahl | IDs |
|-------------|--------|-----|
| Kritisch | 4 | SV-001, SV-002, SV-003, SV-004 |
| Hoch | 7 | SV-005 bis SV-011 |
| Mittel | 10 | SV-012 bis SV-021 |
| Niedrig | 9 | SV-022 bis SV-030 |
| **Gesamt** | **30** | |

## 1.2 Befund-Cluster

### Cluster A: Secrets im Code/Doku

| Befund | Schweregrad | Root Cause |
|--------|-------------|-----------|
| SV-001 | Kritisch | Hardcoded Fallback-Passwoerter in `src/services/pdf_unlock.py:23-35` + Passwoerter in `AGENTS.md:639` |
| SV-004 | Kritisch | API-Key-Architektur: `ai.php:58` sendet OPENROUTER_API_KEY an Client statt Server-side Proxy |
| SV-005 | Hoch | Token-Persistenz ohne OS-Schutz: `src/api/auth.py:295-305` schreibt JSON ohne Permissions |
| SV-006 | Hoch | `known_passwords.password_value` in DB nicht verschluesselt, obwohl `Crypto::encrypt()` existiert |
| SV-008 | Hoch | PFX→PEM Konvertierung schreibt Private Keys als Temp-Files: `transfer_service.py:342-367` |
| SV-010 | Hoch | Zertifikate via `shutil.copy2()` kopiert: `certificates.py:203-204`, kein OS-Schutz |

### Cluster B: Server-Haertung

| Befund | Schweregrad | Root Cause |
|--------|-------------|-----------|
| SV-002 | Kritisch | Kein Security-Header-Layer in `index.php` oder `.htaccess` |
| SV-003 | Kritisch | Kein Rate-Limiting in PHP (Shared Hosting, kein mod_ratelimit) |
| SV-012 | Mittel | Inkonsistenz: 2 von 8 Dateien nutzen String-Interpolation fuer LIMIT/OFFSET |
| SV-018 | Mittel | `setup/` synchronisiert ohne `.htaccess`-Schutz |
| SV-023 | Niedrig | `API_VERSION` im Health-Check `/status` exponiert |

### Cluster C: Input-Validation

| Befund | Schweregrad | Root Cause |
|--------|-------------|-----------|
| SV-007 | Hoch | `zip_handler.py` hat Rekursionslimit aber kein kumulatives Size-Tracking |
| SV-021 | Mittel | `documents.php:408` macht MIME-Type-Check optional (nur Scan-Endpoint erzwingt Whitelist) |
| SV-024 | Niedrig | `pdf_unlock.py:155` nutzt `mkstemp` statt Context-Manager |
| SV-025 | Niedrig | `msg_handler.py:109` verschluckt Exceptions bei PDF-Unlock |

### Cluster D: Datenschutz/PII

| Befund | Schweregrad | Root Cause |
|--------|-------------|-----------|
| SV-013 | Mittel | Architektur-Entscheidung: Client ruft OpenRouter direkt auf, PII-Text geht an Drittanbieter |
| SV-014 | Mittel | DEBUG-Level-Logs in `transfer_service.py` enthalten Versicherungsschein-Nr und Responses |
| SV-019 | Mittel | `activity_log` Tabelle hat kein Retention/Cleanup, waechst unbegrenzt |

### Cluster E: Supply-Chain

| Befund | Schweregrad | Root Cause |
|--------|-------------|-----------|
| SV-011 | Hoch | `requirements.txt` nutzt nur `>=` ohne obere Grenze, keine Lockfile |
| SV-017 | Mittel | `build.bat` erzeugt SHA256 aber kein Authenticode-Signing |
| SV-022 | Niedrig | PHP-Libraries (PHPMailer) manuell in `api/lib/` ohne Composer |
| SV-027 | Niedrig | PyMuPDF (AGPL) und extract-msg (GPL) potenziell inkompatibel mit Closed-Source |

### Cluster F: TLS/Netzwerk/Kryptographie

| Befund | Schweregrad | Root Cause |
|--------|-------------|-----------|
| SV-015 | Mittel | `transfer_service.py:72-75` loescht Proxy-Env-Vars explizit |
| SV-016 | Mittel | `verify=True` aber kein Certificate-Pinning fuer Update-Kanal |
| SV-020 | Mittel | `crypto.php:100-103` nutzt `hash('sha256', MASTER_KEY)` statt HKDF |
| SV-026 | Niedrig | Kein CRL/OCSP fuer Client-Zertifikate |
| SV-029 | Niedrig | PDO-Verbindung ohne `MYSQL_ATTR_SSL_CA` |

### Cluster G: Deployment/Testing/Monitoring

| Befund | Schweregrad | Root Cause |
|--------|-------------|-----------|
| SV-009 | Hoch | Ordner-Sync direkt auf Produktion, kein Staging/Review |
| SV-028 | Niedrig | Kein Uptime-Monitoring, kein Error-Alerting |
| SV-030 | Niedrig | Keine Security-Tests in `src/tests/` |

## 1.3 Abhaengigkeiten zwischen Befunden

```
SV-004 (API-Key) ──abhg──> SV-013 (PII an OpenRouter)
   └── Beide geloest durch Baustein B3 (OpenRouter-Proxy)

SV-001 (Hardcoded PW) ──vorher──> SV-006 (PW in DB Klartext)
   └── Zuerst Fallback entfernen, dann DB verschluesseln

SV-008 (PEM Temp) ──gleicher Baustein──> SV-024 (PDF Temp)
   └── Baustein B4 (Temp-File-Guard)

SV-005 (Token Klartext) ──gleicher Baustein──> SV-010 (Cert Klartext)
   └── Baustein B5 (DPAPI/Keyring)
```

## 1.4 Wiederverwendbare Fix-Bausteine

| ID | Name | Betroffene SV-IDs | Beschreibung |
|----|------|-------------------|-------------|
| B1 | Security-Headers-Middleware | SV-002 | Funktion `send_security_headers()` in `api/lib/response.php`, Aufruf in `index.php` |
| B2 | Rate-Limiter (PHP, DB-basiert) | SV-003 | Neue `api/lib/rate_limiter.php`, IP+Username-basiert, Schwellwert konfigurierbar |
| B3 | OpenRouter-Proxy | SV-004, SV-013 | Neuer PHP-Endpoint `POST /ai/classify`, Server ruft OpenRouter auf |
| B4 | Temp-File-Guard (Python) | SV-008, SV-024 | `atexit`-Handler + `NamedTemporaryFile(delete=True)` Pattern |
| B5 | DPAPI/Keyring-Wrapper (Python) | SV-005, SV-010 | Windows DPAPI oder `keyring` Library fuer lokale Secret-Speicherung |

## 1.5 Umsetzungsreihenfolge

### Welle 1 — Kritisch + Quick Wins (~2 Tage)

| Prio | Massnahme | Befund | Aufwand | Abhaengigkeiten |
|------|-----------|--------|---------|-----------------|
| 1 | M-001 | SV-001 | Klein | Keine |
| 2 | M-002 | SV-002 | Klein | Keine |
| 3 | M-003 | SV-003 | Mittel | Keine |
| 4 | M-012 | SV-012 | Klein | Keine |
| 5 | M-018 | SV-018 | Klein | Keine |

### Welle 2 — Hoch-Prio Secrets + Validation (~3 Tage)

| Prio | Massnahme | Befund | Aufwand | Abhaengigkeiten |
|------|-----------|--------|---------|-----------------|
| 6 | M-004 | SV-004 | Gross | Keine |
| 7 | M-005 | SV-005 | Mittel | Keine |
| 8 | M-006 | SV-006 | Mittel | M-001 |
| 9 | M-007 | SV-007 | Mittel | Keine |
| 10 | M-008 | SV-008 | Mittel | Keine |
| 11 | M-010 | SV-010 | Mittel | M-005 (gleicher Baustein B5) |
| 12 | M-011 | SV-011 | Klein | Keine |
| 13 | M-021 | SV-021 | Klein | Keine |

### Welle 3 — Mittel + Niedrig (~4 Tage)

| Prio | Massnahme | Befund | Aufwand | Abhaengigkeiten |
|------|-----------|--------|---------|-----------------|
| 14 | M-009 | SV-009 | Gross | Keine |
| 15 | M-013 | SV-013 | Klein | M-004 (Proxy loest PII-Problem) |
| 16 | M-014 | SV-014 | Klein | Keine |
| 17 | M-015 | SV-015 | Klein | Keine |
| 18 | M-016 | SV-016 | Mittel | Keine |
| 19 | M-017 | SV-017 | Gross | Keine |
| 20 | M-019 | SV-019 | Mittel | Keine |
| 21 | M-020 | SV-020 | Gross | Keine |
| 22 | M-022 | SV-022 | Mittel | Keine |
| 23 | M-023 | SV-023 | Klein | Keine |
| 24 | M-024 | SV-024 | Klein | Keine |
| 25 | M-025 | SV-025 | Klein | Keine |
| 26 | M-026 | SV-026 | Klein | Keine |
| 27 | M-027 | SV-027 | Mittel | Keine |
| 28 | M-028 | SV-028 | Mittel | Keine |
| 29 | M-029 | SV-029 | Klein | Keine |
| 30 | M-030 | SV-030 | Mittel | Keine |

## 1.6 Geschaetzter Gesamtaufwand

| Welle | Massnahmen | Aufwand |
|-------|-----------|---------|
| 1 | 5 | ~2 Tage |
| 2 | 8 | ~3 Tage |
| 3 | 17 | ~4 Tage |
| **Gesamt** | **30** | **~9 Tage** |
