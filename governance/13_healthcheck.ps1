# ============================================================================
# ATLAS Governance - Healthcheck
# ============================================================================
# Prueft den Systemzustand: Git, Branches, API-Erreichbarkeit, Releases.
#
# Verwendung:
#   .\13_healthcheck.ps1
#   .\13_healthcheck.ps1 -Token $token     # Auch Release-Status pruefen
#   .\13_healthcheck.ps1 -Json             # Strukturierte JSON-Ausgabe
# ============================================================================

param(
    [string]$Token = "",
    [switch]$Json
)

. "$PSScriptRoot\_lib.ps1"

if ($Json) { Set-GovernanceMode -Json }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ATLAS Healthcheck" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$checks = @{}
$allOk = $true

# --- 1. Git-Status ---

Write-Step "Git Working Directory..."

$gitStatus = git status --porcelain 2>&1
if ($LASTEXITCODE -eq 0 -and -not $gitStatus) {
    Write-Ok "Working Directory sauber"
    $checks["git_clean"] = @{ status = "ok" }
}
else {
    $changedFiles = @($gitStatus | Where-Object { $_ }).Count
    Write-Warn "Working Directory hat $changedFiles Aenderung(en)"
    $checks["git_clean"] = @{ status = "dirty"; files = $changedFiles }
}

# --- 2. Branch-Status ---

Write-Step "Branch-Konfiguration..."

$currentBranch = git branch --show-current 2>&1
Write-Info "Aktueller Branch: $currentBranch"
$checks["current_branch"] = @{ value = $currentBranch.Trim() }

git fetch --all --prune 2>&1 | Out-Null

foreach ($b in @("main", "beta", "dev")) {
    $exists = git branch -r --list "origin/$b" 2>&1
    if ($exists) {
        $lastCommit = git log "origin/$b" -1 --format="%h %s" 2>&1
        Write-Ok "$b : $lastCommit"
        $checks["branch_$b"] = @{ status = "ok"; last_commit = "$lastCommit" }
    }
    else {
        Write-Err "Branch '$b' existiert nicht auf Remote!"
        $checks["branch_$b"] = @{ status = "missing" }
        $allOk = $false
    }
}

# --- 3. Branch-Divergenz ---

Write-Step "Branch-Divergenz pruefen..."

$devAheadOfBeta = git rev-list --count "origin/beta..origin/dev" 2>&1
$betaAheadOfMain = git rev-list --count "origin/main..origin/beta" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Info "dev  -> beta: $devAheadOfBeta Commit(s) voraus"
    Write-Info "beta -> main: $betaAheadOfMain Commit(s) voraus"
    $checks["divergence"] = @{
        dev_ahead_of_beta  = [int]$devAheadOfBeta
        beta_ahead_of_main = [int]$betaAheadOfMain
    }
}

# --- 4. Unerwuenschte Branches ---

Write-Step "Feature-Branches pruefen..."

$extraBranches = git branch -r 2>&1 |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -notmatch "HEAD" } |
    ForEach-Object { $_ -replace "^origin/", "" } |
    Where-Object { $_ -notin @("main", "beta", "dev") }

if ($extraBranches.Count -gt 0) {
    Write-Warn "$($extraBranches.Count) Feature-Branch(es) aktiv:"
    foreach ($b in $extraBranches) { Write-Info "  - $b" }
    $checks["extra_branches"] = @{ count = $extraBranches.Count; branches = @($extraBranches) }
}
else {
    Write-Ok "Keine Feature-Branches vorhanden"
    $checks["extra_branches"] = @{ count = 0 }
}

# --- 5. Offene PRs ---

Write-Step "Offene Pull Requests..."

$openPrs = gh pr list --state open --json number,title,baseRefName,headRefName 2>&1
if ($LASTEXITCODE -eq 0) {
    $prs = $openPrs | ConvertFrom-Json
    if ($prs.Count -gt 0) {
        Write-Info "$($prs.Count) offene PR(s):"
        foreach ($pr in $prs) {
            Write-Info "  #$($pr.number): $($pr.title) ($($pr.headRefName) -> $($pr.baseRefName))"
        }
        $checks["open_prs"] = @{ count = $prs.Count }
    }
    else {
        Write-Ok "Keine offenen PRs"
        $checks["open_prs"] = @{ count = 0 }
    }
}
else {
    Write-Warn "Konnte offene PRs nicht abrufen"
    $checks["open_prs"] = @{ status = "error" }
}

# --- 6. API-Erreichbarkeit ---

Write-Step "API-Erreichbarkeit..."

try {
    $apiCheck = Invoke-RestMethod -Uri "$script:API_BASE/updates/check?version=0.0.0&channel=stable" -Method GET -TimeoutSec 10
    Write-Ok "API erreichbar ($script:API_BASE)"
    if ($apiCheck.latest_version) {
        Write-Info "Neueste Stable-Version auf Server: $($apiCheck.latest_version)"
    }
    $checks["api"] = @{ status = "ok"; latest_version = "$($apiCheck.latest_version)" }
}
catch {
    Write-Err "API nicht erreichbar: $($_.Exception.Message)"
    $checks["api"] = @{ status = "unreachable" }
    $allOk = $false
}

# --- 6b. API-Latenz-Messung (10 Pings) ---

Write-Step "API-Latenz messen (10 Requests)..."

$latencies = [System.Collections.ArrayList]::new()
$apiErrors = 0

for ($i = 1; $i -le 10; $i++) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        Invoke-WebRequest -Uri "$script:API_BASE/updates/check?version=0.0.0&channel=stable" -UseBasicParsing -TimeoutSec 10 | Out-Null
        $sw.Stop()
        $latencies.Add($sw.ElapsedMilliseconds) | Out-Null
    }
    catch {
        $sw.Stop()
        $apiErrors++
    }
}

if ($latencies.Count -gt 0) {
    $avgMs = [math]::Round(($latencies | Measure-Object -Average).Average, 0)
    $minMs = ($latencies | Measure-Object -Minimum).Minimum
    $maxMs = ($latencies | Measure-Object -Maximum).Maximum
    $p95 = ($latencies | Sort-Object)[[math]::Min([math]::Floor($latencies.Count * 0.95), $latencies.Count - 1)]

    $latencyColor = if ($avgMs -lt 300) { "Green" } elseif ($avgMs -lt 1000) { "Yellow" } else { "Red" }
    Write-Host "  Latenz: Avg ${avgMs}ms | Min ${minMs}ms | Max ${maxMs}ms | P95 ${p95}ms" -ForegroundColor $latencyColor

    if ($apiErrors -gt 0) { Write-Warn "$apiErrors von 10 Requests fehlgeschlagen" }
    if ($avgMs -gt 2000) { Write-Warn "Durchschnittliche Latenz > 2s -- Server moeglicherweise ueberlastet" }

    $checks["api_latency"] = @{
        avg_ms  = $avgMs
        min_ms  = $minMs
        max_ms  = $maxMs
        p95_ms  = $p95
        errors  = $apiErrors
        samples = $latencies.Count
    }
}
else {
    Write-Err "Alle 10 Latenz-Requests fehlgeschlagen"
    $checks["api_latency"] = @{ status = "unreachable" }
    $allOk = $false
}

# --- 6c. Endpoint-Diagnose (verschiedene API-Pfade) ---

Write-Step "Endpoint-Diagnose..."

$endpoints = @(
    @{ name = "Status/Update-Check"; path = "/updates/check?version=0.0.0&channel=stable"; auth = $false },
    @{ name = "Auth (Preflight)";    path = "/auth/login";    auth = $false; method = "OPTIONS" }
)

if ($Token -ne "") {
    $endpoints += @(
        @{ name = "Admin Releases";  path = "/admin/releases";  auth = $true },
        @{ name = "Admin Users";     path = "/admin/users";     auth = $true },
        @{ name = "Documents List";  path = "/documents";       auth = $true }
    )
}

$endpointResults = @{}

foreach ($ep in $endpoints) {
    $epSw = [System.Diagnostics.Stopwatch]::StartNew()
    $epStatus = "ok"
    $epCode = 0

    try {
        $headers = @{}
        if ($ep.auth -and $Token) { $headers["Authorization"] = "Bearer $Token" }
        $method = if ($ep.method) { $ep.method } else { "GET" }

        $resp = Invoke-WebRequest -Uri "$script:API_BASE$($ep.path)" -Method $method -Headers $headers -UseBasicParsing -TimeoutSec 15
        $epCode = $resp.StatusCode
        $epSw.Stop()
    }
    catch {
        $epSw.Stop()
        if ($_.Exception.Response) {
            $epCode = [int]$_.Exception.Response.StatusCode
            $epStatus = "http_error"
        }
        else {
            $epStatus = "unreachable"
        }
    }

    $epMs = $epSw.ElapsedMilliseconds
    $epColor = if ($epStatus -eq "ok") { "Green" } elseif ($epStatus -eq "http_error" -and $epCode -lt 500) { "Yellow" } else { "Red" }
    Write-Host "  $($ep.name): HTTP $epCode (${epMs}ms)" -ForegroundColor $epColor

    if ($epStatus -ne "ok" -and $epCode -ge 500) { $allOk = $false }

    $endpointResults[$ep.name] = @{ status_code = $epCode; latency_ms = $epMs; status = $epStatus }
}

$checks["endpoints"] = $endpointResults

# --- 7. Release-Status (nur mit Token) ---

if ($Token -ne "") {
    Write-Step "Release-Status pruefen..."

    $releases = Invoke-AtlasApi -Endpoint "/admin/releases" -Method GET -Token $Token

    if ($releases) {
        $releaseData = if ($releases.data) { $releases.data } else { $releases }
        $active = @($releaseData | Where-Object { $_.status -eq "active" })
        $mandatory = @($releaseData | Where-Object { $_.status -eq "mandatory" })
        $pending = @($releaseData | Where-Object { $_.status -eq "pending" })
        $blocked = @($releaseData | Where-Object { $_.status -eq "blocked" })

        Write-Info "Releases: $($active.Count) active, $($mandatory.Count) mandatory, $($pending.Count) pending, $($blocked.Count) blocked"

        if ($blocked.Count -gt 0) {
            Write-Warn "$($blocked.Count) Release(s) sind BLOCKED (Gate-Validierung fehlgeschlagen)"
        }

        $checks["releases"] = @{
            active    = $active.Count
            mandatory = $mandatory.Count
            pending   = $pending.Count
            blocked   = $blocked.Count
        }
    }
    else {
        Write-Warn "Konnte Releases nicht abrufen"
        $checks["releases"] = @{ status = "error" }
    }
}

# --- 8. VERSION ---

Write-Step "VERSION..."

$version = Get-AtlasVersion
Write-Ok "VERSION: $version"
$checks["version"] = @{ value = $version }

# --- 9. Letzter Governance-State ---

$state = Get-GovernanceState
if ($state) {
    Write-Step "Letzter Governance-Lauf..."
    Write-Info "Letzte Aktion: $($state.last_action) ($($state.updated_at))"
    $checks["last_governance"] = @{
        action     = "$($state.last_action)"
        updated_at = "$($state.updated_at)"
    }
}

# --- Ergebnis ---

Write-Host ""
if ($allOk) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Healthcheck: SYSTEM OK" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
else {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host " Healthcheck: WARNUNG(EN) vorhanden" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
}

Write-JsonResult -Action "healthcheck" -Success $allOk -Data $checks

if (-not $allOk) { exit 1 }
