<?php
/**
 * BiPro API - Private Chat (1:1 Nachrichten)
 * 
 * Endpunkte:
 * - GET    /chat/conversations                  - Eigene Chats (mit letzter Nachricht + Unread)
 * - POST   /chat/conversations                  - Neuen 1:1 Chat starten
 * - GET    /chat/conversations/{id}/messages     - Nachrichten eines Chats (paginiert)
 * - POST   /chat/conversations/{id}/messages     - Nachricht senden
 * - PUT    /chat/conversations/{id}/read         - Alle ungelesenen als gelesen markieren
 * - GET    /chat/users                           - Verfuegbare Chat-Partner (noch kein Chat)
 * 
 * Alle Endpunkte erfordern JWT-Authentifizierung.
 * User darf nur eigene Conversations lesen/schreiben.
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/activity_logger.php';

/**
 * Haupt-Handler fuer Chat-Endpunkte.
 * 
 * Routing:
 * - /chat/conversations         → $action='conversations', $id=''
 * - /chat/conversations/5       → $action='conversations', $id='5'
 * - /chat/conversations/5/messages → wird via $parts aufgeloest
 * - /chat/users                 → $action='users', $id=''
 * 
 * @param string $action Sub-Route
 * @param string $id     Sub-ID
 * @param string $method HTTP-Methode
 * @param string|null $sub Sub-Sub-Route (z.B. 'messages', 'read')
 */
function handleChatRequest(string $action, string $id, string $method, ?string $sub = null): void {
    $payload = JWT::requireAuth();
    
    // GET /chat/users
    if ($action === 'users' && $method === 'GET') {
        handleGetAvailableUsers($payload);
        return;
    }
    
    // /chat/conversations
    if ($action === 'conversations') {
        // GET /chat/conversations (Liste)
        if ($method === 'GET' && empty($id)) {
            handleListConversations($payload);
            return;
        }
        
        // POST /chat/conversations (neuen Chat starten)
        if ($method === 'POST' && empty($id)) {
            handleCreateConversation($payload);
            return;
        }
        
        // /chat/conversations/{id}/...
        if (is_numeric($id)) {
            $convId = (int)$id;
            
            // Autorisierung: User muss Teilnehmer sein
            if (!isConversationParticipant($convId, $payload['user_id'])) {
                json_error('Kein Zugriff auf diese Konversation', 403);
            }
            
            // GET /chat/conversations/{id}/messages
            if ($method === 'GET' && $sub === 'messages') {
                handleListMessages($convId, $payload);
                return;
            }
            
            // POST /chat/conversations/{id}/messages
            if ($method === 'POST' && $sub === 'messages') {
                handleSendMessage($convId, $payload);
                return;
            }
            
            // PUT /chat/conversations/{id}/read
            if ($method === 'PUT' && $sub === 'read') {
                handleMarkAsRead($convId, $payload);
                return;
            }
        }
    }
    
    json_error('Unbekannte Chat-Aktion', 404);
}

// ============================================================================
// HILFSFUNKTIONEN
// ============================================================================

/**
 * Prueft ob ein User Teilnehmer einer Conversation ist.
 */
function isConversationParticipant(int $convId, int $userId): bool {
    $conv = Database::queryOne(
        "SELECT id FROM private_conversations
         WHERE id = ? AND (user1_id = ? OR user2_id = ?)",
        [$convId, $userId, $userId]
    );
    return $conv !== null;
}

/**
 * Ermittelt den Gegenpartner einer Conversation.
 */
function getOtherUserId(array $conv, int $currentUserId): int {
    return $conv['user1_id'] == $currentUserId ? $conv['user2_id'] : $conv['user1_id'];
}

// ============================================================================
// GET /chat/conversations - Eigene Chats
// ============================================================================

function handleListConversations(array $payload): void {
    $userId = $payload['user_id'];
    
    // Conversations mit letzter Nachricht und Unread-Count
    $conversations = Database::query(
        "SELECT 
            pc.id,
            pc.user1_id,
            pc.user2_id,
            pc.created_at,
            pc.updated_at,
            u_other.username AS partner_name,
            u_other.id AS partner_id,
            last_msg.content AS last_message,
            last_msg.sender_id AS last_message_sender_id,
            last_msg.created_at AS last_message_at,
            COALESCE(unread.cnt, 0) AS unread_count
         FROM private_conversations pc
         -- Partner-Name ermitteln
         JOIN users u_other ON u_other.id = IF(pc.user1_id = ?, pc.user2_id, pc.user1_id)
         -- Letzte Nachricht (Subquery)
         LEFT JOIN (
             SELECT pm1.conversation_id, pm1.content, pm1.sender_id, pm1.created_at
             FROM private_messages pm1
             INNER JOIN (
                 SELECT conversation_id, MAX(id) AS max_id
                 FROM private_messages
                 GROUP BY conversation_id
             ) pm2 ON pm1.id = pm2.max_id
         ) last_msg ON last_msg.conversation_id = pc.id
         -- Ungelesene Nachrichten zaehlen
         LEFT JOIN (
             SELECT conversation_id, COUNT(*) AS cnt
             FROM private_messages
             WHERE receiver_id = ? AND read_at IS NULL
             GROUP BY conversation_id
         ) unread ON unread.conversation_id = pc.id
         WHERE pc.user1_id = ? OR pc.user2_id = ?
         ORDER BY pc.updated_at DESC",
        [$userId, $userId, $userId, $userId]
    );
    
    // Response aufbereiten
    $result = [];
    foreach ($conversations as $conv) {
        $result[] = [
            'id' => (int)$conv['id'],
            'partner_id' => (int)$conv['partner_id'],
            'partner_name' => $conv['partner_name'],
            'last_message' => $conv['last_message'],
            'last_message_is_mine' => $conv['last_message_sender_id'] == $userId,
            'last_message_at' => $conv['last_message_at'],
            'unread_count' => (int)$conv['unread_count'],
            'updated_at' => $conv['updated_at']
        ];
    }
    
    json_response([
        'success' => true,
        'data' => $result
    ]);
}

// ============================================================================
// POST /chat/conversations - Neuen Chat starten
// ============================================================================

function handleCreateConversation(array $payload): void {
    $userId = $payload['user_id'];
    $data = get_json_body();
    require_fields($data, ['target_user_id']);
    
    $targetId = (int)$data['target_user_id'];
    
    // Validierung: Kann nicht mit sich selbst chatten
    if ($targetId === $userId) {
        json_error('Chat mit sich selbst nicht moeglich', 400);
    }
    
    // Validierung: Zieluser muss existieren und aktiv sein
    $targetUser = Database::queryOne(
        "SELECT id, username FROM users WHERE id = ? AND is_active = 1",
        [$targetId]
    );
    if (!$targetUser) {
        json_error('Nutzer nicht gefunden oder nicht aktiv', 404);
    }
    
    // Sortierung: Kleinere ID als user1_id
    $user1 = min($userId, $targetId);
    $user2 = max($userId, $targetId);
    
    // Pruefen ob Chat bereits existiert
    $existing = Database::queryOne(
        "SELECT id FROM private_conversations WHERE user1_id = ? AND user2_id = ?",
        [$user1, $user2]
    );
    if ($existing) {
        // Chat existiert bereits - ID zurueckgeben
        json_response([
            'success' => true,
            'data' => [
                'id' => (int)$existing['id'],
                'partner_name' => $targetUser['username'],
                'already_exists' => true
            ],
            'message' => 'Chat existiert bereits'
        ]);
        return;
    }
    
    // Neuen Chat erstellen
    $convId = Database::insert(
        "INSERT INTO private_conversations (user1_id, user2_id) VALUES (?, ?)",
        [$user1, $user2]
    );
    
    ActivityLogger::log([
        'user_id' => $userId,
        'username' => $payload['username'] ?? '',
        'action_category' => 'system',
        'action' => 'chat_created',
        'entity_type' => 'conversation',
        'entity_id' => $convId,
        'description' => "Chat eroeffnet mit " . $targetUser['username'],
        'status' => 'success'
    ]);
    
    json_success([
        'id' => $convId,
        'partner_name' => $targetUser['username'],
        'already_exists' => false
    ], 'Chat eroeffnet');
}

// ============================================================================
// GET /chat/conversations/{id}/messages - Nachrichten abrufen
// ============================================================================

function handleListMessages(int $convId, array $payload): void {
    $page = max(1, (int)($_GET['page'] ?? 1));
    $perPage = min(100, max(1, (int)($_GET['per_page'] ?? 50)));
    $offset = ($page - 1) * $perPage;
    
    $messages = Database::query(
        "SELECT pm.id, pm.sender_id, pm.receiver_id, pm.content, 
                pm.created_at, pm.read_at,
                u.username AS sender_name
         FROM private_messages pm
         JOIN users u ON u.id = pm.sender_id
         WHERE pm.conversation_id = ?
         ORDER BY pm.created_at ASC
         LIMIT ? OFFSET ?",
        [$convId, $perPage, $offset]
    );
    
    $total = Database::queryOne(
        "SELECT COUNT(*) AS cnt FROM private_messages WHERE conversation_id = ?",
        [$convId]
    );
    
    // Boolean-Cast fuer read_at
    $currentUserId = $payload['user_id'];
    foreach ($messages as &$msg) {
        $msg['id'] = (int)$msg['id'];
        $msg['sender_id'] = (int)$msg['sender_id'];
        $msg['receiver_id'] = (int)$msg['receiver_id'];
        $msg['is_mine'] = $msg['sender_id'] === $currentUserId;
        $msg['is_read'] = $msg['read_at'] !== null;
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
// POST /chat/conversations/{id}/messages - Nachricht senden
// ============================================================================

function handleSendMessage(int $convId, array $payload): void {
    $userId = $payload['user_id'];
    $data = get_json_body();
    require_fields($data, ['content']);
    
    // Content-Escaping + Laengenlimit
    $content = mb_substr(htmlspecialchars(trim($data['content']), ENT_QUOTES, 'UTF-8'), 0, 2000);
    
    if (empty($content)) {
        json_error('Nachricht darf nicht leer sein', 400);
    }
    
    // Conversation laden fuer receiver_id
    $conv = Database::queryOne(
        "SELECT user1_id, user2_id FROM private_conversations WHERE id = ?",
        [$convId]
    );
    if (!$conv) {
        json_error('Konversation nicht gefunden', 404);
    }
    
    $receiverId = getOtherUserId($conv, $userId);
    
    // Nachricht einfuegen
    $msgId = Database::insert(
        "INSERT INTO private_messages (conversation_id, sender_id, receiver_id, content)
         VALUES (?, ?, ?, ?)",
        [$convId, $userId, $receiverId, $content]
    );
    
    // Conversation updated_at serverseitig aktualisieren
    Database::execute(
        "UPDATE private_conversations SET updated_at = NOW() WHERE id = ?",
        [$convId]
    );
    
    json_success([
        'id' => $msgId,
        'conversation_id' => $convId,
        'sender_id' => $userId,
        'receiver_id' => $receiverId,
        'content' => $content,
        'created_at' => date('Y-m-d H:i:s'),
        'read_at' => null,
        'is_read' => false
    ], 'Nachricht gesendet');
}

// ============================================================================
// PUT /chat/conversations/{id}/read - Als gelesen markieren
// ============================================================================

function handleMarkAsRead(int $convId, array $payload): void {
    $userId = $payload['user_id'];
    
    $affected = Database::execute(
        "UPDATE private_messages
         SET read_at = NOW()
         WHERE conversation_id = ? AND receiver_id = ? AND read_at IS NULL",
        [$convId, $userId]
    );
    
    json_success([
        'marked_read' => $affected
    ], "$affected Nachricht(en) als gelesen markiert");
}

// ============================================================================
// GET /chat/users - Verfuegbare Chat-Partner
// ============================================================================

function handleGetAvailableUsers(array $payload): void {
    $userId = $payload['user_id'];
    
    // Alle aktiven User, mit denen noch KEIN Chat besteht
    $users = Database::query(
        "SELECT u.id, u.username
         FROM users u
         WHERE u.id != ?
           AND u.is_active = 1
           AND u.id NOT IN (
               SELECT IF(pc.user1_id = ?, pc.user2_id, pc.user1_id)
               FROM private_conversations pc
               WHERE pc.user1_id = ? OR pc.user2_id = ?
           )
         ORDER BY u.username ASC",
        [$userId, $userId, $userId, $userId]
    );
    
    json_response([
        'success' => true,
        'data' => $users
    ]);
}
