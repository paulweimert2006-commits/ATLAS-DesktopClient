<?php
/**
 * Migration 013: rate_limits Tabelle fuer SV-003 (Rate-Limiting)
 * 
 * Erstellt die Tabelle fuer fehlgeschlagene Login-Versuche.
 */

require_once __DIR__ . '/../api/config.php';
require_once __DIR__ . '/../api/lib/db.php';

echo "Migration 013: rate_limits Tabelle erstellen...\n";

try {
    Database::execute("
        CREATE TABLE IF NOT EXISTS rate_limits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ip_address VARCHAR(45) NOT NULL,
            username VARCHAR(100) DEFAULT '',
            attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_ip_time (ip_address, attempted_at),
            INDEX idx_cleanup (attempted_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ");
    
    echo "OK: rate_limits Tabelle erstellt.\n";
} catch (Exception $e) {
    echo "FEHLER: " . $e->getMessage() . "\n";
    exit(1);
}
