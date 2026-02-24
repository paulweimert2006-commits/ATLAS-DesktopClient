# Feature-Ideen & Verbesserungen

> Sammlung von Ideen, die noch nicht priorisiert oder geplant sind.
> Verschiebe Eintraege nach `ROADMAP.md` sobald sie konkret geplant werden.

---

## Archiv & Dokumente
- [ ] Lazy Loading fuer sehr grosse Dokumentenlisten (>10.000)
- [ ] Leere-Seiten-Erkennung Phase 2: Admin-Einstellungen fuer Behandlungsoptionen (Auto-Loeschen, Farbmarkierung)
- [ ] WebSocket-Migration fuer Chat-Polling (aktuell QTimer 30s)
- [ ] Erweiterte Volltextsuche mit Facetten/Filtern

## BiPRO
- [ ] Weitere VUs anbinden (Signal Iduna, Nuernberger, Allianz, etc.)
- [ ] acknowledgeShipment implementieren/testen
- [ ] Automatische Abrufe ohne Benutzerinteraktion (Scheduler)

## Provisionsmanagement
- [ ] Phase 2: Rollenbasierte Sichten (Teamleiter sieht Team, Berater sieht sich selbst)
- [ ] Erweiterte VU-Format-Unterstuetzung (weitere Versicherer-Formate)
- [ ] Automatischer Xempus-Daten-Sync

## Infrastruktur
- [ ] Unit-Tests (aktuell nur manuelle Tests + 11 Smoke-Tests)
- [ ] Linter/Formatter einrichten (ruff)
- [ ] i18n-Vollstaendigkeit: Verbleibende hardcodierte UI-Strings migrieren
- [ ] CI/CD-Pipeline
- [ ] Web-Dashboard als Ergaenzung zur Desktop-App (optional)

## UI/UX
- [ ] CSS-Module statt Inline-Styles (aktuell Qt Inline-Styles)
- [ ] `QFont::setPointSize` Warnings beim Start beheben
- [ ] Dark Mode
