<?php
/**
 * BiPro API - Bekannte Passwoerter (PDF / ZIP)
 * 
 * Zentrale Verwaltung von Passwoertern fuer automatisches Entschluesseln
 * von PDF- und ZIP-Dateien beim Upload.
 * 
 * Oeffentliche Endpunkte (JWT erforderlich):
 * - GET /passwords?type=pdf       - Aktive Passwoerter nach Typ abrufen
 * - GET /passwords?type=zip       - Aktive ZIP-Passwoerter abrufen
 * 
 * Admin-Endpunkte (Admin-Rechte erforderlich):
 * - GET    /admin/passwords           - Alle Passwoerter auflisten
 * - GET    /admin/passwords?type=pdf  - Gefiltert nach Typ
 * - POST   /admin/passwords           - Neues Passwort anlegen
 * - PUT    /admin/passwords/{id}      - Passwort bearbeiten
 * - DELETE /admin/passwords/{id}      - Passwort deaktivieren (Soft-Delete)
 */

require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/jwt.php';
require_once __DIR__ . '/lib/response.php';
require_once __DIR__ . '/lib/permissions.php';
require_once __DIR__ . '/lib/activity_logger.php';
require_once __DIR__ . '/lib/crypto.php';

/**
 * Oeffentlicher Endpunkt: GET /passwords?type=pdf|zip
 * Gibt nur die Passwort-Werte zurueck (fuer Desktop-Client).
 */
function handlePasswordsPublicRequest(string $method): void {
    if ($method !== 'GET') {
        json_error('Methode nicht erlaubt', 405);
    }
    
    // JWT erforderlich (aber kein Admin)
    $payload = JWT::requireAuth();
    
    $type = $_GET['type'] ?? '';
    if (!in_array($type, ['pdf', 'zip'])) {
        json_error('Parameter "type" erforderlich (pdf oder zip)', 400);
    }
    
    $passwords = Database::query(
        'SELECT password_value FROM known_passwords WHERE password_type = ? AND is_active = 1 ORDER BY id ASC',
        [$type]
    );
    
    // SV-006 Fix: Passwoerter entschluesseln (verschluesselt gespeichert)
    $values = [];
    foreach ($passwords as $row) {
        try {
            $values[] = Crypto::decrypt($row['password_value']);
        } catch (Exception $e) {
            // Fallback: Klartext-Wert (fuer noch nicht migrierte Eintraege)
            $values[] = $row['password_value'];
        }
    }
    
    json_success(['passwords' => $values]);
}

/**
 * Admin-Endpunkt: /admin/passwords
 */
function handleAdminPasswordsRequest(?string $idOrAction, string $method): void {
    $payload = requireAdmin();
    
    switch ($method) {
        case 'GET':
            handleListPasswords();
            break;
            
        case 'POST':
            handleCreatePassword($payload);
            break;
            
        case 'PUT':
            if (empty($idOrAction) || !is_numeric($idOrAction)) {
                json_error('Passwort-ID erforderlich', 400);
            }
            handleUpdatePassword((int)$idOrAction, $payload);
            break;
            
        case 'DELETE':
            if (empty($idOrAction) || !is_numeric($idOrAction)) {
                json_error('Passwort-ID erforderlich', 400);
            }
            handleDeletePassword((int)$idOrAction, $payload);
            break;
            
        default:
            json_error('Methode nicht erlaubt', 405);
    }
}

/**
 * GET /admin/passwords[?type=pdf|zip]
 * Alle Passwoerter auflisten (mit optionalem Typ-Filter).
 */
function handleListPasswords(): void {
    $type = $_GET['type'] ?? '';
    
    if ($type && in_array($type, ['pdf', 'zip'])) {
        $passwords = Database::query(
            'SELECT id, password_type, password_value, description, created_at, created_by, is_active 
             FROM known_passwords 
             WHERE password_type = ?
             ORDER BY password_type ASC, id ASC',
            [$type]
        );
    } else {
        $passwords = Database::query(
            'SELECT id, password_type, password_value, description, created_at, created_by, is_active 
             FROM known_passwords 
             ORDER BY password_type ASC, id ASC'
        );
    }
    
    // SV-006 Fix: Passwoerter fuer Admin-Anzeige entschluesseln
    foreach ($passwords as &$pw) {
        try {
            $pw['password_value'] = Crypto::decrypt($pw['password_value']);
        } catch (Exception $e) {
            // Klartext-Wert (noch nicht migriert) - unveraendert lassen
        }
    }
    unset($pw);
    
    json_success(['passwords' => $passwords]);
}

/**
 * POST /admin/passwords
 * Body: { password_type: "pdf"|"zip", password_value: "...", description?: "..." }
 */
function handleCreatePassword(array $adminPayload): void {
    $data = get_json_body();
    require_fields($data, ['password_type', 'password_value']);
    
    $type = $data['password_type'];
    $value = trim($data['password_value']);
    $description = trim($data['description'] ?? '');
    
    // Validierung
    if (!in_array($type, ['pdf', 'zip'])) {
        json_error('Ungueltiger Typ. Erlaubt: pdf, zip', 400);
    }
    
    if (strlen($value) === 0) {
        json_error('Passwort darf nicht leer sein', 400);
    }
    
    if (strlen($value) > 255) {
        json_error('Passwort darf maximal 255 Zeichen lang sein', 400);
    }
    
    // SV-006 Fix: Duplikat-Pruefung muss alle vorhandenen Passwoerter entschluesseln und vergleichen
    $allOfType = Database::query(
        'SELECT id, password_value, is_active FROM known_passwords WHERE password_type = ?',
        [$type]
    );
    $existing = null;
    foreach ($allOfType as $row) {
        $storedValue = $row['password_value'];
        try {
            $storedValue = Crypto::decrypt($storedValue);
        } catch (Exception $e) {
            // Klartext-Wert (noch nicht migriert)
        }
        if ($storedValue === $value) {
            $existing = $row;
            break;
        }
    }
    
    if ($existing) {
        if (!$existing['is_active']) {
            // Deaktiviertes Passwort reaktivieren
            Database::execute('UPDATE known_passwords SET is_active = 1, description = ? WHERE id = ?',
                [$description, $existing['id']]);
            
            ActivityLogger::logAdmin($adminPayload, 'password_reactivated', 'known_password', (int)$existing['id'],
                "Passwort reaktiviert: {$type}",
                ['password_type' => $type, 'description' => $description]
            );
            
            $password = Database::queryOne('SELECT * FROM known_passwords WHERE id = ?', [$existing['id']]);
            json_success(['password' => $password], 'Passwort reaktiviert');
        }
        json_error('Dieses Passwort existiert bereits fuer diesen Typ', 409);
    }
    
    // SV-006 Fix: Passwort verschluesselt speichern
    $encryptedValue = Crypto::encrypt($value);
    
    // Einfuegen
    $id = Database::insert(
        'INSERT INTO known_passwords (password_type, password_value, description, created_by) VALUES (?, ?, ?, ?)',
        [$type, $encryptedValue, $description ?: null, $adminPayload['user_id']]
    );
    
    // Activity Log
    ActivityLogger::logAdmin($adminPayload, 'password_created', 'known_password', $id,
        "Neues {$type}-Passwort angelegt",
        ['password_type' => $type, 'description' => $description]
    );
    
    $password = Database::queryOne('SELECT * FROM known_passwords WHERE id = ?', [$id]);
    json_success(['password' => $password], 'Passwort angelegt');
}

/**
 * PUT /admin/passwords/{id}
 * Body: { password_value?: "...", description?: "...", is_active?: 0|1 }
 */
function handleUpdatePassword(int $id, array $adminPayload): void {
    $password = Database::queryOne('SELECT * FROM known_passwords WHERE id = ?', [$id]);
    if (!$password) {
        json_error('Passwort nicht gefunden', 404);
    }
    
    $data = get_json_body();
    $changes = [];
    
    // Passwort-Wert aendern
    if (isset($data['password_value'])) {
        $value = trim($data['password_value']);
        if (strlen($value) === 0) {
            json_error('Passwort darf nicht leer sein', 400);
        }
        // SV-006: Duplikat-Pruefung gegen entschluesselte Werte
        $allOfType = Database::query(
            'SELECT id, password_value FROM known_passwords WHERE password_type = ? AND id != ?',
            [$password['password_type'], $id]
        );
        foreach ($allOfType as $row) {
            $storedValue = $row['password_value'];
            try { $storedValue = Crypto::decrypt($storedValue); } catch (Exception $e) {}
            if ($storedValue === $value) {
                json_error('Dieses Passwort existiert bereits fuer diesen Typ', 409);
            }
        }
        // SV-006 Fix: Verschluesselt speichern
        $encryptedValue = Crypto::encrypt($value);
        Database::execute('UPDATE known_passwords SET password_value = ? WHERE id = ?', [$encryptedValue, $id]);
        $changes['password_value'] = '(geaendert)';
    }
    
    // Beschreibung aendern
    if (isset($data['description'])) {
        $desc = trim($data['description']);
        Database::execute('UPDATE known_passwords SET description = ? WHERE id = ?', [$desc ?: null, $id]);
        $changes['description'] = $desc;
    }
    
    // Aktiv-Status aendern
    if (isset($data['is_active'])) {
        $active = $data['is_active'] ? 1 : 0;
        Database::execute('UPDATE known_passwords SET is_active = ? WHERE id = ?', [$active, $id]);
        $changes['is_active'] = $active;
    }
    
    // Activity Log
    ActivityLogger::logAdmin($adminPayload, 'password_updated', 'known_password', $id,
        "Passwort bearbeitet (Typ: {$password['password_type']})",
        ['changes' => $changes]
    );
    
    $updated = Database::queryOne('SELECT * FROM known_passwords WHERE id = ?', [$id]);
    json_success(['password' => $updated], 'Passwort aktualisiert');
}

/**
 * DELETE /admin/passwords/{id}
 * Soft-Delete (is_active = 0).
 */
function handleDeletePassword(int $id, array $adminPayload): void {
    $password = Database::queryOne('SELECT * FROM known_passwords WHERE id = ?', [$id]);
    if (!$password) {
        json_error('Passwort nicht gefunden', 404);
    }
    
    if (!$password['is_active']) {
        json_error('Passwort ist bereits deaktiviert', 400);
    }
    
    Database::execute('UPDATE known_passwords SET is_active = 0 WHERE id = ?', [$id]);
    
    // Activity Log
    ActivityLogger::logAdmin($adminPayload, 'password_deleted', 'known_password', $id,
        "Passwort deaktiviert (Typ: {$password['password_type']})",
        ['password_type' => $password['password_type']]
    );
    
    json_success([], 'Passwort deaktiviert');
}
