<?php
/**
 * Migration 011: SmartScan Schema-Fix
 * 
 * Behebt Diskrepanzen zwischen Migration 010 und PHP-Code.
 * Loescht alle leeren SmartScan-Tabellen und erstellt sie mit korrektem Schema
 * (passend zu email_accounts.php und smartscan.php).
 * 
 * Ausfuehren via:
 * https://acencia.info/setup/011_fix_smartscan_schema.php?token=BiPro2025Setup!
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
echo "=== Migration 011: SmartScan Schema-Fix ===\n\n";

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
    // SCHRITT 1: Pruefen ob Tabellen leer sind (Sicherheitscheck)
    // ============================================================
    echo "--- Sicherheitscheck: Tabellen leer? ---\n";

    $tablesToCheck = [
        'email_inbox_attachments',
        'email_inbox',
        'smartscan_job_items',
        'smartscan_emails',
        'smartscan_jobs',
        'smartscan_settings',
        'email_accounts',
    ];

    $hasData = false;
    foreach ($tablesToCheck as $table) {
        $stmt = $pdo->query("SHOW TABLES LIKE '$table'");
        if ($stmt->fetch()) {
            $countStmt = $pdo->query("SELECT COUNT(*) AS cnt FROM `$table`");
            $count = (int)$countStmt->fetchColumn();
            // smartscan_settings hat einen Default-Eintrag (id=1) - das ist OK
            if ($table === 'smartscan_settings' && $count <= 1) {
                echo "[OK] $table: $count Eintraege (Default-Eintrag, OK)\n";
            } elseif ($count > 0) {
                echo "[WARNUNG] $table: $count Eintraege! NICHT LEER!\n";
                $hasData = true;
            } else {
                echo "[OK] $table: leer\n";
            }
        } else {
            echo "[OK] $table: existiert nicht\n";
        }
    }

    if ($hasData) {
        echo "\n[ABBRUCH] Mindestens eine Tabelle enthaelt Daten.\n";
        echo "Migration wird NICHT ausgefuehrt um Datenverlust zu vermeiden.\n";
        echo "Bitte Daten manuell sichern und dann Tabellen leeren.\n";
        echo "</pre>";
        exit;
    }

    echo "\nAlle Tabellen leer oder nicht vorhanden. Fahre fort...\n\n";

    // ============================================================
    // SCHRITT 2: Tabellen in umgekehrter FK-Reihenfolge loeschen
    // ============================================================
    echo "--- Tabellen loeschen ---\n";

    $pdo->exec("SET FOREIGN_KEY_CHECKS = 0");

    foreach ($tablesToCheck as $table) {
        $stmt = $pdo->query("SHOW TABLES LIKE '$table'");
        if ($stmt->fetch()) {
            $pdo->exec("DROP TABLE `$table`");
            echo "[OK] $table geloescht.\n";
        } else {
            echo "[SKIP] $table existiert nicht.\n";
        }
    }

    $pdo->exec("SET FOREIGN_KEY_CHECKS = 1");
    echo "\n";

    // ============================================================
    // SCHRITT 3: Tabellen mit korrektem Schema erstellen
    // ============================================================
    echo "--- Tabellen neu erstellen ---\n";

    // 3.1 email_accounts
    $pdo->exec("
        CREATE TABLE email_accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_name VARCHAR(100) NOT NULL,
            email_address VARCHAR(255) NOT NULL,
            from_name VARCHAR(255) DEFAULT '',
            from_address VARCHAR(255) DEFAULT '',
            smtp_host VARCHAR(255) NOT NULL DEFAULT '',
            smtp_port INT NOT NULL DEFAULT 587,
            smtp_encryption VARCHAR(10) NOT NULL DEFAULT 'tls',
            imap_host VARCHAR(255) DEFAULT '',
            imap_port INT NOT NULL DEFAULT 993,
            imap_encryption VARCHAR(10) NOT NULL DEFAULT 'ssl',
            username VARCHAR(255) NOT NULL,
            credentials_encrypted TEXT NOT NULL COMMENT 'AES-256-GCM verschluesselt',
            imap_folder VARCHAR(100) NOT NULL DEFAULT 'INBOX',
            imap_filter_mode VARCHAR(20) NOT NULL DEFAULT 'all',
            imap_filter_keywords TEXT DEFAULT NULL,
            imap_sender_mode VARCHAR(20) NOT NULL DEFAULT 'all',
            imap_sender_whitelist TEXT DEFAULT NULL,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            last_poll_at DATETIME DEFAULT NULL,
            last_poll_status VARCHAR(255) DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_active (is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "[OK] email_accounts erstellt.\n";

    // 3.2 smartscan_settings
    $pdo->exec("
        CREATE TABLE smartscan_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            enabled TINYINT(1) NOT NULL DEFAULT 0,
            email_account_id INT DEFAULT NULL,
            target_address VARCHAR(255) DEFAULT NULL,
            subject_template VARCHAR(500) DEFAULT 'SmartScan {box} - {date}',
            body_template TEXT DEFAULT NULL,
            send_mode_default VARCHAR(10) NOT NULL DEFAULT 'batch',
            batch_max_attachments INT NOT NULL DEFAULT 5,
            batch_max_total_mb INT NOT NULL DEFAULT 20,
            archive_after_send TINYINT(1) NOT NULL DEFAULT 1,
            recolor_after_send TINYINT(1) NOT NULL DEFAULT 0,
            recolor_color VARCHAR(20) DEFAULT NULL,
            imap_auto_import TINYINT(1) NOT NULL DEFAULT 0,
            imap_filter_mode VARCHAR(20) NOT NULL DEFAULT 'none',
            imap_filter_keyword VARCHAR(255) DEFAULT NULL,
            imap_sender_mode VARCHAR(20) NOT NULL DEFAULT 'any',
            imap_allowed_senders TEXT DEFAULT NULL COMMENT 'Kommagetrennte E-Mail-Adressen',
            imap_poll_account_id INT DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_ss_email_account FOREIGN KEY (email_account_id) REFERENCES email_accounts(id) ON DELETE SET NULL,
            CONSTRAINT fk_ss_imap_account FOREIGN KEY (imap_poll_account_id) REFERENCES email_accounts(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    $pdo->exec("INSERT INTO smartscan_settings (id, enabled) VALUES (1, 0)");
    echo "[OK] smartscan_settings erstellt + Default-Eintrag.\n";

    // 3.3 smartscan_jobs
    $pdo->exec("
        CREATE TABLE smartscan_jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            username VARCHAR(100) NOT NULL DEFAULT '',
            status VARCHAR(20) NOT NULL DEFAULT 'queued',
            mode VARCHAR(10) NOT NULL DEFAULT 'batch',
            source_box VARCHAR(50) DEFAULT NULL,
            total_items INT NOT NULL DEFAULT 0,
            processed_items INT NOT NULL DEFAULT 0,
            sent_emails INT NOT NULL DEFAULT 0,
            failed_emails INT NOT NULL DEFAULT 0,
            settings_snapshot TEXT DEFAULT NULL COMMENT 'JSON-Snapshot der Settings bei Job-Erstellung',
            client_request_id VARCHAR(64) DEFAULT NULL,
            target_address VARCHAR(255) NOT NULL DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME DEFAULT NULL,
            INDEX idx_status (status),
            INDEX idx_user (user_id),
            INDEX idx_client_req (client_request_id),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "[OK] smartscan_jobs erstellt.\n";

    // 3.4 smartscan_emails
    $pdo->exec("
        CREATE TABLE smartscan_emails (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_id INT NOT NULL,
            to_address VARCHAR(255) NOT NULL,
            subject VARCHAR(500) NOT NULL DEFAULT '',
            body TEXT DEFAULT NULL,
            attachment_count INT NOT NULL DEFAULT 0,
            total_size BIGINT NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'queued',
            message_id VARCHAR(255) DEFAULT NULL,
            smtp_response TEXT DEFAULT NULL,
            error_message TEXT DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_job (job_id),
            INDEX idx_status (status),
            CONSTRAINT fk_se_job FOREIGN KEY (job_id) REFERENCES smartscan_jobs(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "[OK] smartscan_emails erstellt.\n";

    // 3.5 smartscan_job_items
    $pdo->exec("
        CREATE TABLE smartscan_job_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_id INT NOT NULL,
            document_id INT NOT NULL,
            original_filename VARCHAR(500) DEFAULT NULL,
            storage_path VARCHAR(500) DEFAULT NULL,
            mime_type VARCHAR(100) DEFAULT NULL,
            file_size BIGINT NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'queued',
            email_id INT DEFAULT NULL,
            document_hash VARCHAR(64) DEFAULT NULL COMMENT 'SHA256',
            archived TINYINT(1) NOT NULL DEFAULT 0,
            recolored TINYINT(1) NOT NULL DEFAULT 0,
            error_message TEXT DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_job (job_id),
            INDEX idx_doc (document_id),
            INDEX idx_status (status),
            CONSTRAINT fk_sji_job FOREIGN KEY (job_id) REFERENCES smartscan_jobs(id) ON DELETE CASCADE,
            CONSTRAINT fk_sji_email FOREIGN KEY (email_id) REFERENCES smartscan_emails(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "[OK] smartscan_job_items erstellt.\n";

    // 3.6 email_inbox
    $pdo->exec("
        CREATE TABLE email_inbox (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email_account_id INT NOT NULL,
            message_id VARCHAR(500) DEFAULT NULL COMMENT 'RFC Message-ID fuer Deduplizierung',
            subject VARCHAR(500) DEFAULT NULL,
            from_address VARCHAR(255) DEFAULT NULL,
            from_name VARCHAR(255) DEFAULT NULL,
            received_at DATETIME DEFAULT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'new',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_account (email_account_id),
            INDEX idx_status (status),
            INDEX idx_received (received_at),
            INDEX idx_message_id (message_id(191)),
            CONSTRAINT fk_ei_account FOREIGN KEY (email_account_id) REFERENCES email_accounts(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "[OK] email_inbox erstellt.\n";

    // 3.7 email_inbox_attachments
    $pdo->exec("
        CREATE TABLE email_inbox_attachments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email_inbox_id INT NOT NULL,
            original_filename VARCHAR(500) NOT NULL,
            stored_filename VARCHAR(500) DEFAULT NULL,
            stored_path VARCHAR(500) DEFAULT NULL COMMENT 'Pfad relativ zu DOCUMENTS_PATH',
            mime_type VARCHAR(100) DEFAULT NULL,
            file_size BIGINT NOT NULL DEFAULT 0,
            import_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            import_error TEXT DEFAULT NULL,
            imported_document_id INT DEFAULT NULL,
            imported_at DATETIME DEFAULT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_inbox (email_inbox_id),
            INDEX idx_import_status (import_status),
            CONSTRAINT fk_eia_inbox FOREIGN KEY (email_inbox_id) REFERENCES email_inbox(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");
    echo "[OK] email_inbox_attachments erstellt.\n";

    // ============================================================
    // imap_staging Verzeichnis sicherstellen
    // ============================================================
    $stagingDir = realpath(__DIR__ . '/../') . '/dokumente/imap_staging';
    if (!is_dir($stagingDir)) {
        if (mkdir($stagingDir, 0755, true)) {
            echo "[OK] Verzeichnis 'dokumente/imap_staging/' erstellt.\n";
        } else {
            echo "[WARN] Verzeichnis 'dokumente/imap_staging/' konnte nicht erstellt werden.\n";
        }
    } else {
        echo "[OK] Verzeichnis 'dokumente/imap_staging/' existiert bereits.\n";
    }

    echo "\n=== Migration 011 abgeschlossen ===\n";
    echo "\nBitte diese Datei jetzt loeschen!\n";

} catch (PDOException $e) {
    echo "FEHLER: " . $e->getMessage() . "\n";
}

echo "</pre>";
