<?php
/**
 * BiPro API - Eingehende Scan-Dokumente (Power Automate)
 * 
 * Endpunkt:
 * - POST /incoming-scans - Scan-Dokument empfangen und ins Archiv einpflegen
 * 
 * Authentifizierung: API-Key im Header X-API-Key (kein JWT)
 * 
 * Request-Body (JSON):
 * {
 *   "fileName": "scan.pdf",
 *   "filePath": "/Freigegebene Dokumente/03 Provision/scan.pdf",
 *   "contentType": "application/pdf",
 *   "fileSize": 123456,
 *   "contentBase64": "JVBERi0xLjQK..."
 * }
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/activity_logger.php';

/**
 * Haupt-Handler fuer eingehende Scan-Dokumente.
 */
function handleIncomingScansRequest(string $method): void {
    // Nur POST erlaubt
    if ($method !== 'POST') {
        json_error('Methode nicht erlaubt. Nur POST.', 405);
    }
    
    // API-Key validieren
    validateApiKey();
    
    // Scan verarbeiten
    processIncomingScan();
}

// ============================================================================
// AUTHENTIFIZIERUNG
// ============================================================================

/**
 * Validiert den API-Key aus dem X-API-Key Header.
 * 
 * Verwendet hash_equals() fuer timing-sicheren Vergleich.
 * Bricht mit HTTP 401 ab, wenn der Key fehlt oder ungueltig ist.
 */
function validateApiKey(): void {
    // Key aus Header lesen (Apache: HTTP_X_API_KEY)
    $apiKey = $_SERVER['HTTP_X_API_KEY'] ?? '';
    
    if (empty($apiKey)) {
        // Activity-Log: Fehlgeschlagener Zugriff
        ActivityLogger::log([
            'user_id' => null,
            'username' => 'scan_api',
            'action_category' => 'scan',
            'action' => 'auth_failed',
            'description' => 'Scan-Upload ohne API-Key',
            'status' => 'denied'
        ]);
        json_error('API-Key erforderlich (Header: X-API-Key)', 401);
    }
    
    if (!hash_equals(SCAN_API_KEY, $apiKey)) {
        // Activity-Log: Ungueltiger Key
        ActivityLogger::log([
            'user_id' => null,
            'username' => 'scan_api',
            'action_category' => 'scan',
            'action' => 'auth_failed',
            'description' => 'Scan-Upload mit ungueltigem API-Key',
            'status' => 'denied'
        ]);
        json_error('Ungueltiger API-Key', 401);
    }
}

// ============================================================================
// SCAN-VERARBEITUNG
// ============================================================================

/**
 * Verarbeitet einen eingehenden Scan:
 * 1. JSON validieren
 * 2. MIME-Type pruefen
 * 3. Base64 dekodieren
 * 4. Datei speichern (Atomic Write)
 * 5. DB-Eintrag erstellen
 * 6. Activity-Log schreiben
 */
function processIncomingScan(): void {
    // ---- 1. JSON-Body parsen und validieren ----
    $data = get_json_body();
    
    if (empty($data)) {
        json_error('Leerer oder ungueltiger JSON-Body', 400);
    }
    
    // Pflichtfelder pruefen
    require_fields($data, ['fileName', 'contentBase64']);
    
    $fileName = $data['fileName'];
    $filePath = $data['filePath'] ?? '';       // Optional, nur fuer Logging
    $contentType = $data['contentType'] ?? '';  // Optional, wird validiert wenn vorhanden
    $fileSize = $data['fileSize'] ?? 0;        // Optional, wird nach Dekodierung geprueft
    $contentBase64 = $data['contentBase64'];
    
    // ---- 2. MIME-Type validieren ----
    $resolvedMimeType = validateAndResolveMimeType($fileName, $contentType);
    
    // ---- 3. Dateinamen bereinigen (Path-Traversal-Schutz) ----
    $safeFileName = sanitizeFileName($fileName);
    
    if (empty($safeFileName)) {
        json_error('Ungueltiger Dateiname', 400);
    }
    
    // ---- 4. Base64 dekodieren ----
    $fileContent = base64_decode($contentBase64, true);
    
    if ($fileContent === false) {
        json_error('Ungueltige Base64-Kodierung', 400);
    }
    
    $decodedSize = strlen($fileContent);
    
    // Groessencheck
    if ($decodedSize === 0) {
        json_error('Datei ist leer (0 Bytes)', 400);
    }
    
    if ($decodedSize > MAX_UPLOAD_SIZE) {
        $maxMb = MAX_UPLOAD_SIZE / 1024 / 1024;
        json_error("Datei zu gross: " . round($decodedSize / 1024 / 1024, 2) . " MB (max. {$maxMb} MB)", 400);
    }
    
    // Optionaler Groessenvergleich mit angegebenem fileSize
    if ($fileSize > 0 && abs($decodedSize - $fileSize) > 1024) {
        // Toleranz von 1 KB fuer Base64-Padding-Unterschiede
        error_log("Scan-Upload: Groessenabweichung - angegeben: {$fileSize}, dekodiert: {$decodedSize}");
    }
    
    // ---- 5. Datei speichern (Atomic Write Pattern) ----
    $uniqueFilename = date('Y-m-d_His') . '_' . uniqid() . '_' . $safeFileName;
    $subdir = date('Y/m');
    $targetDir = DOCUMENTS_PATH . $subdir;
    $stagingDir = DOCUMENTS_PATH . 'staging';
    
    // Verzeichnisse erstellen
    if (!is_dir($targetDir)) {
        if (!mkdir($targetDir, 0755, true)) {
            json_error('Zielverzeichnis konnte nicht erstellt werden', 500);
        }
    }
    if (!is_dir($stagingDir)) {
        if (!mkdir($stagingDir, 0755, true)) {
            json_error('Staging-Verzeichnis konnte nicht erstellt werden', 500);
        }
    }
    
    $stagingPath = $stagingDir . '/.tmp_' . $uniqueFilename;
    $targetPath = $targetDir . '/' . $uniqueFilename;
    $storagePath = $subdir . '/' . $uniqueFilename;
    
    // Schritt 5a: In Staging schreiben
    $bytesWritten = file_put_contents($stagingPath, $fileContent);
    
    if ($bytesWritten === false || $bytesWritten !== $decodedSize) {
        @unlink($stagingPath);
        json_error('Datei konnte nicht in Staging geschrieben werden', 500);
    }
    
    // Speicher freigeben (Base64 + Decoded Content nicht mehr noetig)
    unset($contentBase64, $fileContent, $data['contentBase64']);
    
    // Schritt 5b: Content-Hash berechnen
    $contentHash = hash_file('sha256', $stagingPath);
    
    // Schritt 5c: GDV-Pruefung
    $isGdv = isGdvFileScan($stagingPath);
    
    // ---- 6. DB-Eintrag erstellen (Transaktion) ----
    Database::beginTransaction();
    
    try {
        // Duplikat-Pruefung via content_hash
        $version = 1;
        $previousVersionId = null;
        $isDuplicate = false;
        
        if ($contentHash) {
            $existing = Database::queryOne(
                "SELECT id, version, original_filename 
                 FROM documents 
                 WHERE content_hash = ? 
                 ORDER BY version DESC 
                 LIMIT 1",
                [$contentHash]
            );
            
            if ($existing) {
                $isDuplicate = true;
                $previousVersionId = $existing['id'];
                $version = $existing['version'] + 1;
                error_log("Scan-Upload: Duplikat erkannt - Hash=$contentHash, Version=$version");
            }
        }
        
        // DB-Insert
        $docId = Database::insert("
            INSERT INTO documents 
            (filename, original_filename, mime_type, file_size, storage_path, 
             source_type, is_gdv, uploaded_by, box_type, processing_status,
             content_hash, version, previous_version_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ", [
            $uniqueFilename,
            basename($fileName),  // Original-Dateiname (bereinigt)
            $resolvedMimeType,
            $decodedSize,
            $storagePath,
            'scan',              // Herkunft: Scan (Power Automate / SharePoint)
            $isGdv ? 1 : 0,
            null,                // uploaded_by: kein User (API-Key-Auth)
            'eingang',           // Box: Eingangsbox fuer KI-Verarbeitung
            'pending',           // Processing: bereit zur Verarbeitung
            $contentHash,
            $version,
            $previousVersionId
        ]);
        
        // Atomic Move: Staging -> Ziel
        if (!rename($stagingPath, $targetPath)) {
            throw new Exception("Atomic move fehlgeschlagen: $stagingPath -> $targetPath");
        }
        
        // Activity-Log
        ActivityLogger::log([
            'user_id' => null,
            'username' => 'scan_api',
            'action_category' => 'scan',
            'action' => 'upload',
            'entity_type' => 'document',
            'entity_id' => $docId,
            'description' => "Scan-Dokument empfangen: " . basename($fileName) 
                . ($isDuplicate ? " (Version {$version})" : ''),
            'details' => [
                'original_filename' => basename($fileName),
                'sharepoint_path' => $filePath,
                'mime_type' => $resolvedMimeType,
                'file_size' => $decodedSize,
                'content_hash' => $contentHash,
                'version' => $version,
                'is_duplicate' => $isDuplicate,
                'storage_path' => $storagePath
            ],
            'status' => 'success'
        ]);
        
        // Commit
        Database::commit();
        
        // Erfolgs-Response
        $message = $isDuplicate 
            ? "Scan-Dokument gespeichert (Version $version, Duplikat erkannt)"
            : 'Scan-Dokument gespeichert';
        
        json_success([
            'status' => 'success',
            'storedFile' => $storagePath,
            'documentId' => $docId,
            'originalFileName' => basename($fileName),
            'contentHash' => $contentHash,
            'boxType' => 'eingang',
            'version' => $version,
            'isDuplicate' => $isDuplicate
        ], $message);
        
    } catch (Exception $e) {
        // Rollback + Cleanup
        Database::rollback();
        
        if (file_exists($stagingPath)) {
            @unlink($stagingPath);
        }
        if (file_exists($targetPath)) {
            @unlink($targetPath);
        }
        
        // Activity-Log: Fehler
        ActivityLogger::log([
            'user_id' => null,
            'username' => 'scan_api',
            'action_category' => 'scan',
            'action' => 'upload_error',
            'description' => 'Scan-Upload fehlgeschlagen: ' . $e->getMessage(),
            'details' => [
                'original_filename' => basename($fileName),
                'error' => $e->getMessage()
            ],
            'status' => 'error'
        ]);
        
        error_log("Scan-Upload fehlgeschlagen (Rollback): " . $e->getMessage());
        json_error('Scan-Upload fehlgeschlagen: ' . $e->getMessage(), 500);
    }
}

// ============================================================================
// HILFSFUNKTIONEN
// ============================================================================

/**
 * Validiert den MIME-Type gegen die Whitelist.
 * 
 * Prueft sowohl den angegebenen contentType als auch die Dateiendung.
 * Gibt den aufgeloesten MIME-Type zurueck.
 * 
 * @param string $fileName Original-Dateiname
 * @param string $contentType Angegebener Content-Type
 * @return string Aufgeloester MIME-Type
 */
function validateAndResolveMimeType(string $fileName, string $contentType): string {
    // Extension-zu-MIME-Mapping
    $extToMime = [
        'pdf'  => 'application/pdf',
        'jpg'  => 'image/jpeg',
        'jpeg' => 'image/jpeg',
        'png'  => 'image/png',
    ];
    
    // Extension ermitteln
    $ext = strtolower(pathinfo(basename($fileName), PATHINFO_EXTENSION));
    $mimeFromExt = $extToMime[$ext] ?? null;
    
    // Wenn contentType angegeben, validieren
    if (!empty($contentType)) {
        // contentType bereinigen (z.B. "application/pdf; charset=utf-8" -> "application/pdf")
        $cleanContentType = strtolower(trim(explode(';', $contentType)[0]));
        
        if (in_array($cleanContentType, SCAN_ALLOWED_MIME_TYPES)) {
            return $cleanContentType;
        }
    }
    
    // Fallback: MIME-Type aus Extension
    if ($mimeFromExt && in_array($mimeFromExt, SCAN_ALLOWED_MIME_TYPES)) {
        return $mimeFromExt;
    }
    
    // Weder contentType noch Extension sind erlaubt
    $allowed = implode(', ', SCAN_ALLOWED_MIME_TYPES);
    json_error(
        "Nicht erlaubter Dateityp. contentType='$contentType', Extension='$ext'. " .
        "Erlaubt: $allowed",
        400
    );
    
    // Wird nie erreicht (json_error ruft exit() auf), aber fuer statische Analyse
    return '';
}

/**
 * Bereinigt einen Dateinamen fuer sichere Speicherung.
 * 
 * - Extrahiert nur den Basis-Dateinamen (kein Pfad)
 * - Entfernt alle Sonderzeichen ausser a-z, A-Z, 0-9, Punkt, Bindestrich, Unterstrich
 * - Schuetzt vor Path Traversal (.., /, \)
 * 
 * @param string $fileName Original-Dateiname
 * @return string Bereinigter Dateiname
 */
function sanitizeFileName(string $fileName): string {
    // Nur Dateiname, kein Pfad
    $baseName = basename($fileName);
    
    // Sonderzeichen entfernen (erlaubt: a-z, A-Z, 0-9, Punkt, Bindestrich, Unterstrich)
    $safe = preg_replace('/[^a-zA-Z0-9._-]/', '_', $baseName);
    
    // Fuehrende Punkte entfernen (keine versteckten Dateien)
    $safe = ltrim($safe, '.');
    
    // Doppelte Unterstriche zusammenfassen
    $safe = preg_replace('/_+/', '_', $safe);
    
    // Maximal 200 Zeichen
    if (strlen($safe) > 200) {
        $ext = pathinfo($safe, PATHINFO_EXTENSION);
        $name = pathinfo($safe, PATHINFO_FILENAME);
        $safe = substr($name, 0, 200 - strlen($ext) - 1) . '.' . $ext;
    }
    
    return $safe;
}

/**
 * Prueft ob eine Datei eine GDV-Datei ist.
 * (Kopie aus documents.php - eigenstaendig fuer Scan-Endpunkt)
 * 
 * @param string $path Pfad zur Datei
 * @return bool True wenn GDV-Datei
 */
function isGdvFileScan(string $path): bool {
    $handle = @fopen($path, 'r');
    if (!$handle) {
        return false;
    }
    
    $firstLine = fgets($handle, 260);
    fclose($handle);
    
    if (!$firstLine) {
        return false;
    }
    
    return substr($firstLine, 0, 4) === '0001';
}
