<?php
/**
 * BiPro API - Mitteilungen (System + Admin)
 * 
 * Endpunkte:
 * - GET    /messages           - Alle Mitteilungen (paginiert, mit is_read pro User)
 * - POST   /messages           - Neue Mitteilung (API-Key ODER JWT-Admin)
 * - PUT    /messages/read      - Bulk-Read-Markierung
 * - DELETE /messages/{id}      - Mitteilung loeschen (nur Admin)
 * 
 * Authentifizierung:
 * - GET/PUT/DELETE: JWT (alle angemeldeten Nutzer)
 * - POST: API-Key (X-API-Key Header, wie Scan-API) ODER JWT-Admin
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/permissions.php';
require_once __DIR__ . '/lib/activity_logger.php';

/**
 * Haupt-Handler fuer Mitteilungen.
 * 
 * @param string $action Sub-Route (z.B. 'read', oder numerische ID)
 * @param string $method HTTP-Methode
 */
function handleMessagesRequest(string $action, string $method): void {
    // POST kann API-Key ODER JWT verwenden
    if ($method === 'POST' && empty($action)) {
        handleCreateMessage();
        return;
    }
    
    // Alle anderen Endpoints erfordern JWT
    $payload = JWT::requireAuth();
    
    if ($method === 'GET' && empty($action)) {
        handleListMessages($payload);
        return;
    }
    
    if ($method === 'PUT' && $action === 'read') {
        handleMarkMessagesRead($payload);
        return;
    }
    
    if ($method === 'DELETE' && is_numeric($action)) {
        handleDeleteMessage((int)$action, $payload);
        return;
    }
    
    json_error('Unbekannte Aktion', 404);
}

// ============================================================================
// GET /messages - Paginierte Mitteilungen mit Read-Status
// ============================================================================

function handleListMessages(array $payload): void {
    $userId = $payload['user_id'];
    $page = max(1, (int)($_GET['page'] ?? 1));
    $perPage = min(100, max(1, (int)($_GET['per_page'] ?? 20)));
    $offset = ($page - 1) * $perPage;
    
    // Mitteilungen mit Read-Status pro User
    $messages = Database::query(
        "SELECT m.id, m.title, m.description, m.severity, m.source, m.sender_name,
                m.created_at, m.expires_at,
                (mr.read_at IS NOT NULL) AS is_read
         FROM messages m
         LEFT JOIN message_reads mr ON mr.message_id = m.id AND mr.user_id = ?
         WHERE m.expires_at IS NULL OR m.expires_at > NOW()
         ORDER BY m.created_at DESC
         LIMIT ? OFFSET ?",
        [$userId, $perPage, $offset]
    );
    
    // Gesamtzahl fuer Pagination
    $total = Database::queryOne(
        "SELECT COUNT(*) AS cnt FROM messages
         WHERE expires_at IS NULL OR expires_at > NOW()"
    );
    
    // is_read zu boolean casten
    foreach ($messages as &$msg) {
        $msg['is_read'] = (bool)$msg['is_read'];
    }
    unset($msg);
    
    json_response([
        'success' => true,
        'data' => $messages,
        'pagination' => [
            'page' => $page,
            'per_page' => $perPage,
            'total' => (int)$total['cnt'],
            'total_pages' => (int)ceil($total['cnt'] / $perPage)
        ]
    ]);
}

// ============================================================================
// POST /messages - Neue Mitteilung (API-Key oder Admin)
// ============================================================================

function handleCreateMessage(): void {
    // Auth: API-Key ODER JWT-Admin
    $apiKey = $_SERVER['HTTP_X_API_KEY'] ?? '';
    $senderName = null;
    $source = null;
    $isApiKey = false;
    
    if (!empty($apiKey)) {
        // API-Key-Authentifizierung (wie Scan-API)
        if (!hash_equals(SCAN_API_KEY, $apiKey)) {
            ActivityLogger::log([
                'user_id' => null,
                'username' => 'messages_api',
                'action_category' => 'system',
                'action' => 'message_auth_failed',
                'description' => 'Mitteilung mit ungueltigem API-Key',
                'status' => 'denied'
            ]);
            json_error('Ungueltiger API-Key', 401);
        }
        $isApiKey = true;
    } else {
        // JWT-Admin-Authentifizierung
        $payload = requireAdmin();
        $senderName = $payload['username'] ?? 'Admin';
        $source = 'Admin';
    }
    
    $data = get_json_body();
    require_fields($data, ['title']);
    
    // Content-Escaping + Laengenlimits
    $title = mb_substr(htmlspecialchars(trim($data['title']), ENT_QUOTES, 'UTF-8'), 0, 500);
    $description = isset($data['description']) && $data['description'] !== ''
        ? mb_substr(htmlspecialchars(trim($data['description']), ENT_QUOTES, 'UTF-8'), 0, 5000)
        : null;
    
    $severity = $data['severity'] ?? 'info';
    if (!in_array($severity, ['info', 'warning', 'error', 'critical'])) {
        $severity = 'info';
    }
    
    // Bei API-Key muessen source und sender_name im Body stehen
    if ($isApiKey) {
        require_fields($data, ['sender_name']);
        $senderName = mb_substr(htmlspecialchars(trim($data['sender_name']), ENT_QUOTES, 'UTF-8'), 0, 100);
        $source = mb_substr(htmlspecialchars(trim($data['source'] ?? 'System'), ENT_QUOTES, 'UTF-8'), 0, 100);
    }
    
    $expiresAt = $data['expires_at'] ?? null;
    
    $id = Database::insert(
        "INSERT INTO messages (title, description, severity, source, sender_name, expires_at)
         VALUES (?, ?, ?, ?, ?, ?)",
        [$title, $description, $severity, $source, $senderName, $expiresAt]
    );
    
    // Activity-Log
    ActivityLogger::log([
        'user_id' => $isApiKey ? null : ($payload['user_id'] ?? null),
        'username' => $isApiKey ? 'api_key' : ($payload['username'] ?? ''),
        'action_category' => 'system',
        'action' => 'message_created',
        'entity_type' => 'message',
        'entity_id' => $id,
        'description' => "Mitteilung erstellt: $title",
        'details' => [
            'severity' => $severity,
            'source' => $source,
            'sender_name' => $senderName
        ],
        'status' => 'success'
    ]);
    
    json_success([
        'id' => $id,
        'title' => $title,
        'severity' => $severity,
        'source' => $source,
        'sender_name' => $senderName
    ], 'Mitteilung erstellt');
}

// ============================================================================
// PUT /messages/read - Bulk-Read-Markierung
// ============================================================================

function handleMarkMessagesRead(array $payload): void {
    $userId = $payload['user_id'];
    $data = get_json_body();
    
    $messageIds = $data['message_ids'] ?? [];
    if (empty($messageIds) || !is_array($messageIds)) {
        json_error('message_ids erforderlich (Array von IDs)', 400);
    }
    
    // Max 100 IDs pro Request
    $messageIds = array_slice(array_map('intval', $messageIds), 0, 100);
    
    // INSERT IGNORE - markiert nur ungelesene, ignoriert bereits gelesene
    $placeholders = implode(',', array_fill(0, count($messageIds), '(?, ?)'));
    $params = [];
    foreach ($messageIds as $msgId) {
        $params[] = $msgId;
        $params[] = $userId;
    }
    
    Database::execute(
        "INSERT IGNORE INTO message_reads (message_id, user_id) VALUES $placeholders",
        $params
    );
    
    json_success([], 'Mitteilungen als gelesen markiert');
}

// ============================================================================
// DELETE /messages/{id} - Mitteilung loeschen (nur Admin)
// ============================================================================

function handleDeleteMessage(int $messageId, array $payload): void {
    // Nur Admin
    if (!isAdmin($payload['user_id'])) {
        json_error('Nur Administratoren duerfen Mitteilungen loeschen', 403);
    }
    
    $message = Database::queryOne("SELECT id, title FROM messages WHERE id = ?", [$messageId]);
    if (!$message) {
        json_error('Mitteilung nicht gefunden', 404);
    }
    
    // CASCADE loescht auch message_reads Eintraege
    Database::execute("DELETE FROM messages WHERE id = ?", [$messageId]);
    
    ActivityLogger::log([
        'user_id' => $payload['user_id'],
        'username' => $payload['username'] ?? '',
        'action_category' => 'admin',
        'action' => 'message_deleted',
        'entity_type' => 'message',
        'entity_id' => $messageId,
        'description' => "Mitteilung geloescht: " . $message['title'],
        'status' => 'success'
    ]);
    
    json_success([], 'Mitteilung geloescht');
}
