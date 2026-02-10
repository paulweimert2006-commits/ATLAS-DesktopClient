# 04 — Risiko und Regressionen (Aktuell)

## Beobachtete Risiken

| SV-ID | Risiko | Beschreibung | Mitigation |
|-------|--------|-------------|------------|
| SV-001 | Mittel | PDF/ZIP-Unlock schlaegt fehl wenn API nicht erreichbar | Passwoerter sind in DB, API-Erreichbarkeit ist Voraussetzung |
| SV-004 | Hoch | Latenz-Erhoehung bei KI-Klassifikation (~100-200ms pro Call) | Asynchroner Worker im Client, Nutzer merkt nichts |
| SV-004 | Mittel | PHP max_execution_time bei langen KI-Calls | CURLOPT_TIMEOUT=120s in ai.php gesetzt |
| SV-006 | Hoch | Migration 014 muss vor erstem API-Zugriff laufen | Klartext-Fallback in decrypt() vorhanden |
| SV-016 | Niedrig | PINNED_CERT_HASHES leer → Pinning inaktiv | verify=True weiterhin aktiv |
| SV-021 | Mittel | Unbekannte Dateitypen werden abgelehnt (HTTP 415) | application/octet-stream als Catch-All fuer GDV |

## Regressions-Checks

| Check | Ergebnis | Notiz |
|-------|----------|-------|
| Python-Imports | UNVERIFIZIERT | Laufzeit-Test noetig (python run.py) |
| PHP-Syntax | UNVERIFIZIERT | php -l auf geaenderten Dateien noetig |
| KI-Klassifikation | UNVERIFIZIERT | Proxy-Test gegen Live-Server noetig |
| Login | UNVERIFIZIERT | Rate-Limit-Test gegen Live-DB noetig |

## BLOCKED Items — Begruendung

| SV-ID | Grund | Naechster Schritt |
|-------|-------|-------------------|
| SV-017 | Authenticode-Zertifikat muss gekauft werden | Beschaffung bei Sectigo/GlobalSign |
| SV-020 | HKDF erfordert Re-Verschluesselung aller DB-Eintraege | Wartungsfenster + Backup planen |
| SV-028 | Externer Monitoring-Dienst | UptimeRobot kostenlos einrichten |
| SV-029 | Strato muss SSL fuer MySQL unterstuetzen | `SHOW VARIABLES LIKE 'have_ssl'` pruefen |
