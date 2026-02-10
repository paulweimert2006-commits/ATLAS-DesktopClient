<?php
/**
 * BiPro API - AI/KI-Funktionen
 * 
 * Endpunkte:
 * - GET /ai/key - OpenRouter API-Key abrufen (erfordert documents_process Recht)
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
            if ($action === 'key') {
                getOpenRouterKey($payload);
            } else {
                json_error('Unbekannte Aktion', 404);
            }
            break;
            
        default:
            json_error('Methode nicht erlaubt', 405);
    }
}

/**
 * GET /ai/key
 * 
 * Gibt den OpenRouter API-Key zurueck.
 * Erfordert documents_process Berechtigung.
 */
function getOpenRouterKey(array $user): void {
    // Pruefen ob Key konfiguriert ist
    if (!defined('OPENROUTER_API_KEY') || empty(OPENROUTER_API_KEY)) {
        json_error('OpenRouter API-Key nicht konfiguriert', 500);
        return;
    }
    
    // Activity-Log
    ActivityLogger::log([
        'user_id' => $user['user_id'],
        'username' => $user['username'] ?? '',
        'action_category' => 'ai',
        'action' => 'key_access',
        'entity_type' => 'ai',
        'description' => 'OpenRouter API-Key abgerufen',
        'details' => ['purpose' => 'pdf_classification']
    ]);
    
    json_success([
        'api_key' => OPENROUTER_API_KEY,
        'provider' => 'openrouter',
        'expires_hint' => 'Dieser Key ist nur fuer diese Session gueltig'
    ]);
}
