# Security-Dokumentation (ACENCIA ATLAS)

## Zertifikat-Revocation (SV-026)

Client-Zertifikate fuer BiPRO-Verbindungen werden aktuell NICHT gegen CRL/OCSP geprueft.

**Risiko-Bewertung**: Gering. Die Zertifikate werden nur intern zwischen der Desktop-App und den BiPRO-Endpunkten der Versicherer verwendet. Ein kompromittiertes Zertifikat wuerde nur den Zugang zu Lieferungen einer einzelnen VU ermoeglichen.

**Empfehlung**: Bei Zertifikat-Rotation manuell pruefen ob das alte Zertifikat revoziert wurde. Langfristig: `ssl.SSLContext` mit `check_hostname=True` und OCSP-Stapling einsetzen.

---

## MySQL-Verbindung (SV-029)

Die PDO-Verbindung zur MySQL-Datenbank auf Strato wird derzeit OHNE explizite SSL-Parameter aufgebaut.

**Status**: Strato Shared Hosting bietet MySQL-Server im internen Netzwerk an. Externe Zugriffe sind generell blockiert. Die Verbindung erfolgt ueber interne Strato-Infrastruktur.

**Risiko-Bewertung**: Gering fuer Shared Hosting. Der DB-Server ist nicht ueber das Internet erreichbar.

**Empfehlung**: Falls `SHOW VARIABLES LIKE 'have_ssl'` auf dem Strato-Server `YES` zurueckgibt, kann SSL aktiviert werden:
```php
$options[PDO::MYSQL_ATTR_SSL_CA] = '/path/to/ca.pem';
```

---

## Lizenz-Kompatibilitaet (SV-027)

### Kritische Abhaengigkeiten

| Library | Lizenz | Risiko |
|---------|--------|--------|
| PyMuPDF | AGPL-3.0 | HOCH: Closed-Source-Distribution koennte AGPL verletzen |
| extract-msg | GPL-3.0 | MITTEL: GPL erfordert Quellcode-Offenlegung |

### Empfohlene Massnahmen

1. **PyMuPDF**: Kommerzielle Lizenz bei Artifex erwerben (~250-500 EUR/Jahr) ODER durch `pypdf` (MIT-Lizenz) ersetzen (weniger Features)
2. **extract-msg**: Pruefen ob "System Library Exception" greift, da die App nur unter Windows laeuft und extract-msg als separate Bibliothek installiert wird
3. **Rechtsberatung**: Fuer kommerzielle Distribution dringend empfohlen

### Status

Lizenz-Entscheidung steht aus. Bis zur Klaerung werden die Libraries weiterhin verwendet. Das Risiko ist dokumentiert.
