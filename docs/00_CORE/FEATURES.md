# ACENCIA ATLAS - Features und Nutzererlebnis

**Letzte Aktualisierung:** 24. Februar 2026

---

## App-Start und Navigation

### Login
- Benutzername + Passwort → JWT-Token (30 Tage gueltig)
- Auto-Login: Token wird lokal gespeichert, bei Neustart automatisch geprueft
- Single-Session: Pro Nutzer nur eine Sitzung, alte wird bei Neuanmeldung beendet
- Bei ungueltigem Token: Lokale Caches werden automatisch geloescht

### Hauptnavigation (Linke Sidebar)
Die App hat eine linke Sidebar mit 5 Navigationspunkten:

1. **Zentrale** (Mitteilungszentrale) - Index 0
2. **BiPRO** (Datenabruf) - Index 1
3. **Archiv** (Dokumentenarchiv) - Index 2
4. **GDV** (Editor) - Index 3
5. **GF** (Provisionsmanagement) - nur mit `provision_access` sichtbar

Zusaetzlich: **Admin** (Zahnrad-Icon oben rechts) - nur fuer Administratoren

Beim Wechsel in Admin, Chat oder GF-Bereich verschwindet die Sidebar und der Bereich nimmt den vollen Bildschirm ein.

---

## 1. Mitteilungszentrale (Zentrale)

### Was der Nutzer sieht:
- **Grosse Kachel**: System- und Admin-Mitteilungen mit Severity-Farben (Info, Warnung, Fehler)
- **Kleine Kachel**: Aktuelle Version + Release Notes
- **Button**: "Nachrichten" → oeffnet Vollbild-Chat

### 1:1 Chat
- Private Nachrichten zwischen Nutzern
- Lesebestaetigung (Doppel-Haekchen)
- Conversation-Liste links, Nachrichten rechts
- Badge auf "Zentrale"-Button zeigt ungelesene Nachrichten

### Polling
- Alle 30 Sekunden: Pruefung auf neue Nachrichten/Mitteilungen
- Toast-Benachrichtigung bei neuer Chat-Nachricht

---

## 2. BiPRO Datenabruf

### Was der Nutzer sieht:
- **VU-Dropdown**: Versicherungsunternehmen auswaehlen (z.B. Degenia, VEMA)
- **"Alle VUs abholen" Button**: Alle aktiven VUs nacheinander abrufen
- **"Mails abholen" Button**: IMAP-E-Mails abrufen und Anhaenge importieren
- **Lieferungstabelle**: Liste der verfuegbaren Lieferungen mit Kategorie, Datum, Groesse
- **Download**: Einzeln oder alle Lieferungen herunterladen

### Ablauf (BiPRO-Abruf):
1. VU auswaehlen → Credentials werden vom Server geholt
2. STS-Token (Security Token) bei der VU anfordern (BiPRO 410)
3. Lieferungen auflisten (BiPRO 430 listShipments)
4. Dokumente herunterladen (getShipment mit MTOM/XOP)
5. Automatisch ins Dokumentenarchiv hochladen
6. Empfang quittieren (acknowledgeShipment)

### Parallelisierung:
- Max. 10 Worker-Threads fuer gleichzeitige Downloads
- Automatische Anpassung bei wenigen Lieferungen
- AdaptiveRateLimiter bei HTTP 429/503

### Mail-Import:
- IMAP-Postfach abrufen → Anhaenge extrahieren
- Anhaenge verarbeiten (ZIP entpacken, MSG-Anhaenge, PDF entsperren)
- In Eingangsbox hochladen → KI-Verarbeitung

---

## 3. Dokumentenarchiv

### Box-System (7 Boxen + Virtuell):
| Box | Farbe | Beschreibung |
|-----|-------|--------------|
| **ATLAS Index** | - | Virtuelle Such-Box (Volltextsuche ueber alle Dokumente) |
| **Eingang** | - | Neue, unverarbeitete Dokumente |
| **Verarbeitung** | - | Gerade in KI-Verarbeitung (eingeklappt) |
| **GDV** | - | GDV-Dateien (.gdv, .txt) |
| **Courtage** | - | Provisionsabrechnungen (KI-klassifiziert) |
| **Sach** | - | Sachversicherungs-Dokumente (KI) |
| **Leben** | - | Lebensversicherungs-Dokumente (KI) |
| **Kranken** | - | Krankenversicherungs-Dokumente (KI) |
| **Sonstige** | - | Nicht zugeordnete Dokumente |
| **Roh** | - | XML-Rohdateien (BiPRO-Antworten) |

### Dokumenten-Verarbeitung (automatisch):
1. Dokument landet in **Eingang** (via BiPRO, Upload, Drag&Drop, E-Mail, Scan)
2. **Vorsortierung**: XML → Roh, GDV-Endung → GDV, Courtage-Code → Courtage
3. **KI-Klassifikation** (fuer PDFs):
   - Stufe 1: GPT-4o-mini (2 Seiten, schnell) → Confidence high/medium/low
   - Stufe 2: GPT-4o-mini (5 Seiten, nur bei low Confidence)
   - Ergebnis: Box-Zuweisung + automatische Benennung (z.B. "Allianz_Courtage_2026-02-04.pdf")
4. **Leere-Seiten-Erkennung**: 4-Stufen-Algorithmus (Text → Vektoren → Bilder → Pixel)
5. **Duplikat-Erkennung**: SHA256-Hash (Datei) + extrahierter-Text-Hash (Inhalt)
6. **Dokumenten-Regeln** (Admin-konfigurierbar): Automatische Aktionen bei Duplikaten/leeren Seiten

### Upload-Wege:
- **Drag & Drop**: Dateien/Ordner auf das App-Fenster ziehen (funktioniert ueberall)
- **Upload-Button**: Datei-Dialog im Archiv
- **BiPRO**: Automatisch nach Download
- **IMAP Mail-Import**: Anhaenge aus E-Mails
- **Power Automate Scan**: REST-API fuer SharePoint-Flows
- **Outlook Direct-Drop**: E-Mails direkt aus Outlook ziehen (COM-Automation)

### Automatische Verarbeitung bei Upload:
- **ZIP** → Entpacken (auch AES-256, rekursiv bis 3 Ebenen)
- **MSG** → Anhaenge extrahieren, MSG ins Roh-Archiv
- **Passwortgeschuetzte PDFs** → Automatisch entsperren (Passwoerter aus DB)
- **Bilddateien** (PNG, JPG, TIFF, etc.) → In PDF konvertieren

### Vorschau und Bearbeitung:
- **PDF-Vorschau**: Integrierter Viewer mit Thumbnails
- **PDF-Bearbeitung**: Seiten drehen (CW/CCW), loeschen, speichern (Multi-Selection)
- **CSV/Excel-Vorschau**: Tabellen direkt in der App anzeigen
- **Farbmarkierung**: 8 Farben fuer visuelle Organisation (persistent)

### Tastenkuerzel:
| Taste | Aktion |
|-------|--------|
| F2 | Umbenennen |
| Entf | Loeschen |
| Strg+A | Alle auswaehlen |
| Strg+D | Download |
| Strg+F | Suchen |
| Strg+U | Upload |
| Enter | Vorschau |
| Strg+Shift+A | Archivieren |
| F5 | Aktualisieren |

### ATLAS Index (Volltextsuche):
- Suche ueber Dateiname UND extrahierten Textinhalt
- Live-Suche ab 3 Zeichen (abschaltbar)
- Teilstring-Suche (LIKE) oder Vollwort-Suche (FULLTEXT)
- Snippet-Darstellung (Google-Stil) mit hervorgehobenen Treffern
- Doppelklick → Vorschau, Rechtsklick → "In Box anzeigen"

### Smart!Scan (E-Mail-Versand):
- Dokumente per E-Mail an SmartScan-System senden
- Einzel- oder Sammelversand
- Post-Send: Automatisch archivieren und/oder umfaerben
- Revisionssichere Historie

### Dokument-Historie:
- Seitenpanel rechts zeigt Aenderungshistorie
- Farbcodierte Eintraege (Blau=Verschiebung, Gruen=Download, Rot=Loeschung, etc.)
- Cache mit 60s TTL, Debounce 300ms

### Duplikat-Erkennung:
- **Datei-Duplikat**: Gleiche SHA256-Pruefsumme (⚠ amber Icon)
- **Inhaltsduplikat**: Gleicher extrahierter Text (≡ indigo Icon)
- Rich-Tooltip mit Details zum Original
- Klick auf Icon → zum Gegenstueck springen
- Vergleichsansicht: Side-by-Side PDF-Vorschau

---

## 4. GDV-Editor

### Was der Nutzer sieht:
- **Datei oeffnen**: *.gdv, *.txt, *.dat, *.vwb Dateien laden
- **Satz-Tabelle**: Alle Records der GDV-Datei auflisten
- **3 Ansichten**:
  - **Partner-Ansicht**: Firmen und Personen mit Vertraegen
  - **Benutzer-Ansicht**: Nur wichtige, editierbare Felder
  - **Experten-Ansicht**: Alle Felder (fuer Spezialisten)
- **Bearbeiten**: Felder aendern mit Validierung
- **Speichern**: Zurueck ins GDV Fixed-Width-Format

### GDV-Format:
- Branchenstandard fuer Versicherungsdaten-Austausch
- Fixed-Width-Format (256 Bytes pro Zeile)
- Satzarten: 0001 (Vorsatz), 0100 (Partner), 0200 (Vertrag), 0210/0220/0230 (Details), 9999 (Nachsatz)
- Encoding: CP1252 (deutsche Umlaute)

---

## 5. Provisionsmanagement (GF-Bereich)

### Zugang:
- Nur mit `provision_access` Berechtigung sichtbar
- `provision_manage` fuer Gefahrenzone und Rechtevergabe
- Nicht automatisch fuer Admins – muss explizit zugewiesen werden

### 8 Panels (Vollbild mit eigener Sidebar):

1. **Uebersicht (Dashboard)**
   - 4 KPI-Karten: Gesamtprovision, Zuordnungsquote (DonutChart), Klaerfaelle, Auszahlungen
   - Berater-Ranking-Tabelle mit Rollen-Badges

2. **Abrechnungslaeufe**
   - VU-Provisionslisten importieren (Allianz, SwissLife, VB)
   - Xempus-Beratungen importieren
   - Import-Batch-Historie mit Validierungsstatus

3. **Provisionspositionen**
   - Master-Detail-Tabelle mit FilterChips und PillBadges
   - Detail-Seitenpanel (Originaldaten, Matching, Verteilung, Auditlog)
   - Rechtsklick: Vertrag zuordnen, Berater-Mapping erstellen

4. **Xempus Insight** (NEU v3.3.0)
   - 4 Tabs: Arbeitgeber, Statistiken, Import, Status-Mapping
   - 4-Phasen-Import (RAW → Parse → Snapshot → Finalize)
   - Snapshot-Diff-Vergleich zwischen Importen

5. **Zuordnung & Klaerfaelle**
   - Klaerfall-Typen: Kein Vertrag, Unbekannter Vermittler, Kein Modell, Kein Split
   - MatchContractDialog: Multi-Level-Matching (Score 100/90/70/40)
   - Reverse-Matching: Xempus-Vertraege ohne VU-Provision

6. **Verteilschluessel & Rollen**
   - Provisionsmodelle als Karten mit Beispielrechnung
   - Mitarbeiter-Tabelle mit Rollen (Consulter, Teamleiter, Backoffice)

7. **Auszahlungen & Reports**
   - Monatsabrechnungen mit StatementCards
   - Status-Workflow: berechnet → geprueft → freigegeben → ausgezahlt
   - CSV/Excel-Export

8. **Einstellungen**
   - Gefahrenzone: Daten-Reset mit 3s-Countdown-Bestaetigung

---

## 6. Admin-Bereich

### Vollbild-Ansicht mit vertikaler Sidebar (15 Panels in 5 Sektionen):

**VERWALTUNG:**
- Nutzerverwaltung (Erstellen, Bearbeiten, Sperren, Rechte)
- Sessions (Einsehen, Beenden)
- Passwoerter (PDF/ZIP-Passwoerter zentral verwalten)

**MONITORING:**
- Aktivitaetslog (Alle API-Aktionen)
- KI-Kosten (Statistiken, Einzelne Requests, CSV-Export)
- Releases (Upload, Status, Channel, Downloads)

**VERARBEITUNG:**
- KI-Klassifikation (Pipeline, Prompt-Editor, Modell-Auswahl)
- KI-Provider (OpenRouter/OpenAI, API-Keys, Verbindungstest)
- Modell-Preise (Input/Output pro 1M Tokens)
- Dokumenten-Regeln (Duplikate, leere Seiten)

**E-MAIL:**
- E-Mail-Konten (SMTP/IMAP, Verschluesselung)
- SmartScan-Einstellungen (Zieladresse, Modi, Post-Send)
- SmartScan-Historie (Jobs, Items, E-Mails)
- E-Mail-Posteingang (IMAP-Import)

**KOMMUNIKATION:**
- Mitteilungen (System-/Admin-Meldungen erstellen)

---

## 7. Auto-Update

- **Check bei Login**: Synchron nach erfolgreicher Anmeldung
- **Periodisch**: Alle 30 Minuten im Hintergrund
- **3 Modi**: Optional (Spaeter moeglich), Pflicht (App blockiert), Veraltet (Warnung)
- **Installation**: Inno Setup Silent Install
- **Sicherheit**: SHA256-Hash-Verifikation vor Installation

---

## 8. Globale Features

### Drag & Drop
- Dateien/Ordner aus Explorer auf App-Fenster ziehen → Eingangsbox
- E-Mails direkt aus Outlook ziehen (COM-Automation)
- Funktioniert in jedem Bereich (BiPRO, Archiv, GDV, Admin)

### Toast-Benachrichtigungen
- Nicht-blockierende Benachrichtigungen oben rechts
- 4 Typen: Erfolg (gruen), Fehler (rot), Warnung (orange), Info (blau)
- Stacking, Hover-Pause, Action-Buttons (z.B. "Rueckgaengig")
- Progress-Toast fuer Langzeit-Operationen (mit Fortschrittsbalken)

### App-Schliess-Schutz
- Blockiert Schliessen bei laufender KI-Verarbeitung, Kosten-Check oder SmartScan
- Toast-Warnung mit Auflistung der blockierenden Operationen

### Notification-Polling
- Alle 30 Sekunden: Ungelesene Chats + System-Meldungen pruefen
- Roter Badge auf "Zentrale"-Button
- Toast bei neuer Chat-Nachricht
