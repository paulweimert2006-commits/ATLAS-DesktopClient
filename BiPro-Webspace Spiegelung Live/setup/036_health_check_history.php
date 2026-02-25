<?php
/**
 * Migration 036: Health-Check-History
 *
 * Speichert Ergebnisse von Server-Diagnose-Laeufen fuer Trend-Vergleiche.
 */

require_once __DIR__ . '/../api/config.php';
require_once __DIR__ . '/../api/lib/db.php';

echo "Migration 036: Health-Check-History\n";

try {
    Database::getInstance()->exec("
        CREATE TABLE IF NOT EXISTS health_check_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            run_id VARCHAR(36) NOT NULL COMMENT 'UUID des Diagnose-Laufs',
            requested_by VARCHAR(100) DEFAULT NULL,
            total_checks INT NOT NULL DEFAULT 0,
            passed INT NOT NULL DEFAULT 0,
            warnings INT NOT NULL DEFAULT 0,
            critical INT NOT NULL DEFAULT 0,
            errors INT NOT NULL DEFAULT 0,
            total_duration_ms DECIMAL(10,2) NOT NULL DEFAULT 0,
            overall_status ENUM('healthy','degraded','critical','error') NOT NULL DEFAULT 'healthy',
            checks JSON NOT NULL COMMENT 'Alle Einzel-Check-Ergebnisse',
            summary JSON DEFAULT NULL COMMENT 'Zusammenfassende Metriken fuer Vergleich',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

            INDEX idx_created (created_at),
            INDEX idx_status (overall_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "  Tabelle health_check_history erstellt.\n";

    // Migration registrieren
    $name = pathinfo(__FILE__, PATHINFO_FILENAME);
    $existing = Database::queryOne(
        "SELECT id FROM schema_migrations WHERE migration_name = ?", [$name]
    );
    if (!$existing) {
        Database::insert(
            "INSERT INTO schema_migrations (migration_name) VALUES (?)", [$name]
        );
    }
    echo "Migration 036 erfolgreich.\n";
} catch (Exception $e) {
    echo "FEHLER: " . $e->getMessage() . "\n";
    exit(1);
}
