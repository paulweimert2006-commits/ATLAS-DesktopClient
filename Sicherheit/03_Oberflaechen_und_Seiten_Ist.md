# 03 — Oberflaechen und Seiten (IST-Zustand)

**Audit-Datum:** 10.02.2026
**Projekt:** ACENCIA ATLAS v1.6.0

---

## 3.1 Desktop-Views

### Login-Dialog

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | Benutzer-Authentifizierung |
| Einstiegspunkt | `src/ui/login_dialog.py` |
| Daten | Username, Passwort |
| Rollen | Alle (vor Login) |
| Status | Implementiert |
| Sicherheitsrelevant | Passwort-Masking (`QLineEdit.Password`), "Angemeldet bleiben" Checkbox (8h Token), generische Fehlermeldungen |
| Evidenz | `src/ui/login_dialog.py:130` (Password-Mode), `src/ui/login_dialog.py:137` (Remember), `src/ui/login_dialog.py:242-252` (Fehler) |

### MainHub (Navigation)

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | Haupt-Navigation, Drag&Drop-Upload, Close-Schutz |
| Einstiegspunkt | `src/ui/main_hub.py` |
| Daten | Dateien (Upload), Outlook-E-Mails (COM) |
| Rollen | Alle eingeloggten Benutzer (Upload braucht `documents_upload`) |
| Status | Implementiert |
| Sicherheitsrelevant | Permission-Check vor Upload, Outlook COM-Automation, Close-Blocking bei aktiven Operationen |
| Evidenz | `src/ui/main_hub.py:818-823` (Permission), `src/ui/main_hub.py:886-961` (Outlook COM), `src/ui/main_hub.py:1119-1130` (Close-Schutz) |

### BiPRO-Datenabruf

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | BiPRO-Lieferungen abrufen, herunterladen, ins Archiv |
| Einstiegspunkt | `src/ui/bipro_view.py` |
| Daten | BiPRO-Lieferungen (PDFs, GDV-Dateien), VU-Credentials |
| Rollen | `bipro_fetch` Permission |
| Status | Implementiert |
| Sicherheitsrelevant | Credential-Abruf, SOAP-Kommunikation, MTOM-Parsing, parallele Downloads |
| Evidenz | `src/ui/bipro_view.py` (~4900 Zeilen) |

### Dokumentenarchiv (Box-System)

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | Dokumentenverwaltung mit Box-Kategorien, KI-Klassifikation, SmartScan |
| Einstiegspunkt | `src/ui/archive_boxes_view.py` |
| Daten | PDFs, GDV-Dateien, Excel, CSVs, E-Mails |
| Rollen | Diverses (documents_manage, documents_delete, documents_upload, documents_download, documents_process, documents_history, smartscan_send) |
| Status | Implementiert |
| Sicherheitsrelevant | File-Upload, KI-Klassifikation, SmartScan E-Mail-Versand, PDF-Bearbeitung |
| Evidenz | `src/ui/archive_boxes_view.py` (~5380 Zeilen) |

### GDV-Editor

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | GDV-Datensaetze anzeigen und bearbeiten |
| Einstiegspunkt | `src/ui/gdv_editor_view.py`, `src/ui/main_window.py` |
| Daten | GDV Fixed-Width Dateien (personenbezogene Versicherungsdaten) |
| Rollen | `gdv_edit` Permission fuer Bearbeitung |
| Status | Implementiert |
| Sicherheitsrelevant | PII-Anzeige, Datenbearbeitung, Speichern |
| Evidenz | `src/ui/gdv_editor_view.py` (~648 Zeilen), `src/ui/main_window.py` (~1060 Zeilen) |

### Partner-Ansicht

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | Firmen/Personen mit Vertraegen anzeigen |
| Einstiegspunkt | `src/ui/partner_view.py` |
| Daten | Namen, Adressen, Geburtsdaten, IBANs, Versicherungsschein-Nummern |
| Rollen | Alle eingeloggten Benutzer |
| Status | Implementiert |
| Sicherheitsrelevant | Zeigt PII-Daten direkt an |
| Evidenz | `src/ui/partner_view.py` |

### Admin-Panel

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | Nutzerverwaltung, Sessions, Passwoerter, KI-Kosten, Releases, E-Mail, SmartScan |
| Einstiegspunkt | `src/ui/admin_view.py` |
| Daten | User-Daten, Sessions, Passwoerter, Releases, E-Mail-Konten |
| Rollen | Nur Admin (`account_type='admin'`) |
| Status | Implementiert (10 Panels) |
| Sicherheitsrelevant | User-Erstellung, Permission-Vergabe, Session-Kill, Passwort-Verwaltung |
| Evidenz | `src/ui/admin_view.py` (~4000 Zeilen) |

### Update-Dialog

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | Auto-Update Installation (optional/pflicht/veraltet) |
| Einstiegspunkt | `src/ui/update_dialog.py` |
| Daten | Installer-EXE (aus Server-API) |
| Rollen | Alle eingeloggten Benutzer |
| Status | Implementiert |
| Sicherheitsrelevant | EXE-Download und -Ausfuehrung, SHA256-Verifikation |
| Evidenz | `src/ui/update_dialog.py`, `src/services/update_service.py` |

### Einstellungen-Dialog

| Aspekt | Dokumentation |
|--------|---------------|
| Zweck | Zertifikate verwalten (PFX/P12/JKS Import) |
| Einstiegspunkt | `src/ui/settings_dialog.py` |
| Daten | Client-Zertifikate |
| Rollen | Alle eingeloggten Benutzer |
| Status | Implementiert |
| Sicherheitsrelevant | Zertifikat-Import, Passwort-Eingabe |
| Evidenz | `src/ui/settings_dialog.py` (~350 Zeilen) |

---

## 3.2 PHP API Endpoints

### Oeffentliche Endpoints (keine Authentifizierung)

| Endpoint | Methode | Zweck | Sicherheitsrelevant |
|----------|---------|-------|---------------------|
| `GET /status` | GET | Health-Check | API-Version exponiert |
| `POST /auth/login` | POST | Login | Kein Rate-Limiting |
| `GET /updates/check` | GET | Update-Check | Public, Version-Info |
| `GET /releases/download/{id}` | GET | Release-Download | Public, EXE-Download |
| `POST /incoming-scans` | POST | Scan-Upload | API-Key-Auth (kein JWT) |

**Evidenz:** `api/index.php:36-45` (status), `api/index.php:47-49` (auth), `api/releases.php:38,130` (public)

### Authentifizierte Endpoints (JWT)

| Endpoint | Methode | Permission | Zweck |
|----------|---------|------------|-------|
| `POST /auth/logout` | POST | Eingeloggt | Logout |
| `GET /auth/verify` | GET | Eingeloggt | Token verifizieren |
| `GET /documents` | GET | Eingeloggt | Dokumente listen |
| `GET /documents/{id}` | GET | Eingeloggt | Dokument-Detail |
| `POST /documents` | POST | `documents_upload` | Upload |
| `PUT /documents/{id}` | PUT | `documents_manage` | Update |
| `DELETE /documents/{id}` | DELETE | `documents_delete` | Loeschen |
| `GET /documents/{id}/download` | GET | `documents_download` | Download |
| `GET /documents/{id}/history` | GET | `documents_history` | Historie |
| `POST /documents/{id}/replace` | POST | `documents_manage` | Datei ersetzen |
| `POST /documents/archive` | POST | `documents_manage` | Bulk-Archivierung |
| `POST /documents/unarchive` | POST | `documents_manage` | Bulk-Entarchivierung |
| `POST /documents/colors` | POST | `documents_manage` | Bulk-Farbmarkierung |
| `POST /documents/move` | POST | `documents_manage` | Bulk-Verschieben |
| `GET /documents/stats` | GET | Eingeloggt | Box-Statistiken |
| `GET /credentials` | GET | `vu_connections_manage` | VU-Verbindungen |
| `POST /credentials` | POST | `vu_connections_manage` | VU anlegen |
| `GET /credentials/{id}/decrypt` | GET | `vu_connections_manage` | Credentials entschluesseln |
| `GET /gdv/{docId}` | GET | Eingeloggt | GDV-Datei laden |
| `PUT /gdv/{docId}` | PUT | `gdv_edit` | GDV speichern |
| `GET /gdv/{docId}/records` | GET | Eingeloggt | GDV-Records |
| `GET /shipments` | GET | `bipro_fetch` | Lieferungen |
| `POST /shipments` | POST | `bipro_fetch` | Lieferung anlegen |
| `GET /ai/key` | GET | `documents_process` | OpenRouter-API-Key |
| `GET /passwords` | GET | Eingeloggt | PDF/ZIP-Passwoerter |
| `GET /processing-history` | GET | Eingeloggt | Processing-Historie |
| `POST /smartscan/send` | POST | `smartscan_send` | SmartScan-Versand |
| `GET /smartscan/settings` | GET | Eingeloggt | SmartScan-Einstellungen |
| `GET /xml-index` | GET | Eingeloggt | XML-Index |

### Admin-Endpoints (JWT + Admin-Rolle)

| Endpoint | Methode | Zweck |
|----------|---------|-------|
| `GET /admin/users` | GET | Alle Nutzer listen |
| `POST /admin/users` | POST | Nutzer erstellen |
| `PUT /admin/users/{id}` | PUT | Nutzer bearbeiten |
| `PUT /admin/users/{id}/password` | PUT | Passwort aendern |
| `PUT /admin/users/{id}/lock` | PUT | Nutzer sperren |
| `PUT /admin/users/{id}/unlock` | PUT | Nutzer entsperren |
| `DELETE /admin/users/{id}` | DELETE | Nutzer deaktivieren |
| `GET /admin/permissions` | GET | Permissions listen |
| `GET /sessions` | GET | Aktive Sessions |
| `DELETE /sessions/{id}` | DELETE | Session beenden |
| `GET /activity` | GET | Activity-Log |
| `GET /admin/passwords` | GET | Passwoerter verwalten |
| `POST /admin/passwords` | POST | Passwort anlegen |
| `PUT /admin/passwords/{id}` | PUT | Passwort bearbeiten |
| `DELETE /admin/passwords/{id}` | DELETE | Passwort loeschen |
| `GET /admin/releases` | GET | Releases verwalten |
| `POST /admin/releases` | POST | Release hochladen |
| `PUT /admin/releases/{id}` | PUT | Release bearbeiten |
| `DELETE /admin/releases/{id}` | DELETE | Release loeschen |
| `GET /admin/email-accounts` | GET | E-Mail-Konten |
| `POST /admin/email-accounts` | POST | E-Mail-Konto anlegen |
| `GET /smartscan/settings` | GET/PUT | SmartScan konfigurieren |
| `GET /smartscan/jobs` | GET | SmartScan-Historie |

**Evidenz:** `api/index.php` (gesamte Datei)

---

## 3.3 Permissions-Matrix

| Permission | Beschreibung | Schuetzt |
|------------|-------------|----------|
| `vu_connections_manage` | VU-Verbindungen verwalten | Credentials-CRUD |
| `bipro_fetch` | BiPRO-Daten abrufen | Lieferungen-API |
| `documents_manage` | Dokumente verwalten | Move, Archive, Update, Replace |
| `documents_delete` | Dokumente loeschen | Delete-Endpoint |
| `documents_upload` | Dokumente hochladen | Upload, Drag&Drop |
| `documents_download` | Dokumente herunterladen | Download, Vorschau |
| `documents_process` | Dokumente verarbeiten | KI-Klassifikation, AI-Key |
| `documents_history` | Dokument-Historie einsehen | History-Endpoint |
| `gdv_edit` | GDV bearbeiten | GDV-PUT-Endpoint |
| `smartscan_send` | SmartScan-Versand | SmartScan-Send-Endpoint |

**Admin-Bypass:** Administratoren (`account_type='admin'`) haben automatisch alle Permissions.

**Evidenz:** `api/lib/permissions.php:19-21` (Admin-Bypass), `api/lib/permissions.php:106-126` (requirePermission)
