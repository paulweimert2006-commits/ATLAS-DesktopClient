# ============================================================================
# ATLAS Governance - Shared Library
# ============================================================================
# Wird per Dot-Sourcing in alle Governance-Skripte eingebunden:
#   . "$PSScriptRoot\_lib.ps1"
# ============================================================================

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:API_BASE = "https://acencia.info/api"
$script:PROTECTED_BRANCHES = @("main", "beta", "dev")
$script:stepNum = 1
$script:DryRun = $false
$script:JsonMode = $false
$script:StateFile = Join-Path $PSScriptRoot ".governance_state.json"
$script:LogEntries = [System.Collections.ArrayList]::new()

# ---------------------------------------------------------------------------
# Modus-Steuerung (DryRun / JSON)
# ---------------------------------------------------------------------------

function Set-GovernanceMode {
    param(
        [switch]$DryRun,
        [switch]$Json
    )
    $script:DryRun = $DryRun.IsPresent
    $script:JsonMode = $Json.IsPresent
}

function Test-DryRun { return $script:DryRun }

# ---------------------------------------------------------------------------
# Logging (Human + JSON)
# ---------------------------------------------------------------------------

function Write-Step {
    param([string]$msg)
    $script:stepNum++
    Add-LogEntry "STEP" $msg
    if (-not $script:JsonMode) {
        Write-Host "`n[$script:stepNum] $msg" -ForegroundColor Cyan
    }
}

function Write-Ok {
    param([string]$msg)
    Add-LogEntry "OK" $msg
    if (-not $script:JsonMode) {
        Write-Host "  OK - $msg" -ForegroundColor Green
    }
}

function Write-Err {
    param([string]$msg)
    Add-LogEntry "ERROR" $msg
    if (-not $script:JsonMode) {
        Write-Host "  FEHLER: $msg" -ForegroundColor Red
    }
}

function Write-Warn {
    param([string]$msg)
    Add-LogEntry "WARN" $msg
    if (-not $script:JsonMode) {
        Write-Host "  WARNUNG: $msg" -ForegroundColor Yellow
    }
}

function Write-Info {
    param([string]$msg)
    Add-LogEntry "INFO" $msg
    if (-not $script:JsonMode) {
        Write-Host "  $msg" -ForegroundColor Gray
    }
}

function Add-LogEntry {
    param([string]$Level, [string]$Message)
    $entry = @{
        timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        level     = $Level
        message   = $Message
    }
    $script:LogEntries.Add($entry) | Out-Null
}

function Get-GovernanceLog {
    return $script:LogEntries
}

function Write-JsonResult {
    param(
        [string]$Action,
        [bool]$Success,
        [hashtable]$Data = @{}
    )
    if ($script:JsonMode) {
        $result = @{
            action    = $Action
            success   = $Success
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
            data      = $Data
            log       = @($script:LogEntries)
        }
        $result | ConvertTo-Json -Depth 10
    }
}

# ---------------------------------------------------------------------------
# State-Management
# ---------------------------------------------------------------------------

function Save-GovernanceState {
    param([hashtable]$State)
    $State["updated_at"] = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    $State | ConvertTo-Json -Depth 5 | Set-Content $script:StateFile -Encoding UTF8
}

function Get-GovernanceState {
    if (Test-Path $script:StateFile) {
        return (Get-Content $script:StateFile -Raw | ConvertFrom-Json)
    }
    return $null
}

# ---------------------------------------------------------------------------
# Gate-Report Persistenz
# ---------------------------------------------------------------------------

function Save-GateReport {
    param(
        [object]$Report,
        [string]$Version,
        [string]$Channel,
        [bool]$Passed
    )

    $reportDir = Join-Path $PSScriptRoot ".gate_reports"
    if (-not (Test-Path $reportDir)) {
        New-Item -Path $reportDir -ItemType Directory -Force | Out-Null
    }

    $ts = Get-Date -Format "yyyyMMdd_HHmmss"
    $fileName = "gate_${Channel}_${Version}_${ts}.json"
    $filePath = Join-Path $reportDir $fileName

    $entry = @{
        version    = $Version
        channel    = $Channel
        passed     = $Passed
        timestamp  = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        report     = $Report
    }

    $entry | ConvertTo-Json -Depth 10 | Set-Content $filePath -Encoding UTF8
    Write-Info "Gate-Report gespeichert: $fileName"
}

# ---------------------------------------------------------------------------
# Locking (Parallel-Schutz)
# ---------------------------------------------------------------------------

$script:LockFile = Join-Path $PSScriptRoot ".governance.lock"

function Enter-GovernanceLock {
    param([string]$Action = "unknown")

    if (Test-Path $script:LockFile) {
        $lockContent = Get-Content $script:LockFile -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($lockContent) {
            $lockPid = $lockContent.pid
            $lockAction = $lockContent.action
            $lockTime = $lockContent.started_at

            $processRunning = $false
            try { $processRunning = [bool](Get-Process -Id $lockPid -ErrorAction SilentlyContinue) } catch {}

            if ($processRunning) {
                Write-Err "Governance ist bereits aktiv!"
                Write-Info "  Aktion:  $lockAction"
                Write-Info "  PID:     $lockPid"
                Write-Info "  Seit:    $lockTime"
                Write-Info "  Lock:    $($script:LockFile)"
                Write-Info ""
                Write-Info "  Falls der Prozess haengt: Datei manuell loeschen"
                exit 1
            }
            else {
                Write-Warn "Verwaiste Lock-Datei gefunden (PID $lockPid existiert nicht mehr). Entferne..."
                Remove-Item $script:LockFile -Force
            }
        }
    }

    @{
        pid        = $PID
        action     = $Action
        started_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    } | ConvertTo-Json | Set-Content $script:LockFile -Encoding UTF8
}

function Exit-GovernanceLock {
    if (Test-Path $script:LockFile) {
        Remove-Item $script:LockFile -Force -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------------------
# Sicherheitsabfrage
# ---------------------------------------------------------------------------

function Confirm-Action {
    param(
        [string]$Message,
        [string]$RequiredInput = ""
    )

    Write-Host ""
    Write-Host "  $Message" -ForegroundColor Yellow

    if ($RequiredInput -ne "") {
        Write-Host "  Tippe '$RequiredInput' zum Bestaetigen:" -ForegroundColor Yellow
        $input = Read-Host "  "
        if ($input -ne $RequiredInput) {
            Write-Host "  Abgebrochen." -ForegroundColor Red
            return $false
        }
    }
    else {
        $confirm = Read-Host "  Fortfahren? [j/N]"
        if ($confirm -notin @("j", "J", "y", "Y")) {
            Write-Host "  Abgebrochen." -ForegroundColor Red
            return $false
        }
    }
    return $true
}

# ---------------------------------------------------------------------------
# Git-Hilfsfunktionen
# ---------------------------------------------------------------------------

function Assert-GitClean {
    $status = git status --porcelain 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "git status fehlgeschlagen"
        exit 1
    }
    if ($status) {
        Write-Err "Working Directory ist nicht sauber. Bitte erst committen oder stashen."
        Write-Info "Aenderungen:"
        git status --short
        exit 1
    }
}

function Assert-OnBranch {
    param([string]$ExpectedBranch)

    $current = git branch --show-current 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Konnte aktuellen Branch nicht ermitteln"
        exit 1
    }
    if ($current.Trim() -ne $ExpectedBranch) {
        Write-Err "Erwartet Branch '$ExpectedBranch', aber auf '$($current.Trim())'"
        exit 1
    }
}

function Get-CurrentBranch {
    $branch = git branch --show-current 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Konnte aktuellen Branch nicht ermitteln"
        exit 1
    }
    return $branch.Trim()
}

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

function Get-AtlasVersion {
    $versionFile = Join-Path (Get-ProjectRoot) "VERSION"
    if (-not (Test-Path $versionFile)) {
        Write-Err "VERSION-Datei nicht gefunden: $versionFile"
        exit 1
    }
    return (Get-Content $versionFile -Raw).Trim()
}

function Get-ProjectRoot {
    $root = git rev-parse --show-toplevel 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Nicht in einem Git-Repository"
        exit 1
    }
    return $root.Trim()
}

# ---------------------------------------------------------------------------
# API-Authentifizierung (interaktiv)
# ---------------------------------------------------------------------------

function Invoke-AtlasLogin {
    Write-Host ""
    Write-Host "  === ATLAS Admin Login ===" -ForegroundColor Cyan

    $username = Read-Host "  Benutzername"
    $securePassword = Read-Host "  Passwort" -AsSecureString

    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

    try {
        $loginBody = @{
            username = $username
            password = $plainPassword
        } | ConvertTo-Json -Compress

        $response = Invoke-RestMethod `
            -Uri "$script:API_BASE/auth/login" `
            -Method POST `
            -Body $loginBody `
            -ContentType "application/json; charset=utf-8"

        if (-not $response.success) {
            Write-Err "Login fehlgeschlagen: $($response.message)"
            exit 1
        }

        $token = $response.data.token
        $user = $response.data.user

        if ($user.account_type -ne "admin") {
            Write-Err "Nur Administratoren koennen Governance-Operationen ausfuehren!"
            exit 1
        }

        Write-Ok "Angemeldet als '$($user.username)' (Admin)"
        return $token
    }
    catch {
        Write-Err "Login fehlgeschlagen: $($_.Exception.Message)"
        exit 1
    }
    finally {
        $plainPassword = $null
    }
}

# ---------------------------------------------------------------------------
# API-Wrapper
# ---------------------------------------------------------------------------

function Invoke-AtlasApi {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [string]$Token,
        [object]$Body = $null,
        [string]$ContentType = "application/json; charset=utf-8"
    )

    $headers = @{}
    if ($Token) {
        $headers["Authorization"] = "Bearer $Token"
    }

    $params = @{
        Uri         = "$script:API_BASE$Endpoint"
        Method      = $Method
        Headers     = $headers
        ContentType = $ContentType
    }

    if ($Body -and $Method -ne "GET") {
        if ($Body -is [string]) {
            $params["Body"] = $Body
        }
        else {
            $params["Body"] = ($Body | ConvertTo-Json -Compress -Depth 10)
        }
    }

    try {
        $response = Invoke-RestMethod @params
        return $response
    }
    catch {
        $statusCode = $null
        $errorMsg = $_.Exception.Message

        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $errorBody = $reader.ReadToEnd() | ConvertFrom-Json
                if ($errorBody.message) { $errorMsg = $errorBody.message }
            }
            catch {}
        }

        Write-Err "API-Fehler ($Method $Endpoint): $errorMsg"
        if ($statusCode) { Write-Info "HTTP Status: $statusCode" }
        return $null
    }
}

# ---------------------------------------------------------------------------
# Multipart-Upload (fuer Release-Dateien)
# ---------------------------------------------------------------------------

function Invoke-AtlasUpload {
    param(
        [string]$Endpoint,
        [string]$Token,
        [hashtable]$FormFields,
        [string]$FilePath,
        [string]$FileFieldName = "file"
    )

    Add-Type -AssemblyName System.Net.Http

    $httpClient = New-Object System.Net.Http.HttpClient
    $httpClient.Timeout = [System.TimeSpan]::FromSeconds(600)
    $httpClient.DefaultRequestHeaders.Add("Authorization", "Bearer $Token")

    $multipart = New-Object System.Net.Http.MultipartFormDataContent

    foreach ($key in $FormFields.Keys) {
        $multipart.Add(
            [System.Net.Http.StringContent]::new($FormFields[$key], [System.Text.Encoding]::UTF8),
            $key
        )
    }

    $fileStream = [System.IO.File]::OpenRead($FilePath)
    $fileContent = New-Object System.Net.Http.StreamContent($fileStream)
    $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new("application/octet-stream")
    $fileName = [System.IO.Path]::GetFileName($FilePath)
    $multipart.Add($fileContent, $FileFieldName, $fileName)

    try {
        $response = $httpClient.PostAsync("$script:API_BASE$Endpoint", $multipart).GetAwaiter().GetResult()
        $responseBody = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()

        if ($response.IsSuccessStatusCode) {
            return ($responseBody | ConvertFrom-Json)
        }
        else {
            Write-Err "Upload fehlgeschlagen: HTTP $([int]$response.StatusCode)"
            try {
                $errJson = $responseBody | ConvertFrom-Json
                if ($errJson.message) { Write-Err "Server: $($errJson.message)" }
            }
            catch {
                if ($responseBody.Length -lt 500) { Write-Info "Response: $responseBody" }
            }
            return $null
        }
    }
    finally {
        $fileStream.Dispose()
        $multipart.Dispose()
        $httpClient.Dispose()
    }
}

# ---------------------------------------------------------------------------
# GitHub CLI Hilfsfunktionen
# ---------------------------------------------------------------------------

function Assert-GhInstalled {
    $ghPath = Get-Command gh -ErrorAction SilentlyContinue
    if (-not $ghPath) {
        Write-Err "GitHub CLI (gh) ist nicht installiert oder nicht im PATH."
        Write-Info "Installation: https://cli.github.com/"
        exit 1
    }
}

function Get-PrNumber {
    param([string]$PrUrl)
    if ($PrUrl -match '/pull/(\d+)') {
        return $Matches[1]
    }
    if ($PrUrl -match '(\d+)$') {
        return $Matches[1]
    }
    Write-Err "Konnte PR-Nummer nicht aus URL extrahieren: $PrUrl"
    exit 1
}
