<?php
/**
 * BiPro API - Notification Polling (Leichtgewichtig)
 * 
 * Endpunkt:
 * - GET /notifications/summary - Unread-Counts + neueste Chat-Nachricht
 * 
 * Wird alle 30 Sekunden von der Desktop-App gepollt.
 * MUSS extrem schnell sein (2 einfache COUNT-Queries).
 * 
 * Query-Param:
 * - last_message_ts: ISO-Timestamp der letzten bekannten Chat-Nachricht
 *   (fuer Toast-Deduplizierung - nur neuere Nachrichten in latest_chat_message)
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/jwt.php';

/**
 * Haupt-Handler fuer Notification-Polling.
 */
function handleNotificationsRequest(string $action, string $method): void {
    if ($method !== 'GET') {
        json_error('Nur GET erlaubt', 405);
    }
    
    if ($action !== 'summary' && $action !== '') {
        json_error('Unbekannte Aktion', 404);
    }
    
    $payload = JWT::requireAuth();
    handleNotificationsSummary($payload);
}

// ============================================================================
// GET /notifications/summary
// ============================================================================

function handleNotificationsSummary(array $payload): void {
    $userId = $payload['user_id'];
    $lastMessageTs = $_GET['last_message_ts'] ?? null;
    
    // 1. Ungelesene System/Admin-Meldungen (1 Query)
    $unreadSys = Database::queryOne(
        "SELECT COUNT(*) AS cnt 
         FROM messages m
         LEFT JOIN message_reads mr ON mr.message_id = m.id AND mr.user_id = ?
         WHERE mr.read_at IS NULL 
           AND (m.expires_at IS NULL OR m.expires_at > NOW())",
        [$userId]
    );
    
    // 2. Ungelesene Chat-Nachrichten: Anzahl Conversations mit ungelesenen (1 Query)
    $unreadChat = Database::queryOne(
        "SELECT COUNT(DISTINCT conversation_id) AS cnt 
         FROM private_messages
         WHERE receiver_id = ? AND read_at IS NULL",
        [$userId]
    );
    
    // 3. Neueste Chat-Nachricht (fuer Toast) - nur wenn neuer als last_message_ts
    $latestChatMessage = null;
    if ($lastMessageTs) {
        $latest = Database::queryOne(
            "SELECT pm.conversation_id, u.username AS sender_name,
                    SUBSTRING(pm.content, 1, 100) AS preview,
                    pm.created_at
             FROM private_messages pm
             JOIN users u ON u.id = pm.sender_id
             WHERE pm.receiver_id = ? 
               AND pm.read_at IS NULL
               AND pm.created_at > ?
             ORDER BY pm.created_at DESC
             LIMIT 1",
            [$userId, $lastMessageTs]
        );
    } else {
        // Erster Aufruf: Neueste ungelesene Nachricht
        $latest = Database::queryOne(
            "SELECT pm.conversation_id, u.username AS sender_name,
                    SUBSTRING(pm.content, 1, 100) AS preview,
                    pm.created_at
             FROM private_messages pm
             JOIN users u ON u.id = pm.sender_id
             WHERE pm.receiver_id = ? AND pm.read_at IS NULL
             ORDER BY pm.created_at DESC
             LIMIT 1",
            [$userId]
        );
    }
    
    if ($latest) {
        $latestChatMessage = [
            'conversation_id' => (int)$latest['conversation_id'],
            'sender_name' => $latest['sender_name'],
            'preview' => $latest['preview'],
            'created_at' => $latest['created_at']
        ];
    }
    
    json_response([
        'success' => true,
        'unread_chats' => (int)$unreadChat['cnt'],
        'unread_system_messages' => (int)$unreadSys['cnt'],
        'latest_chat_message' => $latestChatMessage
    ]);
}
