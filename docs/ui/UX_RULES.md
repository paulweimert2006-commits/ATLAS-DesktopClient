# UX-Regeln: ACENCIA ATLAS

**Status**: Verbindlich fuer alle Entwickler und Agenten  
**Letzte Aktualisierung**: 10.02.2026

---

## Regel 1: Keine modalen Info-Popups

### Verboten

Die folgenden Aufrufe sind fuer nicht-kritische Meldungen **verboten**:

- `QMessageBox.information(...)`
- `QMessageBox.warning(...)` (fuer nicht-kritische Meldungen)
- `QMessageBox.critical(...)` (fuer nicht-kritische Fehler)
- `QMessageBox.about(...)`
- Jeder modale Dialog mit nur "OK"-Button
- Jeder `.exec()`-Aufruf fuer reine Info-Meldungen

### Stattdessen verwenden

```python
from ui.toast import ToastManager

# In der View (self._toast_manager wird vom MainHub bereitgestellt):
self._toast_manager.show_success("Einstellungen gespeichert")
self._toast_manager.show_error("Verbindung fehlgeschlagen")
self._toast_manager.show_warning("Dokument bereits vorhanden")
self._toast_manager.show_info("3 Dateien hochgeladen")

# Mit Undo-Aktion:
self._toast_manager.show_success(
    "5 Dokumente archiviert",
    action_text=texts.TOAST_UNDO,
    action_callback=lambda: self._undo_archive(doc_ids)
)

# Mit Retry-Aktion:
self._toast_manager.show_error(
    "Upload fehlgeschlagen",
    action_text=texts.TOAST_RETRY,
    action_callback=lambda: self._retry_upload()
)
```

### Erlaubte Ausnahmen

Modale Dialoge (`QMessageBox.question`) bleiben erlaubt fuer:

1. **Sicherheitskritische Bestaetigungen** - z.B. "5 Dokumente endgueltig loeschen?"
2. **Authentifizierungs-Dialoge** - Login, Passwort-Eingabe
3. **Systemkritische Fehler** - App kann nicht starten, Datenverlust droht
4. **Eingabe-Dialoge** - Umbenennen, Werte eingeben (QInputDialog)

---

## Regel 2: Toast-Spezifikation

### Toast-Typen

| Typ | Farbe | Icon | Standard-Dauer | Verwendung |
|-----|-------|------|----------------|------------|
| success | Gruen (#059669) | Haekchen | 4 Sekunden | Aktion erfolgreich |
| error | Rot (#dc2626) | X | 8 Sekunden | Fehler aufgetreten |
| warning | Orange (#fa9939) | Warndreieck | 6 Sekunden | Hinweis/Warnung |
| info | Blau (#88a9c3) | Info | 5 Sekunden | Neutrale Information |

### Position und Verhalten

- **Position**: Oben rechts im Hauptfenster
- **Stacking**: Mehrere Toasts stapeln sich vertikal nach unten
- **Hover**: Pausiert den Auto-Dismiss-Timer
- **Schliessen**: X-Button oder automatisch nach Ablauf
- **Animation**: Fade-Out beim Schliessen
- **Breite**: 400px fest

### Action-Button (optional)

- Toasts koennen einen optionalen Action-Button haben
- Typische Aktionen: "Rueckgaengig", "Erneut versuchen", "Details"
- Action-Button schliesst den Toast nach Klick

### Undo-Pattern

Wenn eine Aktion rueckgaengig gemacht werden kann:

```python
# VOR der Aktion: State sichern
old_state = current_state.copy()

# Aktion ausfuehren
perform_action(new_state)

# Toast mit Undo zeigen
self._toast_manager.show_success(
    "Aktion ausgefuehrt",
    action_text=texts.TOAST_UNDO,
    action_callback=lambda: restore_state(old_state)
)
```

Undo ist sinnvoll bei:
- Dokumente archivieren/verschieben
- Einstellungen aendern
- Farbmarkierungen setzen
- Status-Aenderungen

Undo ist NICHT sinnvoll bei:
- Fehler-Meldungen (stattdessen "Erneut versuchen")
- Reine Info-Meldungen (kein Action-Button noetig)
- Unwiderrufliche Aktionen (Loeschen -> Bestaetigungsdialog verwenden)

---

## Regel 3: Textregeln fuer Toasts

### Kuerze

- Maximal 1-2 Zeilen
- Keine technischen Details im Toast-Text
- Keine Titel ("Fehler:", "Erfolg:") - der Toast-Typ zeigt das ueber Farbe/Icon

### Beispiele

| Schlecht (alt) | Gut (neu) |
|----------------|-----------|
| "Smart!Scan Einstellungen gespeichert." + OK-Button | Toast: "Einstellungen gespeichert" |
| "Fehler: Verbindung zum Server fehlgeschlagen." + OK-Button | Toast: "Verbindung fehlgeschlagen" [Erneut] |
| "3 Dokumente wurden erfolgreich archiviert." + OK-Button | Toast: "3 Dokumente archiviert" [Rueckgaengig] |
| "Bitte waehlen Sie mindestens ein Dokument aus." + OK-Button | Toast: "Bitte mindestens ein Dokument waehlen" |

### i18n

Alle Toast-Texte MUESSEN aus `src/i18n/de.py` kommen. Keine hardcodierten Strings.

---

## Regel 4: Validierung in Formularen

Fuer Eingabe-Validierung in Dialogen (Login, Einstellungen):

- **Inline-Fehler** unter dem betroffenen Feld anzeigen
- Roten Text + roter Border am Feld
- KEIN Toast und KEIN Popup fuer "Bitte Feld ausfuellen"
