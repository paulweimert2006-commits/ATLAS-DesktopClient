# Sicherheit / Loesung — Security Fix Plan

**Projekt:** ACENCIA ATLAS v1.6.0
**Plan-Datum:** 10.02.2026
**Grundlage:** Security Audit vom 10.02.2026 (30 Befunde)
**Audit-Verzeichnis:** [../Sicherheit/](../Sicherheit/)

---

## Statistik

| Kategorie | Wert |
|-----------|------|
| Befunde gesamt | 30 |
| Massnahmen gesamt | 30 |
| Wiederverwendbare Bausteine | 5 (B1-B5) |
| Wellen | 3 |
| Geschaetzter Gesamtaufwand | ~9 Tage |
| DB-Migrationen | 3 |
| Hochrisiko-Massnahmen | 3 (M-004, M-006, M-020) |

---

## Wellenplan (Uebersicht)

| Welle | Prio | Massnahmen | Aufwand | DB-Migration |
|-------|------|-----------|---------|-------------|
| 1 | Kritisch + Quick Wins | M-001, M-002, M-003, M-012, M-018 | ~2 Tage | 1 (rate_limits) |
| 2 | Hoch-Prio Secrets + Validation | M-004 bis M-008, M-010, M-011, M-021 | ~3 Tage | 1 (Passwort-Verschl.) |
| 3 | Mittel + Niedrig | M-009, M-013 bis M-020, M-022 bis M-030 | ~4 Tage | 1 (HKDF Re-Verschl.) |

---

## Inhaltsverzeichnis

| # | Datei | Inhalt |
|---|-------|--------|
| 1 | [01_Plan_Uebersicht.md](01_Plan_Uebersicht.md) | Befund-Cluster, Root-Causes, Bausteine, Abhaengigkeiten, Umsetzungsreihenfolge |
| 2 | [02_Massnahmenkatalog.md](02_Massnahmenkatalog.md) | Alle 30 Massnahmen: Root-Cause, Fix-Beschreibung, betroffene Dateien, Verifikation, Risiko |
| 3 | [03_Technische_Designs.md](03_Technische_Designs.md) | 5 Bausteine (B1-B5): Security Headers, Rate-Limiter, OpenRouter-Proxy, Temp-File-Guard, DPAPI/Keyring |
| 4 | [04_Verifikation_und_Testplan.md](04_Verifikation_und_Testplan.md) | Given/When/Then Tests + Negativ-Tests fuer alle 30 Massnahmen |
| 5 | [05_Risiko_und_Regressionen.md](05_Risiko_und_Regressionen.md) | Risiko-Matrix, Breaking Changes, Fallback-Plaene, kumulative Risiken |
| 6 | [06_Rollout_und_Kompatibilitaet.md](06_Rollout_und_Kompatibilitaet.md) | Wellenplan, DB-Migrationen, Abwaertskompatibilitaet, Rollout-Checklisten |
| A1 | [ANHANG_Mapping_Befund_zu_Massnahme.csv](ANHANG_Mapping_Befund_zu_Massnahme.csv) | SV-ID zu M-ID Mapping (CSV, Semikolon-getrennt) |
| A2 | [ANHANG_Checkliste_Coverage.md](ANHANG_Checkliste_Coverage.md) | Coverage-Tabelle: Alle 30 Befunde mit Testtyp und Automatisierbarkeit |

---

## Bausteine (Quick Reference)

| ID | Name | Loest | Dateien |
|----|------|-------|---------|
| B1 | Security-Headers-Middleware | SV-002 | `api/lib/response.php`, `api/index.php` |
| B2 | Rate-Limiter (PHP, DB-basiert) | SV-003 | `api/lib/rate_limiter.php`, `api/auth.php` |
| B3 | OpenRouter-Proxy | SV-004, SV-013 | `api/ai.php`, `src/api/openrouter.py` |
| B4 | Temp-File-Guard (Python) | SV-008, SV-024 | `src/bipro/transfer_service.py`, `src/services/pdf_unlock.py` |
| B5 | DPAPI/Keyring-Wrapper (Python) | SV-005, SV-010 | `src/services/secure_storage.py` (neu), `src/api/auth.py` |

---

## Naechste Schritte

1. Plan mit Team reviewen
2. DB-Backup vor jeder Welle erstellen
3. Welle 1 umsetzen (Kritisch + Quick Wins)
4. Welle 1 verifizieren (T-001, T-002, T-003, T-012, T-018)
5. Welle 2 umsetzen (koordiniertes Server+Client-Update fuer M-004)
6. Welle 3 umsetzen (M-020 nur im Wartungsfenster!)
7. Abschluss: Alle T-* Tests durchfuehren, AGENTS.md aktualisieren
