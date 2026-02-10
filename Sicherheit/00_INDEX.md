# 00 — Security Audit Index

**Projekt:** ACENCIA ATLAS v1.6.0
**Audit-Datum:** 10.02.2026
**Audit-Typ:** Vollstaendige IST-Zustandspruefung (Code + Konfiguration + Deployment)
**Scope:** Python Desktop-App + PHP REST API + Strato Webspace + MySQL

---

## Dokumente

| Nr. | Dokument | Inhalt |
|-----|----------|--------|
| 01 | [01_Systemuebersicht.md](01_Systemuebersicht.md) | Projekttyp, Tech-Stack, Umgebung, Live-Sync |
| 02 | [02_Architektur_Ist.md](02_Architektur_Ist.md) | Architektur, Datenfluss, Schichten, Thread-Modell |
| 03 | [03_Oberflaechen_und_Seiten_Ist.md](03_Oberflaechen_und_Seiten_Ist.md) | Desktop-Views, API-Endpoints, Permissions-Matrix |
| 04 | [04_Funktionen_und_Flows_Ist.md](04_Funktionen_und_Flows_Ist.md) | Login, Upload, BiPRO, KI, SmartScan, Update, IMAP, Scan |
| 05 | [05_Auth_OAuth_RBAC_Validation_HTTPS_Ist.md](05_Auth_OAuth_RBAC_Validation_HTTPS_Ist.md) | Auth, JWT, RBAC, Validation, TLS, Security Headers, CORS |
| 06 | [06_Input_Validation_und_Datenfluss_Ist.md](06_Input_Validation_und_Datenfluss_Ist.md) | Server-/Client-Validation, PII-Datenfluss, Upload-Typen |
| 07 | [07_Server_Deployment_Webspace_Ist.md](07_Server_Deployment_Webspace_Ist.md) | Strato, .htaccess, PHP-Config, Deployment, Error-Handling |
| 08 | [08_Secrets_Keys_Config_Ist.md](08_Secrets_Keys_Config_Ist.md) | Hardcoded Secrets, config.php, .gitignore, Verschluesselung |
| 09 | [09_Logging_Auditing_Monitoring_Ist.md](09_Logging_Auditing_Monitoring_Ist.md) | Activity-Log, Client-Logs, PII in Logs, Monitoring |
| 10 | [10_Abhaengigkeiten_Lizenzen_Ist.md](10_Abhaengigkeiten_Lizenzen_Ist.md) | Dependencies, Lockfiles, Lizenzen, Audit-Status |
| 11 | [11_Testbarkeit_und_Reproduzierbarkeit_Ist.md](11_Testbarkeit_und_Reproduzierbarkeit_Ist.md) | Tests, Coverage, CI/CD, Reproduzierbarkeit |
| 12 | [12_Schwachstellen_und_Fehlverhalten_Ist.md](12_Schwachstellen_und_Fehlverhalten_Ist.md) | Alle negativen Befunde mit Schweregrad und Evidenz |
| 13 | [13_Staerken_und_Positive_Befunde_Ist.md](13_Staerken_und_Positive_Befunde_Ist.md) | Alle positiven Befunde mit Evidenz |

## Anhaenge

| Anhang | Inhalt |
|--------|--------|
| [ANHANG_DateiInventar.md](ANHANG_DateiInventar.md) | Vollstaendiges Datei-Inventar mit Sicherheitsbezug |
| [ANHANG_Befundliste.csv](ANHANG_Befundliste.csv) | CSV-Export aller Befunde (ID;Kategorie;Schweregrad;Ort;Beschreibung;Evidenz;Status) |

---

## Befund-Statistik

### Schwachstellen (Negativ-Befunde)

| Schweregrad | Anzahl | IDs |
|-------------|--------|-----|
| **Kritisch** | 4 | SV-001, SV-002, SV-003, SV-004 |
| **Hoch** | 7 | SV-005, SV-006, SV-007, SV-008, SV-009, SV-010, SV-011 |
| **Mittel** | 10 | SV-012 bis SV-021 |
| **Niedrig** | 9 | SV-022 bis SV-030 |
| **Gesamt** | **30** | |

### Staerken (Positiv-Befunde)

| Kategorie | Anzahl |
|-----------|--------|
| Datenbank-Sicherheit | 2 |
| Authentifizierung | 5 |
| Verschluesselung | 1 |
| Datei-Operationen | 3 |
| Zugriffskontrolle | 3 |
| Audit und Logging | 2 |
| Auto-Update | 1 |
| BiPRO-Integration | 3 |
| Scan-Upload | 2 |
| Konfiguration | 2 |
| SmartScan | 2 |
| **Gesamt** | **26** |

### Status-Uebersicht

| Status | Anzahl |
|--------|--------|
| Offen | 27 |
| UNVERIFIZIERT | 3 |
| **Gesamt** | **30** |

---

## Kritische Befunde im Ueberblick

| ID | Beschreibung | Ort |
|----|-------------|-----|
| SV-001 | Hardcoded PDF/ZIP-Passwoerter im Quellcode | `src/services/pdf_unlock.py:23-35` |
| SV-002 | Fehlende Security Headers (HSTS, X-Frame-Options, CSP) | `api/index.php` (global) |
| SV-003 | Kein Rate-Limiting auf Login-Endpoint | `api/auth.php` |
| SV-004 | OpenRouter API-Key an Client exponiert | `api/ai.php:58` |

---

## Scope-Hinweise

- **IST-Dokumentation ONLY** — Keine Empfehlungen, keine Fix-Vorschlaege
- Alle Aussagen sind evidenzbasiert (Datei + Zeile) oder als **UNVERIFIZIERT** markiert
- Build-Artefakte (dist/, build/, Output/) wurden nicht analysiert
- Live-Server wurde nicht aktiv getestet (nur Code-Analyse)
- PHP `config.php` ist gitignored — Inhalt aus Dokumentation erschlossen

---

## Naechster Schritt

Fuer einen Loesungsplan zu den identifizierten Schwachstellen: **`security-plan` Skill** verwenden.
