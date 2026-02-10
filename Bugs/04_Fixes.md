# 04 — Fix-Design

**Stand:** 10. Februar 2026  
**Prinzip:** Minimaler Fix, keine Refactors, keine kosmetischen Änderungen.

---

## CRITICAL Fixes

### BUG-0001 — `clear_all()` crasht bei ProgressToastWidget

**Fix:** Type-Check in `clear_all()` vor Zugriff auf `_dismiss_timer`.

```python
# toast.py:546-552
def clear_all(self):
    for toast in list(self._active_toasts):
        if hasattr(toast, '_dismiss_timer'):
            toast._dismiss_timer.stop()
        toast.setVisible(False)
        toast.deleteLater()
    self._active_toasts.clear()
```

**Risiko:** Minimal. `hasattr`-Check ist defensiv, ändert kein Verhalten für `ToastWidget`.

---

### BUG-0002 — `set_document_color()` crasht mit TypeError

**Fix:** `display_color` als Parameter zu `update()` hinzufügen.

```python
# documents.py:572-587 — Parameter hinzufügen:
def update(self, doc_id: int, 
           ...,
           is_archived: Optional[bool] = None,
           display_color: Optional[str] = None) -> bool:
```

Und in der Payload-Erstellung (nach den bestehenden Feldern):

```python
if display_color is not None:
    payload['display_color'] = display_color
```

**Risiko:** Minimal. Neuer optionaler Parameter, Abwärtskompatibel.

---

### BUG-0003 — `self._current_documents` existiert nicht

**Fix:** Variablenname korrigieren.

```python
# archive_boxes_view.py:5151
# ALT: docs = [d for d in self._current_documents if ...]
# NEU:
docs = [d for d in self._documents if d.box_type == box_type and not d.is_archived]
```

**Risiko:** Minimal. Einzeilige Korrektur, gleiche Logik.

---

### BUG-0004 — HTTP Header Injection via Dateiname

**Fix:** Dateiname in `Content-Disposition` bereinigen (Anführungszeichen entfernen/escapen).

```php
// documents.php:621
// ALT: header('Content-Disposition: attachment; filename="' . $doc['original_filename'] . '"');
// NEU:
$safeFilename = str_replace(['"', "\r", "\n", "\0"], '', $doc['original_filename']);
header('Content-Disposition: attachment; filename="' . $safeFilename . '"');
```

**Risiko:** Minimal. Dateinamen mit Anführungszeichen verlieren diese beim Download.

---

## HIGH Fixes

### BUG-0005 — SmartScan sendet falsche Dokumente nach Sortierung

**Fix:** `UserRole`-Data aus Table-Item lesen (gleiche Pattern wie `_get_selected_documents()`).

```python
# archive_boxes_view.py:3335-3346
# Bestehende _get_selected_documents() Methode verwenden:
selected_docs = self._get_selected_documents()
```

**Risiko:** Minimal. Nutzt bereits existierende, korrekte Methode.

---

### BUG-0006 — Auto-Refresh-Pause bei Verarbeitung wirkungslos

**Fix:** `self._cache` verwenden statt `DataCacheService()`.

```python
# archive_boxes_view.py:5006-5012, 5039-5045, 5122-5129
# ALT:
#     from services.data_cache import DataCacheService
#     cache = DataCacheService()
#     cache.pause_auto_refresh()
# NEU:
try:
    self._cache.pause_auto_refresh()
    logger.info("Auto-Refresh für Dokumentenverarbeitung pausiert")
except Exception as e:
    logger.warning(f"Auto-Refresh pausieren fehlgeschlagen: {e}")
```

Gleiche Änderung für `resume_auto_refresh()` in den Callbacks.

**Risiko:** Minimal. `self._cache` ist bereits initialisiert und wird überall sonst korrekt verwendet.

---

### BUG-0007 — Falscher classification_source bei low-Confidence

**Fix:** Bedingung korrigieren: `== 'high'` statt `!= 'medium'`.

```python
# document_processor.py:685, 754
# ALT: classification_source = 'ki_gpt4o_mini' if ki_confidence != 'medium' else 'ki_gpt4o_zweistufig'
# NEU:
classification_source = 'ki_gpt4o_mini' if ki_confidence == 'high' else 'ki_gpt4o_zweistufig'
```

**Risiko:** Minimal. Ändert nur Audit-Metadaten bei low-Confidence (~1-5% der Dokumente).

---

### BUG-0008 — `get_stats()` gibt leeres Dict statt BoxStats bei Fehler

**Fix:** Im Fehlerfall ein leeres `BoxStats`-Objekt mit Nullwerten zurückgeben.

```python
# data_cache.py:330
# ALT: return {}
# NEU:
from api.documents import BoxStats
return BoxStats(eingang=0, verarbeitung=0, gdv=0, courtage=0, sach=0, 
                leben=0, kranken=0, sonstige=0, roh=0, falsch=0)
```

**Risiko:** Minimal. Caller erhalten konsistenten Typ. Nullwerte statt Crash.

---

### BUG-0009 — XML-Injection bei BiPRO-Credentials

**Fix:** `_escape_xml()` auf alle interpolierten Werte anwenden.

```python
# transfer_service.py — überall wo f-Strings in XML verwendet werden:
# Username: {self._escape_xml(self.credentials.username)}
# Consumer-ID: {self._escape_xml(self.credentials.consumer_id)}
# Token: {self._escape_xml(self._token)}
# Shipment-ID: {self._escape_xml(shipment_id)}
```

**Risiko:** Gering. Wenn Credentials keine Sonderzeichen enthalten, ist die Ausgabe identisch.

---

### BUG-0010 — `response.json()` crasht bei Non-JSON-Fehlern

**Fix:** `try/except` um `response.json()`.

```python
# openrouter.py:741-745
if response.status_code != 200:
    try:
        error_data = response.json() if response.text else {}
    except (ValueError, json.JSONDecodeError):
        error_data = {}
    error_msg = error_data.get('error', {}).get('message', f"HTTP {response.status_code}")
```

**Risiko:** Minimal. Verhindert Crash, Fehlermeldung wird generisch.

---

### BUG-0011 — Bulk-Delete löscht Dateien vor DB

**Fix:** Reihenfolge umdrehen: DB-DELETE zuerst, dann Dateien.

```php
// documents.php:690-704
// 1. Zuerst aus DB löschen
$affected = Database::execute(
    "DELETE FROM documents WHERE id IN ($placeholders)",
    array_values($docIds)
);

// 2. Dann Dateien löschen (nur wenn DB-Delete erfolgreich)
if ($affected > 0) {
    foreach ($docs as $doc) {
        $filePath = DOCUMENTS_PATH . $doc['storage_path'];
        if (file_exists($filePath)) {
            @unlink($filePath);
        }
    }
}
```

**Risiko:** Gering. Bei Datei-Löschfehler bleiben Waisen auf dem Dateisystem (besser als Orphaned DB-Records).

---

### BUG-0012 — Toast aus Worker-Threads

**Prüfung nötig:** Werden Toast-Methoden tatsächlich direkt aus Worker-Threads aufgerufen? Wenn ja:

**Fix-Vorschlag:** Thread-Check in `_show()`:

```python
def _show(self, toast_type, message, ...):
    if QThread.currentThread() != QApplication.instance().thread():
        # Aus Worker-Thread: Via Signal dispatchen
        QMetaObject.invokeMethod(self, '_show', Qt.ConnectionType.QueuedConnection, ...)
        return
    # ... bestehender Code
```

**Risiko:** Mittel. Erfordert Prüfung ob `QMetaObject.invokeMethod` mit Python-Methoden funktioniert.

**Status:** DESIGN — Implementierung nach Verifikation ob direkte Thread-Aufrufe existieren.

---

## MEDIUM Fixes (Kurzform)

| Bug | Fix | Risiko |
|-----|-----|--------|
| BUG-0026 (ZipFile-Leak) | `zf.close()` in `except`-Blöcken | Minimal |
| BUG-0027 (XOP CID) | URL-decode auch bei XOP-href-Lookup | Gering |
| BUG-0028 (Double @dataclass) | Doppelten Decorator entfernen | Minimal |
| BUG-0029 (Proxy-Env) | Proxy-Cleanup in eine Funktion verschieben, nur für BiPRO-Sessions | Mittel |

---

## LOW Fixes (keine sofortige Umsetzung nötig)

Bugs 0033-0039: Code-Qualität, keine funktionalen Auswirkungen. Fix bei nächstem Refactoring.
