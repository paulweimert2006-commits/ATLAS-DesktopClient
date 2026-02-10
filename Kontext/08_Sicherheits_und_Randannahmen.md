# 08 - Sicherheits- und Randannahmen

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Erkennbare Security-Mechanismen

### Authentifizierung

| Mechanismus | Beschreibung | Quelle |
|-------------|--------------|--------|
| JWT-Token | Bearer Token fuer alle API-Aufrufe | `auth.php`, `client.py` |
| Auto-Refresh | Bei 401 automatischer Token-Refresh mit Deadlock-Schutz | `client.py` |
| Session-Check | Server prueft bei jeder Anfrage ob Session noch gueltig | `auth.php` |
| bcrypt | Passwort-Hashing mit bcrypt | `auth.php` |
| API-Key | Timing-safe Vergleich (`hash_equals`) fuer Scan-Uploads | `incoming_scans.php` |
| Single-Instance | Windows Mutex verhindert mehrere App-Instanzen | `main.py`, `installer.iss` |

### Autorisierung

| Mechanismus | Beschreibung | Quelle |
|-------------|--------------|--------|
| 2 Kontotypen | administrator (alle Rechte), benutzer (granular) | `auth.php`, `admin.php` |
| 10 Permissions | Granulare Berechtigungen fuer jede Funktion | `lib/permissions.php` |
| Permission Guards | Buttons deaktiviert bei fehlenden Rechten | `archive_boxes_view.py`, `bipro_view.py` |
| Admin-only Routes | `requireAdmin()` Middleware fuer Admin-Endpunkte | `index.php` |
| Activity-Logging | Jede API-Aktion wird in `activity_log` geloggt | `lib/activity_logger.php` |

### Datenverschluesselung

| Mechanismus | Beschreibung | Quelle |
|-------------|--------------|--------|
| HTTPS | Alle Verbindungen verschluesselt | Strato SSL |
| AES-256-GCM | E-Mail-Credentials (SMTP/IMAP) verschluesselt in DB | `email_accounts.php` |
| VU-Credentials | Verschluesselt auf Server gespeichert | `credentials.php` |
| .htaccess | config.php nicht ueber HTTP erreichbar | `.htaccess` |

### Dokumenten-Sicherheit

| Mechanismus | Beschreibung | Quelle |
|-------------|--------------|--------|
| SHA256-Hash | Content-Hash bei Upload berechnet, Duplikat-Erkennung | `documents.php` |
| MIME-Whitelist | Scans: Nur PDF, JPG, PNG erlaubt | `incoming_scans.php` |
| Path-Traversal-Schutz | Dateinamen-Bereinigung bei Scans | `incoming_scans.php` |
| Base64-strict | Strikte Base64-Dekodierung bei Scans | `incoming_scans.php` |
| Atomic Write | Staging -> rename() fuer sichere Dateioperationen | `incoming_scans.php` |

### Smart!Scan-Sicherheit

| Mechanismus | Beschreibung | Quelle |
|-------------|--------------|--------|
| Idempotenz | `client_request_id` verhindert Doppelversand (10 Min Fenster) | `smartscan.php` |
| Revisionssicher | Jobs, Items, Emails mit SHA256-Hashes + SMTP Message-IDs | `smartscan.php` |
| TLS | SMTP-Verbindungen ueber TLS | PHPMailer |
| Permission | `smartscan_send` Berechtigung erforderlich | `lib/permissions.php` |

---

## Sensible Daten im Projekt

| Datei/Ort | Inhalt | Schutz |
|-----------|--------|--------|
| `config.php` | DB-Credentials, Master-Key, JWT-Secret, Scan-API-Key | .htaccess, .gitignore |
| `documents/` | Versicherungsdokumente (DSGVO-relevant) | Server-only, kein Web-Zugriff |
| `releases/` | Installer-EXEs | Server-only |
| GDV-Dateien | Adressen, Geburtsdaten, Bankdaten | Nur in App sichtbar |
| VU-Credentials | BiPRO-Zugangsdaten | AES-verschluesselt in DB |
| E-Mail-Credentials | SMTP/IMAP-Passwoerter | AES-256-GCM in DB |
| JWT-Token | Benutzer-Session | In-Memory (nicht persistiert) |

---

## Implizite Annahmen

### Benutzer-Annahmen

| Annahme | Erkannt in |
|---------|-----------|
| Benutzer ist im lokalen Netzwerk oder VPN | Keine IP-Beschraenkung |
| Benutzer hat Windows 10/11 | pywin32, COM-Automation |
| Benutzer hat Outlook installiert (optional) | COM SaveAs fuer Direct-Drop |
| Nur vertrauenswuerdige Benutzer (2-5 Personen) | Kein MFA, keine Passwort-Ablauf-Policy |
| Benutzer kennt GDV/BiPRO-Konzepte | UI setzt Fachkenntnis voraus |

### Technische Annahmen

| Annahme | Erkannt in |
|---------|-----------|
| Server ist immer erreichbar | Kein Offline-Modus |
| BiPRO-Endpunkte sind erreichbar | Kein Fallback, nur Error-Handling |
| OpenRouter hat Guthaben | Keine automatische Aufladung |
| 256 Bytes/Zeile fuer alle GDV-Dateien | Parser lehnt andere ab |
| CP1252 als Default-Encoding | Fallback auf Latin-1, UTF-8 |
| PDF ist dominanter Dokumententyp | KI-Klassifikation nur fuer PDFs |
| Maximal 10 parallele BiPRO-Downloads | BIPRO_DOWNLOAD_CONFIG |
| Maximal 8 parallele KI-Worker | DocumentProcessor |

### Server-Annahmen

| Annahme | Erkannt in |
|---------|-----------|
| Strato Shared Hosting | PHP 7.4+, kein Root-Zugriff |
| PHP Timeout ~30-60 Sekunden | Client-seitiges Chunking (SmartScan max 10 Docs) |
| MySQL immer verfuegbar | Kein Connection-Pooling |
| Dateisystem-Speicherplatz ausreichend | Kein Quota-Check |

---

## Erkennbare Risiken (deskriptiv)

| Risiko | Beschreibung | Status |
|--------|--------------|--------|
| Live-Sync | Lokale Loeschungen entfernen Server-Dateien | Dokumentiert in AGENTS.md |
| Kein MFA | Nur Username/Password, kein zweiter Faktor | Akzeptiertes Risiko (kleine Nutzergruppe) |
| Kein Passwort-Ablauf | Passwoerter laufen nicht ab | - |
| Kein CSRF-Schutz | JWT-basiert (kein Cookie), CSRF theoretisch nicht relevant | - |
| Rate-Limiting nur BiPRO | Keine eigene Rate-Limitierung der PHP-API | - |
| Kein Backup-Mechanismus | Server-Backup ueber Strato | - |
| Shared Hosting | Kein isolierter Server | - |
| Logging ohne Rotation (PHP) | PHP-Logging wird nicht automatisch rotiert | - |
| MTOM-Parser Duplikat | In bipro_view.py UND transfer_service.py | Tech Debt |

---

## Netzwerk-Kommunikation

### Ausgehende Verbindungen (Desktop)

| Ziel | Port | Zweck |
|------|------|-------|
| acencia.info | 443 | PHP REST API |
| transfer.degenia.de | 443 | BiPRO Degenia |
| (VEMA-Endpoints) | 443 | BiPRO VEMA |
| openrouter.ai | 443 | KI-Klassifikation |

### Eingehende Verbindungen

Keine. Desktop-App initiiert alle Verbindungen.

### Server-seitige Verbindungen

| Ziel | Port | Zweck |
|------|------|-------|
| MySQL Server | 3306 | Datenbankzugriff |
| IMAP Server | 993 | E-Mail-Polling |
| SMTP Server | 587 | E-Mail-Versand (Smart!Scan) |

---

## Datenschutz (DSGVO-relevant)

### Personenbezogene Daten

| Datentyp | Speicherort | Zugriff |
|----------|-------------|---------|
| Kundennamen, Adressen | GDV-Dateien, PDFs | Nur in App |
| Geburtsdaten | GDV-Dateien | Nur in App |
| Bankdaten (IBAN/BIC) | GDV-Dateien | Nur in App |
| Versicherungsschein-Nr. | GDV-Dateien, Dokumente | App + Server |
| Benutzername + Passwort | MySQL (bcrypt) | Server |
| Session-Daten | MySQL | Server |
| Activity-Log | MySQL | Server (nur Admin) |

### Datenfluesse

```
Versicherer (BiPRO) --> Desktop-App --> Server (API) --> MySQL/Dateien
                                    --> OpenRouter (KI) [nur Text, keine Dateien]
                                    --> SMTP (Smart!Scan) [Dokumente als Anhang]
```

---

## Implementierte Haertungsmassnahmen

| Massnahme | Beschreibung | Quelle |
|-----------|--------------|--------|
| HTTPS | Alle Verbindungen verschluesselt | Standard |
| bcrypt | Passwort-Hashing | auth.php |
| AES-256-GCM | E-Mail-Credentials | email_accounts.php |
| JWT mit Ablauf | Token-Lebensdauer begrenzt | auth.php |
| .htaccess | config.php geschuetzt | .htaccess |
| hash_equals | Timing-safe Vergleich (API-Key) | incoming_scans.php |
| SSL-Verify | requests verify=True (Standard) | client.py |
| Path-Traversal-Schutz | Dateinamen-Bereinigung | incoming_scans.php |
| Schliess-Schutz | App blockiert Schliessen bei laufenden Operationen | main_hub.py |
| SHA256-Verifikation | Update-Installer wird vor Installation verifiziert | update_service.py |
| Idempotenz | Smart!Scan Doppelversand-Schutz | smartscan.php |
