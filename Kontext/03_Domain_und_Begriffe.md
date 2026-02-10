# 03 - Domain und Begriffe

**Version:** 1.6.0
**Analyse-Datum:** 2026-02-10

---

## Domaenen-Ueberblick

Das Projekt operiert in drei Domaenen:

1. **GDV (Gesamtverband der Deutschen Versicherungswirtschaft)** - Branchenstandard fuer Datenaustausch
2. **BiPRO (Brancheninstitut fuer Prozessoptimierung)** - Schnittstellen-Standard fuer Versicherer
3. **Dokumentenmanagement** - KI-gestuetztes Archiv mit E-Mail-Integration

---

## GDV-Domaene

### GDV-Format

Das GDV-Format ist ein **Fixed-Width-Format** fuer den Datenaustausch zwischen Versicherungsunternehmen und Vermittlern.

| Merkmal | Wert |
|---------|------|
| Zeilenbreite | 256 Bytes |
| Encoding | CP1252 (Windows-1252) |
| Satzart | Position 1-4 (4 Zeichen) |
| Teildatensatz | Position 256 (1 Zeichen) |

### Satzarten (Implementiert)

| Satzart | Name | Teildatensaetze | Beschreibung |
|---------|------|-----------------|--------------|
| 0001 | Vorsatz | 1 | Datei-Header (VU, Datum, Release) |
| 0100 | Partnerdaten | 1-5 | Kunden, Adressen, Bankdaten |
| 0200 | Vertragsteil | 1 | Grunddaten (Laufzeit, Beitrag, Sparte) |
| 0210 | Spartenspezifisch | 1+ | Wagnisse, Risiken |
| 0220 | Deckungsteil | 1, 6+ | Versicherte Personen, Leistungen |
| 0230 | Fondsanlage | 1+ | Fondsdaten (ISIN, Anteile) |
| 9999 | Nachsatz | 1 | Pruefsummen |

**Quelle:** `src/layouts/gdv_layouts.py`

### Teildatensaetze (Beispiel 0100)

| TD | Inhalt | Quelle |
|----|--------|--------|
| 1 | Adressdaten (Name, Strasse, PLZ, Ort) | `gdv_layouts.py` |
| 2 | Nummern (Kundennummer, Bankverbindung alt) | `gdv_layouts.py` |
| 3 | Zusatzinfo | `gdv_layouts.py` |
| 4 | Bankdaten (IBAN/BIC) | `gdv_layouts.py` |
| 5 | Erweiterte Daten | `gdv_layouts.py` |

### Sparten

| Code | Bezeichnung | Kategorie |
|------|-------------|-----------|
| 10 | Lebensversicherung | Leben |
| 20 | Krankenversicherung | Kranken |
| 30 | Unfallversicherung | Sach |
| 40 | Haftpflichtversicherung | Sach |
| 50 | Kraftfahrt | Sach |
| 70 | Rechtsschutz | Sach |
| 80 | Feuer/Wohngebaude | Sach |

---

## BiPRO-Domaene

### BiPRO-Normen

| Norm | Beschreibung | Status |
|------|--------------|--------|
| 410 | STS (Security Token Service) | Implementiert |
| 420 | TAA (Angebot/Antrag) | Nicht implementiert |
| 430.1 | Transfer allgemein | Implementiert |
| 430.2 | Lieferungen | Implementiert |
| 430.4 | GDV-Daten | Teilweise |
| 430.5 | Dokumente | Implementiert |

### BiPRO-Operationen

| Operation | Norm | Beschreibung |
|-----------|------|--------------|
| RequestSecurityToken | 410 | STS-Token holen |
| listShipments | 430 | Lieferungen auflisten |
| getShipment | 430 | Lieferung herunterladen (MTOM/XOP) |
| acknowledgeShipment | 430 | Empfang quittieren |

### VU-spezifisches Verhalten

| VU | STS-Format | Besonderheiten |
|----|------------|----------------|
| **Degenia** | Standard BiPRO | BestaetigeLieferungen=true ERFORDERLICH |
| **VEMA** | VEMA-spezifisch | Consumer-ID ERFORDERLICH, KEIN BestaetigeLieferungen |

### Lieferungs-Kategorien (BiPRO-Codes)

| Code | Bedeutung | Ziel-Box |
|------|-----------|----------|
| 100001000 | Antragsversand | KI-Klassifikation |
| 100002000 | Eingangsbestaetigung | KI-Klassifikation |
| 100005000 | Nachfrage | KI-Klassifikation |
| 100007000 | Policierung | KI-Klassifikation |
| 110011000 | Adressaenderung | KI-Klassifikation |
| 120010000 | Nachtrag | KI-Klassifikation |
| 140012000 | Mahnung | KI-Klassifikation |
| 140013000 | Beitragsrechnung | KI-Klassifikation |
| 150013000 | Schaden | KI-Klassifikation |
| 160010000 | Kuendigung | KI-Klassifikation |
| **300001000** | **Provisionsabrechnung** | **Courtage** |
| **300002000** | **Courtageabrechnung** | **Courtage** |
| **300003000** | **Verguetungsuebersicht** | **Courtage** |
| **999010010** | **GDV Bestandsdaten** | **GDV** |

**Quelle:** `src/config/processing_rules.py`

---

## Box-System (Dokumentenarchiv)

### Box-Typen (in Anzeigereihenfolge)

| Nr. | Box | Farbe | Beschreibung |
|-----|-----|-------|--------------|
| 1 | GDV | #4caf50 (Gruen) | GDV-Dateien (.gdv, .txt, keine Endung) |
| 2 | Courtage | #ff9800 (Orange) | Provisionsabrechnungen (BiPRO-Code oder KI) |
| 3 | Sach | #2196f3 (Blau) | Sachversicherungs-Dokumente (KI) |
| 4 | Leben | #9c27b0 (Lila) | Lebensversicherungs-Dokumente (KI) |
| 5 | Kranken | #e91e63 (Pink) | Krankenversicherungs-Dokumente (KI) |
| 6 | Sonstige | #607d8b (Grau) | Nicht zugeordnete Dokumente |
| 7 | Roh Archiv | #795548 (Braun) | XML-Rohdateien, ZIP/MSG-Originale |
| - | Eingang | (Systembox) | Unverarbeitete Dokumente |
| - | Verarbeitung | (Systembox) | Gerade in Verarbeitung |

### Dokumenten-Farbmarkierung

8 persistente Farben zur manuellen Organisation (v1.0.3):

| Farbe | Hex | Name |
|-------|-----|------|
| Gruen | #c8e6c9 | green |
| Rot | #ffcdd2 | red |
| Blau | #bbdefb | blue |
| Orange | #ffe0b2 | orange |
| Lila | #e1bee7 | purple |
| Pink | #f8bbd0 | pink |
| Tuerkis | #b2ebf2 | cyan |
| Gelb | #fff9c4 | yellow |

Farben bleiben erhalten bei Verschieben, Archivieren, KI-Verarbeitung.

---

## KI-Klassifikation

### Zweistufiges Confidence-Scoring (v0.9.4)

| Stufe | Modell | Seiten | Token | Bedingung |
|-------|--------|--------|-------|-----------|
| 1 | GPT-4o-mini | 2 | ~200 | Immer |
| 2 | GPT-4o | 5 | ~400 | Nur bei Stufe-1-Confidence = "low" (~1-5% der Dokumente) |

### Keyword-Conflict-Hints (v1.1.0)

Lokaler Scanner (`_build_keyword_hints()`) erkennt widerspruechliche Keywords:

| Konflikt | Hint |
|----------|------|
| Courtage + Leben/Sach/Kranken | Courtage-Keyword hat Vorrang |
| Kontoauszug + Provision | Spezialfall -> Courtage |
| Sach-Keyword allein | Sicherheits-Hint (bekannte KI-Schwaeche) |

95% der Dokumente: 0 extra Tokens, ~5% mit Konflikt: +30 Tokens.

### Benennungs-Schema

| Box | Muster | Beispiel |
|-----|--------|---------|
| Courtage | `VU_Courtage_Datum.pdf` | `Allianz_Courtage_2026-02-04.pdf` |
| Sach/Leben/Kranken | `VU_Sparte.pdf` | `Degenia_Sach.pdf` |
| Sonstige | `VU_Dokumentname.pdf` | `VEMA_Schriftwechsel.pdf` |

---

## Duplikat-Erkennung (v1.1.1)

- Server berechnet SHA256-Hash beim Upload
- Vergleich gegen ALLE Dokumente (inkl. archivierte)
- Duplikate werden hochgeladen, aber als Dopplung markiert (`version > 1`)
- UI: Warn-Icon + Tooltip mit Original-Dokumentname

---

## Glossar

| Begriff | Beschreibung | Quelle |
|---------|--------------|--------|
| VU | Versicherungsunternehmen | Branchenstandard |
| VSNR | Versicherungsschein-Nummer | GDV-Datenmodell |
| Sparte | Versicherungssparte (Leben, Sach, Kranken) | GDV, BiPRO |
| Satzart | 4-stelliger Identifier (0001-9999) | GDV-Format |
| TD | Teildatensatz (1-9 pro Satzart) | GDV-Format |
| STS | Security Token Service | BiPRO 410 |
| MTOM | Message Transmission Optimization Mechanism | BiPRO 430 |
| XOP | XML-binary Optimized Packaging | BiPRO 430 |
| Courtage | Makler-Provision vom Versicherer | Versicherungsbranche |
| Box | Logische Ablage im Dokumentenarchiv | Projekteigen |
| Smart!Scan | SCS Smart!Scan Dokumenten-Digitalisierung | SCS GmbH |
| IMAP | Internet Message Access Protocol | E-Mail-Standard |
| JWT | JSON Web Token | Auth-Standard |
| PHPMailer | PHP-Bibliothek fuer SMTP-Versand | Open Source |
