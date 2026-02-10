# 06 — Rollout und Kompatibilitaet

Wellenplan, DB-Migrationen, Client/Server-Abwaertskompatibilitaet und Rollout-Strategie.

---

## 6.1 Wellenplan (Detail)

### Welle 1 — Kritisch + Quick Wins (~2 Tage)

| Tag | Massnahme | Server | Client | DB-Migration | Abhaengig von |
|-----|-----------|--------|--------|-------------|---------------|
| 1 | M-001 | Nein | Ja | Nein | — |
| 1 | M-002 | Ja (B1) | Nein | Nein | — |
| 1 | M-012 | Ja | Nein | Nein | — |
| 1 | M-018 | Ja | Nein | Nein | — |
| 2 | M-003 | Ja (B2) | Update empfohlen | Ja (rate_limits) | — |

**Deployment-Reihenfolge Welle 1:**
1. PHP-Code deployen (B1, M-012, M-018)
2. DB-Migration ausfuehren (rate_limits Tabelle)
3. Rate-Limiter aktivieren (M-003)
4. Python-Code aendern (M-001 — Fallback entfernen)
5. Testen: Security Headers, Rate-Limiting, Setup-Schutz

---

### Welle 2 — Hoch-Prio Secrets + Validation (~3 Tage)

| Tag | Massnahme | Server | Client | DB-Migration | Abhaengig von |
|-----|-----------|--------|--------|-------------|---------------|
| 3 | M-011 | Nein | Ja | Nein | — |
| 3 | M-007 | Nein | Ja | Nein | — |
| 3 | M-008 | Nein | Ja (B4) | Nein | — |
| 3 | M-021 | Ja | Nein | Nein | — |
| 4 | M-005 | Nein | Ja (B5) | Nein | — |
| 4 | M-010 | Nein | Ja (B5) | Nein | M-005 |
| 4 | M-006 | Ja | Nein | Ja (Verschluesselung) | M-001 |
| 5 | M-004 | Ja (B3) | Ja | Nein | — |

**Deployment-Reihenfolge Welle 2:**
1. Python-Aenderungen (M-007, M-008, M-011)
2. B5 (secure_storage.py) erstellen → M-005, M-010
3. PHP: MIME-Whitelist deployen (M-021)
4. PHP: Passwoerter-Verschluesselung + Migration (M-006)
5. PHP: OpenRouter-Proxy deployen (M-004 Server-Seite)
6. Python: OpenRouter-Client auf Proxy umstellen (M-004 Client-Seite)
7. GET /ai/key deprecaten (Logging, nicht sofort entfernen)

**Kritischer Pfad:** M-004 erfordert koordiniertes Server+Client-Update.

---

### Welle 3 — Mittel + Niedrig (~4 Tage)

| Tag | Massnahme | Server | Client | DB-Migration | Abhaengig von |
|-----|-----------|--------|--------|-------------|---------------|
| 6 | M-014 | Nein | Ja | Nein | — |
| 6 | M-015 | Nein | Ja | Nein | — |
| 6 | M-024 | Nein | Ja | Nein | — |
| 6 | M-025 | Nein | Ja | Nein | — |
| 6 | M-023 | Ja | Nein | Nein | — |
| 7 | M-013 | Ja (in B3) | Nein | Nein | M-004 |
| 7 | M-019 | Ja | Nein | Nein | — |
| 7 | M-009 | Doku | Nein | Nein | — |
| 7 | M-026 | Doku | Nein | Nein | — |
| 7 | M-027 | Doku | Nein | Nein | — |
| 8 | M-016 | Nein | Ja | Nein | — |
| 8 | M-030 | Nein | Ja | Nein | — |
| 8 | M-029 | Ja | Nein | Nein | — |
| 9 | M-020 | Ja | Nein | Ja (Re-Verschl.) | **DB-Backup!** |
| 9 | M-022 | Ja | Nein | Nein | — |
| 9 | M-017 | Build | Nein | Nein | — |
| 9 | M-028 | Extern | Nein | Nein | — |

---

## 6.2 DB-Migrationen

### Migration 1: rate_limits (Welle 1, M-003)

```sql
-- Datei: setup/013_rate_limits.php
CREATE TABLE IF NOT EXISTS rate_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    username VARCHAR(100) DEFAULT '',
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ip_time (ip_address, attempted_at),
    INDEX idx_cleanup (attempted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Risiko:** Keines (neue Tabelle, keine Aenderung bestehender Daten)
**Rollback:** `DROP TABLE rate_limits;`

---

### Migration 2: known_passwords Verschluesselung (Welle 2, M-006)

```sql
-- Datei: setup/014_encrypt_passwords.php
-- Liest alle Klartext-Passwoerter, verschluesselt sie mit Crypto::encrypt()
-- und schreibt sie zurueck.

-- Pseudocode:
-- 1. SELECT id, password_value FROM known_passwords
-- 2. Fuer jeden Eintrag: Pruefen ob bereits verschluesselt (Base64-Pattern)
-- 3. Wenn Klartext: UPDATE SET password_value = Crypto::encrypt(password_value)
```

**Risiko:** Hoch — Daten nicht mehr lesbar bei Fehler
**Voraussetzung:** DB-Backup (`mysqldump known_passwords`)
**Rollback:** Backup einspielen
**Idempotenz:** Script prueft ob Wert bereits verschluesselt (Base64-Laenge > Klartext)

---

### Migration 3: HKDF Re-Verschluesselung (Welle 3, M-020)

```sql
-- Datei: setup/015_hkdf_reencrypt.php
-- Re-Verschluesselung aller verschluesselten Felder:
-- 1. vu_connections.credentials_encrypted (mit altem Key entschluesseln, neuem Key verschluesseln)
-- 2. email_accounts.password_encrypted
-- 3. email_accounts.smtp_password_encrypted
-- 4. known_passwords.password_value (bereits mit M-006 verschluesselt)
```

**Risiko:** Sehr hoch — Alle Credentials unlesbar bei Fehler
**Voraussetzung:** Vollstaendiges DB-Backup
**Wartungsfenster:** App sperren waehrend Migration (5-10 Minuten)
**Rollback:** Vollstaendiges DB-Backup einspielen + Code-Revert
**Dual-Key-Strategie:** Neuer Code versucht zuerst neuen Key, dann alten Key (Uebergangsphase)

---

## 6.3 Server/Client-Abwaertskompatibilitaet

### Szenario: Alter Client + Neuer Server

| Massnahme | Alter Client funktioniert? | Anmerkung |
|-----------|--------------------------|-----------|
| M-002 (Security Headers) | ✅ Ja | Headers werden ignoriert |
| M-003 (Rate-Limiting) | ✅ Ja (mit Einschraenkung) | HTTP 429 muss als Fehler angezeigt werden |
| M-004 (OpenRouter-Proxy) | ❌ **Nein** (wenn /ai/key entfernt) | Uebergangsphase: /ai/key beibehalten |
| M-006 (DB-Verschluesselung) | ✅ Ja | API entschluesselt transparent |
| M-012 (LIMIT/OFFSET) | ✅ Ja | Keine API-Aenderung |
| M-018 (Setup-Schutz) | ✅ Ja | Nicht Client-relevant |
| M-021 (MIME-Whitelist) | ⚠️ Moeglich | Wenn Client unbekannte MIME-Types sendet |
| M-023 (Version entfernt) | ✅ Ja | Client nutzt /status nicht |

### Szenario: Neuer Client + Alter Server

| Massnahme | Neuer Client funktioniert? | Anmerkung |
|-----------|--------------------------|-----------|
| M-001 (Fallback entfernt) | ⚠️ Eingeschraenkt | PDF-Unlock nur mit API (wenn verfuegbar) |
| M-004 (Proxy-Client) | ❌ **Nein** | POST /ai/classify existiert nicht auf altem Server |
| M-005 (Keyring) | ✅ Ja | Nur lokale Aenderung |
| M-007 (Zip-Bomb) | ✅ Ja | Nur lokale Aenderung |
| M-008 (Temp-Files) | ✅ Ja | Nur lokale Aenderung |

### Empfehlung: Koordiniertes Update

Fuer M-004 (OpenRouter-Proxy):
1. **Phase A:** Server deployen mit BEIDEN Endpoints (`/ai/key` + `/ai/classify`)
2. **Phase B:** Client-Update verteilen (nutzt `/ai/classify`)
3. **Phase C:** `/ai/key` entfernen (nach Verifikation dass alle Clients aktualisiert sind)
4. **Phase D:** Pflicht-Update setzen (ueber Releases-System) → erzwingt Client-Update

---

## 6.4 Rollout-Checkliste pro Welle

### Welle 1 Checkliste

- [ ] DB-Backup erstellen
- [ ] Migration 013 (rate_limits) ausfuehren
- [ ] PHP-Code deployen (response.php, index.php, gdv.php, activity.php, setup/.htaccess)
- [ ] Security Headers pruefen: `curl -I https://acencia.info/api/status`
- [ ] Rate-Limiting testen: 6 Fehlversuche → HTTP 429
- [ ] Setup-Schutz testen: `curl https://acencia.info/setup/migration_admin.php` → 403
- [ ] LIMIT/OFFSET testen: GDV-Pagination, Activity-Log-Pagination
- [ ] Python-Code aktualisieren (M-001: Fallback entfernen)
- [ ] PDF-Unlock testen mit API-Passwoertern

### Welle 2 Checkliste

- [ ] DB-Backup erstellen
- [ ] Python: Lockfile erzeugen (M-011)
- [ ] Python: Zip-Bomb-Schutz (M-007), Temp-File-Guard (M-008)
- [ ] Python: secure_storage.py erstellen (B5)
- [ ] Python: JWT-Token-Migration (M-005)
- [ ] Python: Zertifikat-Migration (M-010)
- [ ] PHP: MIME-Whitelist deployen (M-021)
- [ ] PHP: Migration 014 (Passwort-Verschluesselung) ausfuehren (M-006)
- [ ] PHP: OpenRouter-Proxy deployen (M-004)
- [ ] Python: OpenRouter-Client auf Proxy umstellen (M-004)
- [ ] KI-Klassifikation testen (ueber Proxy)
- [ ] PDF/ZIP-Unlock testen (verschluesselte DB-Passwoerter)
- [ ] BiPRO mit Client-Zertifikat testen (B5)
- [ ] Login mit "Angemeldet bleiben" testen (B5)

### Welle 3 Checkliste

- [ ] DB-Backup erstellen (zwingend fuer M-020!)
- [ ] Python: PII-Filterung (M-014), Proxy-Option (M-015)
- [ ] Python: Temp-File-Fix (M-024), MSG-Logging (M-025)
- [ ] PHP: Version aus Status entfernen (M-023)
- [ ] PHP: PII-Redaktion im Proxy (M-013)
- [ ] PHP: Log-Retention (M-019)
- [ ] Dokumentation erstellen: DEPLOYMENT.md, SECURITY.md, LICENSES.md (M-009, M-026, M-027)
- [ ] Python: Certificate-Pinning (M-016), Security-Tests (M-030)
- [ ] PHP: MySQL-SSL pruefen (M-029)
- [ ] **WARTUNGSFENSTER:** Migration 015 (HKDF Re-Verschluesselung, M-020)
- [ ] PHP: composer.json erstellen (M-022)
- [ ] Build: Code-Signing einrichten (M-017)
- [ ] Monitoring: UptimeRobot einrichten (M-028)
- [ ] Abschluss: Alle T-* Tests durchfuehren

---

## 6.5 Versions-Strategie

| Welle | App-Version | Release-Typ | Pflicht-Update |
|-------|------------|-------------|---------------|
| 1 | v1.7.0 | Stable | Nein (Server-Aenderungen abwaertskompatibel) |
| 2 | v1.8.0 | Stable | **Ja** (nach M-004 Client-Update, /ai/key entfernt) |
| 3 | v1.9.0 | Stable | Nein (keine Breaking Client-Changes) |

**VERSION-Datei** wird bei jeder Welle aktualisiert. `build.bat` synchronisiert automatisch.
