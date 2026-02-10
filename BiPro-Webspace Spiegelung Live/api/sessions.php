<?php
/**
 * BiPro API - Session-Verwaltung
 * 
 * NUR fuer Administratoren zugaenglich.
 * 
 * Endpunkte:
 * - GET    /sessions             - Alle aktiven Sessions
 * - GET    /sessions/user/{id}   - Sessions eines Users
 * - DELETE /sessions/{id}        - Einzelne Session beenden
 * - DELETE /sessions/user/{id}   - Alle Sessions eines Users beenden
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/permissions.php';
require_once __DIR__ . '/lib/activity_logger.php';

function handleSessionsRequest(?string $idOrAction, string $method, ?string $extra = null): void {
    // Alle Session-Endpunkte erfordern Admin-Rechte
    $payload = requireAdmin();
    
    // Route: /sessions/user/{userId}
    if ($idOrAction === 'user' && $extra !== null) {
        $userId = (int)$extra;
        
        if ($method === 'GET') {
            handleGetUserSessions($userId);
            return;
        }
        
        if ($method === 'DELETE') {
            handleKillUserSessions($userId, $payload);
            return;
        }
        
        json_error('Methode nicht erlaubt', 405);
    }
    
    // Route: /sessions - Liste
    if ($idOrAction === null || $idOrAction === '') {
        if ($method === 'GET') {
            handleListSessions();
            return;
        }
        json_error('Methode nicht erlaubt', 405);
    }
    
    // Route: /sessions/{id} - Einzelne Session
    if (is_numeric($idOrAction)) {
        $sessionId = (int)$idOrAction;
        
        if ($method === 'DELETE') {
            handleKillSession($sessionId, $payload);
            return;
        }
        
        json_error('Methode nicht erlaubt', 405);
    }
    
    json_error('Unbekannte Session-Aktion', 404);
}

/**
 * GET /sessions - Alle aktiven Sessions
 */
function handleListSessions(): void {
    $sessions = Database::query(
        'SELECT s.id, s.user_id, u.username, s.ip_address, s.user_agent,
                s.created_at, s.last_activity_at, s.expires_at, s.is_active
         FROM sessions s
         JOIN users u ON u.id = s.user_id
         WHERE s.is_active = 1 AND s.expires_at > NOW()
         ORDER BY s.last_activity_at DESC'
    );
    
    // User-Agent kuerzen fuer Anzeige
    foreach ($sessions as &$session) {
        $session['user_agent_short'] = _shortenUserAgent($session['user_agent']);
    }
    unset($session);
    
    json_success(['sessions' => $sessions, 'count' => count($sessions)]);
}

/**
 * GET /sessions/user/{userId} - Sessions eines Users
 */
function handleGetUserSessions(int $userId): void {
    $sessions = Database::query(
        'SELECT s.id, s.user_id, u.username, s.ip_address, s.user_agent,
                s.created_at, s.last_activity_at, s.expires_at, s.is_active
         FROM sessions s
         JOIN users u ON u.id = s.user_id
         WHERE s.user_id = ? AND s.is_active = 1 AND s.expires_at > NOW()
         ORDER BY s.last_activity_at DESC',
        [$userId]
    );
    
    foreach ($sessions as &$session) {
        $session['user_agent_short'] = _shortenUserAgent($session['user_agent']);
    }
    unset($session);
    
    json_success(['sessions' => $sessions, 'count' => count($sessions)]);
}

/**
 * DELETE /sessions/{id} - Einzelne Session beenden
 */
function handleKillSession(int $sessionId, array $adminPayload): void {
    $session = Database::queryOne(
        'SELECT s.id, s.user_id, u.username, s.ip_address
         FROM sessions s
         JOIN users u ON u.id = s.user_id
         WHERE s.id = ?',
        [$sessionId]
    );
    
    if (!$session) {
        json_error('Session nicht gefunden', 404);
    }
    
    Database::execute('UPDATE sessions SET is_active = 0 WHERE id = ?', [$sessionId]);
    
    // Activity Log
    ActivityLogger::logAdmin($adminPayload, 'session_killed', 'session', $sessionId,
        "Session von '{$session['username']}' beendet (IP: {$session['ip_address']})",
        ['target_user_id' => $session['user_id'], 'target_username' => $session['username']]
    );
    
    json_success([], 'Session beendet');
}

/**
 * DELETE /sessions/user/{userId} - Alle Sessions eines Users beenden
 */
function handleKillUserSessions(int $userId, array $adminPayload): void {
    $user = Database::queryOne('SELECT id, username FROM users WHERE id = ?', [$userId]);
    if (!$user) {
        json_error('Benutzer nicht gefunden', 404);
    }
    
    $count = JWT::invalidateAllUserSessions($userId);
    
    // Activity Log
    ActivityLogger::logAdmin($adminPayload, 'all_sessions_killed', 'user', $userId,
        "Alle Sessions von '{$user['username']}' beendet ({$count} Sessions)",
        ['sessions_count' => $count]
    );
    
    json_success(['invalidated' => $count], "{$count} Session(s) beendet");
}

/**
 * Kuerzt den User-Agent String fuer die Anzeige.
 */
function _shortenUserAgent(?string $ua): string {
    if (!$ua) return 'Unbekannt';
    
    // Python requests erkennen
    if (strpos($ua, 'python-requests') !== false) {
        return 'ACENCIA ATLAS Desktop';
    }
    
    // Browser erkennen
    if (preg_match('/Chrome\/[\d.]+/', $ua, $m)) return 'Chrome';
    if (preg_match('/Firefox\/[\d.]+/', $ua, $m)) return 'Firefox';
    if (preg_match('/Safari\/[\d.]+/', $ua, $m)) return 'Safari';
    
    return substr($ua, 0, 50);
}
