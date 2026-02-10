# Deployment-Prozess (SV-009)

## Uebersicht

ACENCIA ATLAS besteht aus zwei Deployment-Bereichen:
- **PHP-API**: Live-Sync auf Strato Webspace (`BiPro-Webspace Spiegelung Live/`)
- **Desktop-App**: Python-EXE via build.bat + Auto-Update

---

## Pre-Deploy Checkliste

### PHP-API (Server)

- [ ] PHP-Syntax-Check auf allen geaenderten Dateien: `php -l api/dateiname.php`
- [ ] Lokale Smoke-Tests (wenn vorhanden)
- [ ] Kritische Dateien gegenpruefen:
  - `api/config.php`: Keine versehentlichen Aenderungen?
  - `api/lib/`: Keine Breaking Changes in Basis-Bibliotheken?
  - `.htaccess`: Kein versehentliches Loeschen von Schutzregeln?
- [ ] Migrations-Skripte vorbereitet (in `setup/`)

### Desktop-App (Client)

- [ ] `requirements-lock.txt` aktuell?
- [ ] `VERSION`-Datei aktualisiert
- [ ] Lokaler Test: `python run.py` startet ohne Fehler
- [ ] `python -m pytest src/tests/` besteht

---

## Deployment-Ablauf

### PHP-API

1. **Dry-Run**: WinSCP Sync mit "Compare only" Modus → Aenderungen pruefen
2. **Sync**: Live-Ordner synchronisieren (automatisch oder WinSCP)
3. **Post-Deploy**: 
   - `curl -I https://acencia.info/api/status` → HTTP 200 + Security Headers?
   - Migrations-Skripte per SFTP in `setup/` hochladen, ausfuehren, loeschen
4. **Verifikation**: Login testen, ein Dokument hochladen, Archiv aufrufen

### Desktop-App

1. `build.bat` ausfuehren → EXE + SHA256-Hash
2. EXE im Admin-Bereich als Release hochladen
3. Status auf "active" setzen
4. Auto-Update bei Nutzern verifizieren

---

## Rollback

### PHP-API
- Git: `git checkout <commit>` und erneut synchronisieren
- DB-Migrationen: Koennen NICHT automatisch zurueckgerollt werden

### Desktop-App
- Release auf "withdrawn" setzen
- Alten Release als "active" markieren

---

## Empfehlung fuer die Zukunft

1. **Staging-Umgebung** auf Strato als Subdomain einrichten
2. **Git-Branch-Workflow**: Feature → PR → Review → Merge → Deploy
3. **CI/CD**: Mindestens `php -l` + Pytest automatisiert ausfuehren
4. **Monitoring**: UptimeRobot auf `/api/status` (siehe SV-028)
