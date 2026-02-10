<?php
/**
 * BiPro API - Releases / Auto-Update
 * 
 * Oeffentlicher Endpoint fuer Update-Checks + Admin CRUD fuer Release-Verwaltung.
 * 
 * Oeffentliche Endpunkte (keine Auth):
 * - GET /updates/check?version=X&channel=Y    - Update pruefen
 * - GET /releases/download/{id}               - Datei herunterladen (zaehlt Downloads)
 * 
 * Admin-Endpunkte:
 * - GET    /admin/releases                    - Alle Releases auflisten
 * - GET    /admin/releases/{id}               - Einzelnes Release
 * - POST   /admin/releases                    - Neues Release hochladen
 * - PUT    /admin/releases/{id}               - Release bearbeiten
 * - DELETE /admin/releases/{id}               - Release loeschen
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/response.php';

// Runtime-Limits fuer grosse Uploads (upload_max_filesize/post_max_size via .user.ini)
@ini_set('max_execution_time', '600');
@ini_set('max_input_time', '600');
@ini_set('memory_limit', '300M');

// Pfad zum Releases-Verzeichnis
define('RELEASES_PATH', __DIR__ . '/../releases/');

// Maximale Upload-Groesse fuer Installer (250 MB)
define('MAX_RELEASE_SIZE', 250 * 1024 * 1024);


/**
 * Oeffentlicher Update-Check Endpoint.
 * Keine Authentifizierung erforderlich.
 */
function handleUpdateCheckRequest(string $method): void {
    if ($method !== 'GET') {
        json_error('Methode nicht erlaubt', 405);
    }
    
    $currentVersion = $_GET['version'] ?? '';
    $channel = $_GET['channel'] ?? 'stable';
    
    if (empty($currentVersion)) {
        json_error('Parameter "version" erforderlich', 400);
    }
    
    // Validierung Channel
    $validChannels = ['stable', 'beta', 'internal'];
    if (!in_array($channel, $validChannels)) {
        $channel = 'stable';
    }
    
    // Neueste verfuegbare Version finden (active oder mandatory)
    $latest = Database::queryOne(
        "SELECT * FROM releases 
         WHERE channel = ? AND status IN ('active', 'mandatory')
         ORDER BY released_at DESC 
         LIMIT 1",
        [$channel]
    );
    
    if (!$latest) {
        // Keine Releases vorhanden
        json_response([
            'current_version' => $currentVersion,
            'latest_version' => $currentVersion,
            'update_available' => false,
            'mandatory' => false,
            'deprecated' => false
        ]);
        return;
    }
    
    // Versionen vergleichen
    $updateAvailable = version_compare($latest['version'], $currentVersion, '>');
    
    // Mandatory pruefen
    $mandatory = false;
    if ($updateAvailable) {
        // Fall 1: Neueste Version ist als mandatory markiert
        if ($latest['status'] === 'mandatory') {
            $mandatory = true;
        }
        // Fall 2: Aktuelle Version liegt unter min_version
        if (!empty($latest['min_version']) && version_compare($currentVersion, $latest['min_version'], '<')) {
            $mandatory = true;
        }
    }
    
    // Deprecated pruefen: Ist die aktuelle Version als deprecated/withdrawn markiert?
    $deprecated = false;
    $currentRelease = Database::queryOne(
        "SELECT status FROM releases WHERE version = ?",
        [$currentVersion]
    );
    if ($currentRelease && in_array($currentRelease['status'], ['deprecated', 'withdrawn'])) {
        $deprecated = true;
    }
    // Auch deprecated wenn aktuelle Version gar nicht in DB existiert und es neuere gibt
    if (!$currentRelease && $updateAvailable) {
        $deprecated = false; // Unbekannte Version ist nicht deprecated, nur veraltet
    }
    
    $response = [
        'current_version' => $currentVersion,
        'latest_version' => $latest['version'],
        'update_available' => $updateAvailable,
        'mandatory' => $mandatory,
        'deprecated' => $deprecated,
    ];
    
    if ($updateAvailable) {
        $response['release_notes'] = $latest['release_notes'] ?? '';
        $response['download_url'] = API_BASE_URL . 'releases/download/' . $latest['id'];
        $response['sha256'] = $latest['sha256'];
        $response['file_size'] = (int)$latest['file_size'];
        $response['released_at'] = $latest['released_at'];
    }
    
    json_response($response);
}


/**
 * Oeffentlicher Download-Endpoint (zaehlt Downloads).
 */
function handleReleaseDownload(int $releaseId): void {
    $release = Database::queryOne(
        "SELECT * FROM releases WHERE id = ?",
        [$releaseId]
    );
    
    if (!$release) {
        json_error('Release nicht gefunden', 404);
    }
    
    if ($release['status'] === 'withdrawn') {
        json_error('Release wurde zurueckgezogen', 410);
    }
    
    $filePath = RELEASES_PATH . $release['filename'];
    if (!file_exists($filePath)) {
        error_log("Release-Datei nicht gefunden: {$filePath}");
        json_error('Release-Datei nicht gefunden', 404);
    }
    
    // Download-Zaehler erhoehen
    Database::execute(
        "UPDATE releases SET download_count = download_count + 1 WHERE id = ?",
        [$releaseId]
    );
    
    // Datei senden
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="' . $release['filename'] . '"');
    header('Content-Length: ' . $release['file_size']);
    header('X-SHA256: ' . $release['sha256']);
    
    readfile($filePath);
    exit();
}


// ================================================================
// Admin-Endpunkte
// ================================================================

/**
 * Admin: Releases verwalten.
 */
function handleAdminReleasesRequest(?string $action, string $method): void {
    require_once __DIR__ . '/lib/jwt.php';
    require_once __DIR__ . '/lib/permissions.php';
    require_once __DIR__ . '/lib/activity_logger.php';
    
    $payload = requireAdmin();
    
    // GET /admin/releases - Alle auflisten
    if ($method === 'GET' && ($action === null || $action === '')) {
        handleListReleases();
        return;
    }
    
    // POST /admin/releases - Neues Release
    if ($method === 'POST' && ($action === null || $action === '')) {
        handleCreateRelease($payload);
        return;
    }
    
    // Ab hier brauchen wir eine Release-ID
    if (!is_numeric($action)) {
        json_error('Release-ID erforderlich', 400);
    }
    
    $releaseId = (int)$action;
    
    switch ($method) {
        case 'GET':
            handleGetRelease($releaseId);
            break;
        case 'PUT':
            handleUpdateRelease($releaseId, $payload);
            break;
        case 'DELETE':
            handleDeleteRelease($releaseId, $payload);
            break;
        default:
            json_error('Methode nicht erlaubt', 405);
    }
}


/**
 * Alle Releases auflisten.
 */
function handleListReleases(): void {
    $releases = Database::query(
        "SELECT r.*, u.username as released_by_name
         FROM releases r
         LEFT JOIN users u ON u.id = r.released_by
         ORDER BY r.released_at DESC"
    );
    
    json_success(['releases' => $releases]);
}


/**
 * Einzelnes Release abrufen.
 */
function handleGetRelease(int $id): void {
    $release = Database::queryOne(
        "SELECT r.*, u.username as released_by_name
         FROM releases r
         LEFT JOIN users u ON u.id = r.released_by
         WHERE r.id = ?",
        [$id]
    );
    
    if (!$release) {
        json_error('Release nicht gefunden', 404);
    }
    
    json_success(['release' => $release]);
}


/**
 * Neues Release erstellen (mit Datei-Upload).
 */
function handleCreateRelease(array $adminPayload): void {
    // Diagnostik: Wenn POST und FILES leer sind, wurde Upload von PHP abgelehnt
    if (empty($_POST) && empty($_FILES)) {
        $maxPost = ini_get('post_max_size');
        $maxUpload = ini_get('upload_max_filesize');
        json_error(
            "Upload von PHP abgelehnt (POST und FILES leer). " .
            "Wahrscheinlich ueberschreitet die Datei die PHP-Limits: " .
            "post_max_size={$maxPost}, upload_max_filesize={$maxUpload}. " .
            "Bitte .user.ini oder php.ini im API-Verzeichnis pruefen.",
            413
        );
    }
    
    // Multipart Form-Data Felder
    $version = $_POST['version'] ?? '';
    $channel = $_POST['channel'] ?? 'stable';
    $releaseNotes = $_POST['release_notes'] ?? '';
    $minVersion = $_POST['min_version'] ?? null;
    
    if (empty($version)) {
        json_error('Version ist erforderlich. POST-Felder: ' . implode(', ', array_keys($_POST)), 400);
    }
    
    // SemVer-Validierung (grob)
    if (!preg_match('/^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$/', $version)) {
        json_error('Version muss dem Format X.Y.Z entsprechen (z.B. 1.0.0 oder 1.1.0-beta.1)', 400);
    }
    
    // Pruefen ob Version bereits existiert
    $existing = Database::queryOne(
        "SELECT id FROM releases WHERE version = ?",
        [$version]
    );
    if ($existing) {
        json_error("Version {$version} existiert bereits", 409);
    }
    
    // Datei-Upload pruefen
    if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
        $errorMessages = [
            UPLOAD_ERR_INI_SIZE => 'Datei zu gross (PHP-Limit)',
            UPLOAD_ERR_FORM_SIZE => 'Datei zu gross (Formular-Limit)',
            UPLOAD_ERR_PARTIAL => 'Upload unvollstaendig',
            UPLOAD_ERR_NO_FILE => 'Keine Datei gesendet',
            UPLOAD_ERR_NO_TMP_DIR => 'Temporaeres Verzeichnis fehlt',
            UPLOAD_ERR_CANT_WRITE => 'Schreibfehler auf Disk',
        ];
        $errCode = $_FILES['file']['error'] ?? UPLOAD_ERR_NO_FILE;
        $msg = $errorMessages[$errCode] ?? "Upload-Fehler (Code: {$errCode})";
        json_error($msg, 400);
    }
    
    $tmpFile = $_FILES['file']['tmp_name'];
    $fileSize = filesize($tmpFile);
    
    if ($fileSize > MAX_RELEASE_SIZE) {
        json_error('Datei zu gross (max. ' . round(MAX_RELEASE_SIZE / 1024 / 1024) . ' MB)', 400);
    }
    
    // Dateiname normalisieren
    $filename = "ACENCIA-ATLAS-Setup-{$version}.exe";
    
    // Releases-Verzeichnis sicherstellen
    if (!is_dir(RELEASES_PATH)) {
        mkdir(RELEASES_PATH, 0755, true);
    }
    
    $targetPath = RELEASES_PATH . $filename;
    
    // SHA256 berechnen
    $sha256 = hash_file('sha256', $tmpFile);
    
    // Datei verschieben
    if (!move_uploaded_file($tmpFile, $targetPath)) {
        json_error('Datei konnte nicht gespeichert werden', 500);
    }
    
    // Channel validieren
    $validChannels = ['stable', 'beta', 'internal'];
    if (!in_array($channel, $validChannels)) {
        $channel = 'stable';
    }
    
    // In DB speichern
    $id = Database::insert(
        "INSERT INTO releases (version, channel, status, min_version, release_notes, filename, file_size, sha256, released_by)
         VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?)",
        [
            $version,
            $channel,
            $minVersion ?: null,
            $releaseNotes,
            $filename,
            $fileSize,
            $sha256,
            $adminPayload['user_id']
        ]
    );
    
    // Aktivitaet loggen
    ActivityLogger::log([
        'user_id' => $adminPayload['user_id'],
        'username' => $adminPayload['username'] ?? '',
        'action_category' => 'admin',
        'action' => 'release_created',
        'description' => "Release {$version} ({$channel}) hochgeladen",
        'details' => ['release_id' => $id, 'version' => $version, 'channel' => $channel],
        'status' => 'success'
    ]);
    
    $release = Database::queryOne("SELECT * FROM releases WHERE id = ?", [$id]);
    json_success(['release' => $release], "Release {$version} erfolgreich erstellt");
}


/**
 * Release bearbeiten (Status, Notes, Min-Version, Channel).
 */
function handleUpdateRelease(int $id, array $adminPayload): void {
    $release = Database::queryOne("SELECT * FROM releases WHERE id = ?", [$id]);
    
    if (!$release) {
        json_error('Release nicht gefunden', 404);
    }
    
    $data = get_json_body();
    
    $updates = [];
    $params = [];
    $changes = [];
    
    // Status aendern
    if (isset($data['status'])) {
        $validStatuses = ['active', 'mandatory', 'deprecated', 'withdrawn'];
        if (!in_array($data['status'], $validStatuses)) {
            json_error('Ungueltiger Status. Erlaubt: ' . implode(', ', $validStatuses), 400);
        }
        $updates[] = 'status = ?';
        $params[] = $data['status'];
        $changes[] = "Status: {$release['status']} → {$data['status']}";
    }
    
    // Channel aendern
    if (isset($data['channel'])) {
        $validChannels = ['stable', 'beta', 'internal'];
        if (!in_array($data['channel'], $validChannels)) {
            json_error('Ungueltiger Channel. Erlaubt: ' . implode(', ', $validChannels), 400);
        }
        $updates[] = 'channel = ?';
        $params[] = $data['channel'];
        $changes[] = "Channel: {$release['channel']} → {$data['channel']}";
    }
    
    // Release Notes aendern
    if (isset($data['release_notes'])) {
        $updates[] = 'release_notes = ?';
        $params[] = $data['release_notes'];
        $changes[] = "Release Notes aktualisiert";
    }
    
    // Min-Version aendern
    if (array_key_exists('min_version', $data)) {
        $minVersion = $data['min_version'];
        if ($minVersion !== null && !empty($minVersion) && !preg_match('/^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$/', $minVersion)) {
            json_error('min_version muss dem Format X.Y.Z entsprechen', 400);
        }
        $updates[] = 'min_version = ?';
        $params[] = $minVersion ?: null;
        $changes[] = "Min-Version: " . ($minVersion ?: 'keine');
    }
    
    if (empty($updates)) {
        json_error('Keine Aenderungen angegeben', 400);
    }
    
    $params[] = $id;
    Database::execute(
        "UPDATE releases SET " . implode(', ', $updates) . " WHERE id = ?",
        $params
    );
    
    // Aktivitaet loggen
    ActivityLogger::log([
        'user_id' => $adminPayload['user_id'],
        'username' => $adminPayload['username'] ?? '',
        'action_category' => 'admin',
        'action' => 'release_updated',
        'description' => "Release {$release['version']} bearbeitet: " . implode(', ', $changes),
        'details' => ['release_id' => $id, 'version' => $release['version'], 'changes' => $changes],
        'status' => 'success'
    ]);
    
    $updated = Database::queryOne("SELECT * FROM releases WHERE id = ?", [$id]);
    json_success(['release' => $updated], "Release {$release['version']} aktualisiert");
}


/**
 * Release loeschen (nur wenn keine Downloads).
 */
function handleDeleteRelease(int $id, array $adminPayload): void {
    $release = Database::queryOne("SELECT * FROM releases WHERE id = ?", [$id]);
    
    if (!$release) {
        json_error('Release nicht gefunden', 404);
    }
    
    if ((int)$release['download_count'] > 0) {
        json_error(
            "Release kann nicht geloescht werden ({$release['download_count']} Downloads). " .
            "Setzen Sie den Status stattdessen auf 'withdrawn'.",
            409,
            ['download_count' => (int)$release['download_count']]
        );
    }
    
    // Datei loeschen
    $filePath = RELEASES_PATH . $release['filename'];
    if (file_exists($filePath)) {
        unlink($filePath);
    }
    
    // DB-Eintrag loeschen
    Database::execute("DELETE FROM releases WHERE id = ?", [$id]);
    
    // Aktivitaet loggen
    ActivityLogger::log([
        'user_id' => $adminPayload['user_id'],
        'username' => $adminPayload['username'] ?? '',
        'action_category' => 'admin',
        'action' => 'release_deleted',
        'description' => "Release {$release['version']} geloescht",
        'details' => ['release_id' => $id, 'version' => $release['version']],
        'status' => 'success'
    ]);
    
    json_success([], "Release {$release['version']} geloescht");
}
