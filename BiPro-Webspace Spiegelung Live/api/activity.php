<?php
/**
 * BiPro API - Aktivitaetslog
 * 
 * NUR fuer Administratoren zugaenglich.
 * 
 * Endpunkte:
 * - GET /activity        - Log-Eintraege mit Filtern und Pagination
 * - GET /activity/stats  - Statistiken
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/permissions.php';

function handleActivityRequest(?string $action, string $method): void {
    // Alle Activity-Endpunkte erfordern Admin-Rechte
    requireAdmin();
    
    if ($method !== 'GET') {
        json_error('Methode nicht erlaubt', 405);
    }
    
    if ($action === 'stats') {
        handleActivityStats();
        return;
    }
    
    // Default: Liste
    handleActivityList();
}

/**
 * GET /activity - Log-Eintraege mit Filtern
 * 
 * Query-Parameter:
 * - user_id (int) - Nach Nutzer filtern
 * - action_category (string) - Nach Kategorie filtern
 * - action (string) - Nach spezifischer Aktion filtern
 * - entity_type (string) - Nach Entity-Typ filtern
 * - status (string) - 'success', 'error', 'denied'
 * - from (string) - Startdatum (YYYY-MM-DD)
 * - to (string) - Enddatum (YYYY-MM-DD)
 * - search (string) - Volltextsuche in description
 * - page (int) - Seite (default: 1)
 * - per_page (int) - Eintraege pro Seite (default: 50, max: 200)
 */
function handleActivityList(): void {
    $where = [];
    $params = [];
    
    // Filter: user_id
    if (isset($_GET['user_id']) && is_numeric($_GET['user_id'])) {
        $where[] = 'a.user_id = ?';
        $params[] = (int)$_GET['user_id'];
    }
    
    // Filter: action_category
    if (!empty($_GET['action_category'])) {
        $where[] = 'a.action_category = ?';
        $params[] = $_GET['action_category'];
    }
    
    // Filter: action
    if (!empty($_GET['action'])) {
        $where[] = 'a.action = ?';
        $params[] = $_GET['action'];
    }
    
    // Filter: entity_type
    if (!empty($_GET['entity_type'])) {
        $where[] = 'a.entity_type = ?';
        $params[] = $_GET['entity_type'];
    }
    
    // Filter: status
    if (!empty($_GET['status']) && in_array($_GET['status'], ['success', 'error', 'denied'])) {
        $where[] = 'a.status = ?';
        $params[] = $_GET['status'];
    }
    
    // Filter: from
    if (!empty($_GET['from'])) {
        $where[] = 'a.created_at >= ?';
        $params[] = $_GET['from'] . ' 00:00:00';
    }
    
    // Filter: to
    if (!empty($_GET['to'])) {
        $where[] = 'a.created_at <= ?';
        $params[] = $_GET['to'] . ' 23:59:59';
    }
    
    // Filter: Volltextsuche
    if (!empty($_GET['search'])) {
        $where[] = '(a.description LIKE ? OR a.username LIKE ? OR a.action LIKE ?)';
        $searchTerm = '%' . $_GET['search'] . '%';
        $params[] = $searchTerm;
        $params[] = $searchTerm;
        $params[] = $searchTerm;
    }
    
    $whereClause = !empty($where) ? 'WHERE ' . implode(' AND ', $where) : '';
    
    // Pagination
    $page = max(1, (int)($_GET['page'] ?? 1));
    $perPage = min(200, max(1, (int)($_GET['per_page'] ?? 50)));
    $offset = ($page - 1) * $perPage;
    
    // Total Count
    $countParams = $params;
    $countRow = Database::queryOne(
        "SELECT COUNT(*) as total FROM activity_log a {$whereClause}",
        $countParams
    );
    $total = (int)($countRow['total'] ?? 0);
    
    // Daten abrufen
    $items = Database::query(
        "SELECT a.id, a.user_id, a.username, a.action_category, a.action, 
                a.entity_type, a.entity_id, a.description, a.details,
                a.ip_address, a.status, a.duration_ms, a.created_at
         FROM activity_log a
         {$whereClause}
         ORDER BY a.created_at DESC
         LIMIT {$perPage} OFFSET {$offset}",
        $params
    );
    
    // Details JSON dekodieren
    foreach ($items as &$item) {
        if ($item['details']) {
            $item['details'] = json_decode($item['details'], true);
        }
    }
    unset($item);
    
    json_success([
        'items' => $items,
        'total' => $total,
        'page' => $page,
        'per_page' => $perPage,
        'total_pages' => ceil($total / $perPage)
    ]);
}

/**
 * GET /activity/stats - Statistiken
 * 
 * Gibt zurueck:
 * - Aktionen pro Kategorie (letzte 24h, 7 Tage, 30 Tage)
 * - Top-Nutzer nach Aktivitaet
 * - Haeufigste Aktionen
 * - Fehler/Denied pro Tag
 */
function handleActivityStats(): void {
    // Aktionen letzte 24 Stunden nach Kategorie
    $last24h = Database::query(
        "SELECT action_category, COUNT(*) as count 
         FROM activity_log 
         WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) 
         GROUP BY action_category 
         ORDER BY count DESC"
    );
    
    // Aktionen letzte 7 Tage nach Kategorie
    $last7d = Database::query(
        "SELECT action_category, COUNT(*) as count 
         FROM activity_log 
         WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) 
         GROUP BY action_category 
         ORDER BY count DESC"
    );
    
    // Top 10 aktivste Nutzer (letzte 7 Tage)
    $topUsers = Database::query(
        "SELECT username, user_id, COUNT(*) as action_count 
         FROM activity_log 
         WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND user_id IS NOT NULL
         GROUP BY user_id, username 
         ORDER BY action_count DESC 
         LIMIT 10"
    );
    
    // Haeufigste Aktionen (letzte 7 Tage)
    $topActions = Database::query(
        "SELECT action_category, action, COUNT(*) as count 
         FROM activity_log 
         WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) 
         GROUP BY action_category, action 
         ORDER BY count DESC 
         LIMIT 15"
    );
    
    // Fehler/Denied letzte 7 Tage pro Tag
    $errors = Database::query(
        "SELECT DATE(created_at) as date, status, COUNT(*) as count 
         FROM activity_log 
         WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) AND status IN ('error', 'denied')
         GROUP BY DATE(created_at), status 
         ORDER BY date DESC"
    );
    
    // Gesamt-Zaehler
    $totals = Database::queryOne(
        "SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
            SUM(CASE WHEN status = 'denied' THEN 1 ELSE 0 END) as denied_count
         FROM activity_log"
    );
    
    json_success([
        'last_24h' => $last24h,
        'last_7d' => $last7d,
        'top_users' => $topUsers,
        'top_actions' => $topActions,
        'errors_by_day' => $errors,
        'totals' => $totals
    ]);
}
