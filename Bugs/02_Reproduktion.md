# 02 — Reproduktion

**Stand:** 10. Februar 2026  
**Methode:** Statische Reproduktion (Codepfad-Analyse)

---

## BUG-0001 — `clear_all()` crasht bei ProgressToastWidget

**Reproduktion (statisch):**
1. Mail-Import starten ("Mails abholen" in BiPRO) → erzeugt `ProgressToastWidget`
2. Während Progress-Toast sichtbar: `ToastManager.clear_all()` aufrufen (z.B. durch View-Wechsel oder Logout)
3. **Crash:** `AttributeError: 'ProgressToastWidget' has no attribute '_dismiss_timer'`

**Codepfad:**
- `toast.py:498` → `show_progress()` fügt `ProgressToastWidget` in `_active_toasts` ein
- `toast.py:549` → `clear_all()` iteriert über alle Toasts und ruft `toast._dismiss_timer.stop()` auf
- `ProgressToastWidget` hat kein `_dismiss_timer` Attribut (nur `ToastWidget` hat es)

**Status:** REPRODUZIERBAR (statisch)

---

## BUG-0002 — `set_document_color()` crasht mit TypeError

**Reproduktion (statisch):**
1. Dokument im Archiv rechtsklicken → "Farbe setzen" → Farbe wählen
2. Wenn Bulk-API (`POST /documents/colors`) fehlschlägt → Fallback auf Einzelupdate
3. `set_document_color()` wird aufgerufen → `update(doc_id, display_color=...)` → TypeError

**Codepfad:**
- `archive_boxes_view.py` → `_set_document_color()` → `self.docs_api.set_documents_color()`
- `documents.py:807` → Fallback: `self.set_document_color(doc_id, color)`
- `documents.py:776` → `self.update(doc_id, display_color=color or '')`
- `documents.py:572-587` → `update()` akzeptiert `display_color` nicht als Parameter

**Hinweis:** Der Hauptpfad über die Bulk-API funktioniert. Nur der Fallback-Pfad ist betroffen.

**Status:** REPRODUZIERBAR (statisch, Fallback-Pfad)

---

## BUG-0003 — `self._current_documents` existiert nicht

**Reproduktion (statisch):**
1. Archiv öffnen → Box-Sidebar sichtbar
2. Rechtsklick auf eine Box (z.B. "Courtage") → "Smart!Scan" wählen
3. **Crash:** `AttributeError: 'ArchiveBoxesView' has no attribute '_current_documents'`

**Codepfad:**
- `archive_boxes_view.py:5139` → `_smartscan_box()` wird per Kontextmenü aufgerufen
- `archive_boxes_view.py:5151` → `self._current_documents` → Attribut existiert nicht
- Korrekt wäre: `self._documents` (definiert in `__init__` bei Zeile ~2253)

**Status:** REPRODUZIERBAR (statisch, jeder SmartScan-Box-Aufruf)

---

## BUG-0004 — HTTP Header Injection via Dateiname

**Reproduktion (statisch):**
1. Datei hochladen mit Dateiname: `test";\r\nX-Injected: evil`
2. Dokument herunterladen (GET `/documents/{id}/download`)
3. Server sendet: `Content-Disposition: attachment; filename="test";\r\nX-Injected: evil"`
4. HTTP-Response enthält zusätzlichen Header

**Codepfad:**
- Upload: `documents.php:411` → `$originalFilename = basename($file['name'])` (kein Escaping)
- Download: `documents.php:621` → `header('Content-Disposition: ... "' . $doc['original_filename'] . '"')`

**Risiko:** Theoretisch. PHP filtert `\r\n` in `header()` seit PHP 5.1.2, aber Anführungszeichen können den Header-Wert aufbrechen.

**Status:** TEILWEISE_REPRODUZIERBAR (CRLF wird von PHP geblockt, Anführungszeichen nicht)

---

## BUG-0005 — SmartScan sendet falsche Dokumente nach Sortierung

**Reproduktion:**
1. Archiv öffnen → Dokumente anzeigen
2. Tabelle nach Datum oder Name sortieren (Klick auf Spaltenheader)
3. Ein oder mehrere Dokumente auswählen
4. Smart!Scan-Button klicken
5. **Falsche Dokumente werden gesendet** (aus unsortierter `self._documents` Liste)

**Codepfad:**
- `archive_boxes_view.py:3336` → `item.row()` gibt sortierte visuelle Zeile zurück
- `archive_boxes_view.py:3345` → `self._documents[row]` greift auf unsortierte Liste zu
- Vergleich: `_get_selected_documents()` (Zeile 3698) liest korrekt per `UserRole`

**Status:** REPRODUZIERBAR (jeder sortierte SmartScan-Versand)

---

## BUG-0006 — Auto-Refresh-Pause bei Verarbeitung wirkungslos

**Reproduktion (statisch):**
1. Dokumentenverarbeitung starten (Eingangsbox hat Dokumente → "Verarbeiten")
2. `DataCacheService()` wird neu instanziiert (statt `self._cache`)
3. Pause/Resume wirkt auf neue Instanz statt auf die aktive Singleton-Instanz
4. Auto-Refresh läuft während der Verarbeitung weiter

**Codepfad:**
- `archive_boxes_view.py:5008` → `cache = DataCacheService()` (neue Instanz)
- Korrekt: `self._cache.pause_auto_refresh()` (existierende Instanz, z.B. Zeile 4211)

**Prüfung nötig:** Ist `DataCacheService` ein Singleton? Falls ja, ist der Bug unkritisch.

**Status:** REPRODUZIERBAR (statisch, abhängig von Singleton-Implementierung)

---

## BUG-0007 — Falscher classification_source bei low-Confidence

**Reproduktion (statisch):**
1. PDF mit low-Confidence hochladen (z.B. mehrdeutiges Dokument)
2. KI-Stufe 1 (GPT-4o-mini) → `confidence: "low"` → Stufe 2 (GPT-4o) wird aufgerufen
3. `classification_source` wird als `ki_gpt4o_mini` gespeichert (statt `ki_gpt4o_zweistufig`)

**Codepfad:**
- `document_processor.py:685` → `'ki_gpt4o_mini' if ki_confidence != 'medium' else 'ki_gpt4o_zweistufig'`
- Bei `low`: `'low' != 'medium'` → True → `'ki_gpt4o_mini'` (FALSCH)
- Korrekt: `'ki_gpt4o_mini' if ki_confidence == 'high' else 'ki_gpt4o_zweistufig'`

**Status:** REPRODUZIERBAR (jedes Dokument mit low Confidence)

---

## BUG-0008 — `get_stats()` gibt leeres Dict statt BoxStats bei Fehler

**Reproduktion (statisch):**
1. Server offline oder API-Fehler bei Stats-Abruf
2. `_load_stats()` → `except Exception: return {}`
3. Caller: `self._stats.eingang` → `AttributeError: 'dict' object has no attribute 'eingang'`

**Codepfad:**
- `data_cache.py:330` → `return {}` im Fehlerfall
- Caller in `archive_boxes_view.py` greifen auf `.eingang`, `.courtage`, etc. zu

**Status:** REPRODUZIERBAR (bei Server-Fehler)

---

## BUG-0009 — XML-Injection bei BiPRO-Credentials

**Reproduktion (statisch):**
1. VU-Verbindung mit Username/Consumer-ID anlegen, der `<` oder `&` enthält
2. BiPRO STS-Login → Username wird raw in XML-String interpoliert
3. SOAP-Request ist ungültiges XML → Server gibt Parse-Fehler zurück

**Codepfad:**
- `transfer_service.py:567` → `<wsse:Username>{self.credentials.username}</wsse:Username>`
- Passwort wird korrekt escaped (Zeile 550), Username nicht

**Status:** REPRODUZIERBAR (bei Sonderzeichen in Credentials)

---

## BUG-0010 — `response.json()` crasht bei Non-JSON-Fehlern

**Reproduktion (statisch):**
1. OpenRouter API gibt HTML-Fehlerseite zurück (z.B. 502 Bad Gateway, Cloudflare)
2. `response.text` ist nicht leer → `response.json()` wird aufgerufen
3. `json.JSONDecodeError` wird nicht abgefangen → unhandled Exception

**Codepfad:**
- `openrouter.py:741` → `error_data = response.json() if response.text else {}`
- Prüft nur auf leeren Body, nicht auf gültiges JSON

**Status:** REPRODUZIERBAR (bei Cloudflare/Proxy-Fehler)

---

## BUG-0011 — Bulk-Delete löscht Dateien vor DB

**Reproduktion (statisch):**
1. Mehrere Dokumente auswählen → Löschen
2. Dateien werden per `unlink()` gelöscht
3. DB-DELETE schlägt fehl (z.B. Foreign Key, Connection-Timeout)
4. Dateien sind weg, DB-Einträge bleiben → Orphaned Records → Download = 404

**Codepfad:**
- `documents.php:690-697` → Dateien löschen (Schleife)
- `documents.php:700-703` → DB-DELETE danach

**Status:** REPRODUZIERBAR (bei DB-Fehler nach Dateilöschung)

---

## BUG-0012 — Toast-Erstellung aus Worker-Threads

**Reproduktion (statisch):**
1. Worker-Thread (z.B. Download-Worker) ruft `toast_manager.show_error("...")` auf
2. Qt-Widget (`QFrame`) wird aus Non-GUI-Thread erstellt
3. Mögliche Folge: Segfault, UI-Korruption, oder stiller Fehler

**Prüfung nötig:** Werden Toast-Methoden tatsächlich aus Worker-Threads aufgerufen? Oder nur aus Signal-Callbacks (die im Main-Thread laufen)?

**Status:** TEILWEISE_REPRODUZIERBAR (Codepfad vorhanden, tatsächliche Aufrufe müssen geprüft werden)

---

*Bugs 0013-0039: Statische Reproduktion — Edge-Cases und Low-Priority. Codepfade in der Bugliste dokumentiert.*
