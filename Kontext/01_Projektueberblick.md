# 01 - Projektueberblick

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Was ist das Projekt?

**ACENCIA ATLAS** ("Der Datenkern.") ist eine Desktop-Anwendung mit Server-Backend fuer Versicherungsvermittler. Es kombiniert vier Hauptbereiche:

1. **BiPRO Datenabruf** - Automatisierter Abruf von Lieferungen (Dokumente, GDV-Daten) von Versicherungsunternehmen ueber BiPRO-Schnittstellen + IMAP Mail-Import
2. **Dokumentenarchiv mit Box-System** - Zentrales Archiv mit KI-gestuetzter Klassifikation, Smart!Scan E-Mail-Versand, PDF-Bearbeitung, Duplikat-Erkennung
3. **GDV-Editor** - Erstellen, Anzeigen und Bearbeiten von GDV-Datensaetzen (Branchenstandard-Format)
4. **Administration** - 10 Panels: Nutzer, Sessions, Passwoerter, Aktivitaetslog, KI-Kosten, Releases, E-Mail-Konten, SmartScan-Settings, SmartScan-Historie, IMAP-Inbox

---

## Zweck

| Ziel | Beschreibung | Status |
|------|--------------|--------|
| **Primaer** | BiPRO-Daten automatisiert von Versicherern abrufen | Funktioniert (Degenia, VEMA) |
| **Sekundaer** | Zentrales Dokumentenarchiv fuer Team (2-5 Personen) | Funktioniert |
| **Tertiaer** | GDV-Dateien visualisieren und bearbeiten | Funktioniert |

---

## Zielgruppe

- **Primaer:** Versicherungsvermittler der ACENCIA GmbH
- **Team-Groesse:** 2-5 Personen
- **Technisches Niveau:** Endanwender (keine IT-Kenntnisse erforderlich)

---

## Explizit NICHT Ziel

| Nicht-Ziel | Begruendung |
|------------|------------|
| Web-Oberflaeche | Desktop-App mit Server-Backend ist gewaehlt |
| XML/JSON-GDV-Varianten | Nur klassisches Fixed-Width-Format (256 Bytes/Zeile) |
| Automatische Abrufe ohne Benutzer | Manuell ausgeloest (aber "Alle VUs" mit einem Klick) |
| Multi-Mandanten | Einzelne Firma (ACENCIA GmbH) |

---

## Technische Eckdaten

| Aspekt | Details |
|--------|---------|
| **Plattform** | Windows 10/11 (Desktop) |
| **Sprache** | Python 3.10+ |
| **GUI Framework** | PySide6 (Qt 6) |
| **Backend** | PHP 7.4+ REST API auf Strato Webspace |
| **Datenbank** | MySQL 8.0 |
| **KI** | OpenRouter API (GPT-4o-mini + GPT-4o fuer PDF-Klassifikation) |
| **BiPRO** | Raw XML mit requests (kein zeep) |
| **E-Mail** | PHPMailer v6.9.3 (SMTP), IMAP-Polling (PHP) |
| **Codeumfang** | ~52.000 Zeilen Python, 63 Dateien |

---

## Versionsverlauf (ab v1.0.1)

| Version | Datum | Meilensteine |
|---------|-------|--------------|
| v1.0.1 | 09.02.2026 | Erste stabile Release-Version |
| v1.0.2 | 08.02.2026 | Scan-Upload fuer Power Automate |
| v1.0.3 | 09.02.2026 | Dokumenten-Farbmarkierung |
| v1.0.4 | 09.02.2026 | Drag & Drop, MSG-Verarbeitung, PDF-Unlock, Outlook-Direct-Drop |
| v1.0.5 | 09.02.2026 | ZIP-Entpackung, Passwort-Verwaltung |
| v1.0.6 | 09.02.2026 | Smart!Scan E-Mail-Versand, IMAP-Import |
| v1.0.7 | 10.02.2026 | Toast-System (keine modalen Popups mehr) |
| v1.0.8 | 10.02.2026 | Tastenkuerzel im Archiv |
| v1.0.9 | 10.02.2026 | Admin-Redesign (vertikale Sidebar), Mail-Import in BiPRO |
| v1.1.0 | 10.02.2026 | Keyword-Conflict-Hints, PDF-Validierung, MTOM-Fixes |
| v1.1.1 | 10.02.2026 | Duplikat-Erkennung (SHA256) |
| v1.1.2 | 10.02.2026 | Dokument-Historie (Seitenpanel) |
| v1.1.3 | 10.02.2026 | PDF-Bearbeitung in Vorschau |
| **v1.1.4** | **10.02.2026** | **App-Schliess-Schutz bei laufenden Operationen** |

---

## Scope der Analyse

Diese Dokumentation umfasst:

- Desktop-Anwendung (`src/`, 63 Python-Dateien)
- Server-API (`BiPro-Webspace Spiegelung Live/api/`, ~20 PHP-Endpunkte)
- Konfiguration und Abhaengigkeiten
- Testdaten (`testdata/`)

**Nicht analysiert:**
- Inhalte von `Projekt Ziel/` (Konzepte, E-Mail-Verkehr)
- Echte Produktionsdaten
- `Echte daten Beispiel/` (personenbezogene Daten)
