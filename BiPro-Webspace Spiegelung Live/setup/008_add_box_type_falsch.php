<?php
/**
 * Migration: box_type ENUM um 'kranken' und 'falsch' erweitern
 * 
 * Problem: Die Spalte box_type war als ENUM definiert ohne 'kranken' und 'falsch'.
 * MySQL speichert bei ungueltigen ENUM-Werten leere Strings (''),
 * was dazu fuehrt dass Dokumente in 'sonstige' statt 'falsch' gezaehlt werden.
 * 
 * Ausfuehren via:
 * https://acencia.info/setup/008_add_box_type_falsch.php?token=BiPro2025Setup!
 * 
 * NACH AUSFUEHRUNG DIESE DATEI LOESCHEN!
 */

// Sicherheitstoken pruefen
$expected_token = 'BiPro2025Setup!';
if (!isset($_GET['token']) || $_GET['token'] !== $expected_token) {
    http_response_code(403);
    die('Zugriff verweigert. Token erforderlich.');
}

require_once __DIR__ . '/../api/config.php';

echo "<pre>\n";
echo "=== Migration: box_type ENUM erweitern (kranken + falsch) ===\n\n";

try {
    $pdo = new PDO(
        "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
        DB_USER,
        DB_PASS,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]
    );
    
    echo "Datenbankverbindung OK\n\n";
    
    // 1. Aktuellen Spaltentyp pruefen
    $stmt = $pdo->query("SHOW COLUMNS FROM documents LIKE 'box_type'");
    $column = $stmt->fetch();
    
    if (!$column) {
        echo "FEHLER: Spalte 'box_type' existiert nicht!\n";
        echo "Bitte zuerst Migration 005 ausfuehren.\n";
    } else {
        echo "Aktueller Typ: " . $column['Type'] . "\n";
        
        // 2. Pruefen ob 'falsch' bereits enthalten ist
        if (strpos($column['Type'], "'falsch'") !== false) {
            echo "'falsch' ist bereits im ENUM enthalten - keine Aenderung noetig.\n";
        } else {
            // 3. ENUM erweitern mit allen Box-Typen (inkl. kranken + falsch)
            $pdo->exec("
                ALTER TABLE documents 
                MODIFY COLUMN box_type ENUM(
                    'eingang',
                    'verarbeitung',
                    'roh',
                    'gdv',
                    'courtage',
                    'sach',
                    'leben',
                    'kranken',
                    'sonstige',
                    'falsch'
                ) NOT NULL DEFAULT 'sonstige'
                COMMENT 'Box in der das Dokument liegt'
            ");
            echo "ENUM erweitert um 'kranken' und 'falsch'!\n";
            
            // 4. Pruefen ob leere Strings existieren (kaputte Eintraege)
            $stmt = $pdo->query("SELECT COUNT(*) as cnt FROM documents WHERE box_type = ''");
            $row = $stmt->fetch();
            $emptyCount = (int)$row['cnt'];
            
            if ($emptyCount > 0) {
                echo "\nWARNUNG: {$emptyCount} Dokument(e) mit leerem box_type gefunden!\n";
                echo "Diese werden auf 'sonstige' gesetzt...\n";
                $fixed = $pdo->exec("UPDATE documents SET box_type = 'sonstige' WHERE box_type = ''");
                echo "{$fixed} Dokument(e) repariert.\n";
            } else {
                echo "Keine Dokumente mit leerem box_type gefunden.\n";
            }
        }
        
        // 5. Neuen Spaltentyp anzeigen
        $stmt = $pdo->query("SHOW COLUMNS FROM documents LIKE 'box_type'");
        $column = $stmt->fetch();
        echo "\nNeuer Typ: " . $column['Type'] . "\n";
    }
    
    echo "\n=== Migration abgeschlossen ===\n";
    echo "\nBitte diese Datei jetzt loeschen!\n";
    
} catch (PDOException $e) {
    echo "FEHLER: " . $e->getMessage() . "\n";
}

echo "</pre>";
