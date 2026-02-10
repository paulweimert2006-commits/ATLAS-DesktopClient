# 06 - Konfiguration und Abhaengigkeiten

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Python-Abhaengigkeiten (Produktion)

| Paket | Version | Zweck |
|-------|---------|-------|
| PySide6 | >=6.6.0 | GUI Framework (Qt 6), QPdfView fuer PDF |
| requests | >=2.31.0 | HTTP Client (API, BiPRO SOAP) |
| cryptography | >=41.0.0 | PFX-Zertifikate (BiPRO) |
| PyMuPDF (fitz) | >=1.23.0 | PDF-Verarbeitung, Thumbnails, Unlock, Reparatur |
| pyjks | >=20.0.0 | JKS-Zertifikate (Java KeyStore) |
| openpyxl | >=3.1.0 | Excel-Dateien lesen (Archiv-Vorschau) |
| extract-msg | >=0.50.0 | Outlook .msg E-Mails parsen |
| pywin32 | >=306 | Windows COM-Automation (Outlook Drag & Drop) |
| pyzipper | >=0.3.6 | ZIP mit AES-256 Verschluesselung |
| pyinstaller | >=6.0.0 | Packaging als EXE |

**Quelle:** `requirements.txt`

## Python-Abhaengigkeiten (Entwicklung)

| Paket | Version | Zweck |
|-------|---------|-------|
| pytest | >=7.0.0 | Test-Framework |
| ruff | >=0.1.0 | Linting |

**Quelle:** `requirements-dev.txt`

---

## Server-Konfiguration

### config.php (SENSIBEL!)

| Konstante | Beschreibung |
|-----------|--------------|
| DB_HOST | `database-5019508812.webspace-host.com` |
| DB_NAME | `dbs15252975` |
| DB_USER | (in config.php) |
| DB_PASS | (in config.php) |
| MASTER_KEY | AES-Verschluesselung fuer E-Mail-Credentials |
| JWT_SECRET | JWT-Token-Signierung |
| SCAN_API_KEY | API-Key fuer Power Automate Scans |
| SCAN_ALLOWED_MIME_TYPES | PDF, JPG, PNG |

**Schutz:** `.htaccess` blockiert direkten HTTP-Zugriff auf config.php

### API-Endpunkte

| Aspekt | Details |
|--------|---------|
| Domain | `https://acencia.info/` |
| API Base | `https://acencia.info/api/` |
| CORS | Nicht konfiguriert (Desktop-App, kein Browser) |
| PHP Version | 7.4+ auf Strato Shared Hosting |

---

## Dokumenten-Verarbeitungsregeln

**Quelle:** `src/config/processing_rules.py`

### GDV-Erkennung

| Einstellung | Wert |
|-------------|------|
| gdv_extensions | `.gdv`, `.gvo`, `.gdvdaten` |
| raw_xml_patterns | `application/xml`, `text/xml`, `.xml`, `.xbrl` |

### BiPRO-Code-Zuordnung

| Code-Bereich | Ziel |
|--------------|------|
| 300001000-300003000 | Courtage (direkt, ohne KI) |
| 999010010 | GDV (direkt, ohne KI) |
| 100xxxxx | VU-Dokumente (KI-Klassifikation) |

### KI-Keywords fuer Klassifikation

| Kategorie | Beispiel-Keywords |
|-----------|-------------------|
| Courtage | provision, courtage, abrechnung, verguetung |
| Sach | haftpflicht, hausrat, wohngebaeude, kfz, PHV |
| Leben | lebensversicherung, pensionskasse, rentenanstalt |
| Kranken | krankenversicherung, krankenzusatz, pflegeversicherung |

### Download-Konfiguration (BiPRO)

| Einstellung | Wert |
|-------------|------|
| max_parallel_workers | 10 |
| min_workers_on_rate_limit | 2 |
| token_refresh_margin_seconds | 120 |
| retry_on_status_codes | [429, 503] |

---

## OpenRouter-Konfiguration

| Einstellung | Wert | Quelle |
|-------------|------|--------|
| Base URL | `https://openrouter.ai/api/v1` | `openrouter.py` |
| Triage-Modell | `openai/gpt-4o-mini` | `openrouter.py` |
| Detail-Modell | `openai/gpt-4o` | `openrouter.py` |
| Vision-Modell | `openai/gpt-4o` (OCR-Fallback) | `openrouter.py` |
| Max Retries | 3 | `openrouter.py` |
| API-Key | Vom Server (`GET /ai/key`) | `ai.php` |
| Credits-Endpoint | OpenRouter `/auth/key` | `openrouter.py` |

### Text-Extraktion

| Stufe | Seiten | Zeichen | Trigger |
|-------|--------|---------|---------|
| Triage (Stufe 1) | 2 | 3000 | Immer |
| Detail (Stufe 2) | 5 | 5000 | Nur bei low Confidence |
| OCR (Vision) | 2 | - | Bei Bild-PDFs (150 DPI) |

---

## BiPRO-Konfiguration

### Bekannte VU-Endpunkte (~40 Stueck)

**Quelle:** `src/config/vu_endpoints.py` -> `KNOWN_ENDPOINTS`

| VU | Auth-Typ | Beschreibung |
|----|----------|--------------|
| Degenia | Passwort | Standard BiPRO 410/430 |
| VEMA | Passwort | VEMA-spezifisches STS-Format, Consumer-ID |
| AIG | Zertifikat (WS) | - |
| Alte Leipziger | Zertifikat (WS) | - |
| Allianz | Passwort | - |
| ARAG | Passwort | - |
| ... | ... | ~36 weitere |

### Authentifizierungs-Methoden

| Typ-ID | Bezeichnung | Beschreibung |
|--------|-------------|--------------|
| 0 | AUTH_TYPE_PASSWORD | Username/Password ueber BiPRO 410 STS |
| 3 | AUTH_TYPE_CERT_WS | WS-Security mit X.509 Zertifikat |
| 4 | AUTH_TYPE_CERT_TGIC | TGIC-Zertifikat |
| 6 | AUTH_TYPE_CERT_DEGENIA | Degenia-spezifisch |

---

## Design-Tokens (ACENCIA CI)

**Quelle:** `src/ui/styles/tokens.py`

### Farben

| Token | Wert | Verwendung |
|-------|------|------------|
| PRIMARY_900 | #001f3d | Sidebar, Buttons, Text |
| PRIMARY_500 | #88a9c3 | Sekundaer-Elemente |
| PRIMARY_100 | #e3ebf2 | Hintergruende |
| ACCENT_500 | #fa9939 | Akzente, aktive Elemente |
| ACCENT_100 | #f8dcbf | Hover-States |

### Typografie

| Token | Wert | Verwendung |
|-------|------|------------|
| FONT_HEADLINE | "Tenor Sans" | Ueberschriften, Navigation |
| FONT_BODY | "Open Sans" | Fliesstext, Tabellen |
| FONT_SIZE_BASE | 14px | Standard-Schriftgroesse |

### Spacing

| Token | Wert |
|-------|------|
| SPACING_XS | 4px |
| SPACING_SM | 8px |
| SPACING_MD | 16px |
| SPACING_LG | 24px |
| SPACING_XL | 32px |

---

## Internationalisierung (i18n)

**Quelle:** `src/i18n/de.py` (~910 Konstanten)

| Sektion | Ungefaehre Key-Anzahl |
|---------|----------------------|
| Allgemein (APP_, LOADING, SAVE, etc.) | ~30 |
| Navigation (NAV_) | ~10 |
| Login (LOGIN_) | ~15 |
| BiPRO (BIPRO_) | ~60 |
| Archiv (ARCHIVE_, BOX_) | ~80 |
| GDV (GDV_) | ~40 |
| Admin (ADMIN_) | ~80 |
| Smart!Scan (SMARTSCAN_) | ~50 |
| E-Mail (EMAIL_ACCOUNT_, EMAIL_INBOX_) | ~40 |
| Passwoerter (PASSWORD_) | ~35 |
| Releases (RELEASE_) | ~40 |
| KI-Kosten (AI_COST_) | ~30 |
| Shortcuts (SHORTCUT_) | ~16 |
| Duplikate (DUPLICATE_) | ~6 |
| Historie (HISTORY_) | ~20 |
| PDF-Bearbeitung (PDF_EDIT_) | ~14 |
| Schliess-Schutz (CLOSE_BLOCKED_) | ~4 |
| Toast (TOAST_) | ~4 |
| Drag & Drop (DROP_) | ~10 |

---

## Umgebungsvariablen

Keine Umgebungsvariablen erforderlich. Alle Konfiguration ist in:
- `src/config/` (Python-seitig)
- `BiPro-Webspace Spiegelung Live/api/config.php` (Server-seitig)

---

## Encoding-Konfiguration

| Aspekt | Wert |
|--------|------|
| GDV-Standard | CP1252 (Windows-1252) |
| Fallback 1 | Latin-1 (ISO 8859-1) |
| Fallback 2 | UTF-8 |
| Zeilenbreite | 256 Bytes (fest) |
| API-Kommunikation | UTF-8 (JSON) |
