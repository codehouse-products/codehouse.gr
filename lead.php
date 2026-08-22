<?php
/**
 * Codehouse lead capture endpoint.
 * Αποθηκεύει κάθε υποβολή σε JSON αρχείο (leads/leads.jsonl)
 * και στέλνει email ειδοποίηση στο hello@codehouse.gr μέσω Zoho Mail API (HTTPS).
 */
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    // lead.php is a form endpoint, not a content page. Send direct visits
    // to the public offer page instead of exposing a confusing 405 response.
    header('Location: /prosfora/', true, 301);
    exit;
}

header('Content-Type: application/json; charset=utf-8');

$raw = file_get_contents('php://input');
$data = json_decode($raw, true);

if (!$data || !is_array($data)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'payload']);
    exit;
}

// Sanitize keys and values
$clean = [];
foreach ($data as $k => $v) {
    if (!is_string($v)) continue;
    $clean_key = substr(preg_replace('/[^a-zA-Z0-9_]/', '', $k), 0, 40);
    $clean[$clean_key] = substr(strip_tags($v), 0, 2000);
}

$clean['ip'] = $_SERVER['REMOTE_ADDR'] ?? '';
$clean['received'] = date('c');

// Save to JSONL
$dir = __DIR__ . '/leads';
if (!is_dir($dir)) { @mkdir($dir, 0750, true); }
@file_put_contents($dir . '/leads.jsonl', json_encode($clean, JSON_UNESCAPED_UNICODE) . "\n", FILE_APPEND | LOCK_EX);

// ------- Email μέσω Zoho Mail API -------
$subject = 'Νέο lead από codehouse.gr — ' . ($clean['name'] ?? 'χωρίς όνομα');
$body = "Νέα εκδήλωση ενδιαφέροντος από τη φόρμα του codehouse.gr:\n\n";
foreach ($clean as $k => $v) {
    if ($v !== '') {
        $body .= ucfirst(str_replace('_', ' ', $k)) . ": $v\n";
    }
}

$mailResult = zoho_send_mail($subject, $body);

echo json_encode([
    'ok' => true, 
    'mail' => $mailResult['sent'],
    'debug' => $mailResult['debug']
]);

function zoho_send_mail(string $subject, string $body): array {
    $cfgFile = '/home/artivoai/htdocs/zoho_secrets/zoho.json';
    if (!is_file($cfgFile)) return ['sent' => false, 'debug' => 'Config file not found'];
    
    $cfg = json_decode(file_get_contents($cfgFile), true);
    if (!$cfg) return ['sent' => false, 'debug' => 'Invalid config JSON'];

    $cacheFile = dirname($cfgFile) . '/token_cache.json';
    $accessToken = null;
    
    if (is_file($cacheFile)) {
        $c = json_decode(file_get_contents($cacheFile), true);
        if ($c && isset($c['token'], $c['exp']) && $c['exp'] > time()) {
            $accessToken = $c['token'];
        }
    }

    if (!$accessToken) {
        $ch = curl_init('https://accounts.zoho.eu/oauth/v2/token');
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
        $res = curl_exec($ch);
        curl_close($ch);
        
        $j = json_decode((string)$res, true);
        if (!$j || empty($j['access_token'])) {
            return ['sent' => false, 'debug' => 'Failed to refresh token: ' . ($res ?? 'no response')];
        }
        
        $accessToken = $j['access_token'];
        @file_put_contents($cacheFile, json_encode(['token' => $accessToken, 'exp' => time() + 3000]));
    }

    $payload = json_encode([
        'fromAddress' => $cfg['from'],
        'toAddress' => $cfg['to'],
        'subject' => $subject,
        'content' => nl2br(htmlspecialchars($body, ENT_QUOTES, 'UTF-8')),
    ], JSON_UNESCAPED_UNICODE);

    $ch = curl_init('https://mail.zoho.eu/api/accounts/' . $cfg['account_id'] . '/messages');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 25,
        CURLOPT_HTTPHEADER => [
            'Authorization: Zoho-oauthtoken ' . $accessToken,
            'Content-Type: application/json',
        ],
        CURLOPT_POSTFIELDS => $payload,
    ]);
    $res = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    return [
        'sent' => ($code === 200 || $code === 201),
        'debug' => "HTTP $code: " . ($res ?? 'no response')
    ];
}
