<?php
// ===== Codehouse Admin — config =====
// Κωδικός πρόσβασης (hash). Αλλαγή: php -r "echo password_hash('ΝΕΟΣ_ΚΩΔΙΚΟΣ', PASSWORD_DEFAULT);"
define('ADMIN_PASSWORD_HASH', '$2y$10$3VK.By22yqUvzF77YGLA5e4sPtvS3QOat.lCjg/8N/wD1InlZQ.s2');
define('SITE_ROOT', dirname(__DIR__)); // /home/artivoai/htdocs/artivoai.com
define('BACKUP_DIR', SITE_ROOT . '/admin/backups');
define('LOGIN_ATTEMPTS_FILE', SITE_ROOT . '/admin/backups/.attempts.json');
define('SESSION_NAME', 'chadmin');

// Επεξεργάσιμα sites και τα αρχεία τους
$SITES = [
  'highhope-menu' => [
    'label' => 'High Hope — Μενού (τιμές & προϊόντα)',
    'file'  => SITE_ROOT . '/clients/highhope/menu.html',
    'type'  => 'qrmenu',
  ],
  'codehouse-contact' => [
    'label' => 'Codehouse — Στοιχεία επικοινωνίας',
    'file'  => SITE_ROOT . '/index.html',
    'type'  => 'contact',
  ],
  'highhope-info' => [
    'label' => 'High Hope — Ωράριο / WiFi / Διεύθυνση',
    'file'  => SITE_ROOT . '/clients/highhope/menu.html',
    'type'  => 'hhinfo',
  ],
];

function admin_session_start() {
  session_name(SESSION_NAME);
  session_set_cookie_params(['lifetime'=>86400*7,'path'=>'/admin/','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);
  session_start();
}

function is_logged_in() { return !empty($_SESSION['ok']) && $_SESSION['ok'] === true; }

function require_login() {
  if (!is_logged_in()) { header('Location: index.php'); exit; }
}

// rate limiting: max 8 αποτυχίες / 15 λεπτά ανά IP
function too_many_attempts($ip) {
  if (!file_exists(LOGIN_ATTEMPTS_FILE)) return false;
  $d = json_decode(file_get_contents(LOGIN_ATTEMPTS_FILE), true) ?: [];
  $a = $d[$ip] ?? [];
  $a = array_filter($a, fn($t) => $t > time() - 900);
  return count($a) >= 8;
}
function record_attempt($ip) {
  $d = file_exists(LOGIN_ATTEMPTS_FILE) ? (json_decode(file_get_contents(LOGIN_ATTEMPTS_FILE), true) ?: []) : [];
  $d[$ip][] = time();
  foreach ($d as $k=>$v) { $d[$k] = array_values(array_filter($v, fn($t)=>$t > time()-900)); if(!$d[$k]) unset($d[$k]); }
  @file_put_contents(LOGIN_ATTEMPTS_FILE, json_encode($d));
}

function make_backup($file) {
  if (!is_dir(BACKUP_DIR)) mkdir(BACKUP_DIR, 0750, true);
  $name = BACKUP_DIR . '/' . basename(dirname($file)) . '-' . basename($file) . '.' . date('Ymd-His') . '.bak';
  copy($file, $name);
  // κράτα μόνο τα 40 τελευταία backups
  $all = glob(BACKUP_DIR . '/*.bak');
  if (count($all) > 40) { usort($all, fn($a,$b)=>filemtime($a)-filemtime($b)); foreach (array_slice($all, 0, count($all)-40) as $old) @unlink($old); }
  return $name;
}

function csrf_token() {
  if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(16));
  return $_SESSION['csrf'];
}
function check_csrf() {
  if (($_POST['csrf'] ?? '') !== ($_SESSION['csrf'] ?? '-')) { http_response_code(403); die('Λάθος CSRF token. Κάνε refresh.'); }
}
function h($s) { return htmlspecialchars($s ?? '', ENT_QUOTES, 'UTF-8'); }
