<?php
/**
 * Migration 010: SmartScan E-Mail System
 * 
 * Erstellt Tabellen fuer:
 * - E-Mail-Konten (SMTP/IMAP)
 * - SmartScan-Einstellungen
 * - SmartScan-Versand-Jobs + Items + Emails
 * - E-Mail-Inbox (IMAP) + Anhaenge
 * 
 * Ausfuehren via:
 * https://acencia.info/setup/010_smartscan_email.php?token=BiPro2025Setup!
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
echo "=== Migration 010: SmartScan E-Mail System ===\n\n";

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
    // 1. email_accounts - SMTP/IMAP Konten
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'email_accounts'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'email_accounts' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE email_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                account_type ENUM('smtp','imap','both') NOT NULL DEFAULT 'smtp',
                smtp_host VARCHAR(255) DEFAULT NULL,
                smtp_port INT DEFAULT 587,
                smtp_encryption ENUM('tls','ssl','none') DEFAULT 'tls',
                imap_host VARCHAR(255) DEFAULT NULL,
                imap_port INT DEFAULT 993,
                imap_encryption ENUM('tls','ssl','none') DEFAULT 'tls',
                username VARCHAR(255) NOT NULL,
                credentials_encrypted TEXT NOT NULL COMMENT 'AES-256-GCM verschluesselt',
                from_address VARCHAR(255) NOT NULL,
                from_name VARCHAR(255) DEFAULT NULL,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_by INT DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_active (is_active),
                INDEX idx_type (account_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'email_accounts' erstellt.\n";
    }

    // ============================================================
    // 2. smartscan_settings - Globale Konfiguration
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'smartscan_settings'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'smartscan_settings' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE smartscan_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                enabled TINYINT(1) NOT NULL DEFAULT 0,
                email_account_id INT DEFAULT NULL,
                target_address VARCHAR(255) DEFAULT NULL,
                subject_template VARCHAR(500) DEFAULT 'SmartScan - {box} - {date}',
                body_template TEXT DEFAULT NULL,
                send_mode_default ENUM('single','batch') NOT NULL DEFAULT 'single',
                batch_max_attachments INT NOT NULL DEFAULT 20,
                batch_max_total_mb INT NOT NULL DEFAULT 25,
                archive_after_send TINYINT(1) NOT NULL DEFAULT 0,
                recolor_after_send TINYINT(1) NOT NULL DEFAULT 0,
                recolor_color VARCHAR(20) DEFAULT NULL,
                imap_auto_import TINYINT(1) NOT NULL DEFAULT 0,
                imap_filter_mode ENUM('all','keyword') NOT NULL DEFAULT 'all',
                imap_filter_keyword VARCHAR(255) DEFAULT 'ATLASabruf',
                imap_sender_mode ENUM('all','whitelist') NOT NULL DEFAULT 'all',
                imap_allowed_senders TEXT DEFAULT NULL COMMENT 'Kommagetrennte E-Mail-Adressen',
                imap_poll_account_id INT DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_ss_email_account FOREIGN KEY (email_account_id) REFERENCES email_accounts(id) ON DELETE SET NULL,
                CONSTRAINT fk_ss_imap_account FOREIGN KEY (imap_poll_account_id) REFERENCES email_accounts(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        // Default-Eintrag anlegen
        $pdo->exec("INSERT INTO smartscan_settings (id, enabled) VALUES (1, 0)");
        echo "[OK] Tabelle 'smartscan_settings' erstellt + Default-Eintrag.\n";
    }

    // ============================================================
    // 3. smartscan_jobs - Versand-Auftraege
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'smartscan_jobs'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'smartscan_jobs' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE smartscan_jobs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                created_by_user_id INT NOT NULL,
                created_by_username VARCHAR(100) NOT NULL,
                mode ENUM('single','batch') NOT NULL,
                source_box VARCHAR(50) DEFAULT NULL,
                target_address VARCHAR(255) NOT NULL,
                subject_template VARCHAR(500) NOT NULL,
                body_template TEXT DEFAULT NULL,
                total_documents INT NOT NULL DEFAULT 0,
                total_emails INT NOT NULL DEFAULT 0,
                sent_emails INT NOT NULL DEFAULT 0,
                failed_emails INT NOT NULL DEFAULT 0,
                archive_after_send TINYINT(1) NOT NULL DEFAULT 0,
                recolor_after_send TINYINT(1) NOT NULL DEFAULT 0,
                recolor_color VARCHAR(20) DEFAULT NULL,
                status ENUM('queued','sending','sent','partial','failed') NOT NULL DEFAULT 'queued',
                client_request_id VARCHAR(64) DEFAULT NULL,
                error_message TEXT DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME DEFAULT NULL,
                INDEX idx_status (status),
                INDEX idx_user (created_by_user_id),
                INDEX idx_client_req (client_request_id),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'smartscan_jobs' erstellt.\n";
    }

    // ============================================================
    // 4. smartscan_emails - Tatsaechlich gesendete Mails
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'smartscan_emails'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'smartscan_emails' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE smartscan_emails (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id INT NOT NULL,
                batch_index INT NOT NULL DEFAULT 0,
                to_address VARCHAR(255) NOT NULL,
                subject VARCHAR(500) NOT NULL,
                body TEXT DEFAULT NULL,
                attachment_count INT NOT NULL DEFAULT 0,
                total_size_bytes BIGINT NOT NULL DEFAULT 0,
                smtp_message_id VARCHAR(255) DEFAULT NULL,
                smtp_response TEXT DEFAULT NULL,
                status ENUM('queued','sending','sent','failed') NOT NULL DEFAULT 'queued',
                error_message TEXT DEFAULT NULL,
                sent_at DATETIME DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_job (job_id),
                INDEX idx_status (status),
                CONSTRAINT fk_se_job FOREIGN KEY (job_id) REFERENCES smartscan_jobs(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'smartscan_emails' erstellt.\n";
    }

    // ============================================================
    // 5. smartscan_job_items - Dokumente pro Job
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'smartscan_job_items'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'smartscan_job_items' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE smartscan_job_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id INT NOT NULL,
                document_id INT NOT NULL,
                document_name_snapshot VARCHAR(500) NOT NULL,
                document_hash VARCHAR(64) DEFAULT NULL COMMENT 'SHA256',
                email_id INT DEFAULT NULL,
                archived TINYINT(1) NOT NULL DEFAULT 0,
                recolored TINYINT(1) NOT NULL DEFAULT 0,
                status ENUM('queued','attached','sent','failed') NOT NULL DEFAULT 'queued',
                error_message TEXT DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_job (job_id),
                INDEX idx_doc (document_id),
                INDEX idx_status (status),
                CONSTRAINT fk_sji_job FOREIGN KEY (job_id) REFERENCES smartscan_jobs(id) ON DELETE CASCADE,
                CONSTRAINT fk_sji_email FOREIGN KEY (email_id) REFERENCES smartscan_emails(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'smartscan_job_items' erstellt.\n";
    }

    // ============================================================
    // 6. email_inbox - Empfangene Mails (IMAP)
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'email_inbox'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'email_inbox' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE email_inbox (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email_account_id INT NOT NULL,
                message_id VARCHAR(500) DEFAULT NULL COMMENT 'RFC Message-ID fuer Deduplizierung',
                uid INT DEFAULT NULL COMMENT 'IMAP UID',
                folder VARCHAR(100) NOT NULL DEFAULT 'INBOX',
                from_address VARCHAR(255) DEFAULT NULL,
                from_name VARCHAR(255) DEFAULT NULL,
                to_address VARCHAR(255) DEFAULT NULL,
                subject VARCHAR(500) DEFAULT NULL,
                body_preview TEXT DEFAULT NULL COMMENT 'Erster Text-Teil gekuerzt',
                received_at DATETIME DEFAULT NULL,
                is_read TINYINT(1) NOT NULL DEFAULT 0,
                has_attachments TINYINT(1) NOT NULL DEFAULT 0,
                attachment_count INT NOT NULL DEFAULT 0,
                processing_status ENUM('new','processed','ignored') NOT NULL DEFAULT 'new',
                fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_account (email_account_id),
                INDEX idx_status (processing_status),
                INDEX idx_received (received_at),
                INDEX idx_message_id (message_id(191)),
                CONSTRAINT fk_ei_account FOREIGN KEY (email_account_id) REFERENCES email_accounts(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'email_inbox' erstellt.\n";
    }

    // ============================================================
    // 7. email_inbox_attachments - Anhaenge empfangener Mails
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'email_inbox_attachments'");
    if ($stmt->fetch()) {
        echo "[SKIP] Tabelle 'email_inbox_attachments' existiert bereits.\n";
    } else {
        $pdo->exec("
            CREATE TABLE email_inbox_attachments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                inbox_id INT NOT NULL,
                filename VARCHAR(500) NOT NULL,
                mime_type VARCHAR(100) DEFAULT NULL,
                file_size_bytes BIGINT NOT NULL DEFAULT 0,
                storage_path VARCHAR(500) DEFAULT NULL COMMENT 'Pfad in imap_staging/',
                content_hash VARCHAR(64) DEFAULT NULL COMMENT 'SHA256',
                document_id INT DEFAULT NULL COMMENT 'Verknuepftes Dokument nach Import',
                import_status ENUM('pending','imported','failed','skipped') NOT NULL DEFAULT 'pending',
                import_error TEXT DEFAULT NULL,
                imported_at DATETIME DEFAULT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_inbox (inbox_id),
                INDEX idx_import_status (import_status),
                CONSTRAINT fk_eia_inbox FOREIGN KEY (inbox_id) REFERENCES email_inbox(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ");
        echo "[OK] Tabelle 'email_inbox_attachments' erstellt.\n";
    }

    // ============================================================
    // imap_staging Verzeichnis erstellen
    // ============================================================
    $stagingDir = realpath(__DIR__ . '/../') . '/dokumente/imap_staging';
    if (!is_dir($stagingDir)) {
        if (mkdir($stagingDir, 0755, true)) {
            echo "[OK] Verzeichnis 'dokumente/imap_staging/' erstellt.\n";
        } else {
            echo "[WARN] Verzeichnis 'dokumente/imap_staging/' konnte nicht erstellt werden.\n";
        }
    } else {
        echo "[SKIP] Verzeichnis 'dokumente/imap_staging/' existiert bereits.\n";
    }

    // ============================================================
    // Permission smartscan_send hinzufuegen (falls permissions-Tabelle existiert)
    // ============================================================
    $stmt = $pdo->query("SHOW TABLES LIKE 'permissions'");
    if ($stmt->fetch()) {
        // Pruefen ob Permission bereits existiert
        $exists = $pdo->prepare("SELECT COUNT(*) FROM permissions WHERE permission_key = 'smartscan_send'");
        $exists->execute();
        if ((int)$exists->fetchColumn() === 0) {
            // Es gibt moeglicherweise keine permissions-Tabelle - die Berechtigungen
            // werden in der users-Tabelle als JSON gespeichert
            echo "[INFO] Permission 'smartscan_send' muss in lib/permissions.php registriert werden.\n";
        }
    } else {
        echo "[INFO] Keine separate permissions-Tabelle - Berechtigungen werden in users.permissions (JSON) gespeichert.\n";
        echo "[INFO] Permission 'smartscan_send' muss in lib/permissions.php und auth.php registriert werden.\n";
    }

    echo "\n=== Migration 010 abgeschlossen ===\n";
    echo "\nBitte diese Datei jetzt loeschen!\n";

} catch (PDOException $e) {
    echo "FEHLER: " . $e->getMessage() . "\n";
}

echo "</pre>";
