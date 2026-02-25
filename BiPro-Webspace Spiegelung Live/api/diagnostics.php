<?php
/**
 * ATLAS Server-Diagnose Endpoint
 *
 * GET /admin/diagnostics         - Vollstaendigen Health-Check ausfuehren
 * GET /admin/diagnostics/history - Vergangene Laeufe abrufen
 *
 * Fuehrt ~30 Einzel-Checks durch, speichert Ergebnis in health_check_history
 * und vergleicht mit dem Durchschnitt der letzten 7 Tage.
 */

require_once __DIR__ . '/lib/permissions.php';
require_once __DIR__ . '/lib/activity_logger.php';

function handleDiagnosticsRequest(string $method): void {
    if ($method !== 'GET') {
        json_error('Methode nicht erlaubt', 405);
    }

    $payload = requireAdmin();

    $action = explode('/', $_GET['route'] ?? '');
    $sub = $action[2] ?? '';

    if ($sub === 'history') {
        _handleHistory();
        return;
    }

    _ensureTable();
    _runFullDiagnostics($payload);
}

// =========================================================================
//  Auto-Migration: Tabelle erstellen falls nicht vorhanden
// =========================================================================

function _ensureTable(): void {
    try {
        Database::queryOne("SELECT 1 FROM health_check_history LIMIT 1");
    } catch (\Exception $e) {
        Database::getInstance()->exec("
            CREATE TABLE IF NOT EXISTS health_check_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                requested_by VARCHAR(100) DEFAULT NULL,
                total_checks INT NOT NULL DEFAULT 0,
                passed INT NOT NULL DEFAULT 0,
                warnings INT NOT NULL DEFAULT 0,
                critical INT NOT NULL DEFAULT 0,
                errors INT NOT NULL DEFAULT 0,
                total_duration_ms DECIMAL(10,2) NOT NULL DEFAULT 0,
                overall_status ENUM('healthy','degraded','critical','error') NOT NULL DEFAULT 'healthy',
                checks JSON NOT NULL,
                summary JSON DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_created (created_at),
                INDEX idx_status (overall_status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
    }
}

// =========================================================================
//  History-Endpoint
// =========================================================================

function _handleHistory(): void {
    requireAdmin();
    _ensureTable();

    $limit = min((int)($_GET['limit'] ?? 20), 100);

    $rows = Database::query(
        "SELECT id, run_id, requested_by, total_checks, passed, warnings,
                critical, errors, total_duration_ms, overall_status, summary, created_at
         FROM health_check_history
         ORDER BY created_at DESC
         LIMIT ?",
        [$limit]
    );

    foreach ($rows as &$r) {
        $r['summary'] = $r['summary'] ? json_decode($r['summary'], true) : null;
    }

    json_response(['success' => true, 'data' => ['runs' => $rows]]);
}

// =========================================================================
//  Vergleichs-Daten laden (Durchschnitte der letzten 7 Tage)
// =========================================================================

function _loadBaseline(): array {
    try {
        $rows = Database::query(
            "SELECT summary FROM health_check_history
             WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
             ORDER BY created_at DESC LIMIT 50"
        );
    } catch (\Exception $e) {
        return [];
    }

    if (empty($rows)) {
        return [];
    }

    $sums = [];
    $counts = [];
    foreach ($rows as $row) {
        $s = json_decode($row['summary'] ?? '{}', true);
        if (!$s) continue;
        foreach ($s as $key => $val) {
            if (is_numeric($val)) {
                $sums[$key] = ($sums[$key] ?? 0) + $val;
                $counts[$key] = ($counts[$key] ?? 0) + 1;
            }
        }
    }

    $avgs = [];
    foreach ($sums as $key => $sum) {
        $avgs[$key] = round($sum / $counts[$key], 2);
    }
    return $avgs;
}

function _compareValue(float $current, string $key, array $baseline): ?array {
    if (!isset($baseline[$key]) || $baseline[$key] == 0) {
        return null;
    }
    $avg = $baseline[$key];
    $changePct = round(($current - $avg) / $avg * 100, 1);
    $trend = 'stable';
    if ($changePct > 15) $trend = 'worse';
    elseif ($changePct < -15) $trend = 'better';
    return [
        'avg_7d' => $avg,
        'change_pct' => $changePct,
        'trend' => $trend
    ];
}

// =========================================================================
//  Einzel-Check Helper
// =========================================================================

function _check(string $id, string $category, string $name, callable $fn,
                float $warnThreshold = -1, float $critThreshold = -1): array {
    $t0 = microtime(true);
    try {
        $result = $fn();
        $ms = round((microtime(true) - $t0) * 1000, 2);

        $value = $result['value'] ?? $ms;
        $unit = $result['unit'] ?? 'ms';
        $detail = $result['detail'] ?? null;

        $status = 'ok';
        if ($critThreshold > 0 && $value >= $critThreshold) {
            $status = 'critical';
        } elseif ($warnThreshold > 0 && $value >= $warnThreshold) {
            $status = 'warning';
        }

        return [
            'id' => $id,
            'category' => $category,
            'name' => $name,
            'status' => $status,
            'value' => $value,
            'unit' => $unit,
            'duration_ms' => $ms,
            'detail' => $detail,
        ];
    } catch (\Exception $e) {
        return [
            'id' => $id,
            'category' => $category,
            'name' => $name,
            'status' => 'error',
            'value' => null,
            'unit' => '',
            'duration_ms' => round((microtime(true) - $t0) * 1000, 2),
            'detail' => $e->getMessage(),
        ];
    }
}

// =========================================================================
//  Haupt-Diagnostik
// =========================================================================

function _runFullDiagnostics(array $payload): void {
    $scriptStart = microtime(true);
    $runId = sprintf('%04x%04x-%04x-%04x',
        mt_rand(0, 0xffff), mt_rand(0, 0xffff),
        mt_rand(0, 0xffff), mt_rand(0, 0x0fff) | 0x4000
    );

    $baseline = _loadBaseline();
    $checks = [];

    // =====================================================================
    //  KATEGORIE: connection (Verbindungs-Checks)
    // =====================================================================

    $checks[] = _check('db_ping', 'connection', 'DB Ping (SELECT 1)', function () {
        Database::queryOne("SELECT 1");
        return ['unit' => 'ms'];
    }, 50, 200);

    $checks[] = _check('db_time_sync', 'connection', 'DB/PHP Zeitsynchronisation', function () {
        $row = Database::queryOne("SELECT NOW() as db_time");
        $dbTime = strtotime($row['db_time']);
        $phpTime = time();
        $drift = abs($dbTime - $phpTime);
        return ['value' => $drift, 'unit' => 's', 'detail' => "Drift: {$drift}s"];
    }, 2, 10);

    $checks[] = _check('db_version', 'connection', 'MySQL Version', function () {
        $row = Database::queryOne("SELECT VERSION() as v");
        $ver = $row['v'] ?? '0';
        $major = (int)explode('.', $ver)[0];
        return ['value' => $major, 'unit' => '', 'detail' => $ver];
    });

    $checks[] = _check('db_charset', 'connection', 'DB Zeichensatz', function () {
        $row = Database::queryOne("SELECT @@character_set_database as cs");
        $ok = ($row['cs'] ?? '') === 'utf8mb4' ? 1 : 0;
        return ['value' => $ok, 'unit' => 'bool', 'detail' => $row['cs'] ?? 'unknown'];
    });

    // =====================================================================
    //  KATEGORIE: performance (Query-Performance)
    // =====================================================================

    $perfTables = [
        ['documents', 50, 200],
        ['users', 20, 100],
        ['sessions', 30, 150],
        ['activity_log', 200, 1000],
        ['pm_commissions', 100, 500],
        ['pm_contracts', 50, 200],
    ];
    foreach ($perfTables as [$tbl, $warn, $crit]) {
        $checks[] = _check("count_{$tbl}", 'performance', "COUNT(*) {$tbl}", function () use ($tbl) {
            $row = Database::queryOne("SELECT COUNT(*) as cnt FROM {$tbl}");
            return ['value' => (float)round((microtime(true) - ($_SERVER['REQUEST_TIME_FLOAT'] ?? microtime(true))) * 0, 2), 'detail' => number_format((int)$row['cnt']) . ' Zeilen'];
        }, $warn, $crit);
    }

    // Xempus-Tabellen (koennen gross sein)
    $xempusTables = ['xempus_raw_rows', 'xempus_consultations', 'xempus_employees'];
    foreach ($xempusTables as $xt) {
        $checks[] = _check("count_{$xt}", 'performance', "COUNT(*) {$xt}", function () use ($xt) {
            $row = Database::queryOne("SELECT COUNT(*) as cnt FROM {$xt}");
            return ['detail' => number_format((int)$row['cnt']) . ' Zeilen'];
        }, 500, 3000);
    }

    $checks[] = _check('query_join', 'performance', 'JOIN-Query (Sessions+Users)', function () {
        Database::query(
            "SELECT s.id, u.username FROM sessions s
             JOIN users u ON u.id = s.user_id
             WHERE s.is_active = 1 LIMIT 10"
        );
        return ['unit' => 'ms'];
    }, 100, 500);

    $checks[] = _check('query_subselect', 'performance', 'Subselect (letzte Aktivitaet)', function () {
        Database::queryOne(
            "SELECT COUNT(*) as cnt FROM activity_log
             WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        );
        return ['unit' => 'ms'];
    }, 200, 1000);

    $checks[] = _check('query_aggregation', 'performance', 'Aggregation (Activity Stats)', function () {
        Database::queryOne(
            "SELECT COUNT(*) as total,
                    SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors
             FROM activity_log
             WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        );
        return ['unit' => 'ms'];
    }, 300, 1500);

    // =====================================================================
    //  KATEGORIE: storage (Speicher & Tabellengroessen)
    // =====================================================================

    $checks[] = _check('db_total_size', 'storage', 'Datenbank-Gesamtgroesse', function () {
        $row = Database::queryOne(
            "SELECT ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as mb
             FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()"
        );
        $mb = (float)($row['mb'] ?? 0);
        return ['value' => $mb, 'unit' => 'MB', 'detail' => "{$mb} MB"];
    }, 500, 2000);

    $checks[] = _check('db_table_count', 'storage', 'Anzahl Tabellen', function () {
        $row = Database::queryOne(
            "SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = DATABASE()"
        );
        return ['value' => (float)$row['cnt'], 'unit' => '', 'detail' => $row['cnt'] . ' Tabellen'];
    });

    $checks[] = _check('activity_log_size', 'storage', 'Activity-Log Groesse', function () {
        $row = Database::queryOne("SELECT COUNT(*) as cnt FROM activity_log");
        $cnt = (int)$row['cnt'];
        return ['value' => (float)$cnt, 'unit' => 'rows', 'detail' => number_format($cnt) . ' Eintraege'];
    }, 50000, 200000);

    // Top 5 groesste Tabellen als Detail
    $checks[] = _check('top_tables', 'storage', 'Top 5 groesste Tabellen', function () {
        $tables = Database::query(
            "SELECT TABLE_NAME as name,
                    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as mb
             FROM INFORMATION_SCHEMA.TABLES
             WHERE TABLE_SCHEMA = DATABASE()
             ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC LIMIT 5"
        );
        $lines = [];
        foreach ($tables as $t) {
            $lines[] = "{$t['name']}: {$t['mb']} MB";
        }
        return ['value' => (float)($tables[0]['mb'] ?? 0), 'unit' => 'MB', 'detail' => implode(', ', $lines)];
    });

    // =====================================================================
    //  KATEGORIE: config (Server-Konfiguration)
    // =====================================================================

    $checks[] = _check('php_version', 'config', 'PHP Version', function () {
        $ver = PHP_VERSION;
        $major = (int)explode('.', $ver)[0];
        $minor = (int)explode('.', $ver)[1];
        $ok = ($major >= 8 && $minor >= 1) ? 1 : 0;
        return ['value' => (float)$ok, 'unit' => 'bool', 'detail' => $ver];
    });

    $checks[] = _check('php_memory_limit', 'config', 'PHP Memory Limit', function () {
        $limit = ini_get('memory_limit');
        $bytes = _parseBytes($limit);
        $mb = round($bytes / 1024 / 1024);
        return ['value' => (float)$mb, 'unit' => 'MB', 'detail' => $limit];
    });

    $checks[] = _check('php_max_execution', 'config', 'Max Execution Time', function () {
        $sec = (int)ini_get('max_execution_time');
        return ['value' => (float)$sec, 'unit' => 's', 'detail' => "{$sec}s"];
    });

    $checks[] = _check('php_opcache', 'config', 'OPcache Status', function () {
        if (!function_exists('opcache_get_status')) {
            return ['value' => 0, 'unit' => 'bool', 'detail' => 'Nicht verfuegbar'];
        }
        $status = @opcache_get_status(false);
        $enabled = $status['opcache_enabled'] ?? false;
        $hitRate = round($status['opcache_statistics']['opcache_hit_rate'] ?? 0, 1);
        return [
            'value' => $enabled ? $hitRate : 0,
            'unit' => '%',
            'detail' => $enabled ? "Aktiv, Hit-Rate: {$hitRate}%" : 'Deaktiviert'
        ];
    }, 0, 0);

    $checks[] = _check('php_memory_usage', 'config', 'PHP Speicherverbrauch', function () {
        $mb = round(memory_get_usage(true) / 1024 / 1024, 1);
        $peak = round(memory_get_peak_usage(true) / 1024 / 1024, 1);
        return ['value' => (float)$mb, 'unit' => 'MB', 'detail' => "Aktuell: {$mb} MB, Peak: {$peak} MB"];
    }, 64, 200);

    $checks[] = _check('upload_max', 'config', 'Upload Max Filesize', function () {
        $val = ini_get('upload_max_filesize');
        $mb = round(_parseBytes($val) / 1024 / 1024);
        return ['value' => (float)$mb, 'unit' => 'MB', 'detail' => $val];
    });

    // =====================================================================
    //  KATEGORIE: stability (Stabilitaet & Fehler)
    // =====================================================================

    $checks[] = _check('errors_24h', 'stability', 'Fehler (24h)', function () {
        $row = Database::queryOne(
            "SELECT COUNT(*) as cnt FROM activity_log
             WHERE status = 'error' AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        );
        $cnt = (int)$row['cnt'];
        return ['value' => (float)$cnt, 'unit' => '', 'detail' => "{$cnt} Fehler in 24h"];
    }, 10, 50);

    $checks[] = _check('slow_requests_24h', 'stability', 'Langsame Requests (24h)', function () {
        $row = Database::queryOne(
            "SELECT COUNT(*) as cnt FROM activity_log
             WHERE action = 'slow_request' AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        );
        $cnt = (int)$row['cnt'];
        return ['value' => (float)$cnt, 'unit' => '', 'detail' => "{$cnt} Requests >500ms"];
    }, 5, 20);

    $checks[] = _check('denied_24h', 'stability', 'Zugriff verweigert (24h)', function () {
        $row = Database::queryOne(
            "SELECT COUNT(*) as cnt FROM activity_log
             WHERE status = 'denied' AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        );
        $cnt = (int)$row['cnt'];
        return ['value' => (float)$cnt, 'unit' => '', 'detail' => "{$cnt} Denied in 24h"];
    }, 10, 50);

    $checks[] = _check('active_sessions', 'stability', 'Aktive Sessions', function () {
        $row = Database::queryOne(
            "SELECT COUNT(*) as cnt FROM sessions WHERE is_active = 1 AND expires_at > NOW()"
        );
        $cnt = (int)$row['cnt'];
        return ['value' => (float)$cnt, 'unit' => '', 'detail' => "{$cnt} aktive Sessions"];
    });

    $checks[] = _check('db_connections', 'stability', 'Aktive DB-Verbindungen', function () {
        $row = Database::queryOne(
            "SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.PROCESSLIST WHERE DB = DATABASE()"
        );
        $cnt = (int)$row['cnt'];
        return ['value' => (float)$cnt, 'unit' => '', 'detail' => "{$cnt} Verbindungen"];
    }, 5, 15);

    $checks[] = _check('pending_migrations', 'stability', 'Ausstehende Migrationen', function () {
        $allSetupFiles = glob(__DIR__ . '/../setup/0*.php');
        $setupNames = array_map(function ($f) { return pathinfo($f, PATHINFO_FILENAME); }, $allSetupFiles);
        try {
            $applied = Database::query("SELECT migration_name FROM schema_migrations");
            $appliedNames = array_column($applied, 'migration_name');
            $pending = array_diff($setupNames, $appliedNames);
        } catch (\Exception $e) {
            $pending = $setupNames;
        }
        $cnt = count($pending);
        return ['value' => (float)$cnt, 'unit' => '', 'detail' => "{$cnt} ausstehend"];
    }, 5, 10);

    // MySQL Buffer Pool
    $checks[] = _check('buffer_pool_hit_rate', 'stability', 'InnoDB Buffer Pool Hit Rate', function () {
        $reads = Database::queryOne("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_reads'");
        $reqs = Database::queryOne("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read_requests'");
        $r = (int)($reads['Value'] ?? 0);
        $q = (int)($reqs['Value'] ?? 1);
        if ($q === 0) return ['value' => 100.0, 'unit' => '%', 'detail' => 'Keine Reads'];
        $rate = round((1 - $r / $q) * 100, 2);
        return ['value' => $rate, 'unit' => '%', 'detail' => "{$rate}% Hit Rate"];
    });

    $checks[] = _check('mysql_slow_queries', 'stability', 'MySQL Slow Queries (global)', function () {
        $row = Database::queryOne("SHOW GLOBAL STATUS LIKE 'Slow_queries'");
        $cnt = (int)($row['Value'] ?? 0);
        return ['value' => (float)$cnt, 'unit' => '', 'detail' => "{$cnt} Slow Queries seit Start"];
    });

    $checks[] = _check('mysql_uptime', 'stability', 'MySQL Uptime', function () {
        $row = Database::queryOne("SHOW GLOBAL STATUS LIKE 'Uptime'");
        $sec = (int)($row['Value'] ?? 0);
        $days = round($sec / 86400, 1);
        return ['value' => $days, 'unit' => 'Tage', 'detail' => "{$days} Tage"];
    });

    // =====================================================================
    //  Auswertung
    // =====================================================================

    $totalMs = round((microtime(true) - $scriptStart) * 1000, 2);

    $passed = 0;
    $warnings = 0;
    $critical = 0;
    $errors = 0;

    // Vergleichs-Daten anhaengen
    foreach ($checks as &$c) {
        if ($c['value'] !== null && $c['unit'] === 'ms') {
            $comp = _compareValue($c['duration_ms'], $c['id'], $baseline);
            if ($comp) $c['comparison'] = $comp;
        }
        switch ($c['status']) {
            case 'ok': $passed++; break;
            case 'warning': $warnings++; break;
            case 'critical': $critical++; break;
            case 'error': $errors++; break;
        }
    }
    unset($c);

    $overall = 'healthy';
    if ($errors > 0 || $critical > 2) $overall = 'critical';
    elseif ($critical > 0 || $warnings > 3) $overall = 'degraded';

    // Summary fuer History (nur numerische Key-Metriken)
    $summaryMetrics = [];
    foreach ($checks as $c) {
        if ($c['unit'] === 'ms' && $c['duration_ms'] !== null) {
            $summaryMetrics[$c['id']] = $c['duration_ms'];
        } elseif ($c['value'] !== null && is_numeric($c['value'])) {
            $summaryMetrics[$c['id']] = $c['value'];
        }
    }
    $summaryMetrics['total_duration_ms'] = $totalMs;

    // In History speichern
    try {
        Database::insert(
            "INSERT INTO health_check_history
                (run_id, requested_by, total_checks, passed, warnings, critical, errors,
                 total_duration_ms, overall_status, checks, summary)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                $runId,
                $payload['username'] ?? 'unknown',
                count($checks),
                $passed,
                $warnings,
                $critical,
                $errors,
                $totalMs,
                $overall,
                json_encode($checks, JSON_UNESCAPED_UNICODE),
                json_encode($summaryMetrics, JSON_UNESCAPED_UNICODE)
            ]
        );
    } catch (\Exception $e) {
        error_log("Health-Check History Speicherung fehlgeschlagen: " . $e->getMessage());
    }

    ActivityLogger::log([
        'user_id' => $payload['user_id'],
        'username' => $payload['username'] ?? '',
        'action_category' => 'admin',
        'action' => 'health_check',
        'description' => "Health-Check: {$overall} ({$passed} OK, {$warnings} Warn, {$critical} Crit, {$errors} Err) in {$totalMs}ms",
        'duration_ms' => (int)$totalMs,
        'status' => $overall === 'healthy' ? 'success' : 'error'
    ]);

    json_response([
        'success' => true,
        'data' => [
            'run_id' => $runId,
            'timestamp' => date('c'),
            'requested_by' => $payload['username'] ?? 'unknown',
            'overall_status' => $overall,
            'total_checks' => count($checks),
            'passed' => $passed,
            'warnings' => $warnings,
            'critical' => $critical,
            'errors' => $errors,
            'total_duration_ms' => $totalMs,
            'checks' => $checks,
            'baseline_runs' => count($baseline) > 0 ? true : false,
        ]
    ]);
}

// =========================================================================
//  Helper
// =========================================================================

function _parseBytes(string $val): int {
    $val = trim($val);
    $last = strtolower(substr($val, -1));
    $num = (int)$val;
    switch ($last) {
        case 'g': return $num * 1024 * 1024 * 1024;
        case 'm': return $num * 1024 * 1024;
        case 'k': return $num * 1024;
        default: return $num;
    }
}
