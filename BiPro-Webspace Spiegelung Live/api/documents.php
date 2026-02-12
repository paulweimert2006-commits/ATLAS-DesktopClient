<?php
/**
 * BiPro API - Dokumente
 * 
 * Endpunkte:
 * - GET /documents - Liste aller Dokumente
 * - GET /documents/stats - Box-Statistiken
 * - POST /documents - Dokument hochladen
 * - POST /documents/move - Dokumente verschieben
 * - POST /documents/colors - Bulk-Farbmarkierung setzen/entfernen
 * - GET /documents/{id} - Dokument herunterladen
 * - PUT /documents/{id} - Dokument-Metadaten aktualisieren
 * - DELETE /documents/{id} - Dokument loeschen
 */

require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/permissions.php';
require_once __DIR__ . '/lib/activity_logger.php';

function handleDocumentsRequest(string $idOrAction, string $method, ?string $sub = null): void {
    // Basis-Auth fuer alle Endpunkte
    $payload = JWT::requireAuth();
    
    switch ($method) {
        case 'GET':
            if (empty($idOrAction) || $idOrAction === 'list') {
                // Liste/Stats: Alle authentifizierten User
                ActivityLogger::logDocument($payload, 'list', null, 'Dokumentenliste abgerufen');
                listDocuments($payload);
            } elseif ($idOrAction === 'stats') {
                getBoxStats($payload);
            } elseif ($sub === 'history' && is_numeric($idOrAction)) {
                // GET /documents/{id}/history → Dokument-Historie
                getDocumentHistory($idOrAction, $payload);
            } elseif ($sub === 'info' && is_numeric($idOrAction)) {
                // GET /documents/{id}/info → Dokument-Metadaten (BUG-0013 Fix)
                getDocumentInfo($idOrAction, $payload);
            } else {
                // Download: Recht erforderlich
                if (!hasPermission($payload['user_id'], 'documents_download')) {
                    ActivityLogger::logDocument($payload, 'download_denied', (int)$idOrAction, 'Download verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Herunterladen', 403, ['required_permission' => 'documents_download']);
                }
                downloadDocument($idOrAction, $payload);
            }
            break;
            
        case 'POST':
            // POST /documents/{id}/replace → Datei ersetzen
            if ($sub === 'replace' && is_numeric($idOrAction)) {
                if (!hasPermission($payload['user_id'], 'documents_manage')) {
                    ActivityLogger::logDocument($payload, 'replace_denied', (int)$idOrAction, 'Datei-Ersetzung verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Verwalten', 403, ['required_permission' => 'documents_manage']);
                }
                replaceDocumentFile($idOrAction, $payload);
            } elseif ($idOrAction === 'move') {
                // Verschieben: documents_manage Recht
                if (!hasPermission($payload['user_id'], 'documents_manage')) {
                    ActivityLogger::logDocument($payload, 'move_denied', null, 'Verschieben verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Verwalten', 403, ['required_permission' => 'documents_manage']);
                }
                moveDocuments($payload);
            } elseif ($idOrAction === 'archive') {
                // Bulk-Archivieren: documents_manage Recht
                if (!hasPermission($payload['user_id'], 'documents_manage')) {
                    ActivityLogger::logDocument($payload, 'archive_denied', null, 'Archivierung verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Verwalten', 403, ['required_permission' => 'documents_manage']);
                }
                bulkArchiveDocuments($payload);
            } elseif ($idOrAction === 'unarchive') {
                // Bulk-Entarchivieren: documents_manage Recht
                if (!hasPermission($payload['user_id'], 'documents_manage')) {
                    ActivityLogger::logDocument($payload, 'unarchive_denied', null, 'Entarchivierung verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Verwalten', 403, ['required_permission' => 'documents_manage']);
                }
                bulkUnarchiveDocuments($payload);
            } elseif ($idOrAction === 'colors') {
                // Bulk-Farbmarkierung: documents_manage Recht
                if (!hasPermission($payload['user_id'], 'documents_manage')) {
                    ActivityLogger::logDocument($payload, 'color_denied', null, 'Farbmarkierung verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Verwalten', 403, ['required_permission' => 'documents_manage']);
                }
                bulkSetDocumentColors($payload);
            } elseif ($idOrAction === 'delete') {
                // Bulk-Loeschen: documents_delete Recht
                if (!hasPermission($payload['user_id'], 'documents_delete')) {
                    ActivityLogger::logDocument($payload, 'bulk_delete_denied', null, 'Bulk-Loeschen verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Loeschen', 403, ['required_permission' => 'documents_delete']);
                }
                bulkDeleteDocuments($payload);
            } elseif ($idOrAction === 'process') {
                // Verarbeitung: documents_process Recht
                if (!hasPermission($payload['user_id'], 'documents_process')) {
                    ActivityLogger::logDocument($payload, 'process_denied', null, 'Verarbeitung verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zur Verarbeitung', 403, ['required_permission' => 'documents_process']);
                }
                // Verarbeitung wird vom Client gesteuert, hier nur Berechtigung pruefen
                json_success([], 'Verarbeitung erlaubt');
            } else {
                // Upload: documents_upload Recht
                if (!hasPermission($payload['user_id'], 'documents_upload')) {
                    ActivityLogger::logDocument($payload, 'upload_denied', null, 'Upload verweigert: Keine Berechtigung', null, 'denied');
                    json_error('Keine Berechtigung zum Hochladen', 403, ['required_permission' => 'documents_upload']);
                }
                uploadDocument($payload);
            }
            break;
            
        case 'PUT':
            if (empty($idOrAction)) {
                json_error('Dokument-ID erforderlich', 400);
            }
            // Update/Rename: documents_manage Recht
            if (!hasPermission($payload['user_id'], 'documents_manage')) {
                ActivityLogger::logDocument($payload, 'update_denied', (int)$idOrAction, 'Bearbeitung verweigert: Keine Berechtigung', null, 'denied');
                json_error('Keine Berechtigung zum Verwalten', 403, ['required_permission' => 'documents_manage']);
            }
            updateDocument($idOrAction, $payload);
            break;
            
        case 'DELETE':
            if (empty($idOrAction)) {
                json_error('Dokument-ID erforderlich', 400);
            }
            // Loeschen: documents_delete Recht
            if (!hasPermission($payload['user_id'], 'documents_delete')) {
                ActivityLogger::logDocument($payload, 'delete_denied', (int)$idOrAction, 'Loeschen verweigert: Keine Berechtigung', null, 'denied');
                json_error('Keine Berechtigung zum Loeschen', 403, ['required_permission' => 'documents_delete']);
            }
            deleteDocument($idOrAction, $payload);
            break;
            
        default:
            json_error('Methode nicht erlaubt', 405);
    }
}

/**
 * GET /documents
 * Query-Parameter: vu, type, from, to, is_gdv, box
 */
function listDocuments(array $user): void {
    $conditions = ['1=1'];
    $params = [];
    
    // Filter: Box-Typ
    if (!empty($_GET['box'])) {
        $validBoxes = ['eingang', 'verarbeitung', 'roh', 'gdv', 'courtage', 'sach', 'leben', 'kranken', 'sonstige', 'falsch'];
        if (in_array($_GET['box'], $validBoxes)) {
            $conditions[] = 'd.box_type = ?';
            $params[] = $_GET['box'];
        }
    }
    
    // Filter: VU
    if (!empty($_GET['vu'])) {
        $conditions[] = 'd.shipment_id IN (SELECT id FROM shipments WHERE vu_connection_id = ?)';
        $params[] = $_GET['vu'];
    }
    
    // Filter: Quelle
    if (!empty($_GET['source'])) {
        $conditions[] = 'd.source_type = ?';
        $params[] = $_GET['source'];
    }
    
    // Filter: Nur GDV
    if (isset($_GET['is_gdv']) && $_GET['is_gdv'] === '1') {
        $conditions[] = 'd.is_gdv = 1';
    }
    
    // Filter: Datum von
    if (!empty($_GET['from'])) {
        $conditions[] = 'd.created_at >= ?';
        $params[] = $_GET['from'];
    }
    
    // Filter: Datum bis
    if (!empty($_GET['to'])) {
        $conditions[] = 'd.created_at <= ?';
        $params[] = $_GET['to'] . ' 23:59:59';
    }
    
    // Filter: Processing Status
    if (!empty($_GET['processing_status'])) {
        $conditions[] = 'd.processing_status = ?';
        $params[] = $_GET['processing_status'];
    }
    
    // Filter: Archiviert (is_archived)
    if (isset($_GET['is_archived'])) {
        $conditions[] = 'd.is_archived = ?';
        $params[] = $_GET['is_archived'] === '1' ? 1 : 0;
    }
    
    $where = implode(' AND ', $conditions);
    
    $documents = Database::query("
        SELECT 
            d.id,
            d.filename,
            d.original_filename,
            d.mime_type,
            d.file_size,
            d.source_type,
            d.is_gdv,
            d.created_at,
            u.username as uploaded_by_name,
            COALESCE(d.external_shipment_id, s.external_shipment_id) as external_shipment_id,
            COALESCE(d.vu_name, vc.vu_name) as vu_name,
            COALESCE(d.ai_renamed, 0) as ai_renamed,
            d.ai_processing_error,
            COALESCE(d.box_type, 'sonstige') as box_type,
            COALESCE(d.processing_status, 'completed') as processing_status,
            d.document_category,
            d.bipro_category,
            COALESCE(d.is_archived, 0) as is_archived,
            d.display_color,
            d.content_hash,
            COALESCE(d.version, 1) as version,
            d.previous_version_id,
            -- Duplikat-Erkennung: Originalname des Quell-Dokuments (fuer UI-Tooltip)
            COALESCE(orig.original_filename, '') as duplicate_of_filename
        FROM documents d
        LEFT JOIN users u ON d.uploaded_by = u.id
        LEFT JOIN shipments s ON d.shipment_id = s.id
        LEFT JOIN vu_connections vc ON s.vu_connection_id = vc.id
        -- Self-Join fuer Duplikat-Original (previous_version_id -> Original-Dokument)
        LEFT JOIN documents orig ON d.previous_version_id = orig.id
        WHERE $where
        ORDER BY d.created_at DESC
        LIMIT 1000
    ", $params);
    
    json_success([
        'documents' => $documents,
        'count' => count($documents)
    ]);
}

/**
 * GET /documents/{id}/info
 * BUG-0013 Fix: Einzelnes Dokument per ID abrufen (nur Metadaten, kein Download).
 * Vermeidet O(N) Aufrufe von listDocuments() fuer Einzelabfragen.
 */
function getDocumentInfo(string $id, array $user): void {
    $doc = Database::queryOne("
        SELECT 
            d.id,
            d.filename,
            d.original_filename,
            d.mime_type,
            d.file_size,
            d.source_type,
            d.is_gdv,
            d.created_at,
            u.username as uploaded_by_name,
            COALESCE(d.external_shipment_id, s.external_shipment_id) as external_shipment_id,
            COALESCE(d.vu_name, vc.vu_name) as vu_name,
            COALESCE(d.ai_renamed, 0) as ai_renamed,
            d.ai_processing_error,
            COALESCE(d.box_type, 'sonstige') as box_type,
            COALESCE(d.processing_status, 'completed') as processing_status,
            d.document_category,
            d.bipro_category,
            COALESCE(d.is_archived, 0) as is_archived,
            d.display_color,
            d.content_hash,
            COALESCE(d.version, 1) as version,
            d.previous_version_id,
            COALESCE(orig.original_filename, '') as duplicate_of_filename
        FROM documents d
        LEFT JOIN users u ON d.uploaded_by = u.id
        LEFT JOIN shipments s ON d.shipment_id = s.id
        LEFT JOIN vu_connections vc ON s.vu_connection_id = vc.id
        LEFT JOIN documents orig ON d.previous_version_id = orig.id
        WHERE d.id = ?
    ", [(int)$id]);

    if (!$doc) {
        json_error('Dokument nicht gefunden', 404);
    }

    json_success(['document' => $doc]);
}

/**
 * GET /documents/stats
 * Gibt Anzahl Dokumente pro Box zurueck (inkl. archivierte)
 */
function getBoxStats(array $user): void {
    // Nicht-archivierte Dokumente pro Box
    $stats = Database::query("
        SELECT 
            COALESCE(box_type, 'sonstige') as box_type,
            COUNT(*) as count
        FROM documents
        WHERE COALESCE(is_archived, 0) = 0
        GROUP BY box_type
    ");
    
    // Archivierte Dokumente pro Box
    $archivedStats = Database::query("
        SELECT 
            COALESCE(box_type, 'sonstige') as box_type,
            COUNT(*) as count
        FROM documents
        WHERE COALESCE(is_archived, 0) = 1
        GROUP BY box_type
    ");
    
    // In assoziatives Array umwandeln
    $result = [
        'eingang' => 0,
        'verarbeitung' => 0,
        'roh' => 0,
        'gdv' => 0,
        'courtage' => 0,
        'sach' => 0,
        'leben' => 0,
        'kranken' => 0,
        'sonstige' => 0,
        'falsch' => 0,
        'total' => 0,
        // Archivierte Zaehlungen
        'gdv_archived' => 0,
        'courtage_archived' => 0,
        'sach_archived' => 0,
        'leben_archived' => 0,
        'kranken_archived' => 0,
        'sonstige_archived' => 0,
        'falsch_archived' => 0
    ];
    
    // Nicht-archivierte zaehlen
    foreach ($stats as $row) {
        $box = $row['box_type'] ?: 'sonstige';
        $result[$box] = (int)$row['count'];
        $result['total'] += (int)$row['count'];
    }
    
    // Archivierte zaehlen
    foreach ($archivedStats as $row) {
        $box = $row['box_type'] ?: 'sonstige';
        $archivedKey = $box . '_archived';
        if (isset($result[$archivedKey])) {
            $result[$archivedKey] = (int)$row['count'];
        }
        // Archivierte auch zum Gesamt zaehlen
        $result['total'] += (int)$row['count'];
    }
    
    json_success($result);
}

/**
 * POST /documents/move
 * Verschiebt mehrere Dokumente in eine andere Box
 */
function moveDocuments(array $user): void {
    $data = get_json_body();
    
    if (empty($data['document_ids']) || !is_array($data['document_ids'])) {
        json_error('document_ids erforderlich (Array)', 400);
    }
    
    if (empty($data['target_box'])) {
        json_error('target_box erforderlich', 400);
    }
    
    $validBoxes = ['eingang', 'verarbeitung', 'roh', 'gdv', 'courtage', 'sach', 'leben', 'kranken', 'sonstige', 'falsch'];
    if (!in_array($data['target_box'], $validBoxes)) {
        json_error('Ungueltiger Box-Typ: ' . $data['target_box'], 400);
    }
    
    $docIds = array_map('intval', $data['document_ids']);
    $targetBox = $data['target_box'];
    
    // Optionaler processing_status (Standard: 'completed')
    $processingStatus = 'completed';
    if (!empty($data['processing_status'])) {
        $validStatuses = ['completed', 'pending', 'manual_excluded'];
        if (in_array($data['processing_status'], $validStatuses)) {
            $processingStatus = $data['processing_status'];
        }
    }
    
    // Placeholders fuer IN-Clause
    $placeholders = implode(',', array_fill(0, count($docIds), '?'));
    
    // Alte Box-Typen laden (fuer Historie-Logging)
    $oldBoxRows = Database::query(
        "SELECT id, box_type FROM documents WHERE id IN ($placeholders)",
        $docIds
    );
    $oldBoxTypes = [];
    foreach ($oldBoxRows as $row) {
        $oldBoxTypes[(int)$row['id']] = $row['box_type'];
    }
    
    // Dokumente verschieben
    $params = array_merge([$targetBox, $processingStatus], $docIds);
    $affected = Database::execute(
        "UPDATE documents SET box_type = ?, processing_status = ? WHERE id IN ($placeholders)",
        $params
    );
    
    // Activity-Log: Pro Dokument einen Eintrag (fuer per-Dokument-Historie)
    foreach ($docIds as $docId) {
        $sourceBox = $oldBoxTypes[(int)$docId] ?? null;
        ActivityLogger::logDocument($user, 'move', (int)$docId,
            "Dokument von '{$sourceBox}' nach '{$targetBox}' verschoben",
            ['target_box' => $targetBox, 'source_box' => $sourceBox, 'processing_status' => $processingStatus]
        );
    }
    
    json_success([
        'moved_count' => $affected,
        'target_box' => $targetBox
    ], "$affected Dokument(e) verschoben");
}

/**
 * POST /documents
 * Multipart-Upload mit Datei
 * 
 * ATOMIC WRITE PATTERN:
 * 1. Datei als .tmp in Staging schreiben
 * 2. Hash/Size verifizieren
 * 3. beginTransaction()
 * 4. DB Insert
 * 5. Atomic move via rename() ins finale Ziel
 * 6. commit()
 * 7. On error: rollback() + tmp-Datei loeschen
 */
function uploadDocument(array $user): void {
    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        $errorMessages = [
            UPLOAD_ERR_INI_SIZE => 'Datei zu groß (PHP-Limit)',
            UPLOAD_ERR_FORM_SIZE => 'Datei zu groß (Form-Limit)',
            UPLOAD_ERR_PARTIAL => 'Upload unvollständig',
            UPLOAD_ERR_NO_FILE => 'Keine Datei hochgeladen',
        ];
        $error = $_FILES['file']['error'] ?? UPLOAD_ERR_NO_FILE;
        json_error($errorMessages[$error] ?? 'Upload-Fehler', 400);
    }
    
    $file = $_FILES['file'];
    
    // Größe prüfen
    if ($file['size'] > MAX_UPLOAD_SIZE) {
        json_error('Datei zu groß (max. ' . (MAX_UPLOAD_SIZE / 1024 / 1024) . ' MB)', 400);
    }
    
    // SV-021 Fix: MIME-Type-Whitelist fuer alle Uploads
    $mimeType = $file['type'] ?: 'application/octet-stream';
    $allowedMimeTypes = [
        'application/pdf',
        'image/jpeg', 'image/png', 'image/gif',
        'text/plain', 'text/csv', 'text/xml',
        'application/xml',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'application/zip', 'application/x-zip-compressed',
        'application/octet-stream',  // GDV-Dateien, .dat, .gdv
        'application/vnd.ms-outlook', // .msg Dateien
        'message/rfc822',
    ];
    if (!in_array($mimeType, $allowedMimeTypes)) {
        json_error('Dateityp nicht erlaubt: ' . $mimeType, 415);
    }
    
    // Dateiname bereinigen
    $originalFilename = basename($file['name']);
    $safeFilename = preg_replace('/[^a-zA-Z0-9._-]/', '_', $originalFilename);
    
    // Eindeutigen Dateinamen generieren
    $uniqueFilename = date('Y-m-d_His') . '_' . uniqid() . '_' . $safeFilename;
    
    // Zielordner (nach Jahr/Monat organisiert)
    $subdir = date('Y/m');
    $targetDir = DOCUMENTS_PATH . $subdir;
    $stagingDir = DOCUMENTS_PATH . 'staging';
    
    // Verzeichnisse erstellen
    if (!is_dir($targetDir)) {
        mkdir($targetDir, 0755, true);
    }
    if (!is_dir($stagingDir)) {
        mkdir($stagingDir, 0755, true);
    }
    
    // SCHRITT 1: Datei als .tmp in Staging schreiben
    $stagingPath = $stagingDir . '/.tmp_' . $uniqueFilename;
    $targetPath = $targetDir . '/' . $uniqueFilename;
    $storagePath = $subdir . '/' . $uniqueFilename;
    
    if (!move_uploaded_file($file['tmp_name'], $stagingPath)) {
        json_error('Datei konnte nicht in Staging gespeichert werden', 500);
    }
    
    // SCHRITT 2: Hash/Size verifizieren
    $actualSize = filesize($stagingPath);
    if ($actualSize !== $file['size']) {
        @unlink($stagingPath);
        json_error("Upload unvollstaendig: erwartet {$file['size']}, erhalten $actualSize Bytes", 500);
    }
    
    // Content-Hash berechnen (fuer spaetere Deduplizierung)
    $contentHash = hash_file('sha256', $stagingPath);
    
    // Prüfen ob GDV-Datei (vor dem Move, da wir Staging-Pfad haben)
    $isGdv = isGdvFile($stagingPath);
    
    // Quelle bestimmen
    $sourceType = $_POST['source_type'] ?? 'manual_upload';
    if (!in_array($sourceType, ['bipro_auto', 'manual_upload', 'self_created', 'scan'])) {
        $sourceType = 'manual_upload';
    }
    
    // VU-Name fuer BiPRO-Lieferungen
    $vuName = $_POST['vu_name'] ?? null;
    
    // External Shipment ID (BiPRO-Lieferungs-ID als String)
    $externalShipmentId = $_POST['shipment_id'] ?? null;
    
    // Box-Typ (Standard: eingang fuer neue Uploads)
    $boxType = $_POST['box_type'] ?? 'eingang';
    $validBoxes = ['eingang', 'verarbeitung', 'roh', 'gdv', 'courtage', 'sach', 'leben', 'kranken', 'sonstige', 'falsch'];
    if (!in_array($boxType, $validBoxes)) {
        $boxType = 'eingang';
    }
    
    // BiPRO-Kategorie (z.B. "300001000" fuer Provisionsabrechnung)
    $biproCategory = $_POST['bipro_category'] ?? null;
    
    // PDF-Validierungsstatus (NEU)
    // Gueltige Werte: OK, PDF_ENCRYPTED, PDF_CORRUPT, PDF_INCOMPLETE, PDF_XFA, PDF_REPAIRED, PDF_NO_PAGES, PDF_LOAD_ERROR
    $validationStatus = $_POST['validation_status'] ?? null;
    $validValidationStatuses = ['OK', 'PDF_ENCRYPTED', 'PDF_CORRUPT', 'PDF_INCOMPLETE', 'PDF_XFA', 'PDF_REPAIRED', 'PDF_NO_PAGES', 'PDF_LOAD_ERROR'];
    if ($validationStatus !== null && !in_array($validationStatus, $validValidationStatuses)) {
        $validationStatus = null;  // Ungueltige Werte ignorieren
    }
    
    // Processing Status
    $processingStatus = 'pending';
    
    // SCHRITT 3: Transaction starten
    Database::beginTransaction();
    
    try {
        // SCHRITT 3.5: Duplikat-Pruefung via content_hash (Idempotenz)
        $version = 1;
        $previousVersionId = null;
        $isDuplicate = false;
        
        if ($contentHash) {
            // Prüfe ob Datei mit gleichem Hash bereits existiert
            $existing = Database::queryOne(
                "SELECT id, version, original_filename 
                 FROM documents 
                 WHERE content_hash = ? 
                 ORDER BY version DESC 
                 LIMIT 1",
                [$contentHash]
            );
            
            if ($existing) {
                // Duplikat gefunden - neue Version erstellen
                $isDuplicate = true;
                $previousVersionId = $existing['id'];
                $version = $existing['version'] + 1;
                
                error_log("Duplikat erkannt: Hash=$contentHash, vorherige Version={$existing['version']}, neue Version=$version");
            }
        }
        
        // SCHRITT 4: In DB speichern (mit Versionierung)
        $docId = Database::insert("
            INSERT INTO documents 
            (filename, original_filename, mime_type, file_size, storage_path, source_type, is_gdv, uploaded_by, shipment_id, vu_name, external_shipment_id, bipro_category, box_type, processing_status, validation_status, content_hash, version, previous_version_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ", [
            $uniqueFilename,
            $originalFilename,
            $mimeType,
            $file['size'],
            $storagePath,
            $sourceType,
            $isGdv ? 1 : 0,
            $user['user_id'],
            null,  // shipment_id (internal) - not used currently
            $vuName,
            $externalShipmentId,
            $biproCategory,
            $boxType,
            $processingStatus,
            $validationStatus,
            $contentHash,
            $version,
            $previousVersionId
        ]);
        
        // SCHRITT 5: Atomic move via rename() ins finale Ziel
        // rename() ist atomar auf gleichem Filesystem
        if (!rename($stagingPath, $targetPath)) {
            throw new Exception("Atomic move fehlgeschlagen: $stagingPath -> $targetPath");
        }
        
        // Activity-Log (innerhalb der Transaktion)
        ActivityLogger::logDocument($user, 'upload', $docId,
            "Dokument hochgeladen: {$originalFilename}" . ($isDuplicate ? " (Version {$version})" : ''),
            ['filename' => $originalFilename, 'content_hash' => $contentHash, 'version' => $version, 'is_duplicate' => $isDuplicate, 'box_type' => $boxType]
        );
        
        // SCHRITT 6: Commit
        Database::commit();
        
        $message = $isDuplicate 
            ? "Dokument hochgeladen (Version $version, Duplikat erkannt)"
            : 'Dokument hochgeladen';
        
        json_success([
            'id' => $docId,
            'filename' => $uniqueFilename,
            'original_filename' => $originalFilename,
            'is_gdv' => $isGdv,
            'storage_path' => $storagePath,
            'box_type' => $boxType,
            'processing_status' => $processingStatus,
            'bipro_category' => $biproCategory,
            'validation_status' => $validationStatus,
            'content_hash' => $contentHash,
            'version' => $version,
            'is_duplicate' => $isDuplicate,
            'previous_version_id' => $previousVersionId
        ], $message);
        
    } catch (Exception $e) {
        // SCHRITT 7: On error - Rollback + tmp-Datei loeschen
        Database::rollback();
        
        // Staging-Datei aufraumen (falls noch vorhanden)
        if (file_exists($stagingPath)) {
            @unlink($stagingPath);
        }
        // Falls bereits ins Ziel verschoben wurde, auch dort loeschen
        if (file_exists($targetPath)) {
            @unlink($targetPath);
        }
        
        error_log("Upload fehlgeschlagen (Rollback): " . $e->getMessage());
        json_error('Upload fehlgeschlagen: ' . $e->getMessage(), 500);
    }
}

/**
 * GET /documents/{id}
 */
function downloadDocument(string $id, array $user): void {
    $doc = Database::queryOne(
        'SELECT * FROM documents WHERE id = ?',
        [$id]
    );
    
    if (!$doc) {
        json_error('Dokument nicht gefunden', 404);
    }
    
    $filePath = DOCUMENTS_PATH . $doc['storage_path'];
    
    if (!file_exists($filePath)) {
        json_error('Datei nicht gefunden', 404);
    }
    
    // Activity-Log
    ActivityLogger::logDocument($user, 'download', (int)$id,
        "Dokument heruntergeladen: {$doc['original_filename']}",
        ['filename' => $doc['original_filename'], 'file_size' => $doc['file_size']]
    );
    
    // Download-Header
    header('Content-Type: ' . ($doc['mime_type'] ?: 'application/octet-stream'));
    $safeFilename = str_replace(['"', "\r", "\n", "\0"], '', $doc['original_filename']);
    header('Content-Disposition: attachment; filename="' . $safeFilename . '"');
    header('Content-Length: ' . filesize($filePath));
    header('Cache-Control: no-cache, must-revalidate');
    
    readfile($filePath);
    exit();
}

/**
 * DELETE /documents/{id}
 */
function deleteDocument(string $id, array $user): void {
    $doc = Database::queryOne(
        'SELECT * FROM documents WHERE id = ?',
        [$id]
    );
    
    if (!$doc) {
        json_error('Dokument nicht gefunden', 404);
    }
    
    $filePath = DOCUMENTS_PATH . $doc['storage_path'];
    
    // Aus DB löschen
    Database::execute('DELETE FROM documents WHERE id = ?', [$id]);
    
    // Datei löschen
    if (file_exists($filePath)) {
        unlink($filePath);
    }
    
    // Activity-Log
    ActivityLogger::logDocument($user, 'delete', (int)$id,
        "Dokument geloescht: {$doc['original_filename']}",
        ['filename' => $doc['original_filename'], 'box_type' => $doc['box_type'] ?? '']
    );
    
    json_success([], 'Dokument gelöscht');
}

/**
 * POST /documents/delete
 * Bulk-Loeschen: Loescht mehrere Dokumente inkl. Dateien in einem Call
 * 
 * Body: {"ids": [1, 2, 3, ...]}
 */
function bulkDeleteDocuments(array $user): void {
    $data = get_json_body();
    
    if (empty($data['ids']) || !is_array($data['ids'])) {
        json_error('ids erforderlich (Array von Dokument-IDs)', 400);
    }
    
    $docIds = array_map('intval', $data['ids']);
    $docIds = array_filter($docIds, function($id) { return $id > 0; });
    
    if (empty($docIds)) {
        json_error('Keine gueltigen Dokument-IDs', 400);
    }
    
    $placeholders = implode(',', array_fill(0, count($docIds), '?'));
    
    // Dokument-Infos holen (fuer Datei-Loeschung und Logging)
    $docs = Database::query(
        "SELECT id, storage_path, original_filename, box_type FROM documents WHERE id IN ($placeholders)",
        array_values($docIds)
    );
    
    // BUG-0011 Fix: Zuerst aus DB loeschen, dann Dateien (atomarer Zustand)
    $affected = Database::execute(
        "DELETE FROM documents WHERE id IN ($placeholders)",
        array_values($docIds)
    );
    
    // Dateien vom Dateisystem loeschen (nur nach erfolgreichem DB-Delete)
    if ($affected > 0) {
        foreach ($docs as $doc) {
            $filePath = DOCUMENTS_PATH . $doc['storage_path'];
            if (file_exists($filePath)) {
                @unlink($filePath);
            }
        }
    }
    
    // Activity-Log
    $filenames = array_map(function($d) { return $d['original_filename']; }, $docs);
    ActivityLogger::logDocument($user, 'bulk_delete', null, 
        "{$affected} Dokument(e) geloescht",
        ['document_ids' => $docIds, 'count' => $affected, 'filenames' => array_slice($filenames, 0, 10)]
    );
    
    json_success([
        'deleted_count' => $affected,
        'requested_count' => count($docIds)
    ], "$affected Dokument(e) geloescht");
}

/**
 * PUT /documents/{id}
 * Aktualisiert Dokument-Metadaten (Dateiname, KI-Status)
 */
function updateDocument(string $id, array $user): void {
    $doc = Database::queryOne(
        'SELECT * FROM documents WHERE id = ?',
        [$id]
    );
    
    if (!$doc) {
        json_error('Dokument nicht gefunden', 404);
    }
    
    $data = get_json_body();
    
    $updates = [];
    $params = [];
    $changes = [];
    
    // Erlaubte Felder fuer Update
    $allowedFields = [
        'original_filename', 
        'ai_renamed', 
        'ai_processing_error',
        'box_type',
        'processing_status',
        'document_category',
        'validation_status',           // Technischer PDF-Validierungsstatus
        'classification_source',       // Quelle: ki_gpt4o, rule_bipro, fallback, etc.
        'classification_confidence',   // Konfidenz: high, medium, low
        'classification_reason',       // Begruendung/Erklaerung (max 500 Zeichen)
        'classification_timestamp',    // Zeitpunkt der Klassifikation
        'bipro_document_id',           // Eindeutige ID aus BiPRO-Response (Idempotenz)
        'source_xml_index_id',         // Relation zur XML-Quell-Lieferung
        'is_archived',                 // Archivierungs-Status (nach Download)
        'display_color'                // Farbmarkierung (green, red, blue, orange, purple, pink, cyan, yellow)
    ];
    
    // Box-Typ validieren
    $validBoxes = ['eingang', 'verarbeitung', 'roh', 'gdv', 'courtage', 'sach', 'leben', 'kranken', 'sonstige', 'falsch'];
    if (isset($data['box_type']) && !in_array($data['box_type'], $validBoxes)) {
        json_error('Ungueltiger Box-Typ', 400);
    }
    
    // display_color validieren (NULL zum Entfernen erlaubt)
    $validColors = ['green', 'red', 'blue', 'orange', 'purple', 'pink', 'cyan', 'yellow'];
    if (array_key_exists('display_color', $data)) {
        if ($data['display_color'] === null || $data['display_color'] === '') {
            // NULL/leer = Farbe entfernen - als spezielle Behandlung
            $updates[] = "display_color = NULL";
            $changes['display_color'] = null;
            // Aus allowedFields-Verarbeitung ausschliessen (wird manuell behandelt)
            unset($data['display_color']);
        } elseif (!in_array($data['display_color'], $validColors)) {
            json_error('Ungueltige Farbmarkierung: ' . $data['display_color'] . '. Erlaubt: ' . implode(', ', $validColors), 400);
        }
    }
    
    // Processing-Status validieren (erweiterte State-Machine mit Transition-Erzwingung)
    $validStatuses = [
        // Neue granulare Status
        'downloaded',   // Datei vom BiPRO heruntergeladen
        'validated',    // PDF-Validierung durchgefuehrt
        'classified',   // KI/Regel-Klassifikation abgeschlossen
        'renamed',      // Dateiname angepasst
        'archived',     // In Ziel-Box verschoben
        'quarantined',  // In Quarantaene (z.B. ungueltiges Format)
        'error',        // Fehler aufgetreten
        // Legacy-Status (abwaertskompatibel)
        'pending',
        'processing',
        'completed',
        // Manueller Ausschluss
        'manual_excluded'  // Vom Benutzer manuell bearbeitet, nicht verarbeiten
    ];
    
    if (isset($data['processing_status'])) {
        $newStatus = $data['processing_status'];
        
        if (!in_array($newStatus, $validStatuses)) {
            json_error('Ungueltiger Processing-Status: ' . $newStatus, 400);
        }
        
        // STATE-MACHINE: Transition-Erzwingung
        $currentStatus = $doc['processing_status'] ?? 'pending';
        if (!isValidStatusTransition($currentStatus, $newStatus)) {
            json_error(
                "Ungueltiger Statusuebergang: '$currentStatus' -> '$newStatus'. " .
                "Erlaubte Uebergaenge: " . implode(', ', getValidTransitionsFrom($currentStatus)),
                400
            );
        }
        
        // Automatische History-Eintraege fuer Statuswechsel
        if ($currentStatus !== $newStatus) {
            logStatusTransition($id, $currentStatus, $newStatus, $user);
        }
    }
    
    // validation_status Aenderung auch historisieren
    if (isset($data['validation_status'])) {
        $oldValidation = $doc['validation_status'] ?? null;
        $newValidation = $data['validation_status'];
        if ($oldValidation !== $newValidation) {
            logValidationStatusChange($id, $oldValidation, $newValidation, $user);
        }
    }
    
    foreach ($allowedFields as $field) {
        if (isset($data[$field])) {
            $updates[] = "$field = ?";
            $params[] = $data[$field];
            $changes[$field] = $data[$field];
        }
    }
    
    if (empty($updates)) {
        json_error('Keine Aenderungen angegeben', 400);
    }
    
    $params[] = $id;
    $sql = "UPDATE documents SET " . implode(', ', $updates) . " WHERE id = ?";
    Database::execute($sql, $params);
    
    // Activity-Log: Alten box_type mitloggen wenn geaendert
    $logDetails = ['changes' => $changes, 'filename' => $doc['original_filename'] ?? ''];
    if (isset($changes['box_type'])) {
        $logDetails['old_box_type'] = $doc['box_type'];
    }
    ActivityLogger::logDocument($user, 'update', (int)$id,
        "Dokument aktualisiert: " . implode(', ', array_keys($changes)),
        $logDetails
    );
    
    json_success([
        'id' => (int)$id,
        'updated_fields' => array_keys($changes)
    ], 'Dokument aktualisiert');
}

/**
 * POST /documents/archive
 * Bulk-Archivierung: Setzt is_archived=1 fuer mehrere Dokumente in einem Call
 * 
 * Body: {"ids": [1, 2, 3, ...]}
 */
function bulkArchiveDocuments(array $user): void {
    $data = get_json_body();
    
    if (empty($data['ids']) || !is_array($data['ids'])) {
        json_error('ids erforderlich (Array von Dokument-IDs)', 400);
    }
    
    $docIds = array_map('intval', $data['ids']);
    $docIds = array_filter($docIds, function($id) { return $id > 0; });
    
    if (empty($docIds)) {
        json_error('Keine gueltigen Dokument-IDs', 400);
    }
    
    $placeholders = implode(',', array_fill(0, count($docIds), '?'));
    
    $affected = Database::execute(
        "UPDATE documents SET is_archived = 1 WHERE id IN ($placeholders) AND COALESCE(is_archived, 0) = 0",
        array_values($docIds)
    );
    
    // Activity-Log
    ActivityLogger::logDocument($user, 'bulk_archive', null, 
        "{$affected} Dokument(e) archiviert",
        ['document_ids' => $docIds, 'count' => $affected]
    );
    
    json_success([
        'archived_count' => $affected,
        'requested_count' => count($docIds)
    ], "$affected Dokument(e) archiviert");
}

/**
 * POST /documents/unarchive
 * Bulk-Entarchivierung: Setzt is_archived=0 fuer mehrere Dokumente in einem Call
 * 
 * Body: {"ids": [1, 2, 3, ...]}
 */
function bulkUnarchiveDocuments(array $user): void {
    $data = get_json_body();
    
    if (empty($data['ids']) || !is_array($data['ids'])) {
        json_error('ids erforderlich (Array von Dokument-IDs)', 400);
    }
    
    $docIds = array_map('intval', $data['ids']);
    $docIds = array_filter($docIds, function($id) { return $id > 0; });
    
    if (empty($docIds)) {
        json_error('Keine gueltigen Dokument-IDs', 400);
    }
    
    $placeholders = implode(',', array_fill(0, count($docIds), '?'));
    
    $affected = Database::execute(
        "UPDATE documents SET is_archived = 0 WHERE id IN ($placeholders) AND COALESCE(is_archived, 0) = 1",
        array_values($docIds)
    );
    
    // Activity-Log
    ActivityLogger::logDocument($user, 'bulk_unarchive', null, 
        "{$affected} Dokument(e) entarchiviert",
        ['document_ids' => $docIds, 'count' => $affected]
    );
    
    json_success([
        'unarchived_count' => $affected,
        'requested_count' => count($docIds)
    ], "$affected Dokument(e) entarchiviert");
}

/**
 * POST /documents/colors
 * Bulk-Farbmarkierung: Setzt display_color fuer mehrere Dokumente in einem Call
 * 
 * Body: {"ids": [1, 2, 3, ...], "color": "green"}
 * Body (entfernen): {"ids": [1, 2, 3, ...], "color": null}
 */
function bulkSetDocumentColors(array $user): void {
    $data = get_json_body();
    
    if (empty($data['ids']) || !is_array($data['ids'])) {
        json_error('ids erforderlich (Array von Dokument-IDs)', 400);
    }
    
    if (!array_key_exists('color', $data)) {
        json_error('color erforderlich (Farbname oder null zum Entfernen)', 400);
    }
    
    $color = $data['color'];
    $validColors = ['green', 'red', 'blue', 'orange', 'purple', 'pink', 'cyan', 'yellow'];
    
    if ($color !== null && $color !== '' && !in_array($color, $validColors)) {
        json_error('Ungueltige Farbmarkierung: ' . $color . '. Erlaubt: ' . implode(', ', $validColors), 400);
    }
    
    // NULL oder leerer String -> Farbe entfernen
    if ($color === '' || $color === null) {
        $color = null;
    }
    
    $docIds = array_map('intval', $data['ids']);
    $docIds = array_filter($docIds, function($id) { return $id > 0; });
    
    if (empty($docIds)) {
        json_error('Keine gueltigen Dokument-IDs', 400);
    }
    
    $placeholders = implode(',', array_fill(0, count($docIds), '?'));
    $params = array_merge([$color], array_values($docIds));
    
    $affected = Database::execute(
        "UPDATE documents SET display_color = ? WHERE id IN ($placeholders)",
        $params
    );
    
    // Activity-Log
    $colorLabel = $color ?? 'entfernt';
    ActivityLogger::logDocument($user, 'bulk_set_color', null, 
        "Farbmarkierung '{$colorLabel}' fuer {$affected} Dokument(e) gesetzt",
        ['document_ids' => $docIds, 'color' => $color, 'count' => $affected]
    );
    
    json_success([
        'updated_count' => $affected,
        'requested_count' => count($docIds),
        'color' => $color
    ], "Farbmarkierung fuer $affected Dokument(e) aktualisiert");
}

// ============================================================================
// STATE-MACHINE: Transition-Regeln und Logging
// ============================================================================

/**
 * Erlaubte Statusuebergaenge (State-Machine)
 * 
 * Jeder Verarbeitungsschritt darf nur starten, wenn sich ein Dokument
 * im dafuer vorgesehenen Zustand befindet.
 */
function getValidTransitions(): array {
    return [
        // Neue granulare Uebergaenge
        'downloaded'  => ['validated', 'quarantined', 'error', 'processing', 'classified', 'manual_excluded'],
        'validated'   => ['classified', 'quarantined', 'error', 'manual_excluded'],
        'classified'  => ['renamed', 'archived', 'error', 'manual_excluded'],
        'renamed'     => ['archived', 'error', 'manual_excluded'],
        'archived'    => ['error', 'manual_excluded'],
        'quarantined' => ['downloaded', 'error', 'manual_excluded'],
        'error'       => ['downloaded', 'pending', 'quarantined', 'manual_excluded'],
        
        // Legacy-Uebergaenge (abwaertskompatibel)
        'pending'     => ['processing', 'downloaded', 'error', 'classified', 'manual_excluded'],
        'processing'  => ['completed', 'classified', 'validated', 'error', 'quarantined', 'renamed', 'archived', 'manual_excluded'],
        'completed'   => ['archived', 'error', 'manual_excluded'],
        
        // Manueller Ausschluss: Nur zurueck nach pending (= Freigabe)
        'manual_excluded' => ['pending'],
        
        // Null/Empty als Startpunkt - flexibler fuer parallele Verarbeitung
        ''            => ['downloaded', 'pending', 'processing', 'classified', 'renamed', 'archived', 'manual_excluded'],
        null          => ['downloaded', 'pending', 'processing', 'classified', 'renamed', 'archived', 'manual_excluded'],
    ];
}

/**
 * Prueft ob ein Statusuebergang gueltig ist
 */
function isValidStatusTransition(?string $from, string $to): bool {
    $transitions = getValidTransitions();
    $fromKey = $from ?? '';
    
    // Wenn from nicht bekannt, erlaube alle gueltigen Stati als Ziel
    if (!isset($transitions[$fromKey])) {
        return true;  // Unbekannter Status -> erlaube Uebergang (Flexibilitaet)
    }
    
    return in_array($to, $transitions[$fromKey], true);
}

/**
 * Gibt erlaubte Uebergaenge von einem Status zurueck
 */
function getValidTransitionsFrom(?string $from): array {
    $transitions = getValidTransitions();
    $fromKey = $from ?? '';
    return $transitions[$fromKey] ?? [];
}

/**
 * Loggt einen Statusuebergang in processing_history
 */
function logStatusTransition(string $docId, ?string $fromStatus, string $toStatus, array $user): void {
    try {
        // Pruefen ob processing_history Tabelle existiert
        $tableExists = Database::queryOne(
            "SHOW TABLES LIKE 'processing_history'"
        );
        
        if (!$tableExists) {
            return;  // Tabelle existiert noch nicht
        }
        
        Database::insert("
            INSERT INTO processing_history 
            (document_id, previous_status, new_status, action, success, created_by)
            VALUES (?, ?, ?, 'status_change', 1, ?)
        ", [
            (int)$docId,
            $fromStatus,
            $toStatus,
            $user['name'] ?? 'system'
        ]);
    } catch (Exception $e) {
        // History-Logging sollte Update nicht blockieren
        error_log("Status-Transition-Log fehlgeschlagen: " . $e->getMessage());
    }
}

/**
 * Loggt eine validation_status Aenderung in processing_history
 */
function logValidationStatusChange(string $docId, ?string $oldStatus, string $newStatus, array $user): void {
    try {
        $tableExists = Database::queryOne(
            "SHOW TABLES LIKE 'processing_history'"
        );
        
        if (!$tableExists) {
            return;
        }
        
        Database::insert("
            INSERT INTO processing_history 
            (document_id, previous_status, new_status, action, action_details, success, created_by)
            VALUES (?, ?, ?, 'validation_change', ?, 1, ?)
        ", [
            (int)$docId,
            $oldStatus ?? 'null',
            $newStatus,
            json_encode(['type' => 'validation_status', 'old' => $oldStatus, 'new' => $newStatus]),
            $user['name'] ?? 'system'
        ]);
    } catch (Exception $e) {
        error_log("Validation-Status-Log fehlgeschlagen: " . $e->getMessage());
    }
}

// ============================================================================
// HILFSFUNKTIONEN
// ============================================================================

/**
 * Prueft ob eine Datei eine GDV-Datei ist
 */
function isGdvFile(string $path): bool {
    $handle = fopen($path, 'r');
    if (!$handle) {
        return false;
    }
    
    // Erste Zeile lesen
    $firstLine = fgets($handle, 260);
    fclose($handle);
    
    if (!$firstLine) {
        return false;
    }
    
    // GDV-Dateien beginnen mit Satzart 0001
    return substr($firstLine, 0, 4) === '0001';
}

/**
 * GET /documents/{id}/history
 * Laedt die Aenderungshistorie eines Dokuments aus dem activity_log.
 * Berechtigung: documents_history
 */
function getDocumentHistory(string $id, array $user): void {
    // Berechtigung pruefen
    if (!hasPermission($user['user_id'], 'documents_history')) {
        json_error('Keine Berechtigung fuer Dokument-Historie', 403, ['required_permission' => 'documents_history']);
    }
    
    // Dokument existiert?
    $doc = Database::queryOne('SELECT id FROM documents WHERE id = ?', [(int)$id]);
    if (!$doc) {
        json_error('Dokument nicht gefunden', 404);
    }
    
    // Alle Eintraege aus activity_log wo entity_id = $id UND entity_type = 'document'
    $history = Database::query(
        "SELECT id, created_at, username, action, description, details, status
         FROM activity_log 
         WHERE entity_type = 'document' AND entity_id = ?
         ORDER BY created_at DESC
         LIMIT 200",
        [(int)$id]
    );
    
    // details-JSON dekodieren
    foreach ($history as &$entry) {
        if (!empty($entry['details']) && is_string($entry['details'])) {
            $decoded = json_decode($entry['details'], true);
            $entry['details'] = $decoded !== null ? $decoded : [];
        } else {
            $entry['details'] = [];
        }
    }
    unset($entry);
    
    json_success(['history' => $history, 'count' => count($history)]);
}

/**
 * POST /documents/{id}/replace
 * Ersetzt die Datei eines bestehenden Dokuments.
 * Metadaten (box_type, filename, etc.) bleiben erhalten.
 * content_hash und file_size werden neu berechnet.
 * Berechtigung: documents_manage
 */
function replaceDocumentFile(string $id, array $user): void {
    // 1. Dokument laden
    $doc = Database::queryOne('SELECT * FROM documents WHERE id = ?', [(int)$id]);
    if (!$doc) {
        json_error('Dokument nicht gefunden', 404);
    }
    
    // 2. Upload-Datei validieren
    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        $errorMessages = [
            UPLOAD_ERR_INI_SIZE => 'Datei zu gross (PHP-Limit)',
            UPLOAD_ERR_FORM_SIZE => 'Datei zu gross (Form-Limit)',
            UPLOAD_ERR_PARTIAL => 'Upload unvollstaendig',
            UPLOAD_ERR_NO_FILE => 'Keine Datei hochgeladen',
        ];
        $error = $_FILES['file']['error'] ?? UPLOAD_ERR_NO_FILE;
        json_error($errorMessages[$error] ?? 'Upload-Fehler', 400);
    }
    
    $file = $_FILES['file'];
    
    if ($file['size'] > MAX_UPLOAD_SIZE) {
        json_error('Datei zu gross (max. ' . (MAX_UPLOAD_SIZE / 1024 / 1024) . ' MB)', 400);
    }
    
    // 3. Staging: Neue Datei in Staging schreiben
    $stagingDir = DOCUMENTS_PATH . 'staging';
    if (!is_dir($stagingDir)) {
        mkdir($stagingDir, 0755, true);
    }
    
    $stagingPath = $stagingDir . '/.tmp_replace_' . $id . '_' . uniqid();
    if (!move_uploaded_file($file['tmp_name'], $stagingPath)) {
        json_error('Datei konnte nicht in Staging gespeichert werden', 500);
    }
    
    // 4. Hash + Groesse berechnen
    $newHash = hash_file('sha256', $stagingPath);
    $newSize = filesize($stagingPath);
    
    // 5. Alte Datei ersetzen (atomisch)
    $targetPath = DOCUMENTS_PATH . $doc['storage_path'];
    $targetDir = dirname($targetPath);
    
    if (!is_dir($targetDir)) {
        mkdir($targetDir, 0755, true);
    }
    
    // Alte Datei ueberschreiben via rename (atomisch)
    if (!rename($stagingPath, $targetPath)) {
        @unlink($stagingPath);
        json_error('Datei konnte nicht ersetzt werden', 500);
    }
    
    // 6. DB aktualisieren: content_hash, file_size, mime_type
    $mimeType = $file['type'] ?: ($doc['mime_type'] ?: 'application/octet-stream');
    Database::execute(
        "UPDATE documents SET content_hash = ?, file_size = ?, mime_type = ? WHERE id = ?",
        [$newHash, $newSize, $mimeType, (int)$id]
    );
    
    // 7. Activity-Log
    ActivityLogger::logDocument($user, 'file_replaced', (int)$id,
        "Datei ersetzt: {$doc['original_filename']}",
        [
            'filename' => $doc['original_filename'],
            'old_hash' => $doc['content_hash'] ?? '',
            'new_hash' => $newHash,
            'old_size' => $doc['file_size'],
            'new_size' => $newSize
        ]
    );
    
    json_success([
        'id' => (int)$id,
        'content_hash' => $newHash,
        'file_size' => $newSize
    ], 'Datei erfolgreich ersetzt');
}
