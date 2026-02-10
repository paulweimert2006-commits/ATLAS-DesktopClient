# 03 — Root Cause Analyse

**Stand:** 10. Februar 2026

---

## BUG-0001 — `clear_all()` crasht bei ProgressToastWidget

- **Root Cause:** `ProgressToastWidget` und `ToastWidget` erben beide von `QFrame`, aber NICHT voneinander. `_active_toasts` enthält gemischte Typen, `clear_all()` setzt `ToastWidget`-API voraus (`_dismiss_timer`).
- **Betroffene Dateien:** `src/ui/toast.py:464, 498, 546-552`
- **Warum:** `ProgressToastWidget` wurde nachträglich als eigener Typ hinzugefügt (v1.0.9), ohne `clear_all()` anzupassen.
- **Warum nicht früher erkannt:** `clear_all()` wird selten aufgerufen und nur bei gleichzeitig sichtbarem ProgressToast.

---

## BUG-0002 — `set_document_color()` crasht mit TypeError

- **Root Cause:** `update()` hat eine explizite Parameterliste (13 benannte Parameter), aber `display_color` fehlt. `set_document_color()` übergibt `display_color=...` als Keyword-Argument → TypeError.
- **Betroffene Dateien:** `src/api/documents.py:572-587, 776`
- **Warum:** `display_color` wurde zum Backend hinzugefügt (PHP `allowedFields`), aber nicht zur `update()`-Methode im Python-Client.
- **Warum nicht früher erkannt:** Bulk-API (`/documents/colors`) funktioniert — Fallback wird nur bei Bulk-API-Fehler getriggert.

---

## BUG-0003 — `self._current_documents` existiert nicht

- **Root Cause:** Tippfehler/Refactoring-Artefakt. Die Instanzvariable heißt `self._documents`, nicht `self._current_documents`.
- **Betroffene Dateien:** `src/ui/archive_boxes_view.py:5151`
- **Warum:** Wahrscheinlich bei einem Refactoring von einem älteren Variablennamen übriggeblieben.
- **Warum nicht früher erkannt:** SmartScan auf ganze Boxen per Rechtsklick ist ein seltener Pfad.

---

## BUG-0004 — HTTP Header Injection via Dateiname

- **Root Cause:** `$doc['original_filename']` wird unbereinigt in den `Content-Disposition`-Header eingefügt. Es fehlt sowohl ein Escaping der Anführungszeichen als auch eine RFC-konforme Kodierung.
- **Betroffene Dateien:** `BiPro-Webspace Spiegelung Live/api/documents.php:411, 621`
- **Warum:** Upload speichert `basename($file['name'])` ohne weitere Bereinigung.
- **Warum nicht früher erkannt:** Typische Dateinamen enthalten keine Anführungszeichen.

---

## BUG-0005 — SmartScan sendet falsche Dokumente nach Sortierung

- **Root Cause:** `_on_smartscan_btn_clicked()` nutzt `item.row()` als Index in `self._documents`. Nach Sortierung stimmen visuelle Zeilen nicht mehr mit der internen Listenposition überein. Andere Methoden (z.B. `_get_selected_documents()`) lesen korrekt per `UserRole`-Data.
- **Betroffene Dateien:** `src/ui/archive_boxes_view.py:3336-3346`
- **Warum:** Copy-Paste-Fehler — die korrekte Pattern existiert bereits in der gleichen Datei (Zeile 3698-3713).
- **Warum nicht früher erkannt:** Nur sichtbar wenn Tabelle sortiert UND SmartScan-Button benutzt wird.

---

## BUG-0006 — Auto-Refresh-Pause bei Verarbeitung wirkungslos

- **Root Cause:** `DataCacheService()` wird direkt instanziiert statt über `self._cache` (die Singleton-Instanz). Falls kein Singleton-Pattern implementiert ist, operiert die neue Instanz auf eigenem Timer.
- **Betroffene Dateien:** `src/ui/archive_boxes_view.py:5006-5012, 5039-5045, 5122-5129`
- **Warum:** Inkonsistenz — an 3 Stellen wird `DataCacheService()` instanziiert, an 10+ Stellen wird korrekt `self._cache` verwendet.
- **Warum nicht früher erkannt:** Auto-Refresh alle 90s — Race-Condition tritt nur auf wenn Refresh genau während Verarbeitung triggert.

---

## BUG-0007 — Falscher classification_source bei low-Confidence

- **Root Cause:** Logischer Fehler in der Bedingung: `ki_confidence != 'medium'` schließt sowohl `high` als auch `low` ein. Korrekt wäre `ki_confidence == 'high'`.
- **Betroffene Dateien:** `src/services/document_processor.py:685, 754`
- **Warum:** Falsche Annahme, dass es nur zwei Werte gibt (`high` und `medium`). `low` wurde vergessen.
- **Warum nicht früher erkannt:** Audit-Trail wird selten geprüft, funktional kein Unterschied.

---

## BUG-0008 — `get_stats()` gibt leeres Dict statt BoxStats bei Fehler

- **Root Cause:** Inkonsistenter Fehler-Rückgabewert. Erfolgsfall: `BoxStats`-Dataclass, Fehlerfall: `{}` (leeres Dict). Type-Annotation sagt `Dict[str, int]`, stimmt für keinen Fall.
- **Betroffene Dateien:** `src/services/data_cache.py:229, 313-330`
- **Warum:** Fehlerfall wurde als "einfach leeres Dict zurückgeben" implementiert, ohne die Caller zu prüfen.
- **Warum nicht früher erkannt:** Server-Fehler sind selten im Normalbetrieb.

---

## BUG-0009 — XML-Injection bei BiPRO-Credentials

- **Root Cause:** Inkonsistente Anwendung von `_escape_xml()`. Passwort wird escaped (Zeile 550), Username, Consumer-ID, Shipment-ID und Token werden raw interpoliert.
- **Betroffene Dateien:** `src/bipro/transfer_service.py:567, 589, 713, 754, 850, 863, 1249, 1256`
- **Warum:** `_escape_xml()` existiert, wurde aber nicht auf alle interpolierten Werte angewendet.
- **Warum nicht früher erkannt:** Credentials enthalten typischerweise keine XML-Sonderzeichen.

---

## BUG-0010 — `response.json()` crasht bei Non-JSON-Fehlern

- **Root Cause:** Prüfung `if response.text` testet nur auf leeren Body, nicht auf Content-Type oder JSON-Validität.
- **Betroffene Dateien:** `src/api/openrouter.py:741-745`
- **Warum:** Annahme, dass OpenRouter immer JSON zurückgibt. Proxy-/CDN-Fehler liefern HTML.
- **Warum nicht früher erkannt:** OpenRouter ist im Normalbetrieb stabil, CDN-Fehler selten.

---

## BUG-0011 — Bulk-Delete löscht Dateien vor DB

- **Root Cause:** Falsche Reihenfolge: Dateien zuerst, DB danach. Kein Transaction-Wrapping.
- **Betroffene Dateien:** `BiPro-Webspace Spiegelung Live/api/documents.php:690-704`
- **Warum:** Vermutlich die "sicherere" Annahme: Dateien sofort weg, DB-Cleanup danach. Aber: Bei DB-Fehler ist der Zustand inkonsistent.
- **Warum nicht früher erkannt:** DB-Fehler bei DELETE sind sehr selten.

---

## BUG-0012 — Toast-Erstellung aus Worker-Threads

- **Root Cause:** `ToastManager._show()` erstellt Qt-Widgets direkt. Qt verbietet Widget-Erstellung aus Non-GUI-Threads. Kein Thread-Check oder Signal-basierter Dispatch.
- **Betroffene Dateien:** `src/ui/toast.py:505-524`
- **Warum:** Toast-System wurde als Main-Thread-API designed, aber Worker-Threads haben Zugriff auf die Manager-Instanz.
- **Warum nicht früher erkannt:** Worker kommunizieren überwiegend über Qt-Signale (die automatisch im Main-Thread ankommen). Direktaufrufe sind selten.
