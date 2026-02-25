# ATLAS Governance Toolchain

> **Version**: 1.1.0 | **Stand**: 25.02.2026
> **Sprache**: PowerShell 5.1+ (Windows-nativ)
> **Voraussetzungen**: `git`, `gh` (GitHub CLI), `python`, optional `PyInstaller`, `Inno Setup`

---

## 1. Ueberblick

Die Governance-Toolchain automatisiert den gesamten Release-Lifecycle von ATLAS:
Branch-Management, PR-Erstellung, CI-Ueberwachung, Build, Gate-Validierung, Release-Upload und Deprecation.

**Architekturprinzip**: Jedes Skript erledigt **exakt eine Aufgabe**.
Flow-Skripte orchestrieren mehrere Einzelskripte.
`atlas.ps1` ist der zentrale Entry-Point fuer alle Operationen.

---

## 2. Ordnerstruktur

```
governance/
  _lib.ps1                    Shared Library (alle Skripte laden diese)
  atlas.ps1                   Zentraler Orchestrator (Entry-Point)

  -- Einzelskripte (je eine Aufgabe) --
  01_cleanup_branches.ps1     Feature-Branches loeschen
  02_reset_branches.ps1       beta + dev auf main zuruecksetzen
  03_create_pr.ps1            Pull Request erstellen
  04_wait_for_checks.ps1      CI-Checks pollen
  05_merge_pr.ps1             PR mergen (squash)
  06_build_installer.ps1      PyInstaller + Inno Setup Build
  07_upload_release.ps1       Upload + Gate-Validierung + Aktivierung
  08_deprecate_releases.ps1   Alte Releases auf deprecated setzen
  09_version_bump.ps1         Idempotente Versionierung (SemVer)
  10_git_tag.ps1              Git-Tags erstellen (stable/beta)
  11_rollback.ps1             Git- oder API-Rollback
  12_verify_env.ps1           Umgebungs-Pruefung (Tools, Auth, Repo)
  13_healthcheck.ps1          System-Healthcheck (Git, API, Latenz, Endpoints)
  14_changelog_from_pr.ps1    Release Notes aus PR-History

  -- Flow-Orchestratoren --
  flow_beta_release.ps1       dev -> beta: Bump, PR, CI, Merge, Tag, Build, Upload
  flow_stable_release.ps1     beta -> main: PR, CI, Merge, Tag, Build, Upload, Deprecate
  flow_full_governance.ps1    Cleanup + Reset + Beta-Flow + Stable-Flow

  -- Temporaere Dateien (in .gitignore) --
  .last_pr                    Letzte PR-Nummer (Uebergabe zwischen Skripten)
  .last_build                 Build-Info JSON (Pfad, Version, Hash)
  .last_release_id            Letzte Release-ID (fuer Deprecation-Ausschluss)
  .governance_state.json      Letzter Governance-Lauf (Action, Exitcode, Dauer)
  .governance.lock            Lock-Datei (Parallel-Schutz)
  .gate_reports/              Gate-Validierungsergebnisse (archiviert)
```

---

## 3. Shared Library (`_lib.ps1`)

Wird per Dot-Sourcing in jedes Skript geladen: `. "$PSScriptRoot\_lib.ps1"`

### Bereitgestellte Funktionen

| Funktion | Zweck |
|----------|-------|
| `Write-Step`, `Write-Ok`, `Write-Err`, `Write-Warn`, `Write-Info` | Logging (Human + JSON-Modus) |
| `Set-GovernanceMode -DryRun -Json` | Modus-Steuerung |
| `Test-DryRun` | DryRun-Abfrage |
| `Add-LogEntry`, `Get-GovernanceLog` | Strukturiertes Logging |
| `Write-JsonResult` | JSON-Ausgabe fuer Machine-Readability |
| `Save-GovernanceState`, `Get-GovernanceState` | State-Persistenz |
| `Save-GateReport` | Gate-Ergebnisse als JSON archivieren |
| `Enter-GovernanceLock`, `Exit-GovernanceLock` | Parallel-Schutz (PID-basiert) |
| `Confirm-Action` | Sicherheitsabfrage (optional mit Codewort) |
| `Assert-GitClean`, `Assert-OnBranch`, `Get-CurrentBranch` | Git-Hilfsfunktionen |
| `Get-AtlasVersion`, `Get-ProjectRoot` | Version + Pfade |
| `Invoke-AtlasLogin` | Interaktiver Admin-Login (JWT) |
| `Invoke-AtlasApi` | REST-API-Wrapper (GET/POST/PUT) |
| `Invoke-AtlasUpload` | Multipart-Upload (Release-Dateien) |
| `Assert-GhInstalled`, `Get-PrNumber` | GitHub-CLI-Helfer |

### Konfiguration

| Variable | Wert | Aenderbar |
|----------|------|-----------|
| `$script:API_BASE` | `https://acencia.info/api` | Nur bei Server-Wechsel |
| `$script:PROTECTED_BRANCHES` | `main, beta, dev` | Nein |

---

## 4. Einzelskripte -- Referenz

### 01_cleanup_branches.ps1

Loescht alle Remote- und lokalen Branches ausser `main`, `beta`, `dev`.

```powershell
.\01_cleanup_branches.ps1          # Mit Bestaetigung
.\01_cleanup_branches.ps1 -Force   # Ohne Bestaetigung
```

### 02_reset_branches.ps1

Hard-Reset von `beta` und `dev` auf `main`. Force-Push.

**Sicherheitsmechanismen**:
- Divergenz-Analyse VOR dem Reset (zeigt verlorene Commits)
- Erfordert Eingabe von "RESET" zur Bestaetigung
- Working Directory muss sauber sein

```powershell
.\02_reset_branches.ps1
```

### 03_create_pr.ps1

Erstellt einen GitHub Pull Request.

```powershell
.\03_create_pr.ps1 -Base beta -Head dev -Title "v3.4.1: DEV -> BETA"
```

Speichert PR-Nummer in `.last_pr`.

### 04_wait_for_checks.ps1

Pollt CI-Checks bis Abschluss, Fehler oder Timeout.

```powershell
.\04_wait_for_checks.ps1 -PRNumber 42
.\04_wait_for_checks.ps1 -PRNumber 42 -Interval 30 -Timeout 900
.\04_wait_for_checks.ps1                  # Liest .last_pr
```

**Exit-Codes**: 0 = OK, 1 = Failed/Cancelled, 2 = Timeout

**Behandelte Zustaende**: COMPLETED, SUCCESS, FAILURE, ERROR, CANCELLED, TIMED_OUT, STALE, QUEUED

### 05_merge_pr.ps1

Squash-Merge eines PRs.

```powershell
.\05_merge_pr.ps1 -PRNumber 42
.\05_merge_pr.ps1 -PRNumber 42 -Force   # Ohne Bestaetigung
```

### 06_build_installer.ps1

Baut den Installer (PyInstaller + Inno Setup). Speichert Build-Info in `.last_build`.

```powershell
.\06_build_installer.ps1
.\06_build_installer.ps1 -Version "3.4.1"
```

### 07_upload_release.ps1

Upload + 7-Gate-Validierung + Aktivierung.

```powershell
.\07_upload_release.ps1 -Token $token -Channel beta
.\07_upload_release.ps1 -Token $token -Channel stable -Mandatory
```

**Flow intern**:
1. Upload (POST /admin/releases) -> Status: `pending`
2. Validierung (POST /admin/releases/{id}/validate) -> `validated` / `blocked`
3. Aktivierung (PUT status=active)
4. Optional: Mandatory (PUT status=mandatory)

**Gate-Reports** werden automatisch unter `.gate_reports/` archiviert.

### 08_deprecate_releases.ps1

Setzt alle aktiven/mandatory Releases auf `deprecated`.

```powershell
.\08_deprecate_releases.ps1 -Token $token
.\08_deprecate_releases.ps1 -Token $token -ExcludeId 42   # Eines ausnehmen
.\08_deprecate_releases.ps1 -Token $token -Force           # Ohne Bestaetigung
```

Liest automatisch `.last_release_id` als ExcludeId, wenn nicht angegeben.

### 09_version_bump.ps1

Idempotente SemVer-Versionierung der `VERSION`-Datei.

```powershell
.\09_version_bump.ps1 -Action bump -Type patch
.\09_version_bump.ps1 -Action bump -Type minor -Commit -Push
.\09_version_bump.ps1 -Action set -Version "4.0.0"
```

### 10_git_tag.ps1

Idempotente Git-Tag-Erstellung.

```powershell
.\10_git_tag.ps1 -Channel stable           # vX.Y.Z
.\10_git_tag.ps1 -Channel beta -Push       # vX.Y.Z-beta.N (auto-increment)
```

### 11_rollback.ps1

Git-Rollback (Force-Push auf Tag/Commit) oder API-Rollback (Release zurueckziehen).

```powershell
.\11_rollback.ps1 -Mode git -Branch main -Target v3.3.0
.\11_rollback.ps1 -Mode api -Token $token -WithdrawReleaseId 42
```

### 12_verify_env.ps1

Prueft Voraussetzungen: Tools, Versionen, Git-Status, GitHub-Auth.

```powershell
.\12_verify_env.ps1
.\12_verify_env.ps1 -Json
```

### 13_healthcheck.ps1

Umfassender System-Healthcheck.

```powershell
.\13_healthcheck.ps1                       # Basis (Git, Branches, API)
.\13_healthcheck.ps1 -Token $token         # + Release-Status
.\13_healthcheck.ps1 -Json                 # JSON-Ausgabe
```

**Prueft**:
- Git Working Directory (sauber/dirty)
- Branch-Existenz und Divergenz (main/beta/dev)
- Feature-Branch-Erkennung
- Offene Pull Requests
- API-Erreichbarkeit + Latenz (10 Requests: Avg/Min/Max/P95)
- Endpoint-Diagnose (Status, Auth-Preflight, Admin-Endpoints)
- Release-Status (active/mandatory/pending/blocked)
- VERSION-Datei
- Letzter Governance-Lauf

### 14_changelog_from_pr.ps1

Generiert Release Notes aus gemergten PRs.

```powershell
.\14_changelog_from_pr.ps1 -SinceTag v3.3.0
.\14_changelog_from_pr.ps1 -SinceTag v3.3.0 -OutputFile CHANGELOG.md
```

---

## 5. Flow-Orchestratoren

### flow_beta_release.ps1 (dev -> beta)

Schritte:
1. Admin-Login (interaktiv)
2. Version bump (patch, oder `-BumpType minor/major`)
3. PR: dev -> beta
4. CI-Checks abwarten
5. PR mergen (squash)
6. Git-Tag (beta, auto-increment)
7. Build (PyInstaller + Inno Setup)
8. Upload + Gates + Aktivierung (beta, optional)

```powershell
.\flow_beta_release.ps1
.\flow_beta_release.ps1 -BumpType minor
.\flow_beta_release.ps1 -SkipBuild            # Nur Git-Flow
```

### flow_stable_release.ps1 (beta -> main)

Schritte:
1. Admin-Login
2. PR: beta -> main
3. CI-Checks abwarten
4. PR mergen (squash)
5. Git-Tag (stable)
6. Build
7. **Upload + Gates + Aktivierung (stable, MANDATORY)**
8. **Dann: Alle alten Releases deprecaten**

**WICHTIG**: Reihenfolge ist absichtlich Upload-First.
Wenn Deprecate zuerst laeuft und Upload dann fehlschlaegt,
gibt es KEIN aktives Release mehr -- alle Clients blockieren.

```powershell
.\flow_stable_release.ps1
.\flow_stable_release.ps1 -SkipBuild
```

### flow_full_governance.ps1 (alles)

Die aggressivste Operation. Erfordert Eingabe von "GOVERNANCE".

Phasen:
1. Branch Cleanup
2. Branch Reset (beta + dev = main)
3. Beta Release Flow
4. Stable Release Flow (MANDATORY)

```powershell
.\flow_full_governance.ps1
.\flow_full_governance.ps1 -SkipCleanup -SkipReset   # Nur Releases
.\flow_full_governance.ps1 -SkipBuild                  # Nur Git-Flow
```

---

## 6. Zentraler Orchestrator (`atlas.ps1`)

Entry-Point fuer alle Operationen. Unterstützt JSON-Ausgabe und Locking.

```powershell
.\atlas.ps1 -Action health
.\atlas.ps1 -Action health -Json
.\atlas.ps1 -Action cleanup -Force
.\atlas.ps1 -Action bump -BumpType minor
.\atlas.ps1 -Action pr -Base beta -Head dev -Title "DEV -> BETA"
.\atlas.ps1 -Action beta-flow -BumpType patch
.\atlas.ps1 -Action stable-flow
.\atlas.ps1 -Action full -BumpType minor
```

### Locking

Schreibende Aktionen erwerben automatisch ein Lock (`.governance.lock`).
Wenn ein anderer Governance-Prozess laeuft, wird mit Fehlermeldung abgebrochen.
Read-Only-Aktionen (`verify-env`, `health`, `status`, `changelog`, `wait-ci`) benoetigen kein Lock.

Verwaiste Lock-Dateien (Prozess existiert nicht mehr) werden automatisch bereinigt.

### State

Nach jeder Aktion speichert `atlas.ps1` den Zustand in `.governance_state.json`:
- `last_action`: Zuletzt ausgefuehrte Aktion
- `exit_code`: Ergebnis (0 = OK)
- `duration_sec`: Dauer in Sekunden
- `version`: Aktuelle VERSION
- `updated_at`: Zeitstempel

---

## 7. Sicherheitsmechanismen

| Mechanismus | Wo |
|-------------|-----|
| Codewort "RESET" | `02_reset_branches.ps1` |
| Codewort "GOVERNANCE" | `flow_full_governance.ps1` |
| Bestaetigung j/N | `05_merge_pr.ps1`, `08_deprecate_releases.ps1` |
| `-Force` Flag | Ueberspringt Bestaetigungen |
| Lock-Datei mit PID | `atlas.ps1` (automatisch) |
| Admin-Only-Check | `Invoke-AtlasLogin` (prueft `account_type=admin`) |
| Divergenz-Anzeige | `02_reset_branches.ps1` (vor Reset) |
| Upload-First-Reihenfolge | `flow_stable_release.ps1` (verhindert Release-Luecke) |
| Gate-Validierung | `07_upload_release.ps1` (7 Gates, Retry-Logik) |
| Gate-Report-Archiv | `.gate_reports/` (JSON pro Validierung) |

---

## 8. Datenfluss zwischen Skripten

```
06_build_installer.ps1  --> .last_build (JSON: installer, version, hash)
    |
    v
07_upload_release.ps1   --> .last_release_id (Release-ID)
                            .gate_reports/gate_*.json (Validierungsergebnis)
    |
    v
08_deprecate_releases.ps1  <-- liest .last_release_id als ExcludeId

03_create_pr.ps1        --> .last_pr (PR-Nummer)
    |
    v
04_wait_for_checks.ps1  <-- liest .last_pr
05_merge_pr.ps1         <-- liest .last_pr
```

---

## 9. API-Endpunkte (verwendet)

| Endpunkt | Methode | Zweck |
|----------|---------|-------|
| `/auth/login` | POST | Admin-Authentifizierung (JWT) |
| `/admin/releases` | GET | Alle Releases abrufen |
| `/admin/releases` | POST | Release hochladen (Multipart) |
| `/admin/releases/{id}` | PUT | Status aendern (active/mandatory/deprecated) |
| `/admin/releases/{id}/validate` | POST | 7-Gate-Validierung triggern |
| `/admin/releases/{id}/withdraw` | POST | Release zurueckziehen (Rollback) |
| `/updates/check?version=X&channel=Y` | GET | Update-Check (Healthcheck) |

---

## 10. Cursor-Agent-Nutzung

Die Toolchain ist vollstaendig non-interaktiv nutzbar. Alle interaktiven Blocker
(Login, Codewort-Bestaetigungen) koennen per Parameter umgangen werden.

### Schluessel-Flags fuer Agents

| Flag | Wirkung |
|------|---------|
| `-Force` | Ueberspringt ALLE Bestaetigungen (RESET-Codewort, GOVERNANCE-Codewort, j/N-Prompts) |
| `-Token <jwt>` | Uebergibt JWT direkt, ueberspringt interaktiven Login |
| `-Json` | Strukturierte JSON-Ausgabe statt farbigem Terminal-Output |

### Beispiele (Agent-kompatibel)

```powershell
# Healthcheck (kein Login noetig)
.\atlas.ps1 -Action health -Json

# Status abfragen
.\atlas.ps1 -Action status -Json

# Branch Cleanup (non-interaktiv)
.\atlas.ps1 -Action cleanup -Force

# Branch Reset (non-interaktiv)
.\atlas.ps1 -Action reset -Force

# PR erstellen + CI abwarten + mergen
.\atlas.ps1 -Action pr -Base beta -Head dev -Title "DEV -> BETA"
.\atlas.ps1 -Action wait-ci
.\atlas.ps1 -Action merge -Force

# Release hochladen (mit Token)
.\atlas.ps1 -Action upload -Token $jwt -Channel beta

# Kompletter Beta-Flow (non-interaktiv)
.\atlas.ps1 -Action beta-flow -Token $jwt -Force -SkipBuild

# Kompletter Stable-Flow (non-interaktiv)
.\atlas.ps1 -Action stable-flow -Token $jwt -Force

# Full Governance (non-interaktiv)
.\atlas.ps1 -Action full -Token $jwt -Force -BumpType minor
```

### Token beschaffen

Ein Agent kann einen JWT-Token ueber die Login-API beschaffen:

```powershell
$body = @{ username = "admin"; password = "***" } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri "https://acencia.info/api/auth/login" -Method POST -Body $body -ContentType "application/json"
$token = $resp.data.token
```

Danach kann der Token bei allen Aufrufen per `-Token $token` uebergeben werden.

### Interaktivitaets-Matrix

| Aktion | Ohne Flags | Mit `-Force -Token` |
|--------|-----------|---------------------|
| health, status, verify-env, changelog, wait-ci | Nicht-interaktiv | Nicht-interaktiv |
| cleanup | Bestaetigung (j/N) | Non-interaktiv |
| reset | Codewort "RESET" | Non-interaktiv |
| merge | Bestaetigung (j/N) | Non-interaktiv |
| upload, deprecate | Interaktiver Login | Non-interaktiv |
| beta-flow | Login + Bestaetigung | Non-interaktiv |
| stable-flow | Login + Bestaetigung | Non-interaktiv |
| full | Login + Codewort "GOVERNANCE" | Non-interaktiv |

### Typischer Agent-Workflow

1. `.\atlas.ps1 -Action health -Json` -- Systemzustand pruefen
2. `.\atlas.ps1 -Action status -Json` -- Divergenz/Branches pruefen
3. Entscheidung treffen (basierend auf JSON-Output)
4. `.\atlas.ps1 -Action beta-flow -Token $jwt -Force` -- Ausfuehren
5. `.\atlas.ps1 -Action health -Json` -- Ergebnis verifizieren

---

## 11. Hinweise fuer Agent-Entwickler

### Beim Aendern der Governance-Skripte

1. `_lib.ps1` ist die zentrale Abhaengigkeit -- Aenderungen hier betreffen ALLE Skripte
2. Temporaere Dateien (`.last_*`) sind die Schnittstelle zwischen Skripten -- Format nicht aendern
3. Die Reihenfolge Upload-vor-Deprecate in `flow_stable_release.ps1` ist ABSICHTLICH -- nicht umdrehen
4. Gate-Reports unter `.gate_reports/` dienen als Audit-Trail -- nicht loeschen

### Beim Hinzufuegen neuer Skripte

1. Shared Library laden: `. "$PSScriptRoot\_lib.ps1"`
2. Logging-Funktionen verwenden (`Write-Step`, `Write-Ok`, etc.)
3. Alle Bestaetigungen muessen per `-Force` umgehbar sein
4. Alle Logins muessen per `-Token` umgehbar sein
5. Bei schreibenden Operationen: Lock in `atlas.ps1` registrieren
6. Neue Aktion in `atlas.ps1` `ValidateSet` und `switch`-Block eintragen
7. `-Token`, `-Force`, `-Json` Parameter durchreichen
8. Temporaere Dateien in `.gitignore` aufnehmen

### Bekannte Limitierungen

- Kein Transaktionsmodell (Teilausfaelle moeglich, aber durch Upload-First-Reihenfolge entschaerft)
- Kein Resume nach Abbruch (muss manuell ab dem fehlgeschlagenen Schritt fortgesetzt werden)
- Lock ist prozessbasiert, nicht maschinenuebergreifend
- Gate-Retry ist zeitbasiert, nicht event-basiert
