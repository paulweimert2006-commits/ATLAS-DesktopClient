<?php
/**
 * BiPro API - Haupt-Router
 * 
 * Alle API-Anfragen werden über diese Datei geroutet.
 * URL-Rewriting über .htaccess leitet /api/xyz hierher.
 */

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/jwt.php';

// Request-Timing: Startzeit erfassen
$_requestStartTime = $_SERVER['REQUEST_TIME_FLOAT'] ?? microtime(true);

// SV-002 Fix: Security Headers fuer alle Responses
send_security_headers();

// SV-019 Fix: Probabilistischer Log-Cleanup (1% der Requests)
require_once __DIR__ . '/lib/log_cleanup.php';
LogCleanup::maybePurge();

// CORS Pre-flight Handling
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Route aus URL extrahieren
$route = isset($_GET['route']) ? trim($_GET['route'], '/') : '';
$method = $_SERVER['REQUEST_METHOD'];

// Route-Teile
$parts = $route ? explode('/', $route) : [];
$resource = $parts[0] ?? '';
$action = $parts[1] ?? '';
$id = $parts[2] ?? '';
$subAction = $parts[3] ?? '';

// Debug-Logging (nur wenn DEBUG_MODE aktiv)
if (DEBUG_MODE) {
    error_log("API Request: $method /$route");
}

try {
    // Routing
    switch ($resource) {
        case '':
        case 'status':
            // API Status / Health Check
            // SV-023 Fix: API-Version nicht mehr im Health-Check exponieren
            $statusData = [
                'status' => 'ok',
                'timestamp' => date('c')
            ];
            try {
                $dbCheckStart = microtime(true);
                $latest = Database::queryOne("SELECT migration_name FROM schema_migrations ORDER BY id DESC LIMIT 1");
                $dbCheckMs = round((microtime(true) - $dbCheckStart) * 1000, 2);
                
                $statusData['schema_version'] = $latest ? $latest['migration_name'] : 'unknown';
                $statusData['db_response_ms'] = $dbCheckMs;
                
                $allSetupFiles = glob(__DIR__ . '/../setup/0*.php');
                $setupNames = array_map(function($f) { return pathinfo($f, PATHINFO_FILENAME); }, $allSetupFiles);
                $applied = Database::query("SELECT migration_name FROM schema_migrations");
                $appliedNames = array_column($applied, 'migration_name');
                $pending = array_diff($setupNames, $appliedNames);
                $statusData['pending_migrations'] = count($pending);
            } catch (Exception $e) {
                $statusData['schema_version'] = 'unavailable';
                $statusData['db_error'] = true;
            }
            
            // Admin-Diagnostics: Erweiterte Metriken nur mit gueltigem Admin-JWT
            $adminToken = JWT::getTokenFromHeader();
            if ($adminToken) {
                $adminPayload = JWT::verify($adminToken);
                if ($adminPayload) {
                    require_once __DIR__ . '/lib/permissions.php';
                    if (isAdmin($adminPayload['user_id'])) {
                        $diag = [];
                        
                        // DB Ping
                        try {
                            $t0 = microtime(true);
                            Database::queryOne("SELECT 1");
                            $diag['db_ping_ms'] = round((microtime(true) - $t0) * 1000, 2);
                        } catch (Exception $e) {
                            $diag['db_ping_ms'] = -1;
                        }
                        
                        // Kerntabellen-Counts
                        $tableCounts = [];
                        $countTables = ['documents', 'activity_log', 'sessions', 'users'];
                        foreach ($countTables as $tbl) {
                            try {
                                $t0 = microtime(true);
                                $row = Database::queryOne("SELECT COUNT(*) as cnt FROM {$tbl}");
                                $tableCounts[$tbl] = [
                                    'count' => (int)$row['cnt'],
                                    'duration_ms' => round((microtime(true) - $t0) * 1000, 2)
                                ];
                            } catch (Exception $e) {
                                $tableCounts[$tbl] = ['error' => true];
                            }
                        }
                        $diag['table_counts'] = $tableCounts;
                        
                        // DB-Groesse
                        try {
                            $sizeRow = Database::queryOne(
                                "SELECT ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as total_mb
                                 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()"
                            );
                            $diag['db_size_mb'] = (float)($sizeRow['total_mb'] ?? 0);
                        } catch (Exception $e) {
                            $diag['db_size_mb'] = -1;
                        }
                        
                        // Aktive DB-Verbindungen
                        try {
                            $connRow = Database::queryOne(
                                "SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.PROCESSLIST WHERE DB = DATABASE()"
                            );
                            $diag['active_db_connections'] = (int)($connRow['cnt'] ?? 0);
                        } catch (Exception $e) {
                            $diag['active_db_connections'] = -1;
                        }
                        
                        // Slow Queries (letzte 24h aus Activity Log)
                        try {
                            $slowRow = Database::queryOne(
                                "SELECT COUNT(*) as cnt FROM activity_log 
                                 WHERE action = 'slow_request' AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
                            );
                            $diag['slow_requests_24h'] = (int)($slowRow['cnt'] ?? 0);
                        } catch (Exception $e) {
                            $diag['slow_requests_24h'] = -1;
                        }
                        
                        // PHP-Info
                        $diag['php'] = [
                            'version' => PHP_VERSION,
                            'memory_usage_mb' => round(memory_get_usage(true) / 1024 / 1024, 2),
                            'memory_peak_mb' => round(memory_get_peak_usage(true) / 1024 / 1024, 2),
                            'memory_limit' => ini_get('memory_limit'),
                            'max_execution_time' => ini_get('max_execution_time'),
                            'opcache_enabled' => function_exists('opcache_get_status') ? 
                                (opcache_get_status(false)['opcache_enabled'] ?? false) : false
                        ];
                        
                        // MySQL-Version
                        try {
                            $verRow = Database::queryOne("SELECT VERSION() as v");
                            $diag['mysql_version'] = $verRow['v'] ?? 'unknown';
                        } catch (Exception $e) {
                            $diag['mysql_version'] = 'unknown';
                        }
                        
                        // Gesamtdauer der Diagnostics
                        $diag['diagnostics_duration_ms'] = round(
                            (microtime(true) - ($_requestStartTime ?? microtime(true))) * 1000, 2
                        );
                        
                        $statusData['diagnostics'] = $diag;
                    }
                }
            }
            
            json_response($statusData);
            break;
            
        case 'auth':
            require_once __DIR__ . '/auth.php';
            handleAuthRequest($action, $method);
            break;
            
        case 'documents':
            require_once __DIR__ . '/documents.php';
            // /documents/{id}/history → $action=id, $id='history'
            $docSub = $parts[2] ?? null;
            handleDocumentsRequest($action ?: $id, $method, $docSub);
            break;
            
        case 'gdv':
            require_once __DIR__ . '/gdv.php';
            handleGdvRequest($action, $id, $method);
            break;
            
        case 'vu-connections':
            require_once __DIR__ . '/credentials.php';
            // Für /vu-connections/4/credentials brauchen wir action UND id
            $vuPath = $action;
            if ($id) {
                $vuPath .= '/' . $id;
            }
            handleVuConnectionsRequest($vuPath, $method);
            break;
            
        case 'shipments':
            require_once __DIR__ . '/shipments.php';
            handleShipmentsRequest($action ?: $id, $method);
            break;
            
        case 'ai':
            require_once __DIR__ . '/ai.php';
            handleAiRequest($action, $method);
            break;
            
        case 'xml_index':
        case 'xml-index':
            require_once __DIR__ . '/xml_index.php';
            handleXmlIndexRequest($action ?: $id, $method);
            break;

        case 'bipro-events':
            require_once __DIR__ . '/bipro_events.php';
            handleBiproEventsRequest($action ?: '', $method);
            break;
            
        case 'processing_history':
        case 'processing-history':
            require_once __DIR__ . '/processing_history.php';
            handleProcessingHistoryRequest($action ?: $id, $method);
            break;
        
        case 'passwords':
            // Oeffentlicher Endpunkt: GET /passwords?type=pdf|zip
            require_once __DIR__ . '/passwords.php';
            handlePasswordsPublicRequest($method);
            break;
        
        case 'processing-settings':
            // KI-Klassifikation Einstellungen (oeffentlich: GET)
            // /processing-settings/ai
            require_once __DIR__ . '/processing_settings.php';
            handleProcessingSettingsRequest($action ?: '', $method);
            break;
        
        case 'pm':
            // Provisionsmanagement (Geschaeftsfuehrer-Ebene)
            // /pm/{action}[/{id}][/{sub}]
            require_once __DIR__ . '/provision.php';
            $pmSub = $parts[3] ?? null;
            handleProvisionRequest($action ?: null, $method, $id ?: null, $pmSub);
            break;
        
        case 'document-rules':
            // Dokumenten-Regeln (oeffentlich: GET)
            require_once __DIR__ . '/document_rules.php';
            handleDocumentRulesRequest($method);
            break;
        
        case 'smartscan':
            // SmartScan Versand + Historie
            // /smartscan/settings, /smartscan/send, /smartscan/jobs, /smartscan/jobs/{id}, /smartscan/jobs/{id}/process
            require_once __DIR__ . '/smartscan.php';
            handleSmartScanRequest($action, $id, $method);
            break;
        
        case 'email-inbox':
            // E-Mail Inbox (IMAP empfangene Mails)
            // /email-inbox, /email-inbox/{id}, /email-inbox/pending-attachments,
            // /email-inbox/attachments/{id}/download, /email-inbox/attachments/{id}/imported
            require_once __DIR__ . '/email_accounts.php';
            handleEmailInboxRequest($action ?: null, $method);
            break;
        
        case 'admin':
            // /admin/releases → separater Handler
            if ($action === 'releases') {
                require_once __DIR__ . '/releases.php';
                handleAdminReleasesRequest($id ?: null, $method, $subAction ?: null);
                break;
            }
            
            // /admin/passwords → Passwort-Verwaltung
            if ($action === 'passwords') {
                require_once __DIR__ . '/passwords.php';
                handleAdminPasswordsRequest($id ?: null, $method);
                break;
            }
            
            // /admin/email-accounts → E-Mail-Konten-Verwaltung
            if ($action === 'email-accounts') {
                require_once __DIR__ . '/email_accounts.php';
                $sub = $parts[3] ?? null;
                handleAdminEmailAccountsRequest($id ?: null, $method, $sub);
                break;
            }
            
            // /admin/smartscan → SmartScan-Einstellungen
            if ($action === 'smartscan') {
                require_once __DIR__ . '/smartscan.php';
                handleAdminSmartScanRequest($id ?: null, $method);
                break;
            }
            
            // /admin/processing-settings → KI-Klassifikation Einstellungen
            // /admin/processing-settings/ai, /admin/processing-settings/prompt-versions, 
            // /admin/processing-settings/prompt-versions/{id}/activate
            if ($action === 'processing-settings') {
                require_once __DIR__ . '/processing_settings.php';
                $psSub = $parts[3] ?? null;
                handleAdminProcessingSettingsRequest($id ?: null, $method, $psSub);
                break;
            }
            
            // /admin/ai-providers → KI-Provider-Verwaltung
            // /admin/ai-providers/{id}, /admin/ai-providers/{id}/activate, /admin/ai-providers/{id}/test
            if ($action === 'ai-providers') {
                require_once __DIR__ . '/ai_providers.php';
                $apSub = $parts[3] ?? null;
                handleAdminAiProvidersRequest($id ?: null, $method, $apSub);
                break;
            }
            
            // /admin/model-pricing → Modell-Preise
            // /admin/model-pricing/{id}
            if ($action === 'model-pricing') {
                require_once __DIR__ . '/model_pricing.php';
                handleAdminModelPricingRequest($id ?: null, $method);
                break;
            }
            
            // /admin/document-rules → Dokumenten-Regeln
            if ($action === 'document-rules') {
                require_once __DIR__ . '/document_rules.php';
                handleAdminDocumentRulesRequest($method);
                break;
            }
            
            // /admin/diagnostics → Server-Performance-Diagnose
            if ($action === 'diagnostics') {
                require_once __DIR__ . '/diagnostics.php';
                handleDiagnosticsRequest($method);
                break;
            }
            
            require_once __DIR__ . '/admin.php';
            // /admin/users → ('users', method, null)
            // /admin/users/5 → ('5', method, null)  [is_numeric → User-ID]
            // /admin/users/5/password → ('5', method, 'password')
            // /admin/permissions → ('permissions', method, null)
            $adminSub = $parts[3] ?? null;
            if ($action === 'users' && !empty($id)) {
                // /admin/users/{id}[/sub]
                handleAdminRequest($id, $method, $adminSub);
            } else {
                handleAdminRequest($action ?: null, $method, null);
            }
            break;
        
        case 'sessions':
            require_once __DIR__ . '/sessions.php';
            // /sessions, /sessions/{id}, /sessions/user/{userId}
            $extra = $parts[2] ?? null;
            handleSessionsRequest($action ?: null, $method, $extra);
            break;
        
        case 'activity':
            require_once __DIR__ . '/activity.php';
            handleActivityRequest($action ?: null, $method);
            break;
        
        case 'updates':
            // Oeffentlicher Update-Check (keine Auth erforderlich)
            require_once __DIR__ . '/releases.php';
            if ($action === 'check') {
                handleUpdateCheckRequest($method);
            } else {
                json_error('Unbekannte Updates-Aktion', 404);
            }
            break;
        
        case 'releases':
            require_once __DIR__ . '/releases.php';
            if ($action === 'latest' && $method === 'GET') {
                // Oeffentlicher Download der neuesten Version (fuer neue Nutzer)
                handleLatestDownload();
            } elseif ($action === 'download' && !empty($id) && is_numeric($id)) {
                // Oeffentlicher Download-Endpoint (nach ID)
                handleReleaseDownload((int)$id);
            } elseif (empty($action) && $method === 'GET') {
                // Oeffentliche Release-Liste (fuer Mitteilungszentrale)
                handlePublicReleasesList();
            } else {
                json_error('Unbekannte Releases-Aktion', 404);
            }
            break;
        
        case 'incoming-scans':
            // Eingehende Scan-Dokumente (Power Automate)
            // Auth: API-Key im Header X-API-Key (kein JWT)
            require_once __DIR__ . '/incoming_scans.php';
            handleIncomingScansRequest($method);
            break;
        
        case 'messages':
            // Mitteilungszentrale: System- und Admin-Mitteilungen
            // GET /messages, POST /messages, PUT /messages/read, DELETE /messages/{id}
            require_once __DIR__ . '/messages.php';
            handleMessagesRequest($action ?: '', $method);
            break;
        
        case 'chat':
            // Private 1:1 Chat-Nachrichten
            // /chat/conversations, /chat/conversations/{id}/messages, /chat/users
            require_once __DIR__ . '/chat.php';
            $chatSub = $parts[3] ?? null;
            handleChatRequest($action ?: '', $id ?: '', $method, $chatSub);
            break;
        
        case 'notifications':
            // Leichtgewichtiger Polling-Endpoint (alle 30s)
            // GET /notifications/summary
            require_once __DIR__ . '/notifications.php';
            handleNotificationsRequest($action ?: '', $method);
            break;
            
        default:
            json_error('Endpoint nicht gefunden', 404);
    }
} catch (PDOException $e) {
    error_log('Database Error: ' . $e->getMessage());
    json_error('Datenbankfehler', 500);
} catch (Exception $e) {
    error_log('API Error: ' . $e->getMessage());
    json_error($e->getMessage(), 400);
}
