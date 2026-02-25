# ============================================================================
# ATLAS Governance - CI-Checks abwarten
# ============================================================================
# Pollt die GitHub CI-Checks eines PRs bis alle abgeschlossen sind.
#
# Verwendung:
#   .\04_wait_for_checks.ps1 -PRNumber 42
#   .\04_wait_for_checks.ps1 -PRNumber 42 -Interval 30 -Timeout 900
#
# Exit-Codes:
#   0 = Alle Checks bestanden
#   1 = Mindestens ein Check fehlgeschlagen
#   2 = Timeout erreicht
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$PRNumber = "",

    [int]$Interval = 15,

    [int]$Timeout = 600
)

. "$PSScriptRoot\_lib.ps1"

Assert-GhInstalled

if ($PRNumber -eq "") {
    $lastPrFile = Join-Path $PSScriptRoot ".last_pr"
    if (Test-Path $lastPrFile) {
        $PRNumber = (Get-Content $lastPrFile -Raw).Trim()
    }
    if ($PRNumber -eq "") {
        Write-Err "Keine PR-Nummer angegeben und keine .last_pr Datei gefunden."
        Write-Info "Verwendung: .\04_wait_for_checks.ps1 -PRNumber <nummer>"
        exit 1
    }
    Write-Info "PR-Nummer aus .last_pr gelesen: $PRNumber"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS CI-Checks: PR #$PRNumber" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Step "Warte auf CI-Checks (Interval: ${Interval}s, Timeout: ${Timeout}s)..."

$elapsed = 0
$lastStatus = ""

while ($true) {
    $checksJson = gh pr checks $PRNumber --json "name,state,conclusion" 2>&1

    if ($LASTEXITCODE -ne 0) {
        if ($elapsed -eq 0) {
            Write-Warn "Noch keine Checks gestartet. Warte..."
        }
    }
    else {
        $checks = $checksJson | ConvertFrom-Json

        if ($checks.Count -eq 0) {
            Write-Info "Keine CI-Checks konfiguriert fuer diesen PR."
            Write-Ok "Keine Checks zu pruefen - fortfahren."
            exit 0
        }

        $terminalStates = @("COMPLETED", "SUCCESS", "FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "STALE")
        $failConclusions = @("FAILURE", "failure", "TIMED_OUT", "timed_out")
        $cancelConclusions = @("CANCELLED", "cancelled", "STALE", "stale")

        $completed = @($checks | Where-Object { $_.state -in $terminalStates -and $_.conclusion -notin ($failConclusions + $cancelConclusions) })
        $pending = @($checks | Where-Object { $_.state -notin $terminalStates })
        $failed = @($checks | Where-Object { $_.conclusion -in $failConclusions -or $_.state -in @("FAILURE", "ERROR") })
        $cancelled = @($checks | Where-Object { $_.conclusion -in $cancelConclusions -or $_.state -in @("CANCELLED", "STALE") })

        $statusLine = "  Checks: $($completed.Count) ok, $($pending.Count) laufend, $($failed.Count) fehlgeschlagen, $($cancelled.Count) abgebrochen ($($elapsed)s)"

        if ($statusLine -ne $lastStatus) {
            Write-Host $statusLine -ForegroundColor Gray
            $lastStatus = $statusLine
        }

        if ($failed.Count -gt 0) {
            Write-Host ""
            Write-Err "CI-Checks FEHLGESCHLAGEN:"
            foreach ($f in $failed) {
                Write-Host "    X $($f.name): $($f.conclusion)" -ForegroundColor Red
            }
            foreach ($c in $completed) {
                Write-Host "    + $($c.name): $($c.conclusion)" -ForegroundColor Green
            }
            exit 1
        }

        if ($cancelled.Count -gt 0 -and $pending.Count -eq 0) {
            Write-Host ""
            Write-Err "CI-Checks ABGEBROCHEN:"
            foreach ($c in $cancelled) {
                Write-Host "    ~ $($c.name): $($c.conclusion)" -ForegroundColor Yellow
            }
            exit 1
        }

        if ($pending.Count -eq 0 -and $completed.Count -gt 0) {
            Write-Host ""
            Write-Ok "Alle CI-Checks bestanden:"
            foreach ($c in $completed) {
                Write-Host "    + $($c.name): $($c.conclusion)" -ForegroundColor Green
            }
            exit 0
        }
    }

    if ($elapsed -ge $Timeout) {
        Write-Host ""
        Write-Err "Timeout nach ${Timeout}s erreicht. Checks noch nicht abgeschlossen."
        if ($checks) {
            foreach ($p in $pending) {
                Write-Host "    ? $($p.name): $($p.state)" -ForegroundColor Yellow
            }
        }
        exit 2
    }

    Start-Sleep -Seconds $Interval
    $elapsed += $Interval
}
