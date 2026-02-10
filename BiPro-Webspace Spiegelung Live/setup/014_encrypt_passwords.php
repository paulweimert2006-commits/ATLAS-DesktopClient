<?php
/**
 * Migration 014: Bestehende Klartext-Passwoerter verschluesseln (SV-006)
 * 
 * Verschluesselt alle password_value-Eintraege in known_passwords
 * mit Crypto::encrypt() (AES-256-GCM).
 * 
 * Idempotent: Bereits verschluesselte Werte werden uebersprungen.
 */

require_once __DIR__ . '/../api/config.php';
require_once __DIR__ . '/../api/lib/db.php';
require_once __DIR__ . '/../api/lib/crypto.php';

echo "Migration 014: Passwoerter verschluesseln (SV-006)...\n";

try {
    $passwords = Database::query('SELECT id, password_value FROM known_passwords');
    
    $encrypted = 0;
    $skipped = 0;
    
    foreach ($passwords as $pw) {
        // Pruefe ob bereits verschluesselt (Base64 + entschluesselbar)
        try {
            Crypto::decrypt($pw['password_value']);
            $skipped++;
            echo "  ID {$pw['id']}: Bereits verschluesselt, uebersprungen\n";
            continue;
        } catch (Exception $e) {
            // Nicht entschluesselbar = Klartext, muss verschluesselt werden
        }
        
        $encValue = Crypto::encrypt($pw['password_value']);
        Database::execute(
            'UPDATE known_passwords SET password_value = ? WHERE id = ?',
            [$encValue, $pw['id']]
        );
        $encrypted++;
        echo "  ID {$pw['id']}: Verschluesselt\n";
    }
    
    echo "OK: {$encrypted} verschluesselt, {$skipped} uebersprungen.\n";
} catch (Exception $e) {
    echo "FEHLER: " . $e->getMessage() . "\n";
    exit(1);
}
