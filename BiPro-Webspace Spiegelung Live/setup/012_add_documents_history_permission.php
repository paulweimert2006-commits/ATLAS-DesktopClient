<?php
/**
 * Migration 012: Permission 'documents_history' hinzufuegen
 * 
 * Fuegt die Berechtigung 'documents_history' zur permissions-Tabelle hinzu.
 * Erlaubt Nutzern, die Aenderungshistorie einzelner Dokumente einzusehen.
 */

require_once __DIR__ . '/../api/config.php';

try {
    $pdo = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER,
        DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );

    echo "=== Migration 012: Permission 'documents_history' ===\n\n";

    // Pruefen ob Permission bereits existiert
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM permissions WHERE permission_key = 'documents_history'");
    $stmt->execute();
    
    if ((int)$stmt->fetchColumn() > 0) {
        echo "[SKIP] Permission 'documents_history' existiert bereits.\n";
    } else {
        $pdo->exec("
            INSERT INTO permissions (permission_key, name, description) 
            VALUES ('documents_history', 'Dokument-Historie einsehen', 'Erlaubt das Einsehen der Aenderungshistorie einzelner Dokumente (Verschiebungen, Downloads, etc.)')
        ");
        echo "[OK] Permission 'documents_history' hinzugefuegt.\n";
    }

    echo "\n=== Migration 012 abgeschlossen ===\n";

} catch (PDOException $e) {
    echo "[FEHLER] " . $e->getMessage() . "\n";
    exit(1);
}
