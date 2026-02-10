# 03 — Technische Designs

5 wiederverwendbare Bausteine fuer die Security-Massnahmen.

---

## Baustein B1: Security-Headers-Middleware

**Loest:** SV-002 (Kritisch — Fehlende Security Headers)

### Kontext

Die PHP-API auf Strato antwortet aktuell ohne jegliche Security-Headers. Dieser Baustein fuegt eine zentrale Funktion ein, die bei jedem API-Request alle relevanten Headers setzt.

### Design

**Neue Funktion in `api/lib/response.php`:**

```php
/**
 * Sendet Security Headers fuer alle API-Responses.
 * Muss am Anfang von index.php aufgerufen werden.
 */
function send_security_headers(): void {
    // HSTS: Browser soll nur HTTPS nutzen (1 Jahr)
    header('Strict-Transport-Security: max-age=31536000; includeSubDomains');

    // Verhindert MIME-Type-Sniffing
    header('X-Content-Type-Options: nosniff');

    // Verhindert Einbetten in Frames (Clickjacking)
    header('X-Frame-Options: DENY');

    // Moderner XSS-Schutz: Abschalten des veralteten Browser-Filters
    // (CSP ist der richtige Schutz)
    header('X-XSS-Protection: 0');

    // Referrer nur bei Same-Origin vollstaendig senden
    header('Referrer-Policy: strict-origin-when-cross-origin');

    // CSP fuer API: Nichts laden, keine Frames
    header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'");

    // Feature-Policy: Keine Browser-Features erlauben
    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
}
```

**Einbindung in `api/index.php`:**

```php
// Zeile ~18 (nach CORS, vor Routing)
send_security_headers();
```

### Reihenfolge der Header

1. `send_security_headers()` setzt die Default-Headers
2. Spaetere `json_response()` setzt `Content-Type: application/json` (ueberschreibt nicht die Security-Headers)
3. Download-Endpoints setzen `Content-Disposition` zusaetzlich

### Kompatibilitaet

| Client | Auswirkung |
|--------|-----------|
| Desktop-App (requests) | Keine. Python `requests` ignoriert Browser-Security-Headers |
| Power Automate (Scan-Upload) | Keine. HTTP-Client ignoriert Browser-Headers |
| Browser (falls direkt auf API) | Clickjacking/MIME-Sniffing verhindert |

### Edge Cases

- **CORS Pre-flight (OPTIONS):** Headers werden auch bei OPTIONS gesetzt — kein Problem, da Pre-flight vor dem `exit()` in Zeile 16 beendet wird. Loesung: `send_security_headers()` vor dem OPTIONS-Block platzieren.
- **Download-Endpoints:** `Content-Disposition: attachment` ist kompatibel mit CSP `default-src 'none'`
- **Strato Shared Hosting:** `header()` Funktion ist universell verfuegbar, keine Einschraenkungen

---

## Baustein B2: Rate-Limiter (PHP, DB-basiert)

**Loest:** SV-003 (Kritisch — Kein Rate-Limiting auf Login)

### Kontext

Strato Shared Hosting hat kein `mod_ratelimit`. Rate-Limiting muss in PHP mit DB-Backend implementiert werden. Die `activity_log` Tabelle existiert bereits und loggt fehlgeschlagene Logins.

### Design

**Neue Datei `api/lib/rate_limiter.php`:**

```php
class RateLimiter {
    // Konfigurierbare Schwellwerte
    private const MAX_ATTEMPTS = 5;       // Max. Versuche
    private const WINDOW_SECONDS = 900;   // 15 Minuten Fenster
    private const LOCKOUT_SECONDS = 900;  // 15 Minuten Sperre

    /**
     * Prueft ob eine IP/Username-Kombination gesperrt ist.
     *
     * @return bool true wenn Zugriff erlaubt, false wenn gesperrt
     */
    public static function check(string $ip, string $username = ''): bool {
        self::cleanup();  // Abgelaufene Eintraege entfernen

        // Zaehle fehlgeschlagene Versuche im Zeitfenster
        $since = date('Y-m-d H:i:s', time() - self::WINDOW_SECONDS);

        $count = Database::queryOne(
            'SELECT COUNT(*) as cnt FROM rate_limits
             WHERE ip_address = ? AND attempted_at > ?',
            [$ip, $since]
        );

        return ((int)($count['cnt'] ?? 0)) < self::MAX_ATTEMPTS;
    }

    /**
     * Registriert einen fehlgeschlagenen Versuch.
     */
    public static function recordFailure(string $ip, string $username = ''): void {
        Database::execute(
            'INSERT INTO rate_limits (ip_address, username, attempted_at)
             VALUES (?, ?, NOW())',
            [$ip, $username]
        );
    }

    /**
     * Setzt Rate-Limit fuer eine IP zurueck (nach erfolgreichem Login).
     */
    public static function reset(string $ip): void {
        Database::execute(
            'DELETE FROM rate_limits WHERE ip_address = ?',
            [$ip]
        );
    }

    /**
     * Entfernt abgelaufene Eintraege.
     */
    private static function cleanup(): void {
        $cutoff = date('Y-m-d H:i:s', time() - self::WINDOW_SECONDS);
        Database::execute(
            'DELETE FROM rate_limits WHERE attempted_at < ?',
            [$cutoff]
        );
    }

    /**
     * Gibt die verbleibende Lockout-Zeit in Sekunden zurueck.
     */
    public static function getLockoutRemaining(string $ip): int {
        $since = date('Y-m-d H:i:s', time() - self::WINDOW_SECONDS);
        $oldest = Database::queryOne(
            'SELECT MIN(attempted_at) as first_attempt FROM rate_limits
             WHERE ip_address = ? AND attempted_at > ?',
            [$ip, $since]
        );

        if (!$oldest || !$oldest['first_attempt']) {
            return 0;
        }

        $firstAttempt = strtotime($oldest['first_attempt']);
        $lockoutEnd = $firstAttempt + self::LOCKOUT_SECONDS;
        $remaining = $lockoutEnd - time();

        return max(0, $remaining);
    }
}
```

**DB-Tabelle (Migration):**

```sql
CREATE TABLE IF NOT EXISTS rate_limits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    username VARCHAR(100) DEFAULT '',
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ip_time (ip_address, attempted_at),
    INDEX idx_cleanup (attempted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**Einbindung in `auth.php` handleLogin():**

```php
// Am Anfang von handleLogin(), vor DB-Query:
require_once __DIR__ . '/lib/rate_limiter.php';

$clientIp = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
if (!RateLimiter::check($clientIp, $username)) {
    $remaining = RateLimiter::getLockoutRemaining($clientIp);
    header('Retry-After: ' . $remaining);
    json_error('Zu viele fehlgeschlagene Anmeldeversuche. Bitte warten.', 429);
}

// ... bestehende Login-Logik ...

// Bei fehlgeschlagenem Login (nach Password-Check):
RateLimiter::recordFailure($clientIp, $username);

// Bei erfolgreichem Login:
RateLimiter::reset($clientIp);
```

### Skalierung

| Szenario | Verhalten |
|----------|----------|
| Normaler User, 1-2 Fehlversuche | Kein Effekt |
| Brute-Force: 6+ Versuche in 15 Min | IP gesperrt, HTTP 429 |
| NAT/Shared-IP: Mehrere User hinter einer IP | Username-Differenzierung moeglich (Erweiterung) |
| Cleanup: Tabelle wuechst | Alte Eintraege werden bei jedem Check geloescht |

### Kompatibilitaet

- Desktop-App: Muss HTTP 429 als Fehlermeldung anzeigen (Toast mit "Bitte warten")
- `src/api/auth.py`: `login()` Methode muss 429 erkennen und benutzerfreundliche Meldung zeigen

---

## Baustein B3: OpenRouter-Proxy

**Loest:** SV-004 (Kritisch — API-Key exponiert), SV-013 (Mittel — PII an OpenRouter)

### Kontext

Aktuell holt der Desktop-Client den OpenRouter-API-Key vom Server (`GET /ai/key`) und ruft OpenRouter direkt auf. Durch einen Server-seitigen Proxy bleibt der Key auf dem Server und PII-Redaktion kann zentral eingefuegt werden.

### Design

**Neuer PHP-Endpoint `POST /ai/classify` in `api/ai.php`:**

```php
/**
 * POST /ai/classify
 * Body: { "text": "...", "mode": "triage|detail", "model": "..." }
 *
 * Server ruft OpenRouter auf und gibt Klassifikation zurueck.
 */
function handleClassify(array $payload): void {
    requirePermission($payload, 'documents_process');

    $data = get_json_body();
    require_fields($data, ['text', 'mode']);

    $text = $data['text'];
    $mode = $data['mode']; // 'triage' oder 'detail'

    // PII-Redaktion (M-013)
    $text = redact_pii($text);

    // Model-Auswahl
    $model = ($mode === 'detail')
        ? 'openai/gpt-4o'
        : 'openai/gpt-4o-mini';

    // System-Prompt (Server-seitig, nicht vom Client)
    $systemPrompt = getClassificationPrompt($mode);

    // OpenRouter-Call via cURL
    $result = callOpenRouter($model, $systemPrompt, $text);

    json_success(['classification' => $result]);
}

/**
 * PII-Redaktion: E-Mails, Telefon, IBAN, VS-Nr entfernen.
 */
function redact_pii(string $text): string {
    // E-Mail-Adressen
    $text = preg_replace('/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/', '[EMAIL]', $text);

    // Telefonnummern (DE-Format)
    $text = preg_replace('/(\+49|0)\s*[\d\s\-\/]{6,15}/', '[PHONE]', $text);

    // IBAN
    $text = preg_replace('/[A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{0,2}/', '[IBAN]', $text);

    return $text;
}

/**
 * cURL-Aufruf an OpenRouter API.
 */
function callOpenRouter(string $model, string $systemPrompt, string $text): array {
    $apiKey = OPENROUTER_API_KEY;

    $payload = json_encode([
        'model' => $model,
        'messages' => [
            ['role' => 'system', 'content' => $systemPrompt],
            ['role' => 'user', 'content' => $text]
        ],
        'temperature' => 0.1,
        'max_tokens' => 200
    ]);

    $ch = curl_init('https://openrouter.ai/api/v1/chat/completions');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $apiKey,
            'HTTP-Referer: https://acencia.info',
            'X-Title: ACENCIA ATLAS'
        ]
    ]);

    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($httpCode !== 200) {
        json_error('KI-Klassifikation fehlgeschlagen', 502);
    }

    $result = json_decode($response, true);
    $content = $result['choices'][0]['message']['content'] ?? '';

    return json_decode($content, true) ?: ['error' => 'Ungueltige KI-Antwort'];
}
```

**Route in `index.php`:**

```php
case 'ai':
    require_once __DIR__ . '/ai.php';
    if ($action === 'classify' && $method === 'POST') {
        $payload = JWT::requireAuth();
        handleClassify($payload);
    }
    // GET /ai/key entfernen:
    json_error('Endpoint entfernt', 410);
    break;
```

**Python-Client-Aenderungen (`src/api/openrouter.py`):**

```python
# Statt direkter OpenRouter-Aufruf:
def _classify_via_proxy(self, text: str, mode: str) -> dict:
    """Klassifikation ueber Server-Proxy."""
    response = self.api_client.post('/ai/classify', json={
        'text': text,
        'mode': mode
    })
    return response.get('classification', {})
```

### Datenfluss (Vorher vs. Nachher)

```
VORHER:
Client → GET /ai/key → API-Key
Client → OpenRouter API (mit Key + PII-Text)

NACHHER:
Client → POST /ai/classify (Text, Mode) → Server
Server → PII-Redaktion → OpenRouter API (mit Key, ohne PII)
Server → Klassifikation → Client
```

### Performance

| Aspekt | Vorher | Nachher |
|--------|--------|---------|
| Latenz pro Call | ~500ms (direkt) | ~600-700ms (+Server-Hop) |
| PHP max_execution_time | Nicht relevant | 30s Default, ausreichend |
| Parallel-Calls | Unbegrenzt (Client) | Durch PHP-Worker begrenzt |

### Fallback

Wenn der Proxy-Endpoint nicht erreichbar ist (Server-Ausfall):
- KI-Klassifikation schlaegt fehl
- Dokumente bleiben in "eingang" mit `processing_status='pending'`
- Erneute Verarbeitung nach Server-Recovery moeglich

---

## Baustein B4: Temp-File-Guard (Python)

**Loest:** SV-008 (Hoch — PEM-Temp-Files), SV-024 (Niedrig — PDF-Temp-Leak)

### Kontext

An mehreren Stellen werden temporaere Dateien mit sensiblen Inhalten (Private Keys, entschluesselte PDFs) erstellt. Der Cleanup ist nicht in allen Fehlerpfaden garantiert.

### Design

**Pattern 1: atexit-basiertes Tracking fuer langlebige Temp-Files (PEM)**

```python
import atexit
import os
import threading

class TempFileTracker:
    """Tracking und automatisches Cleanup von temporaeren Dateien."""

    _files: list = []
    _lock = threading.Lock()

    @classmethod
    def register(cls, path: str) -> str:
        """Registriert eine Temp-Datei fuer automatisches Cleanup."""
        with cls._lock:
            cls._files.append(path)
        return path

    @classmethod
    def unregister(cls, path: str) -> None:
        """Entfernt eine Datei aus dem Tracking (z.B. nach manuellem Cleanup)."""
        with cls._lock:
            if path in cls._files:
                cls._files.remove(path)

    @classmethod
    def cleanup_all(cls) -> None:
        """Raeumt alle registrierten Temp-Dateien auf."""
        with cls._lock:
            for path in cls._files[:]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass
            cls._files.clear()

# atexit-Handler registrieren
atexit.register(TempFileTracker.cleanup_all)
```

**Anwendung in `transfer_service.py` (PEM-Files):**

```python
# Statt:
temp_fd, cert_path = tempfile.mkstemp(suffix='.pem')
os.close(temp_fd)
with open(cert_path, 'wb') as f:
    f.write(pem_data)

# Neu:
temp_fd, cert_path = tempfile.mkstemp(suffix='.pem')
os.close(temp_fd)
os.chmod(cert_path, 0o600)  # Restriktive Permissions
TempFileTracker.register(cert_path)
with open(cert_path, 'wb') as f:
    f.write(pem_data)
```

**Pattern 2: try/finally fuer kurzlebige Temp-Files (PDF)**

```python
# In pdf_unlock.py:
temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
os.close(temp_fd)
try:
    doc.save(temp_path, encryption=fitz.PDF_ENCRYPT_NONE)
    doc.close()
    shutil.move(temp_path, file_path)
    temp_path = None  # Erfolgreich verschoben
finally:
    if temp_path and os.path.exists(temp_path):
        os.unlink(temp_path)
```

### Einsatzstellen

| Datei | Pattern | Temp-File-Typ |
|-------|---------|--------------|
| `transfer_service.py:342-367` | Pattern 1 (atexit) | PEM mit Private Key |
| `pdf_unlock.py:155-166` | Pattern 2 (try/finally) | Entschluesselte PDF |
| Zukuenftige Temp-Files | Pattern 1 oder 2 | Nach Bedarf |

### Begrenzungen

- `atexit` wird bei `SIGKILL` (kill -9) nicht ausgefuehrt
- `atexit` wird bei Python-Crash (Segfault) nicht ausgefuehrt
- Fuer diese Faelle: OS-Level Temp-Cleanup (reboot, tmpwatch/tmpreaper)
- In-Memory-Loesung (ohne Temp-Files) waere ideal, aber `requests` erfordert Datei-Pfade fuer Client-Zertifikate

---

## Baustein B5: DPAPI/Keyring-Wrapper (Python)

**Loest:** SV-005 (Hoch — JWT-Token auf Disk), SV-010 (Hoch — Zertifikate auf Disk)

### Kontext

Sensitive Daten (JWT-Tokens, Zertifikate) werden als Klartext-Dateien gespeichert. Windows bietet mit DPAPI (Data Protection API) eine betriebssystem-gestuetzte Verschluesselung, die an den aktuellen Benutzer gebunden ist.

### Design

**Wrapper-Modul `src/services/secure_storage.py`:**

```python
"""
ACENCIA ATLAS - Sichere lokale Speicherung

Nutzt Windows DPAPI (via keyring) fuer sichere Speicherung von Secrets.
Fallback auf dateibasierte Speicherung mit restriktiven Permissions.
"""
import json
import logging
import os
import stat
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = "acencia_atlas"

# Keyring verfuegbar?
_keyring_available = False
try:
    import keyring
    _keyring_available = True
except ImportError:
    logger.info("keyring nicht verfuegbar, nutze Datei-Fallback mit Permissions")


def secure_store(key: str, value: str) -> bool:
    """
    Speichert einen Wert sicher.

    Args:
        key: Eindeutiger Schluessel (z.B. "jwt_token", "cert_degenia")
        value: Zu speichernder Wert (String, ggf. Base64)

    Returns:
        True wenn erfolgreich
    """
    if _keyring_available:
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            logger.debug(f"Secret '{key}' in Keyring gespeichert")
            return True
        except Exception as e:
            logger.warning(f"Keyring-Speicherung fehlgeschlagen: {e}, nutze Fallback")

    # Fallback: Datei mit restriktiven Permissions
    return _file_store(key, value)


def secure_load(key: str) -> Optional[str]:
    """
    Laedt einen gespeicherten Wert.

    Returns:
        Gespeicherter Wert oder None
    """
    if _keyring_available:
        try:
            value = keyring.get_password(SERVICE_NAME, key)
            if value is not None:
                return value
        except Exception as e:
            logger.warning(f"Keyring-Laden fehlgeschlagen: {e}, versuche Fallback")

    return _file_load(key)


def secure_delete(key: str) -> bool:
    """Loescht einen gespeicherten Wert."""
    if _keyring_available:
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except Exception:
            pass

    return _file_delete(key)


# --- Datei-Fallback mit Permissions ---

def _get_storage_dir() -> Path:
    """Gibt das sichere Speicherverzeichnis zurueck."""
    base = Path(os.environ.get('APPDATA', Path.home())) / 'ACENCIA ATLAS' / 'secure'
    base.mkdir(parents=True, exist_ok=True)

    # Verzeichnis-Permissions (nur Owner)
    try:
        os.chmod(str(base), stat.S_IRWXU)  # 0o700
    except Exception:
        pass

    return base


def _file_store(key: str, value: str) -> bool:
    """Speichert in Datei mit restriktiven Permissions."""
    path = _get_storage_dir() / f"{key}.enc"
    try:
        path.write_text(value, encoding='utf-8')
        os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        return True
    except Exception as e:
        logger.error(f"Datei-Speicherung fehlgeschlagen: {e}")
        return False


def _file_load(key: str) -> Optional[str]:
    """Laedt aus Datei."""
    path = _get_storage_dir() / f"{key}.enc"
    try:
        if path.exists():
            return path.read_text(encoding='utf-8')
    except Exception as e:
        logger.warning(f"Datei-Laden fehlgeschlagen: {e}")
    return None


def _file_delete(key: str) -> bool:
    """Loescht Datei."""
    path = _get_storage_dir() / f"{key}.enc"
    try:
        if path.exists():
            path.unlink()
        return True
    except Exception:
        return False
```

**Anwendung fuer JWT-Token (`src/api/auth.py`):**

```python
from services.secure_storage import secure_store, secure_load, secure_delete

def _save_token(self, token: str, user_data: dict) -> None:
    data = json.dumps({'token': token, 'user': user_data})
    secure_store('jwt_token', data)

def _load_saved_token(self) -> Optional[dict]:
    data = secure_load('jwt_token')
    if data:
        return json.loads(data)
    return None

def _delete_saved_token(self) -> None:
    secure_delete('jwt_token')
```

**Anwendung fuer Zertifikate (`src/config/certificates.py`):**

```python
import base64
from services.secure_storage import secure_store, secure_load, secure_delete

def save_certificate(name: str, cert_bytes: bytes) -> None:
    b64 = base64.b64encode(cert_bytes).decode('ascii')
    secure_store(f'cert_{name}', b64)

def load_certificate(name: str) -> Optional[bytes]:
    b64 = secure_load(f'cert_{name}')
    if b64:
        return base64.b64decode(b64)
    return None
```

### Keyring-Backend auf Windows

| Backend | Schutz | Verfuegbarkeit |
|---------|--------|---------------|
| Windows Credential Manager | DPAPI (User-gebunden) | Immer (mit pywin32) |
| KeePass (falls installiert) | Master-Password | Optional |
| Datei-Fallback | chmod 0o600 | Immer |

### Migration bestehender Tokens

1. Beim ersten Start mit neuem Code:
   - Altes `~/.bipro_gdv_token.json` lesen
   - In `secure_store('jwt_token', ...)` migrieren
   - Alte Datei loeschen
2. Analog fuer Zertifikate in `%APPDATA%/ACENCIA ATLAS/certs/`

### Abhaengigkeiten

- `keyring>=24.0.0` in `requirements.txt` (optional, Fallback vorhanden)
- `pywin32>=306` bereits vorhanden (wird von keyring auf Windows genutzt)
