<?php
/**
 * BiPro API - AI/KI-Funktionen
 * 
 * SV-004 Fix: OpenRouter-Proxy (Baustein B3)
 * API-Key bleibt auf dem Server. Client sendet Anfragen an unseren Proxy.
 * 
 * Endpunkte:
 * - POST /ai/classify - KI-Klassifikation via Server-Proxy
 * - GET /ai/credits  - OpenRouter-Guthaben abfragen (Proxy)
 * - GET /ai/key      - ENTFERNT (SV-004: Key nicht mehr an Client senden)
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/permissions.php';
require_once __DIR__ . '/lib/activity_logger.php';

function handleAiRequest(string $action, string $method): void {
    // Authentifizierung + documents_process Recht erforderlich
    $payload = requirePermission('documents_process');
    
    switch ($method) {
        case 'GET':
            if ($action === 'credits') {
                getOpenRouterCredits($payload);
            } elseif ($action === 'key') {
                // SV-004: Key-Endpunkt deaktiviert
                json_error('API-Key-Endpunkt ist deaktiviert. Nutze POST /ai/classify.', 410);
            } else {
                json_error('Unbekannte Aktion', 404);
            }
            break;
            
        case 'POST':
            if ($action === 'classify') {
                handleClassify($payload);
            } else {
                json_error('Unbekannte Aktion', 404);
            }
            break;
            
        default:
            json_error('Methode nicht erlaubt', 405);
    }
}

/**
 * POST /ai/classify
 * 
 * SV-004/SV-013: Server-seitiger OpenRouter-Proxy.
 * Client sendet messages/model/max_tokens/response_format.
 * Server injiziert API-Key und reduziert PII.
 * 
 * Body: { "messages": [...], "model": "...", "max_tokens": N, "response_format": {...} }
 */
function handleClassify(array $user): void {
    if (!defined('OPENROUTER_API_KEY') || empty(OPENROUTER_API_KEY)) {
        json_error('OpenRouter API-Key nicht konfiguriert', 500);
        return;
    }
    
    $data = get_json_body();
    require_fields($data, ['messages', 'model']);
    
    $messages = $data['messages'];
    $model = $data['model'];
    $maxTokens = isset($data['max_tokens']) ? (int)$data['max_tokens'] : 200;
    $responseFormat = $data['response_format'] ?? null;
    
    // SV-013 Fix: PII-Redaktion auf Message-Inhalte anwenden
    $messages = redact_pii_in_messages($messages);
    
    // OpenRouter-Payload zusammenbauen
    $orPayload = [
        'model' => $model,
        'messages' => $messages,
        'max_tokens' => min($maxTokens, 4096) // Limit
    ];
    
    if ($responseFormat) {
        $orPayload['response_format'] = $responseFormat;
    }
    
    // cURL-Aufruf an OpenRouter
    $result = callOpenRouter($orPayload);
    
    if ($result === null) {
        json_error('OpenRouter-Anfrage fehlgeschlagen', 502);
        return;
    }
    
    // Activity-Log (ohne PII)
    ActivityLogger::log([
        'user_id' => $user['user_id'],
        'username' => $user['username'] ?? '',
        'action_category' => 'ai',
        'action' => 'classify',
        'entity_type' => 'ai',
        'description' => "KI-Klassifikation via Proxy (Modell: {$model})",
        'details' => ['model' => $model, 'max_tokens' => $maxTokens]
    ]);
    
    json_success($result);
}

/**
 * GET /ai/credits
 * 
 * Proxy fuer OpenRouter Credits-Abfrage.
 */
function getOpenRouterCredits(array $user): void {
    if (!defined('OPENROUTER_API_KEY') || empty(OPENROUTER_API_KEY)) {
        json_error('OpenRouter API-Key nicht konfiguriert', 500);
        return;
    }
    
    // OpenRouter /api/v1/credits liefert {data: {total_credits, total_usage}}
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => 'https://openrouter.ai/api/v1/credits',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'Authorization: Bearer ' . OPENROUTER_API_KEY
        ],
        CURLOPT_TIMEOUT => 15,
        CURLOPT_SSL_VERIFYPEER => true
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($error || $httpCode !== 200) {
        json_error('Credits-Abfrage fehlgeschlagen: ' . ($error ?: "HTTP {$httpCode}"), 502);
        return;
    }
    
    $raw = json_decode($response, true);
    
    // OpenRouter Antwort: {data: {total_credits: X, total_usage: Y}}
    // Direkt durchreichen - Python-Client erwartet genau dieses Format
    json_success($raw['data'] ?? $raw);
}

/**
 * SV-013: PII-Redaktion in Chat-Messages.
 * 
 * Entfernt personenbezogene Daten aus dem Text, bevor er an OpenRouter gesendet wird.
 * Betrifft nur den 'content' der User-Messages.
 */
function redact_pii_in_messages(array $messages): array {
    foreach ($messages as &$msg) {
        if (isset($msg['content']) && is_string($msg['content'])) {
            $msg['content'] = redact_pii($msg['content']);
        }
    }
    return $messages;
}

/**
 * PII-Redaktion: E-Mails, Telefon, IBAN ersetzen.
 * Vorsichtig: Nur sichere Patterns um False Positives zu vermeiden.
 */
function redact_pii(string $text): string {
    // E-Mail-Adressen
    $text = preg_replace('/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/', '[EMAIL]', $text);
    
    // IBAN (DE und andere europaeische)
    $text = preg_replace('/[A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{0,2}/', '[IBAN]', $text);
    
    // Deutsche Telefonnummern (konservativ)
    $text = preg_replace('/(?:\+49|0049|0)\s*[\d\s\-\/\.]{8,15}/', '[PHONE]', $text);
    
    return $text;
}

/**
 * cURL-Aufruf an OpenRouter API.
 */
function callOpenRouter(array $payload): ?array {
    $ch = curl_init();
    
    curl_setopt_array($ch, [
        CURLOPT_URL => 'https://openrouter.ai/api/v1/chat/completions',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_HTTPHEADER => [
            'Authorization: Bearer ' . OPENROUTER_API_KEY,
            'Content-Type: application/json',
            'HTTP-Referer: https://acencia.info',
            'X-Title: ACENCIA ATLAS'
        ],
        CURLOPT_TIMEOUT => 120, // KI-Calls koennen lange dauern
        CURLOPT_SSL_VERIFYPEER => true
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($error) {
        error_log("OpenRouter cURL-Fehler: {$error}");
        return null;
    }
    
    if ($httpCode >= 400) {
        error_log("OpenRouter HTTP-Fehler: {$httpCode} - {$response}");
        return null;
    }
    
    return json_decode($response, true);
}
