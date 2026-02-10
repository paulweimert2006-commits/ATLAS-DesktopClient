# Bug-Analyse: ACENCIA ATLAS v1.1.4

**Datum:** 10. Februar 2026  
**Methode:** Statische Code-Analyse aller kritischen Module  
**Analysierte Dateien:** 16 Quelldateien (Python + PHP)  
**Gefundene Bugs:** 39 (4 CRITICAL, 11 HIGH, 14 MEDIUM, 10 LOW)

---

## Navigation

| Datei | Inhalt |
|-------|--------|
| [01_Bugliste.md](01_Bugliste.md) | Alle identifizierten Bugs mit Schweregrad |
| [02_Reproduktion.md](02_Reproduktion.md) | Reproduktionsschritte pro Bug |
| [03_Root_Cause_Analyse.md](03_Root_Cause_Analyse.md) | Ursachenanalyse |
| [04_Fixes.md](04_Fixes.md) | Fix-Design & Umsetzungsplan |
| [05_Verifikation.md](05_Verifikation.md) | Testdokumentation |
| [06_Regressionen_und_Risiken.md](06_Regressionen_und_Risiken.md) | Nebenwirkungen |

---

## Schweregrad-Übersicht

| Schweregrad | Anzahl | Beschreibung |
|-------------|--------|--------------|
| **CRITICAL** | 4 | Crash, Datenverlust, Sicherheitslücke |
| **HIGH** | 11 | Falsches Verhalten, falsche Daten, Sicherheitsrisiko |
| **MEDIUM** | 14 | Edge-Cases, Resource-Leaks, Race-Conditions |
| **LOW** | 10 | Kosmetisch, Performance, Code-Qualität |

## Top-Priority Bugs (sofort beheben)

| ID | Modul | Bug | Severity |
|----|-------|-----|----------|
| BUG-0001 | `toast.py` | `clear_all()` crasht bei ProgressToastWidget | CRITICAL |
| BUG-0002 | `documents.py` | `set_document_color()` crasht mit TypeError | CRITICAL |
| BUG-0003 | `archive_boxes_view.py` | `self._current_documents` existiert nicht → AttributeError | CRITICAL |
| BUG-0004 | `documents.php` | HTTP Header Injection via Dateiname | CRITICAL |
| BUG-0005 | `archive_boxes_view.py` | SmartScan sendet falsche Dokumente nach Sortierung | HIGH |
| BUG-0006 | `archive_boxes_view.py` | Auto-Refresh-Pause bei Verarbeitung wirkungslos | HIGH |
| BUG-0007 | `document_processor.py` | Falscher classification_source bei low-Confidence | HIGH |
| BUG-0008 | `data_cache.py` | `get_stats()` gibt leeres Dict statt BoxStats bei Fehler | HIGH |
| BUG-0009 | `transfer_service.py` | XML-Injection bei Username/Consumer-ID/Token | HIGH |
| BUG-0010 | `openrouter.py` | `response.json()` crasht bei Non-JSON-Fehlern | HIGH |
| BUG-0011 | `documents.php` | Bulk-Delete löscht Dateien vor DB-Eintrag | HIGH |
| BUG-0012 | `toast.py` | Toast-Erstellung aus Worker-Threads crasht Qt | HIGH |
