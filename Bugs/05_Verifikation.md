# 05 — Verifikation

**Stand:** 10. Februar 2026  
**Methode:** Statische Verifikation (Code-Review nach Fix) + Linter

---

## BUG-0001 — `clear_all()` crasht bei ProgressToastWidget

- **Testschritte:** `hasattr(toast, '_dismiss_timer')` Check in `clear_all()` verifiziert
- **Ergebnis vorher:** `AttributeError` wenn `ProgressToastWidget` in `_active_toasts`
- **Ergebnis nachher:** `hasattr` gibt `False` zurück → `_dismiss_timer.stop()` wird übersprungen, `setVisible(False)` und `deleteLater()` werden für alle Toast-Typen korrekt aufgerufen
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0002 — `set_document_color()` crasht mit TypeError

- **Testschritte:** `display_color` Parameter in `update()` Signatur + Payload-Erstellung verifiziert
- **Ergebnis vorher:** `TypeError: update() got an unexpected keyword argument 'display_color'`
- **Ergebnis nachher:** `display_color` wird als optionaler Parameter akzeptiert und in die Payload aufgenommen. Bulk-API bleibt Hauptpfad, Fallback funktioniert jetzt
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0003 — `self._current_documents` existiert nicht

- **Testschritte:** Variablenname auf `self._documents` korrigiert. Grep bestätigt: Attribut existiert und wird korrekt befüllt
- **Ergebnis vorher:** `AttributeError: 'ArchiveBoxesView' has no attribute '_current_documents'`
- **Ergebnis nachher:** Korrekte Liste wird verwendet. Filterung nach `box_type` und `is_archived` funktioniert
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0004 — HTTP Header Injection via Dateiname

- **Testschritte:** `str_replace()` entfernt Anführungszeichen, CR, LF und NULL-Bytes aus Dateinamen
- **Ergebnis vorher:** Unescapter Dateiname direkt im Header
- **Ergebnis nachher:** Gefährliche Zeichen werden entfernt. Normaler Download-Dateiname bleibt unverändert
- **Linter:** N/A (PHP)
- **Status:** FIXED ✅

---

## BUG-0005 — SmartScan sendet falsche Dokumente nach Sortierung

- **Testschritte:** `_on_smartscan_btn_clicked()` nutzt jetzt `self._get_selected_documents()` (identische Methode wie Download, Löschen, etc.)
- **Ergebnis vorher:** Sortierte Zeilen-Indices → falsche Dokumente aus unsortierter Liste
- **Ergebnis nachher:** `UserRole`-Data aus Table-Items → immer korrekte Dokumente unabhängig von Sortierung
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0006 — Auto-Refresh-Pause bei Verarbeitung wirkungslos

- **Testschritte:** Alle 3 Stellen korrigiert: `_start_processing`, `_on_processing_finished`, `_on_processing_error`. Grep bestätigt: 0 `DataCacheService()`-Aufrufe in der Datei verbleiben. Alle 15 `self._cache.pause/resume_auto_refresh()`-Aufrufe konsistent
- **Ergebnis vorher:** Neue `DataCacheService()`-Instanz → Pause/Resume auf falsches Objekt
- **Ergebnis nachher:** `self._cache` (Singleton-Referenz) → Pause/Resume wirkt auf den aktiven Timer
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0007 — Falscher classification_source bei low-Confidence

- **Testschritte:** Bedingung an beiden Stellen (Zeile 685 und 754) von `!= 'medium'` auf `== 'high'` geändert
- **Ergebnis vorher:** `low` → `ki_gpt4o_mini` (falsch, da Stufe 2 verwendet wurde)
- **Ergebnis nachher:** `high` → `ki_gpt4o_mini`, `medium` oder `low` → `ki_gpt4o_zweistufig` (korrekt)
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0008 — `get_stats()` gibt leeres Dict statt BoxStats bei Fehler

- **Testschritte:** Fehlerfall gibt jetzt `BoxStats()` zurück (alle Felder = 0)
- **Ergebnis vorher:** `{}` → `AttributeError` bei `.eingang`, `.courtage`, etc.
- **Ergebnis nachher:** `BoxStats(eingang=0, ...)` → Caller erhalten gültiges Objekt mit Nullwerten
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0009 — XML-Injection bei BiPRO-Credentials

- **Testschritte:** `_escape_xml()` wird jetzt auf Username (2x), Consumer-ID (3x), Token (1x), Shipment-ID (2x) angewendet
- **Ergebnis vorher:** Raw-Interpolation → XML-Fehler bei Sonderzeichen
- **Ergebnis nachher:** `<`, `>`, `&`, `"`, `'` werden korrekt escaped
- **Zusatz:** Doppelter `@dataclass`-Decorator entfernt (BUG-0028)
- **Linter:** 1 vorbestehender Warning (`jks` Import) — kein neuer Fehler
- **Status:** FIXED ✅

---

## BUG-0010 — `response.json()` crasht bei Non-JSON-Fehlern

- **Testschritte:** `try/except (ValueError, Exception)` um `response.json()` hinzugefügt
- **Ergebnis vorher:** `json.JSONDecodeError` bei HTML/Text-Fehlerantwort
- **Ergebnis nachher:** Fallback auf leeres Dict, generische Fehlermeldung `HTTP {status_code}`
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0011 — Bulk-Delete löscht Dateien vor DB

- **Testschritte:** Reihenfolge umgedreht: DB-DELETE zuerst, Dateien nur bei `$affected > 0`
- **Ergebnis vorher:** Dateien gelöscht + DB-Fehler → Orphaned Records
- **Ergebnis nachher:** DB-DELETE zuerst. Bei DB-Fehler: Dateien bleiben, JSON-Fehler wird zurückgegeben. Bei Erfolg: Dateien werden gelöscht (mit `@` um unkritische Fehler zu unterdrücken)
- **Linter:** N/A (PHP)
- **Status:** FIXED ✅

---

## BUG-0026 — ZipFile-Handle-Leak bei verschlüsselter ZIP-Erkennung

- **Testschritte:** `zf.close()` in beiden `except`-Blöcken hinzugefügt
- **Ergebnis vorher:** Offenes File-Handle bei RuntimeError (Encryption) oder anderem Exception
- **Ergebnis nachher:** Handle wird geschlossen vor Fallback auf Passwort-Versuch
- **Linter:** Keine neuen Fehler
- **Status:** FIXED ✅

---

## BUG-0028 — Double `@dataclass` Decorator

- **Testschritte:** Doppelten Decorator entfernt
- **Ergebnis vorher:** `@dataclass @dataclass class ShipmentInfo`
- **Ergebnis nachher:** `@dataclass class ShipmentInfo`
- **Status:** FIXED ✅

---

## BUG-0039 — `DOWNLOADABLE_BOXES` mit falscher Variable

- **Testschritte:** Code nochmals geprüft — Zeile 2060 nutzt bereits korrekt `DOWNLOADABLE_BOXES_ADMIN`
- **Status:** UNVERIFIZIERT — Bug existiert nicht, Sub-Agent hat sich geirrt ❌

---

## Zusammenfassung

| Status | Anzahl |
|--------|--------|
| FIXED ✅ | 13 (BUG-0001 bis BUG-0011, BUG-0026, BUG-0028) |
| UNVERIFIZIERT ❌ | 1 (BUG-0039) |
| DESIGN (nicht implementiert) | 1 (BUG-0012, Thread-Sicherheit Toast) |
| NICHT GEFIXT (MEDIUM/LOW) | 24 (BUG-0013 bis BUG-0025, BUG-0027, BUG-0029-0038) |
