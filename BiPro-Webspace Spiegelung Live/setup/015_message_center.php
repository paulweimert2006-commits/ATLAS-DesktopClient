<?php
/**
 * Migration 015: Mitteilungszentrale (Message Center)
 * 
 * Erstellt Tabellen fuer:
 * - messages (System- und Admin-Mitteilungen)
 * - message_reads (Per-User Lesestatus)
 * - private_conversations (1:1 Chats)
 * - private_messages (Chat-Nachrichten mit receiver_id)
 * 
 * Voraussetzungen:
 * - users-Tabelle mit PRIMARY KEY users.id (INT)
 * - InnoDB, utf8mb4
 * 
 * Ausfuehren via:
 * https://acencia.info/setup/015_message_center.php?token=BiPro2025Setup!
 * 
 * NACH AUSFUEHRUNG DIESE DATEI LOESCHEN!
 */

$expected_token = 'BiPro2025Setup!';
if (!isset($_GET['token']) || $_GET['token'] !== $expected_token) {
    http_response_code(403);
    die('Zugriff verweigert. Token erforderlich.');
}

require_once __DIR__ . '/../api/config.php';

echo "<pre>\n";
echo "=== Migration 015: Mitteilungszentrale (Message Center) ===\n\n";

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

    // ============================================================
    // 1. messages - System- und Admin-Mitteilungen
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'messages'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'messages' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE `messages` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `title` VARCHAR(500) NOT NULL,
                `description` TEXT NULL,
                `severity` ENUM('info','warning','error','critical') NOT NULL DEFAULT 'info',
                `source` VARCHAR(100) NOT NULL,
                `sender_name` VARCHAR(100) NOT NULL,
                `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `expires_at` DATETIME NULL,
                PRIMARY KEY (`id`),
                INDEX `idx_created_at` (`created_at`),
                INDEX `idx_expires_at` (`expires_at`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'messages' erstellt.\n";
    }

    // ============================================================
    // 2. message_reads - Per-User Lesestatus fuer Mitteilungen
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'message_reads'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'message_reads' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE `message_reads` (
                `message_id` INT NOT NULL,
                `user_id` INT NOT NULL,
                `read_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`message_id`, `user_id`),
                INDEX `idx_user_read` (`user_id`, `read_at`),
                CONSTRAINT `fk_message_reads_message`
                    FOREIGN KEY (`message_id`) REFERENCES `messages`(`id`) ON DELETE CASCADE,
                CONSTRAINT `fk_message_reads_user`
                    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'message_reads' erstellt.\n";
    }

    // ============================================================
    // 3. private_conversations - 1:1 Chats
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'private_conversations'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'private_conversations' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE `private_conversations` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `user1_id` INT NOT NULL,
                `user2_id` INT NOT NULL,
                `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (`id`),
                UNIQUE KEY `uniq_users` (`user1_id`, `user2_id`),
                INDEX `idx_updated_at` (`updated_at`),
                CONSTRAINT `fk_private_conv_user1`
                    FOREIGN KEY (`user1_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
                CONSTRAINT `fk_private_conv_user2`
                    FOREIGN KEY (`user2_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'private_conversations' erstellt.\n";
    }

    // ============================================================
    // 4. private_messages - Chat-Nachrichten
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'private_messages'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'private_messages' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE `private_messages` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `conversation_id` INT NOT NULL,
                `sender_id` INT NOT NULL,
                `receiver_id` INT NOT NULL,
                `content` TEXT NOT NULL,
                `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `read_at` DATETIME NULL,
                PRIMARY KEY (`id`),
                INDEX `idx_conversation_created` (`conversation_id`, `created_at`),
                INDEX `idx_receiver_unread` (`receiver_id`, `read_at`),
                INDEX `idx_created_at` (`created_at`),
                CONSTRAINT `fk_private_msg_conversation`
                    FOREIGN KEY (`conversation_id`) REFERENCES `private_conversations`(`id`) ON DELETE CASCADE,
                CONSTRAINT `fk_private_msg_sender`
                    FOREIGN KEY (`sender_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
                CONSTRAINT `fk_private_msg_receiver`
                    FOREIGN KEY (`receiver_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'private_messages' erstellt.\n";
    }

    echo "\n=== Migration 015 abgeschlossen ===\n";
    echo "\nVerifikation:\n";

    // Verifikation: Alle 4 Tabellen pruefen
    $tables = ['messages', 'message_reads', 'private_conversations', 'private_messages'];
    $allOk = true;
    foreach ($tables as $table) {
        $stmt = $pdo->query("SHOW TABLES LIKE '$table'");
        if ($stmt->fetch()) {
            echo "  [✓] $table\n";
        } else {
            echo "  [✗] $table FEHLT!\n";
            $allOk = false;
        }
    }

    if ($allOk) {
        echo "\nAlle 4 Tabellen erfolgreich erstellt.\n";
        echo "DIESE DATEI JETZT LOESCHEN!\n";
    } else {
        echo "\nWARNUNG: Nicht alle Tabellen wurden erstellt!\n";
    }

} catch (Throwable $e) {
    echo "\nERROR: Migration 015 fehlgeschlagen: " . $e->getMessage() . "\n";
    echo "Stack: " . $e->getTraceAsString() . "\n";
    exit(1);
}

echo "</pre>\n";
