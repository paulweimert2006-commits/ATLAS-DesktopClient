# Security-Fix-Umsetzung — Index

**Projekt:** ACENCIA ATLAS v1.6.0
**Umsetzungsdatum:** 10.02.2026
**Grundlage:** Security Audit + Fix-Plan vom 10.02.2026

---

## Statistik

| Status | Anzahl |
|--------|--------|
| DONE | 26 |
| BLOCKED | 4 |
| **Gesamt** | **30** |

### BLOCKED Begruendung

| SV-ID | Grund |
|-------|-------|
| SV-017 | Code-Signing: Authenticode-Zertifikat noetig (~100-300 EUR/Jahr) |
| SV-020 | HKDF: DB-Migration mit Wartungsfenster + Backup erforderlich |
| SV-028 | Monitoring: Externer Dienst muss eingerichtet werden |
| SV-029 | MySQL-SSL: Strato-seitige Pruefung erforderlich |

---

## Dokumente

| Datei | Inhalt |
|-------|--------|
| [01_Arbeitsprotokoll.md](01_Arbeitsprotokoll.md) | Chronologisches Protokoll aller Aenderungen |
| [02_Aenderungsliste.md](02_Aenderungsliste.md) | Alle geaenderten/neuen Dateien mit SV-Bezug |
| [03_Verifikationsergebnisse.md](03_Verifikationsergebnisse.md) | Test-Ergebnisse je SV |
| [04_Risiko_und_Regressionen_Aktuell.md](04_Risiko_und_Regressionen_Aktuell.md) | Aktuelle Risiken und BLOCKED-Begruendungen |
| [05_Statusmatrix.csv](05_Statusmatrix.csv) | Maschinenlesbare Statusmatrix |

---

## Neue Dateien (erstellt waehrend Umsetzung)

| Datei | SV-ID | Zweck |
|-------|-------|-------|
| `api/lib/rate_limiter.php` | SV-003 | Rate-Limiting Klasse |
| `api/lib/log_cleanup.php` | SV-019 | Log-Retention-Policy |
| `setup/013_rate_limits.php` | SV-003 | DB-Migration |
| `setup/014_encrypt_passwords.php` | SV-006 | Passwort-Verschluesselung |
| `setup/.htaccess` | SV-018 | Zugriffsschutz |
| `composer.json` | SV-022 | PHP Dependency-Management |
| `docs/DEPLOYMENT.md` | SV-009 | Deployment-Checkliste |
| `docs/SECURITY.md` | SV-026/027/029 | Security-Dokumentation |
| `src/tests/test_security.py` | SV-030 | Security-Tests |
| `requirements-lock.txt` | SV-011 | Dependency-Lockfile |

---

## Erforderliche Post-Deploy-Aktionen

1. **DB-Migration 013** ausfuehren: `rate_limits` Tabelle erstellen
2. **DB-Migration 014** ausfuehren: Bestehende Passwoerter verschluesseln
3. **Server-Test**: `curl -I https://acencia.info/api/status` → Security Headers pruefen
4. **Login-Test**: Rate-Limiting verifizieren (6. Fehlversuch → HTTP 429)
5. **KI-Test**: Dokumenten-Klassifikation ueber Proxy testen
6. **Upload-Test**: PDF, CSV, GDV-Datei hochladen (MIME-Whitelist pruefen)
