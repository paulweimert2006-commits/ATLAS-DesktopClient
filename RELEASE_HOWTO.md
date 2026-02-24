# ACENCIA ATLAS - Neues Release erstellen

## Methode 1: Automatisch (empfohlen)

Ein einziger Befehl erledigt alles - Version hochzaehlen, bauen und hochladen:

```
0_release.bat
```

Das Script fragt interaktiv nach:
1. Version bestaetigen (wird automatisch hochgezaehlt)
2. **Neue Features** eingeben (werden automatisch formatiert - siehe unten)
3. Admin-Zugangsdaten fuer den Upload

**Automatisches Release-Notes-Format:**
```
Willkommen bei ACENCIA ATLAS.
Der Datenkern für Versicherungsprofis. [...]
----------------------------------------------------------------
- Neue Feature 1 (was du eingibst)
- Neue Feature 2
----------------------------------------------------------------
- Alle bisherigen Features (automatisch aus RELEASE_FEATURES_HISTORY.txt)
```

Die eingegebenen Features werden automatisch zur History-Datei hinzugefuegt,
sodass sie bei zukuenftigen Releases im unteren Bereich erscheinen.

**Optionen fuer Versions-Increment:**
```
0_release.bat              ← Patch:  0.9.8 → 0.9.9  (Standard)
0_release.bat minor        ← Minor:  0.9.8 → 0.10.0
0_release.bat major        ← Major:  0.9.8 → 1.0.0
```

Nach Abschluss ist das Release sofort in der Admin-Verwaltung sichtbar.

---

## Methode 2: Manuell (Schritt fuer Schritt)

Falls das automatische Script nicht funktioniert oder du einzelne Schritte
manuell ausfuehren moechtest:

### Schritt 1: Version hochzaehlen

Oeffne die Datei `VERSION` im Projektroot und erhoehe die Versionsnummer:

```
0.9.9
```

Die Datei enthaelt NUR die Versionsnummer, nichts anderes.

**Schema:** `MAJOR.MINOR.PATCH` (z.B. 0.9.8 → 0.9.9 → 0.10.0 → 1.0.0)

### Schritt 2: Build ausfuehren

Doppelklick auf **`build.bat`** im Projektroot.

Das Script macht automatisch:
- Alte Builds aufraumen
- `version_info.txt` und `installer.iss` auf neue Version aktualisieren
- EXE mit PyInstaller erstellen
- Installer mit Inno Setup erstellen
- SHA256-Hash generieren

**Dauer:** ca. 3-5 Minuten

**Ergebnis:**
```
Output\ACENCIA-ATLAS-Setup-X.Y.Z.exe     ← Installer (zum Hochladen)
Output\ACENCIA-ATLAS-Setup-X.Y.Z.sha256  ← Hash (zur Kontrolle)
dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe      ← Standalone-EXE (zum Testen)
```

### Schritt 3: Testen

Starte die gebaute EXE:
```
dist\ACENCIA-ATLAS\ACENCIA-ATLAS.exe
```

Pruefe mindestens:
- [ ] App startet und Login funktioniert
- [ ] BiPRO-Bereich oeffnet sich
- [ ] Dokumentenarchiv laedt
- [ ] Version in Fenstertitel ist korrekt

### Schritt 4: Release im Admin-Bereich hochladen

1. App starten (entweder die neue EXE oder `python run.py`)
2. Als **Admin** einloggen
3. Navigation → **Administration**
4. Tab → **Releases**
5. Button **"Neues Release"** klicken
6. Im Dialog:
   - **Datei**: Die `Output\ACENCIA-ATLAS-Setup-X.Y.Z.exe` auswaehlen
   - **Version**: z.B. `0.9.9` (wird automatisch vorgeschlagen)
   - **Kanal**: `stable` (Standard) / `beta` / `internal`
   - **Release Notes**: Was ist neu? (Markdown erlaubt)
7. **Hochladen** klicken → Datei wird auf den Server uebertragen

### Schritt 5: Fertig

Ab sofort erhalten alle Nutzer mit aelterer Version beim naechsten Login
(oder spaetestens nach 30 Minuten) den Hinweis, dass ein Update verfuegbar ist.

---

## Optionale Aktionen nach dem Upload

### Version als Pflicht-Update markieren

Im Releases-Tab: Klicke "Bearbeiten" beim Release → Status auf **"Pflichtupdate"** setzen.

→ Nutzer mit aelterer Version koennen die App nicht mehr nutzen, bis sie aktualisiert haben.

### Alte Version als veraltet markieren

Status auf **"Veraltet"** setzen → Nutzer bekommen eine Warnung, koennen aber weiterarbeiten.

### Alte Version sperren

Status auf **"Zurueckgezogen"** setzen → Version wird komplett deaktiviert.

---

## Voraussetzungen (einmalig)

| Tool | Version | Installation |
|------|---------|-------------|
| Python | 3.10+ | python.org |
| PyInstaller | 6.x | `pip install pyinstaller` |
| Inno Setup 6 | 6.x | jrsoftware.org/isdl.php |

Alle drei sind auf diesem Rechner bereits installiert.

---

## Troubleshooting

**Build schlaegt fehl:**
→ `pip install -r requirements.txt` ausfuehren, dann nochmal bauen

**Installer zu gross (>200 MB):**
→ Normal fuer PySide6-Apps. Der Installer komprimiert auf ~50%.

**EXE startet nicht:**
→ Logs pruefen: `dist\ACENCIA-ATLAS\_internal\`
→ Debug-Build: `build_debug.bat` (zeigt Fehlermeldungen im Konsolenfenster)

**SHA256-Datei leer:**
→ Manuell in PowerShell: `(Get-FileHash "Output\ACENCIA-ATLAS-Setup-X.Y.Z.exe" -Algorithm SHA256).Hash`
