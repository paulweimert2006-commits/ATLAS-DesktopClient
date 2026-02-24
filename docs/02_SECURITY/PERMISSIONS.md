# Berechtigungssystem

> **Stand**: 24.02.2026 | **Gesamt**: 14 Berechtigungen
> **Implementierung**: `BiPro-Webspace Spiegelung Live/api/lib/permissions.php`
> **Client-Seite**: `src/api/auth.py` → `User.has_permission()`

---

## Kontotypen

| Typ | Beschreibung | Standard-Rechte |
|-----|-------------|-----------------|
| `admin` | Administrator | Alle Standard-Rechte automatisch (NICHT Provisions-Rechte) |
| `user` | Benutzer | Nur explizit zugewiesene Rechte |

---

## Berechtigungen

### Standard-Berechtigungen (Admin hat automatisch)

| Permission-Key | Beschreibung | Bereich |
|---------------|-------------|---------|
| `vu_connections_manage` | VU-Verbindungen erstellen/bearbeiten/loeschen | BiPRO |
| `bipro_fetch` | BiPRO-Lieferungen abrufen und herunterladen | BiPRO |
| `documents_manage` | Dokumente verschieben, umbenennen, Farbe setzen | Archiv |
| `documents_delete` | Dokumente loeschen | Archiv |
| `documents_upload` | Dokumente hochladen (Button, Drag&Drop, BiPRO) | Archiv |
| `documents_download` | Dokumente herunterladen (Einzel + Box-Download) | Archiv |
| `documents_process` | Automatische KI-Verarbeitung ausloesen | Archiv |
| `documents_history` | Dokument-Aenderungshistorie einsehen | Archiv |
| `gdv_edit` | GDV-Dateien bearbeiten und speichern | GDV-Editor |
| `smartscan_send` | Dokumente per Smart!Scan (E-Mail) versenden | SmartScan |

### Provisions-Berechtigungen (MUESSEN immer explizit zugewiesen werden)

| Permission-Key | Beschreibung | Besonderheit |
|---------------|-------------|-------------|
| `provision_access` | Zugriff auf Provisions-/GF-Bereich (alle PM-Endpoints) | Auch Admins brauchen explizite Zuweisung |
| `provision_manage` | Darf Provisions-Rechte an andere vergeben + Gefahrenzone | Super-Admin-Konzept |

> **Wichtig**: `provision_access` und `provision_manage` werden NICHT automatisch an Admins vergeben.
> Nur Nutzer mit `provision_manage` koennen diese Rechte an andere Nutzer vergeben.
> `administrator + provision_manage` = Super-Admin (Vollzugriff inkl. Rechtevergabe)

---

## Technische Details

### Berechtigungspruefung (Server)
```php
// Standard-Berechtigung (Admin hat automatisch)
requirePermission('documents_upload');

// Provision-Berechtigung (muss explizit zugewiesen sein)
requirePermission('provision_access');
// → Auch Admin wird geblockt wenn Recht nicht explizit vorhanden
```

### Berechtigungspruefung (Client)
```python
if not self._user.has_permission('documents_upload'):
    button.setEnabled(False)
    button.setToolTip("Keine Berechtigung")
```

### DB-Schema
- **Tabelle `permissions`**: `id`, `permission_key`, `name`, `description`
- **Tabelle `user_permissions`**: `user_id`, `permission_id`, `granted_by`, `created_at`
- **Logik in `lib/permissions.php`**: `hasPermission()`, `requirePermission()`, `getEffectivePermissions()`

### Permission Guards im Client
- BiPRO-Buttons: `bipro_fetch`, `vu_connections_manage`
- Archiv-Buttons: `documents_upload`, `documents_download`, `documents_delete`, `documents_manage`, `documents_process`
- GDV-Editor: `gdv_edit`
- SmartScan: `smartscan_send` (Button + Kontextmenue nur sichtbar wenn Recht vorhanden)
- Provision: `provision_access` (Sidebar-Button nur sichtbar wenn Recht vorhanden)

### Activity-Logging bei Zugriffsverweigerung
Jeder abgelehnte Zugriff wird in `activity_log` geloggt:
- `action_category`: system
- `action`: permission_denied
- `details`: `{"required_permission": "..."}`

---

## Migrationen
- **012**: `documents_history` Berechtigung hinzugefuegt
- **029**: `provision_access` + `provision_manage` hinzugefuegt + Admin-User zugewiesen
