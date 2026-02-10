# 01 — Bugliste

**Stand:** 10. Februar 2026  
**Methode:** Statische Code-Analyse  
**Gesamt:** 39 Bugs (4 CRITICAL, 11 HIGH, 14 MEDIUM, 10 LOW)

---

## CRITICAL (4)

### BUG-0001 — `clear_all()` crasht bei ProgressToastWidget
- **Datei:** `src/ui/toast.py:549`
- **Sichtbares Fehlverhalten:** `AttributeError: 'ProgressToastWidget' has no attribute '_dismiss_timer'`
- **Erwartetes Verhalten:** Alle Toasts (inkl. ProgressToast) werden sauber entfernt
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0002 — `set_document_color()` crasht mit TypeError
- **Datei:** `src/api/documents.py:776`
- **Sichtbares Fehlverhalten:** `TypeError: update() got an unexpected keyword argument 'display_color'`
- **Erwartetes Verhalten:** Einzelne Farbmarkierung per Fallback funktioniert
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0003 — `self._current_documents` existiert nicht
- **Datei:** `src/ui/archive_boxes_view.py:5151`
- **Sichtbares Fehlverhalten:** `AttributeError: 'ArchiveBoxesView' has no attribute '_current_documents'`
- **Erwartetes Verhalten:** SmartScan-Versand einer ganzen Box funktioniert
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0004 — HTTP Header Injection via Dateiname
- **Datei:** `BiPro-Webspace Spiegelung Live/api/documents.php:621`
- **Sichtbares Fehlverhalten:** Unescapter Dateiname in `Content-Disposition` Header ermöglicht Header-Injection
- **Erwartetes Verhalten:** Dateinamen werden bereinigt/escaped
- **Quelle:** Code-Analyse (Sicherheit)
- **Status:** IDENTIFIZIERT

---

## HIGH (11)

### BUG-0005 — SmartScan sendet falsche Dokumente nach Sortierung
- **Datei:** `src/ui/archive_boxes_view.py:3336-3346`
- **Sichtbares Fehlverhalten:** Nach Tabellen-Sortierung werden falsche Dokumente an SmartScan gesendet
- **Erwartetes Verhalten:** Immer die visuell ausgewählten Dokumente werden versendet
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0006 — Auto-Refresh-Pause bei Verarbeitung wirkungslos
- **Datei:** `src/ui/archive_boxes_view.py:5006-5012, 5039-5045, 5122-5129`
- **Sichtbares Fehlverhalten:** `DataCacheService()` wird neu instanziiert statt `self._cache` → Pause wirkt nicht
- **Erwartetes Verhalten:** Auto-Refresh wird während Dokumentenverarbeitung tatsächlich pausiert
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0007 — Falscher classification_source bei low-Confidence
- **Datei:** `src/services/document_processor.py:685, 754`
- **Sichtbares Fehlverhalten:** Dokumente mit low-Confidence werden als `ki_gpt4o_mini` geloggt statt `ki_gpt4o_zweistufig`
- **Erwartetes Verhalten:** `classification_source` spiegelt tatsächlich verwendetes Modell wider
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0008 — `get_stats()` gibt leeres Dict statt BoxStats bei Fehler
- **Datei:** `src/services/data_cache.py:313-330`
- **Sichtbares Fehlverhalten:** Caller greifen auf `.eingang` zu → `AttributeError` bei API-Fehler
- **Erwartetes Verhalten:** Konsistenter Rückgabetyp (immer BoxStats oder Exception)
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0009 — XML-Injection bei Username/Consumer-ID/Token
- **Datei:** `src/bipro/transfer_service.py:567, 589, 713, 754, 850, 863, 1249, 1256`
- **Sichtbares Fehlverhalten:** Sonderzeichen in BiPRO-Credentials erzeugen ungültiges XML
- **Erwartetes Verhalten:** Alle Werte werden XML-escaped
- **Quelle:** Code-Analyse (Sicherheit)
- **Status:** IDENTIFIZIERT

### BUG-0010 — `response.json()` crasht bei Non-JSON-Fehlern
- **Datei:** `src/api/openrouter.py:741-745`
- **Sichtbares Fehlverhalten:** `json.JSONDecodeError` statt `APIError` bei HTML/Text-Fehlerantwort
- **Erwartetes Verhalten:** Nicht-JSON-Fehler werden sauber abgefangen
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0011 — Bulk-Delete löscht Dateien vor DB-Eintrag
- **Datei:** `BiPro-Webspace Spiegelung Live/api/documents.php:690-704`
- **Sichtbares Fehlverhalten:** Bei DB-Fehler: Dateien gelöscht, DB-Einträge bleiben → Orphaned Records
- **Erwartetes Verhalten:** Atomare Operation: DB-Delete zuerst, dann Dateien
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0012 — Toast-Erstellung aus Worker-Threads crasht Qt
- **Datei:** `src/ui/toast.py:505-524`
- **Sichtbares Fehlverhalten:** Segfault oder UI-Korruption wenn `show_*()` aus QThread aufgerufen
- **Erwartetes Verhalten:** Thread-sichere Toast-Erstellung über Qt-Signale
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0013 — `get_document()` lädt ALLE Dokumente für Einzelabfrage
- **Datei:** `src/api/documents.py:380-386`
- **Sichtbares Fehlverhalten:** O(N) API-Calls bei N Dokumenten in Parallelverarbeitung
- **Erwartetes Verhalten:** Einzelnes Dokument per ID abrufen
- **Quelle:** Code-Analyse (Performance)
- **Status:** IDENTIFIZIERT

### BUG-0014 — Token zwischen set/validate für andere Threads sichtbar
- **Datei:** `src/api/auth.py:202-224`
- **Sichtbares Fehlverhalten:** Race-Condition: Threads nutzen ggf. ungültigen Token nach Auto-Login
- **Erwartetes Verhalten:** Token erst nach Validierung für andere Threads sichtbar
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0015 — SharedTokenManager gibt nicht thread-safe Session zurück
- **Datei:** `src/bipro/transfer_service.py:1465-1477`
- **Sichtbares Fehlverhalten:** Parallele BiPRO-Downloads könnten Session-State korrumpieren
- **Erwartetes Verhalten:** Pro-Thread-Sessions oder keine Session-Exposition
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

---

## MEDIUM (14)

### BUG-0016 — Non-dict JSON-Response → AttributeError im API-Client
- **Datei:** `src/api/client.py:156-177`
- **Sichtbares Fehlverhalten:** `AttributeError: 'list' object has no attribute 'get'` bei Array-Response
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0017 — `rename_document()` kann `ai_renamed=False` nicht setzen
- **Datei:** `src/api/documents.py:670-674`
- **Sichtbares Fehlverhalten:** `False` wird als `None` übergeben (falsy-Check)
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0018 — Token-Datei ohne JSON-Struktur-Validierung
- **Datei:** `src/api/auth.py:307-314`
- **Sichtbares Fehlverhalten:** Crash bei korrupter Token-Datei (z.B. JSON-Array statt Dict)
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0019 — Token-Datei im Klartext ohne Dateiberechtigungen
- **Datei:** `src/api/auth.py:295-305`
- **Sichtbares Fehlverhalten:** JWT-Token für andere Nutzer auf Multi-User-System lesbar
- **Quelle:** Code-Analyse (Sicherheit)
- **Status:** IDENTIFIZIERT

### BUG-0020 — Cache-Read ohne Lock im Background-Thread
- **Datei:** `src/services/data_cache.py:510-513`
- **Sichtbares Fehlverhalten:** Race-Condition bei Connection-Cache-Zugriff
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0021 — `refresh_all_sync()` lädt nur Stats, nicht Dokumente/Connections
- **Datei:** `src/services/data_cache.py:524-539`
- **Sichtbares Fehlverhalten:** F5 "Aktualisieren" zeigt keine neuen Dokumente bis nächster Lazy-Load
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0022 — Negative Kosten bei OpenRouter-Aufladung während Verarbeitung
- **Datei:** `src/services/document_processor.py:346-348`
- **Sichtbares Fehlverhalten:** Negative Kosten in DB und Admin-Kostenauswertung
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0023 — Fehler-Dokumente permanent in 'sonstige' statt Recovery
- **Datei:** `src/services/document_processor.py:881-908`
- **Sichtbares Fehlverhalten:** Transiente Fehler (Netzwerk, Timeout) → Dokument permanent nicht verarbeitet
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0024 — Drop-Upload-Dialog hat keinen funktionierenden Cancel-Button
- **Datei:** `src/ui/main_hub.py:977-987`
- **Sichtbares Fehlverhalten:** Klick auf "Abbrechen" hat keine Wirkung
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0025 — DropUploadWorker hat keine cancel()-Methode
- **Datei:** `src/ui/main_hub.py:1141-1143`
- **Sichtbares Fehlverhalten:** `quit()` stoppt ThreadPoolExecutor nicht → App kann bei Beenden hängen
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0026 — ZipFile-Handle-Leak bei verschlüsselter ZIP-Erkennung
- **Datei:** `src/services/zip_handler.py:186-205`
- **Sichtbares Fehlverhalten:** Geöffnetes ZipFile wird bei Encryption-RuntimeError nicht geschlossen
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0027 — XOP Content-ID URL-Decoding asymmetrisch
- **Datei:** `src/bipro/transfer_service.py:1050-1058, 1107`
- **Sichtbares Fehlverhalten:** CIDs mit `%40` werden in Header dekodiert, in XOP-Reference nicht → kein Match
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0028 — Double `@dataclass` Decorator
- **Datei:** `src/bipro/transfer_service.py:142-143`
- **Sichtbares Fehlverhalten:** Doppelte Verarbeitung, potentielle Metaklassen-Probleme
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0029 — Globale Proxy-Umgebungsvariablen bei Module-Import gelöscht
- **Datei:** `src/bipro/transfer_service.py:72-75`
- **Sichtbares Fehlverhalten:** Proxy-Settings für gesamten Prozess (inkl. OpenRouter) deaktiviert
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0030 — `replaceDocumentFile` nicht transaktional
- **Datei:** `BiPro-Webspace Spiegelung Live/api/documents.php:1237-1247`
- **Sichtbares Fehlverhalten:** Bei DB-Fehler nach rename: Datei ersetzt, Hash/Size in DB alt
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0031 — MSG-Handler verwirft Nicht-PDF/ZIP-Anhänge ohne Warnung
- **Datei:** `src/services/msg_handler.py:84-87`
- **Sichtbares Fehlverhalten:** Bilder, Word-Docs etc. werden aus E-Mails still verworfen
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

### BUG-0032 — `process_pdf_smart` liest alle Seiten statt 2-5
- **Datei:** `src/api/openrouter.py:1017-1024`
- **Sichtbares Fehlverhalten:** Unnötige Speicher-/CPU-Last bei großen PDFs
- **Quelle:** Code-Analyse
- **Status:** IDENTIFIZIERT

---

## LOW (10)

### BUG-0033 — `post()` setzt falschen Content-Type bei Form-Data
- **Datei:** `src/api/client.py:276-290`
- **Status:** IDENTIFIZIERT

### BUG-0034 — `requests.Session` in API-Client nie geschlossen
- **Datei:** `src/api/client.py:49-52`
- **Status:** IDENTIFIZIERT

### BUG-0035 — `vu_id=0` wird als falsy übersprungen
- **Datei:** `src/api/documents.py:291-294`
- **Status:** IDENTIFIZIERT

### BUG-0036 — QTimer für Cache-Info aus Worker-Thread abgerufen
- **Datei:** `src/services/data_cache.py:559-568`
- **Status:** IDENTIFIZIERT

### BUG-0037 — Bare `except:` fängt SystemExit/KeyboardInterrupt
- **Datei:** `src/bipro/transfer_service.py:1212, 1305, 1311`
- **Status:** IDENTIFIZIERT

### BUG-0038 — `_thread_apis` Dict ohne Lock in ThreadPoolExecutor
- **Datei:** `src/ui/main_hub.py:201-208`
- **Status:** IDENTIFIZIERT

### BUG-0039 — `DOWNLOADABLE_BOXES` entfernt mit falscher Variablen
- **Datei:** `src/ui/archive_boxes_view.py:2059`
- **Status:** IDENTIFIZIERT
