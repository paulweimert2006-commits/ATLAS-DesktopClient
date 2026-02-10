# 06 — Regressionen und Risiken

**Stand:** 10. Februar 2026

---

## Regressions-Analyse

### BUG-0001 Fix (toast.py)
- **Geändert:** `clear_all()` — `hasattr`-Check vor `_dismiss_timer`
- **Angrenzende Funktionen:** `_remove_toast()`, `_show()`, `show_progress()`
- **Regressions-Risiko:** ⬇️ MINIMAL — `hasattr` ist rein additiv, bestehende `ToastWidget`-Logik unverändert
- **Manueller Test empfohlen:** Mehrere Toasts gleichzeitig anzeigen, dann View wechseln → `clear_all()` triggern

### BUG-0002 Fix (documents.py)
- **Geändert:** `update()` — neuer optionaler Parameter `display_color`
- **Angrenzende Funktionen:** Alle Caller von `update()` (Rename, Move, Process, etc.)
- **Regressions-Risiko:** ⬇️ MINIMAL — Neuer Parameter ist optional mit Default `None`, bestehende Aufrufe unverändert
- **Manueller Test empfohlen:** Dokument-Farbmarkierung setzen (Einzeln per Rechtsklick), danach Farbe entfernen

### BUG-0003 Fix (archive_boxes_view.py)
- **Geändert:** `_smartscan_box()` — Variablenname korrigiert
- **Angrenzende Funktionen:** `_start_smartscan()`, Box-Sidebar-Kontextmenü
- **Regressions-Risiko:** ⬇️ MINIMAL — Einzeilige Korrektur, gleiche Filterlogik
- **Manueller Test empfohlen:** Rechtsklick auf Box → "Smart!Scan" → Prüfen ob korrekte Dokumente gesendet werden

### BUG-0004 Fix (documents.php)
- **Geändert:** `downloadDocument()` — Dateiname-Bereinigung
- **Angrenzende Funktionen:** Download-Endpunkt
- **Regressions-Risiko:** ⬇️ MINIMAL — `str_replace` entfernt nur Zeichen die in normalen Dateinamen nicht vorkommen
- **Neues Risiko:** Dateinamen die tatsächlich Anführungszeichen enthalten (extrem selten) verlieren diese

### BUG-0005 Fix (archive_boxes_view.py)
- **Geändert:** `_on_smartscan_btn_clicked()` — nutzt jetzt `_get_selected_documents()`
- **Angrenzende Funktionen:** `_get_selected_documents()` (bereits von Download, Delete, etc. genutzt)
- **Regressions-Risiko:** ⬇️ MINIMAL — Verwendet bewährte Methode, weniger Code
- **Manueller Test empfohlen:** Tabelle sortieren, Dokumente auswählen, SmartScan-Button klicken

### BUG-0006 Fix (archive_boxes_view.py)
- **Geändert:** 3 Stellen: `_start_processing`, `_on_processing_finished`, `_on_processing_error`
- **Angrenzende Funktionen:** Dokumentenverarbeitung, Auto-Refresh-Timer
- **Regressions-Risiko:** ⬇️ MINIMAL — `self._cache` ist die gleiche Referenz die an 12+ anderen Stellen korrekt verwendet wird
- **Manueller Test empfohlen:** Dokumente verarbeiten lassen, prüfen ob Auto-Refresh während Verarbeitung pausiert

### BUG-0007 Fix (document_processor.py)
- **Geändert:** Bedingung von `!= 'medium'` auf `== 'high'`
- **Angrenzende Funktionen:** Audit-Trail, Admin KI-Kosten Tab
- **Regressions-Risiko:** ⬇️ MINIMAL — Ändert nur Metadaten-Feld, keine funktionale Auswirkung auf Verarbeitung
- **Manueller Test empfohlen:** PDF mit niedriger Confidence hochladen → Admin Aktivitätslog prüfen

### BUG-0008 Fix (data_cache.py)
- **Geändert:** Fehlerfall-Rückgabewert von `{}` auf `BoxStats()`
- **Angrenzende Funktionen:** `get_stats()` Caller in `archive_boxes_view.py`
- **Regressions-Risiko:** ⬇️ MINIMAL — `BoxStats()` hat gleiche Attribute wie ein funktionierender Stats-Abruf, nur mit Nullwerten
- **Neues Risiko:** Bei Server-Fehler zeigt das UI jetzt "0" statt zu crashen — korrekt, aber Nutzer sieht keine Fehlermeldung

### BUG-0009 Fix (transfer_service.py)
- **Geändert:** XML-Escaping für Username, Consumer-ID, Token, Shipment-ID
- **Angrenzende Funktionen:** STS-Login, listShipments, getShipment, acknowledgeShipment
- **Regressions-Risiko:** ⬇️⬇️ NIEDRIG, aber TESTEN! — Wenn Credentials/IDs keine Sonderzeichen enthalten (Normalfall), ist das Ergebnis identisch. `_escape_xml()` ist eine bestehende Methode die bereits für Passwörter funktioniert
- **Manueller Test ZWINGEND:** BiPRO-Verbindung zu Degenia und VEMA testen (STS-Token holen, Lieferungen abrufen)

### BUG-0010 Fix (openrouter.py)
- **Geändert:** `try/except` um `response.json()`
- **Angrenzende Funktionen:** KI-Klassifikation, PDF-Benennung
- **Regressions-Risiko:** ⬇️ MINIMAL — Bestehende JSON-Antworten werden weiterhin korrekt verarbeitet
- **Neues Risiko:** Bei Non-JSON-Fehlern wird jetzt eine generische Fehlermeldung statt Crash angezeigt — korrektes Verhalten

### BUG-0011 Fix (documents.php)
- **Geändert:** Reihenfolge von Delete-Operationen umgedreht
- **Angrenzende Funktionen:** Bulk-Delete, Activity-Logging
- **Regressions-Risiko:** ⬇️ NIEDRIG — Logik ist funktional identisch im Erfolgsfall
- **Neues Risiko:** Bei Datei-Löschfehler: Dateien bleiben als Waisen auf dem Dateisystem. Besser als Orphaned DB-Records, aber perspektivisch Cleanup nötig

### BUG-0026 Fix (zip_handler.py)
- **Geändert:** `zf.close()` in Exception-Handlern
- **Angrenzende Funktionen:** ZIP-Entpackung, Passwort-Handling
- **Regressions-Risiko:** ⬇️ MINIMAL — `close()` ist idempotent und in `try/except` gewrappt

### BUG-0028 Fix (transfer_service.py)
- **Geändert:** Doppelten `@dataclass` Decorator entfernt
- **Regressions-Risiko:** ⬇️ MINIMAL — Einfacher Decorator auf Klasse, CPython-Verhalten identisch

---

## Offene Risiken (nicht gefixt)

### HOCH
| Bug | Risiko | Empfehlung |
|-----|--------|------------|
| BUG-0012 | Toast aus Worker-Thread → möglicher Qt-Crash | Prüfen ob direkte Aufrufe existieren, ggf. Signal-Dispatch |
| BUG-0013 | O(N²) API-Calls bei Parallelverarbeitung | get_document() mit Server-Endpoint für Einzelabruf ersetzen |
| BUG-0014 | Race-Condition bei Token-Refresh | Validierung vor `set_token()` oder atomarer Swap |
| BUG-0015 | Shared Session nicht thread-safe | Per-Thread-Sessions in ParallelDownloadManager |

### MITTEL
| Bug | Risiko | Empfehlung |
|-----|--------|------------|
| BUG-0021 | `refresh_all_sync()` unvollständig | Dokumente und Connections ebenfalls laden |
| BUG-0023 | Error-Dokumente permanent in 'sonstige' | Auto-Retry-Mechanismus implementieren |
| BUG-0027 | XOP CID URL-Decoding asymmetrisch | URL-Decode bei XOP-Lookup hinzufügen |
| BUG-0029 | Proxy-Env global gelöscht | Nur für BiPRO-Sessions konfigurieren |
| BUG-0030 | replaceDocumentFile nicht transaktional | DB-Transaction wrapping |

---

## Empfehlung

**Sofort testen:**
1. BiPRO-Verbindung (Degenia + VEMA) → Lieferungen abrufen (BUG-0009)
2. Dokumentenverarbeitung (BUG-0006, BUG-0007)
3. SmartScan nach Tabellensortierung (BUG-0005)
4. Farbmarkierung per Rechtsklick → Einzeldokument (BUG-0002)
5. Rechtsklick auf Box → SmartScan (BUG-0003)

**Perspektivisch beheben:**
- BUG-0012 (Toast Thread-Safety) — VOR nächstem Release prüfen
- BUG-0013 (get_document Performance) — Bei Performance-Problemen
- BUG-0014/0015 (Token/Session Race) — Bei intermittierenden Auth-Fehlern
