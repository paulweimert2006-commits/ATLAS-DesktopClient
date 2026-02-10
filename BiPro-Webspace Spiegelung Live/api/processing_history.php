<?php
/**
 * Processing History API
 * 
 * Verwaltet den Audit-Trail fuer Dokumenten-Verarbeitung.
 * Jeder Verarbeitungsschritt wird protokolliert.
 */

require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/response.php';

/**
 * Router fuer Processing-History-Anfragen
 */
function handleProcessingHistoryRequest(string $action, string $method): void {
    $user = JWT::requireAuth();
    
    switch ($action) {
        case 'list':
            if ($method === 'GET') {
                listHistory($user);
            }
            break;
            
        case 'get':
            if ($method === 'GET' && isset($_GET['document_id'])) {
                getDocumentHistory($user, intval($_GET['document_id']));
            }
            break;
            
        case 'create':
            if ($method === 'POST') {
                createHistoryEntry($user);
            }
            break;
            
        case 'stats':
            if ($method === 'GET') {
                getHistoryStats($user);
            }
            break;
            
        case 'errors':
            if ($method === 'GET') {
                getRecentErrors($user);
            }
            break;
        
        case 'costs':
            if ($method === 'GET') {
                getCostHistory($user);
            }
            break;
        
        case 'cost_stats':
        case 'cost-stats':
            if ($method === 'GET') {
                getCostStats($user);
            }
            break;
            
        default:
            // ID als Action interpretieren (GET /processing_history/123)
            if (is_numeric($action) && $method === 'GET') {
                getDocumentHistory($user, intval($action));
            } else {
                json_error('Unbekannte Aktion: ' . $action);
            }
            break;
    }
}

/**
 * Listet History-Eintraege mit Filteroptionen
 */
function listHistory(array $user): void {
    $limit = isset($_GET['limit']) ? min(intval($_GET['limit']), 1000) : 100;
    $offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
    
    $where = ['1=1'];
    $params = [];
    
    // Filter: document_id
    if (isset($_GET['document_id'])) {
        $where[] = 'h.document_id = ?';
        $params[] = intval($_GET['document_id']);
    }
    
    // Filter: action
    if (isset($_GET['action'])) {
        $where[] = 'h.action = ?';
        $params[] = $_GET['action'];
    }
    
    // Filter: status
    if (isset($_GET['status'])) {
        $where[] = 'h.new_status = ?';
        $params[] = $_GET['status'];
    }
    
    // Filter: success
    if (isset($_GET['success'])) {
        $where[] = 'h.success = ?';
        $params[] = $_GET['success'] === 'true' || $_GET['success'] === '1' ? 1 : 0;
    }
    
    // Filter: Zeitraum
    if (isset($_GET['from'])) {
        $where[] = 'h.created_at >= ?';
        $params[] = $_GET['from'];
    }
    if (isset($_GET['to'])) {
        $where[] = 'h.created_at <= ?';
        $params[] = $_GET['to'];
    }
    
    $whereClause = implode(' AND ', $where);
    
    // Zählen
    $total = Database::queryOne(
        "SELECT COUNT(*) as count FROM processing_history h WHERE $whereClause",
        $params
    )['count'];
    
    // Daten abrufen mit Dokument-Info
    $params[] = $limit;
    $params[] = $offset;
    
    $entries = Database::query("
        SELECT 
            h.*,
            d.filename as document_filename,
            d.original_filename as document_original_filename
        FROM processing_history h
        LEFT JOIN documents d ON h.document_id = d.id
        WHERE $whereClause
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
    ", $params);
    
    // action_details JSON decodieren
    foreach ($entries as &$entry) {
        if (!empty($entry['action_details'])) {
            $entry['action_details'] = json_decode($entry['action_details'], true);
        }
    }
    
    json_success([
        'entries' => $entries,
        'total' => $total,
        'limit' => $limit,
        'offset' => $offset
    ]);
}

/**
 * Holt die komplette History eines Dokuments
 */
function getDocumentHistory(array $user, int $documentId): void {
    // Dokument pruefen
    $doc = Database::queryOne(
        "SELECT id, filename, original_filename, processing_status FROM documents WHERE id = ?",
        [$documentId]
    );
    
    if (!$doc) {
        json_error('Dokument nicht gefunden', 404);
    }
    
    // History abrufen
    $history = Database::query("
        SELECT * FROM processing_history 
        WHERE document_id = ? 
        ORDER BY created_at ASC
    ", [$documentId]);
    
    // action_details JSON decodieren
    foreach ($history as &$entry) {
        if (!empty($entry['action_details'])) {
            $entry['action_details'] = json_decode($entry['action_details'], true);
        }
    }
    
    // Statistiken berechnen
    $totalDuration = 0;
    $errorCount = 0;
    foreach ($history as $entry) {
        if ($entry['duration_ms']) {
            $totalDuration += $entry['duration_ms'];
        }
        if (!$entry['success']) {
            $errorCount++;
        }
    }
    
    json_success([
        'document' => $doc,
        'history' => $history,
        'stats' => [
            'total_steps' => count($history),
            'total_duration_ms' => $totalDuration,
            'error_count' => $errorCount
        ]
    ]);
}

/**
 * Erstellt einen neuen History-Eintrag
 */
function createHistoryEntry(array $user): void {
    $data = get_json_body();
    
    // Pflichtfelder validieren (document_id darf null sein fuer Batch-Ops)
    if (empty($data['action'])) {
        json_error('action ist erforderlich');
    }
    if (empty($data['new_status'])) {
        json_error('new_status ist erforderlich');
    }
    
    // document_id: null fuer Batch, int fuer Einzel-Dokument
    $documentId = isset($data['document_id']) && $data['document_id'] !== null 
        ? intval($data['document_id']) 
        : null;
    
    // Dokument pruefen (nur wenn document_id gesetzt)
    $doc = null;
    if ($documentId !== null && $documentId > 0) {
        $doc = Database::queryOne(
            "SELECT id, processing_status FROM documents WHERE id = ?",
            [$documentId]
        );
        
        if (!$doc) {
            json_error('Dokument nicht gefunden', 404);
        }
    }
    
    // action_details als JSON speichern
    $actionDetails = null;
    if (!empty($data['action_details'])) {
        $actionDetails = is_string($data['action_details']) 
            ? $data['action_details'] 
            : json_encode($data['action_details'], JSON_UNESCAPED_UNICODE);
    }
    
    // Eintrag erstellen
    $id = Database::insert("
        INSERT INTO processing_history 
        (document_id, previous_status, new_status, action, action_details, success, error_message, classification_source, classification_result, duration_ms, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ", [
        $documentId,
        $data['previous_status'] ?? ($doc ? $doc['processing_status'] : null),
        $data['new_status'],
        $data['action'],
        $actionDetails,
        isset($data['success']) ? ($data['success'] ? 1 : 0) : 1,
        $data['error_message'] ?? null,
        $data['classification_source'] ?? null,
        $data['classification_result'] ?? null,
        $data['duration_ms'] ?? null,
        $user['username'] ?? 'system'
    ]);
    
    json_success([
        'id' => $id,
        'message' => 'History-Eintrag erstellt'
    ]);
}

/**
 * Liefert Statistiken ueber die Verarbeitung
 */
function getHistoryStats(array $user): void {
    // Zeitraum-Filter
    $from = $_GET['from'] ?? date('Y-m-d', strtotime('-7 days'));
    $to = $_GET['to'] ?? date('Y-m-d H:i:s');
    
    // Aktionen pro Typ
    $actionStats = Database::query("
        SELECT 
            action,
            COUNT(*) as count,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count,
            AVG(duration_ms) as avg_duration_ms,
            MAX(duration_ms) as max_duration_ms
        FROM processing_history
        WHERE created_at BETWEEN ? AND ?
        GROUP BY action
        ORDER BY count DESC
    ", [$from, $to]);
    
    // Status-Verteilung
    $statusStats = Database::query("
        SELECT 
            new_status,
            COUNT(*) as count
        FROM processing_history
        WHERE created_at BETWEEN ? AND ?
        GROUP BY new_status
        ORDER BY count DESC
    ", [$from, $to]);
    
    // Klassifikationsquellen
    $classificationStats = Database::query("
        SELECT 
            classification_source,
            COUNT(*) as count
        FROM processing_history
        WHERE classification_source IS NOT NULL
          AND created_at BETWEEN ? AND ?
        GROUP BY classification_source
        ORDER BY count DESC
    ", [$from, $to]);
    
    // Gesamt-Statistiken
    $totals = Database::queryOne("
        SELECT 
            COUNT(*) as total_actions,
            COUNT(DISTINCT document_id) as unique_documents,
            SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as total_errors,
            AVG(duration_ms) as avg_duration_ms
        FROM processing_history
        WHERE created_at BETWEEN ? AND ?
    ", [$from, $to]);
    
    json_success([
        'period' => ['from' => $from, 'to' => $to],
        'totals' => $totals,
        'by_action' => $actionStats,
        'by_status' => $statusStats,
        'by_classification_source' => $classificationStats
    ]);
}

/**
 * Liefert die letzten Fehler
 */
function getRecentErrors(array $user): void {
    $limit = isset($_GET['limit']) ? min(intval($_GET['limit']), 100) : 20;
    
    $errors = Database::query("
        SELECT 
            h.*,
            d.filename as document_filename,
            d.original_filename as document_original_filename
        FROM processing_history h
        LEFT JOIN documents d ON h.document_id = d.id
        WHERE h.success = 0
        ORDER BY h.created_at DESC
        LIMIT ?
    ", [$limit]);
    
    // action_details JSON decodieren
    foreach ($errors as &$entry) {
        if (!empty($entry['action_details'])) {
            $entry['action_details'] = json_decode($entry['action_details'], true);
        }
    }
    
    json_success([
        'errors' => $errors,
        'count' => count($errors)
    ]);
}

/**
 * Liefert die Kosten-Historie (alle batch_cost_update Eintraege)
 * 
 * Gibt eine Liste aller Verarbeitungslaeufe mit Kosten-Informationen zurueck.
 * Nutzt batch_cost_update als primaere Quelle (mit tatsaechlichen Kosten),
 * faellt auf batch_complete zurueck (fuer aeltere Eintraege mit sofort-berechneten Kosten).
 */
function getCostHistory(array $user): void {
    $limit = isset($_GET['limit']) ? min(intval($_GET['limit']), 500) : 100;
    $offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
    
    $where = ["h.action IN ('batch_cost_update', 'batch_complete')"];
    $params = [];
    
    // Zeitraum-Filter
    if (isset($_GET['from'])) {
        $where[] = 'h.created_at >= ?';
        $params[] = $_GET['from'];
    }
    if (isset($_GET['to'])) {
        $where[] = 'h.created_at <= ?';
        $params[] = $_GET['to'];
    }
    
    $whereClause = implode(' AND ', $where);
    
    // Zaehlen
    $total = Database::queryOne(
        "SELECT COUNT(*) as count FROM processing_history h WHERE $whereClause",
        $params
    )['count'];
    
    // Daten abrufen
    $queryParams = array_merge($params, [$limit, $offset]);
    
    $entries = Database::query("
        SELECT h.*
        FROM processing_history h
        WHERE $whereClause
        ORDER BY h.created_at DESC
        LIMIT ? OFFSET ?
    ", $queryParams);
    
    // action_details decodieren und in einheitliches Format bringen
    $costEntries = [];
    $seenReferences = []; // Tracking welche batch_complete schon durch cost_update abgedeckt sind
    
    foreach ($entries as $entry) {
        $details = !empty($entry['action_details']) 
            ? json_decode($entry['action_details'], true) 
            : [];
        
        if ($entry['action'] === 'batch_cost_update') {
            // Primaere Quelle: Verzoegerter Kosten-Check (genauer)
            $refId = $details['reference_entry_id'] ?? null;
            if ($refId) {
                $seenReferences[$refId] = true;
            }
            
            $costEntries[] = [
                'id' => intval($entry['id']),
                'date' => $entry['created_at'],
                'total_cost_usd' => floatval($details['total_cost_usd'] ?? 0),
                'cost_per_document_usd' => floatval($details['cost_per_document_usd'] ?? 0),
                'total_documents' => intval($details['total_documents'] ?? 0),
                'successful_documents' => intval($details['successful_documents'] ?? 0),
                'failed_documents' => intval($details['failed_documents'] ?? 0),
                'duration_seconds' => floatval($details['duration_seconds'] ?? 0),
                'credits_before_usd' => floatval($details['credits_before_usd'] ?? 0),
                'credits_after_usd' => floatval($details['credits_after_usd'] ?? 0),
                'user' => $entry['created_by'] ?? 'system',
                'source' => 'delayed'  // Verzoegerter Check
            ];
        }
    }
    
    // Zweitdurchlauf: batch_complete Eintraege die NICHT durch cost_update abgedeckt sind
    // (aeltere Eintraege mit direkt berechneten Kosten)
    foreach ($entries as $entry) {
        if ($entry['action'] !== 'batch_complete') continue;
        
        $entryId = intval($entry['id']);
        if (isset($seenReferences[$entryId])) continue; // Schon durch cost_update abgedeckt
        
        $details = !empty($entry['action_details']) 
            ? json_decode($entry['action_details'], true) 
            : [];
        
        // Nur Eintraege mit tatsaechlichen Kosten-Daten
        if (isset($details['total_cost_usd']) && !($details['cost_pending'] ?? false)) {
            $costEntries[] = [
                'id' => $entryId,
                'date' => $entry['created_at'],
                'total_cost_usd' => floatval($details['total_cost_usd'] ?? 0),
                'cost_per_document_usd' => floatval($details['cost_per_document_usd'] ?? 0),
                'total_documents' => intval($details['total_documents'] ?? 0),
                'successful_documents' => intval($details['successful_documents'] ?? 0),
                'failed_documents' => intval($details['failed_documents'] ?? 0),
                'duration_seconds' => floatval($details['duration_seconds'] ?? 0),
                'credits_before_usd' => floatval($details['credits_before_usd'] ?? 0),
                'credits_after_usd' => floatval($details['credits_after_usd'] ?? 0),
                'user' => $entry['created_by'] ?? 'system',
                'source' => 'immediate'  // Sofort-Berechnung (Legacy)
            ];
        }
    }
    
    // Nach Datum sortieren (neueste zuerst)
    usort($costEntries, function($a, $b) {
        return strcmp($b['date'], $a['date']);
    });
    
    json_success([
        'entries' => $costEntries,
        'total' => count($costEntries),
        'limit' => $limit,
        'offset' => $offset
    ]);
}

/**
 * Liefert aggregierte Kosten-Statistiken
 */
function getCostStats(array $user): void {
    // Zeitraum-Filter
    $from = $_GET['from'] ?? null;
    $to = $_GET['to'] ?? date('Y-m-d H:i:s');
    
    $where = ["h.action IN ('batch_cost_update', 'batch_complete')"];
    $params = [];
    
    if ($from) {
        $where[] = 'h.created_at >= ?';
        $params[] = $from;
    }
    $where[] = 'h.created_at <= ?';
    $params[] = $to;
    
    $whereClause = implode(' AND ', $where);
    
    // Alle relevanten Eintraege holen
    $entries = Database::query("
        SELECT h.action, h.action_details, h.created_at
        FROM processing_history h
        WHERE $whereClause
        ORDER BY h.created_at DESC
    ", $params);
    
    // Kosten aggregieren (gleiche Logik wie getCostHistory)
    $totalRuns = 0;
    $totalDocs = 0;
    $totalSuccessful = 0;
    $totalFailed = 0;
    $totalCostUsd = 0.0;
    $totalDurationSeconds = 0.0;
    $seenReferences = [];
    
    // Erst batch_cost_update verarbeiten
    foreach ($entries as $entry) {
        if ($entry['action'] !== 'batch_cost_update') continue;
        
        $details = !empty($entry['action_details']) 
            ? json_decode($entry['action_details'], true) 
            : [];
        
        $refId = $details['reference_entry_id'] ?? null;
        if ($refId) {
            $seenReferences[$refId] = true;
        }
        
        $totalRuns++;
        $totalDocs += intval($details['total_documents'] ?? 0);
        $totalSuccessful += intval($details['successful_documents'] ?? 0);
        $totalFailed += intval($details['failed_documents'] ?? 0);
        $totalCostUsd += floatval($details['total_cost_usd'] ?? 0);
        $totalDurationSeconds += floatval($details['duration_seconds'] ?? 0);
    }
    
    // Dann batch_complete ohne zugehoerigen cost_update
    foreach ($entries as $entry) {
        if ($entry['action'] !== 'batch_complete') continue;
        
        $details = !empty($entry['action_details']) 
            ? json_decode($entry['action_details'], true) 
            : [];
        
        // Schon abgedeckt oder keine Kosten?
        if (isset($seenReferences[intval($entry['id'] ?? 0)])) continue;
        if (!isset($details['total_cost_usd']) || ($details['cost_pending'] ?? false)) continue;
        
        $totalRuns++;
        $totalDocs += intval($details['total_documents'] ?? 0);
        $totalSuccessful += intval($details['successful_documents'] ?? 0);
        $totalFailed += intval($details['failed_documents'] ?? 0);
        $totalCostUsd += floatval($details['total_cost_usd'] ?? 0);
        $totalDurationSeconds += floatval($details['duration_seconds'] ?? 0);
    }
    
    // Durchschnitte berechnen
    $avgCostPerDoc = $totalSuccessful > 0 ? $totalCostUsd / $totalSuccessful : 0;
    $avgCostPerRun = $totalRuns > 0 ? $totalCostUsd / $totalRuns : 0;
    $successRate = $totalDocs > 0 ? ($totalSuccessful / $totalDocs) * 100 : 0;
    
    json_success([
        'total_runs' => $totalRuns,
        'total_documents' => $totalDocs,
        'total_successful' => $totalSuccessful,
        'total_failed' => $totalFailed,
        'total_cost_usd' => round($totalCostUsd, 6),
        'avg_cost_per_document_usd' => round($avgCostPerDoc, 8),
        'avg_cost_per_run_usd' => round($avgCostPerRun, 6),
        'total_duration_seconds' => round($totalDurationSeconds, 2),
        'success_rate_percent' => round($successRate, 1),
        'period' => [
            'from' => $from,
            'to' => $to
        ]
    ]);
}
