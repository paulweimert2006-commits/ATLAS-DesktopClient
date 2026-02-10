# 05 — Risiko und Regressionen

Analyse von Breaking Changes, Fallback-Plaenen und Regressionsrisiken fuer alle 30 Massnahmen.

---

## 5.1 Risiko-Matrix

| M-ID | Regressions-Risiko | Breaking Change | Rollback moeglich | Fallback-Plan |
|------|-------------------|-----------------|-------------------|---------------|
| M-001 | **Mittel** | Ja (Fallback entfaellt) | Ja (Code revert) | Leere Liste statt Fehler |
| M-002 | **Keines** | Nein | Ja (Funktion entfernen) | Desktop-App ignoriert Headers |
| M-003 | **Niedrig** | Nein (neue Funktionalitaet) | Ja (Rate-Limiter-Check auskommentieren) | Lockout-Zeit verkuerzen |
| M-004 | **Hoch** | Ja (API-Aenderung) | Bedingt (alter Endpoint reaktivierbar) | GET /ai/key temporaer beibehalten |
| M-005 | **Niedrig** | Nein (Migration) | Ja (auf Datei zurueckfallen) | Datei-Fallback mit 0o600 |
| M-006 | **Hoch** | Ja (DB-Schema) | Bedingt (Backup noetig) | DB-Backup vor Migration |
| M-007 | **Niedrig** | Nein | Ja (Limit erhoehen) | 500 MB Limit ist grosszuegig |
| M-008 | **Keines** | Nein | Ja (atexit entfernen) | Bestehender close()-Cleanup bleibt |
| M-009 | **Keines** | Nein (nur Doku) | N/A | N/A |
| M-010 | **Niedrig** | Nein (Migration) | Ja (auf Datei zurueckfallen) | Datei-Fallback mit 0o600 |
| M-011 | **Keines** | Nein | N/A | Alte requirements.txt bleibt |
| M-012 | **Keines** | Nein | Ja | Int-Cast bleibt als Backup |
| M-013 | **Niedrig** | Nein | Ja (Redaktion ausschalten) | KI-Qualitaet monitoren |
| M-014 | **Keines** | Nein | Ja | Maskierung entfernen |
| M-015 | **Keines** | Nein (Default unveraendert) | Ja | Default = kein Proxy (wie bisher) |
| M-016 | **Niedrig** | Nein | Ja (Pinning deaktivieren) | 2 Pins speichern (aktuell + naechster) |
| M-017 | **Keines** | Nein (additiv) | N/A | SHA256-Check bleibt |
| M-018 | **Keines** | Nein | Ja (.htaccess loeschen) | Manuell aufrufbar per SFTP |
| M-019 | **Keines** | Nein | Ja (Cleanup stoppen) | Retention-Days erhoehen |
| M-020 | **Hoch** | Ja (Kryptographie) | **DB-Backup zwingend** | Alter Key als Fallback |
| M-021 | **Mittel** | Moeglich | Ja (Whitelist erweitern) | octet-stream als Catch-All |
| M-022 | **Keines** | Nein | N/A | Manuell weiter |
| M-023 | **Keines** | Nein | Ja | Version wieder einbauen |
| M-024 | **Keines** | Nein | Ja | Alten Code wiederherstellen |
| M-025 | **Keines** | Nein | Ja | Logging entfernen |
| M-026 | **Keines** | Nein (nur Doku) | N/A | N/A |
| M-027 | **Keines** | Nein (nur Doku/Entscheidung) | N/A | N/A |
| M-028 | **Keines** | Nein | Ja (Monitor abschalten) | N/A |
| M-029 | **Keines** | Nein | Ja | SSL-Parameter entfernen |
| M-030 | **Keines** | Nein (nur Tests) | N/A | Tests loeschen |

---

## 5.2 Hochrisiko-Massnahmen (Detail)

### M-004: OpenRouter-Proxy — Regressions-Risiko HOCH

**Breaking Change:**
- `GET /ai/key` liefert keinen API-Key mehr
- Client muss `POST /ai/classify` statt direktem OpenRouter-Call nutzen

**Regressions-Szenarien:**
1. PHP `max_execution_time` zu kurz fuer OpenRouter-Response (30s Default)
   - **Mitigation:** `set_time_limit(60)` im Proxy-Handler
2. OpenRouter-Fehler werden anders an Client weitergegeben
   - **Mitigation:** Proxy gibt strukturierte Fehlercodes zurueck
3. Parallele Verarbeitung: Mehrere Proxy-Calls gleichzeitig auf Shared Hosting
   - **Mitigation:** Client serialisiert Calls (wie bisher)
4. OpenRouter-Guthaben-Abfrage muss auch ueber Proxy laufen
   - **Mitigation:** Separater Endpoint `GET /ai/credits`

**Fallback-Plan:**
- Phase 1: `GET /ai/key` erstmal beibehalten (deprecated, Logging wenn aufgerufen)
- Phase 2: Client-Update deployed mit Proxy-Support
- Phase 3: `GET /ai/key` entfernen nach Verifikation

**Rollback:**
- `GET /ai/key` wieder aktivieren
- Client-Code hat Fallback auf direkte OpenRouter-Calls

---

### M-006: Passwoerter verschluesseln — Regressions-Risiko HOCH

**Breaking Change:**
- `password_value` Spalte enthaelt nach Migration verschluesselte Werte
- Alter Client-Code ohne Entschluesselung wuerde nicht funktionieren

**Regressions-Szenarien:**
1. Migration schlaegt fehl → Halb-verschluesselte Tabelle
   - **Mitigation:** Migration in Transaktion, Rollback bei Fehler
2. MASTER_KEY aendert sich → Alte Verschluesselung nicht mehr lesbar
   - **Mitigation:** MASTER_KEY NICHT aendern waehrend Migration
3. PHP-Version auf Strato unterstuetzt `Crypto::encrypt()` nicht
   - **Mitigation:** Wird bereits fuer VU-Credentials genutzt, also verfuegbar

**Fallback-Plan:**
- DB-Backup VOR Migration erstellen (`mysqldump known_passwords`)
- Migration hat Dry-Run-Modus (liest und validiert, aendert nicht)
- Bei Fehler: Backup zurueckspielen

**Rollback:**
- `mysqldump`-Backup zurueckspielen
- Code-Revert auf Pre-Verschluesselung

---

### M-020: HKDF Key-Derivation — Regressions-Risiko HOCH

**Breaking Change:**
- Neuer Key-Derivation-Algorithmus → Bestehende verschluesselte Daten nicht mehr direkt lesbar
- Erfordert Re-Verschluesselung ALLER verschluesselten Daten

**Betroffene Daten:**
- `vu_connections.credentials_encrypted` (VU-Credentials)
- `email_accounts.password_encrypted`, `email_accounts.smtp_password_encrypted` (E-Mail)
- `known_passwords.password_value` (nach M-006)

**Regressions-Szenarien:**
1. Re-Verschluesselung laeuft nicht vollstaendig → Mischzustand
   - **Mitigation:** Migration in Transaktion
2. PHP-Version hat kein `hash_hkdf()` (erst ab PHP 8.1)
   - **Mitigation:** Eigene HKDF-Implementierung auf Basis von `hash_hmac()`
3. Bestehende Sessions nutzen alten Key → Temporaerer Fehler
   - **Mitigation:** Dual-Key-Strategie (alter + neuer Key fuer Entschluesselung)

**Fallback-Plan:**
- Dual-Key: Versuche neuen Key, bei Fehler alten Key
- DB-Backup zwingend vor Migration
- Migration kann schrittweise: Neue Daten mit neuem Key, alte Daten on-demand migrieren

**Rollback:**
- DB-Backup zurueckspielen
- Code-Revert auf `hash('sha256', ...)` Derivation

---

### M-001: Hardcoded Passwords entfernen — Regressions-Risiko MITTEL

**Breaking Change:**
- Wenn API nicht erreichbar: PDF/ZIP-Unlock schlaegt fehl (kein Fallback mehr)

**Regressions-Szenarien:**
1. Erster Start nach Update, API noch nicht konfiguriert
   - **Mitigation:** Verstaendliche Fehlermeldung im Toast
2. Netzwerk-Ausfall waehrend Upload
   - **Mitigation:** Passwoerter werden gecacht (Session-Cache bleibt)
3. Neue Installation ohne DB-Seed-Daten
   - **Mitigation:** Migration-Script prueft ob Seed-Daten vorhanden

**Fallback-Plan:**
- Session-Cache verhindert wiederholte API-Calls
- Fehlermeldung statt stilles Scheitern

---

### M-021: MIME-Whitelist — Regressions-Risiko MITTEL

**Breaking Change:**
- Bisher akzeptierte Dateitypen koennten abgelehnt werden

**Regressions-Szenarien:**
1. BiPRO-Dokumente mit unbekanntem MIME-Type
   - **Mitigation:** `application/octet-stream` in Whitelist
2. GDV-Dateien haben keinen Standard-MIME-Type
   - **Mitigation:** Endungs-Check als Fallback (.gdv, .dat, .txt)
3. Automatischer Upload aus BiPRO schlaegt fehl
   - **Mitigation:** BiPRO-Upload umgeht MIME-Check (vertrauenswuerdige Quelle)

**Fallback-Plan:**
- Whitelist kann schnell erweitert werden (1 Zeile PHP)
- Logging aller abgelehnten Uploads fuer Analyse

---

## 5.3 Kumulative Risiken bei gleichzeitiger Umsetzung

| Kombination | Risiko | Empfehlung |
|-------------|--------|-----------|
| M-001 + M-006 | Passwoerter nicht mehr als Fallback UND DB-Verschluesselung | M-001 zuerst, M-006 danach testen |
| M-004 + M-013 | Proxy + PII-Redaktion gleichzeitig | M-004 (Proxy) zuerst ohne PII, PII als zweiter Schritt |
| M-005 + M-010 | Beide nutzen B5 (Keyring) | Zusammen umsetzen, da gleicher Baustein |
| M-006 + M-020 | Beide aendern Kryptographie | M-006 zuerst (vorhandener Algo), M-020 spaeter (neuer Algo) |
| M-020 + M-006 | Doppelte Re-Verschluesselung | M-020 NACH M-006, nicht gleichzeitig |

---

## 5.4 Nicht-technische Risiken

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|-----------|-----------|
| Team versteht Rate-Limiting nicht | Mittel | Support-Anfragen | Dokumentation + Toast-Meldung |
| Proxy erhoecht Latenz merkbar | Niedrig | UX-Verschlechterung | Monitoring, ggf. Timeout erhoehen |
| Keyring-Probleme auf manchen Windows-Systemen | Niedrig | Login funktioniert nicht | Datei-Fallback |
| Code-Signing-Zertifikat laeuft ab | Hoch (jaehrlich) | Installer unsigniert | Erinnerung 30 Tage vorher |
| HKDF-Migration fehlschlaegt im Produktivbetrieb | Niedrig | VU-Credentials nicht lesbar | Wartungsfenster, DB-Backup |
