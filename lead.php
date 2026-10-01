<?php
/**
 * Codehouse lead capture endpoint.
 * Stores submissions in JSONL and sends email notifications via Zoho Mail API.
 */

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Location: /prosfora/', true, 301);
    exit;
}

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

const MAX_BODY_BYTES = 32768;
const RATE_WINDOW_SECONDS = 900;
const RATE_LIMIT = 6;

function respond(int $status, array $payload): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}

function fail_request(int $status, string $code): void
{
    respond($status, ['ok' => false, 'saved' => false, 'error' => $code]);
}

$contentLength = isset($_SERVER['CONTENT_LENGTH']) ? (int)$_SERVER['CONTENT_LENGTH'] : 0;
if ($contentLength > MAX_BODY_BYTES) {
    fail_request(413, 'payload_too_large');
}

$raw = file_get_contents('php://input', false, null, 0, MAX_BODY_BYTES + 1);
if ($raw === false || strlen($raw) > MAX_BODY_BYTES) {
    fail_request(413, 'payload_too_large');
}

$data = json_decode($raw, true);
if (!is_array($data) || $data === [] || array_is_list($data) || json_last_error() !== JSON_ERROR_NONE) {
    fail_request(400, 'invalid_payload');
}

$isStudio = isset($data['_form']) && $data['_form'] === 'studio';
if (array_key_exists('_form', $data) && !$isStudio) {
    fail_request(422, 'invalid_submission');
}
if ($isStudio) {
    if (array_key_exists('website', $data) && (!is_string($data['website']) || trim($data['website']) !== '')) {
        fail_request(400, 'invalid_submission');
    }

    $requiredFields = ['name', 'email', 'service', 'description'];
    foreach ($requiredFields as $field) {
        if (!isset($data[$field]) || !is_string($data[$field]) || trim($data[$field]) === '') {
            fail_request(422, 'invalid_submission');
        }
    }

    $serviceAllowlist = ['web', 'ecommerce', 'apps', 'ai', 'booking', 'branding'];
    $studioLimits = [
        'name' => 120,
        'company' => 160,
        'email' => 254,
        'service' => 20,
        'description' => 5000,
        'budget' => 120,
    ];
    $clean = ['_form' => 'studio'];
    foreach ($studioLimits as $field => $limit) {
        if (!array_key_exists($field, $data)) {
            continue;
        }
        if (!is_string($data[$field])) {
            fail_request(422, 'invalid_submission');
        }
        $value = trim(strip_tags($data[$field]));
        $valueLength = unicode_length($value);
        if ($valueLength > $limit) {
            fail_request(422, 'invalid_submission');
        }
        $clean[$field] = $value;
    }
    $clean['email'] = filter_var($clean['email'], FILTER_VALIDATE_EMAIL) ? $clean['email'] : '';
    if ($clean['email'] === '' || !in_array($clean['service'], $serviceAllowlist, true)) {
        fail_request(422, 'invalid_submission');
    }
    if (trim($clean['name']) === '' || unicode_length($clean['description']) < 10) {
        fail_request(422, 'invalid_submission');
    }
} else {
    // Preserve the legacy quiz's existing fields (notably name and phone).
    $clean = [];
    foreach ($data as $key => $value) {
        if (!is_string($key) || !is_string($value)) {
            continue;
        }
        $safeKey = substr(preg_replace('/[^a-zA-Z0-9_]/', '', $key), 0, 40);
        if ($safeKey === '' || in_array($safeKey, ['ip', 'ip_hash', 'received'], true)) {
            continue;
        }
        $value = trim(strip_tags($value));
        if (strlen($value) > 2000) {
            fail_request(422, 'invalid_submission');
        }
        $clean[$safeKey] = $value;
    }
    if (isset($clean['email']) && $clean['email'] !== '' && !filter_var($clean['email'], FILTER_VALIDATE_EMAIL)) {
        fail_request(422, 'invalid_submission');
    }
}

$remoteAddress = $_SERVER['REMOTE_ADDR'] ?? '';
if (!is_string($remoteAddress) || $remoteAddress === '') {
    $remoteAddress = 'unknown';
}
$rateLimitResult = consume_rate_limit($remoteAddress);
if ($rateLimitResult === null) {
    fail_request(503, 'rate_limit_unavailable');
}
if (!$rateLimitResult) {
    fail_request(429, 'rate_limited');
}

$clean['received'] = date(DATE_ATOM);
$jsonLine = json_encode($clean, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
if ($jsonLine === false || !persist_lead($jsonLine . "\n")) {
    fail_request(500, 'storage_unavailable');
}

$subjectName = str_replace(["\r", "\n"], ' ', $clean['name'] ?? 'χωρίς όνομα');
$subject = 'Νέο lead από codehouse.gr — ' . $subjectName;
$body = "Νέα εκδήλωση ενδιαφέροντος από τη φόρμα του codehouse.gr:\n\n";
foreach ($clean as $key => $value) {
    if ($value !== '') {
        $body .= ucfirst(str_replace('_', ' ', $key)) . ': ' . $value . "\n";
    }
}

$mailSent = zoho_send_mail($subject, $body);
respond($mailSent ? 200 : 202, [
    'ok' => true,
    'saved' => true,
    'mail' => $mailSent,
]);

function consume_rate_limit(string $ip): ?bool
{
    $directory = dirname(__DIR__) . '/.codehouse-lead-rate';
    if (!is_dir($directory) && !@mkdir($directory, 0700, true) && !is_dir($directory)) {
        return null;
    }
    @chmod($directory, 0700);

    $ipHash = hash('sha256', $ip);
    $path = $directory . '/' . $ipHash . '.json';
    $handle = @fopen($path, 'c+');
    if ($handle === false) {
        return null;
    }
    @chmod($path, 0600);

    $result = null;
    if (flock($handle, LOCK_EX)) {
        rewind($handle);
        $stored = stream_get_contents($handle);
        $timestamps = json_decode($stored === false ? '' : $stored, true);
        if (!is_array($timestamps)) {
            $timestamps = [];
        }
        $now = time();
        $timestamps = array_values(array_filter($timestamps, static function ($time) use ($now): bool {
            return is_int($time) && $time > $now - RATE_WINDOW_SECONDS;
        }));
        if (count($timestamps) >= RATE_LIMIT) {
            $result = false;
        } else {
            $timestamps[] = $now;
            $encoded = json_encode($timestamps);
            rewind($handle);
            if ($encoded !== false && ftruncate($handle, 0) && fwrite($handle, $encoded) === strlen($encoded) && fflush($handle)) {
                $result = true;
            }
        }
        flock($handle, LOCK_UN);
    }
    fclose($handle);
    return $result;
}

function unicode_length(string $value): int
{
    if (function_exists('mb_strlen')) {
        return mb_strlen($value, 'UTF-8');
    }
    $length = preg_match_all('/./us', $value, $matches);
    return $length === false ? PHP_INT_MAX : $length;
}

function persist_lead(string $line): bool
{
    // Store future submissions outside the document root. Historical files in
    // the old webroot leads directory are intentionally left untouched.
    $directory = dirname(__DIR__) . '/.codehouse-leads';
    if (is_link($directory)) {
        return false;
    }
    if (!is_dir($directory) && !@mkdir($directory, 0700, true) && !is_dir($directory)) {
        return false;
    }
    if (!@chmod($directory, 0700) || ((fileperms($directory) & 0777) !== 0700)) {
        return false;
    }

    $path = $directory . '/leads.jsonl';
    if (is_link($path)) {
        return false;
    }
    $handle = @fopen($path, 'c+b');
    if ($handle === false) {
        return false;
    }
    if (!@chmod($path, 0600) || ((fileperms($path) & 0777) !== 0600)) {
        fclose($handle);
        return false;
    }

    $saved = false;
    if (flock($handle, LOCK_EX) && fseek($handle, 0, SEEK_END) === 0) {
        $start = ftell($handle);
        $length = strlen($line);
        $written = 0;
        while ($start !== false && $written < $length) {
            $result = fwrite($handle, substr($line, $written));
            if ($result === false || $result === 0) {
                break;
            }
            $written += $result;
        }
        $flushed = $written === $length && fflush($handle);
        if ($flushed && function_exists('fsync')) {
            $flushed = fsync($handle);
        }
        $saved = $start !== false && $flushed;
        if (!$saved && $start !== false) {
            ftruncate($handle, $start);
            fflush($handle);
        }
        flock($handle, LOCK_UN);
    }
    fclose($handle);
    return $saved;
}

function zoho_send_mail(string $subject, string $body): bool
{
    $cfgFile = '/home/artivoai/htdocs/zoho_secrets/zoho.json';
    if (!is_file($cfgFile) || !function_exists('curl_init')) {
        return false;
    }

    $cfgContents = @file_get_contents($cfgFile);
    $cfg = $cfgContents === false ? null : json_decode($cfgContents, true);
    if (!is_array($cfg)) {
        return false;
    }
    foreach (['client_id', 'client_secret', 'refresh_token', 'from', 'to', 'account_id'] as $key) {
        if (!isset($cfg[$key]) || !is_string($cfg[$key]) || $cfg[$key] === '') {
            return false;
        }
    }

    $cacheFile = dirname($cfgFile) . '/token_cache.json';
    $accessToken = null;
    if (is_file($cacheFile)) {
        $cacheContents = @file_get_contents($cacheFile);
        $cache = $cacheContents === false ? null : json_decode($cacheContents, true);
        if (is_array($cache) && isset($cache['token'], $cache['exp']) && is_string($cache['token']) && (int)$cache['exp'] > time()) {
            $accessToken = $cache['token'];
        }
    }

    if (!$accessToken) {
        $ch = curl_init('https://accounts.zoho.eu/oauth/v2/token');
        if ($ch === false) {
            return false;
        }
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 20,
            CURLOPT_POSTFIELDS => http_build_query([
                'grant_type' => 'refresh_token',
                'client_id' => $cfg['client_id'],
                'client_secret' => $cfg['client_secret'],
                'refresh_token' => $cfg['refresh_token'],
            ]),
        ]);
        $response = curl_exec($ch);
        curl_close($ch);

        $tokenResponse = is_string($response) ? json_decode($response, true) : null;
        if (!is_array($tokenResponse) || empty($tokenResponse['access_token']) || !is_string($tokenResponse['access_token'])) {
            return false;
        }

        $accessToken = $tokenResponse['access_token'];
        $cacheData = json_encode(['token' => $accessToken, 'exp' => time() + 3000]);
        if ($cacheData !== false) {
            @file_put_contents($cacheFile, $cacheData, LOCK_EX);
            @chmod($cacheFile, 0600);
        }
    }

    $mailPayload = json_encode([
        'fromAddress' => $cfg['from'],
        'toAddress' => $cfg['to'],
        'subject' => $subject,
        'content' => nl2br(htmlspecialchars($body, ENT_QUOTES, 'UTF-8')),
    ], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    if ($mailPayload === false) {
        return false;
    }

    $ch = curl_init('https://mail.zoho.eu/api/accounts/' . rawurlencode($cfg['account_id']) . '/messages');
    if ($ch === false) {
        return false;
    }
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 25,
        CURLOPT_HTTPHEADER => [
            'Authorization: Zoho-oauthtoken ' . $accessToken,
            'Content-Type: application/json',
        ],
        CURLOPT_POSTFIELDS => $mailPayload,
    ]);
    curl_exec($ch);
    $statusCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    return $statusCode === 200 || $statusCode === 201;
}