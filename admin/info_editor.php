<?php
require __DIR__ . '/config.php';
admin_session_start();
require_login();

$file = $SITES['highhope-info']['file'];
$msg = ''; $err = '';

// parse τρέχουσες τιμές από το footer του menu.html
function hh_get($html) {
  $out = ['address'=>'', 'hours'=>'', 'wifi'=>'', 'phone'=>''];
  if (preg_match('#<footer class="qr-footer">\s*<p>(.*?)<br>(.*?)</p>#s', $html, $m)) {
    $out['address'] = html_entity_decode(trim($m[1]), ENT_QUOTES|ENT_HTML5, 'UTF-8');
    $out['hours'] = html_entity_decode(trim($m[2]), ENT_QUOTES|ENT_HTML5, 'UTF-8');
  }
  if (preg_match('#<span class="wifi">(.*?)</span>#s', $html, $m)) {
    $out['wifi'] = html_entity_decode(trim($m[1]), ENT_QUOTES|ENT_HTML5, 'UTF-8');
  }
  if (preg_match('#href="tel:([^"]+)"#', $html, $m)) $out['phone'] = $m[1];
  return $out;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  check_csrf();
  $html = file_get_contents($file);
  make_backup($file);
  $e = fn($s) => htmlspecialchars(trim($s), ENT_QUOTES|ENT_HTML5, 'UTF-8');
  $address = $e($_POST['address'] ?? '');
  $hours   = $e($_POST['hours'] ?? '');
  $wifi    = $e($_POST['wifi'] ?? '');
  $phone   = preg_replace('/[^0-9+]/', '', $_POST['phone'] ?? '');
  if ($address && $hours) {
    $html = preg_replace('#(<footer class="qr-footer">\s*<p>).*?(</p>)#s', '$1' . $address . '<br>' . $hours . '$2', $html, 1);
  }
  if ($wifi) $html = preg_replace('#(<span class="wifi">).*?(</span>)#s', '$1' . $wifi . '$2', $html, 1);
  if ($phone) $html = preg_replace('#href="tel:[^"]*"#', 'href="tel:' . $phone . '"', $html, 1);
  file_put_contents($file, $html, LOCK_EX);
  $msg = '✅ Αποθηκεύτηκε!';
}

$v = hh_get(file_get_contents($file));
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>High Hope — Στοιχεία</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="dashboard.php" class="back">←</a> <span>High Hope — Στοιχεία</span></div>
</header>
<main class="wrap wrap-narrow">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?> <a href="https://codehouse.gr/clients/highhope/menu.html" target="_blank">Δες το ↗</a></div><?php endif; ?>
  <form method="post" class="form-card">
    <input type="hidden" name="csrf" value="<?=csrf_token()?>">
    <label>Διεύθυνση</label>
    <input name="address" value="<?=h($v['address'])?>">
    <label>Ωράριο</label>
    <input name="hours" value="<?=h($v['hours'])?>">
    <label>WiFi (όνομα & κωδικός)</label>
    <input name="wifi" value="<?=h($v['wifi'])?>">
    <label>Τηλέφωνο παραγγελιών</label>
    <input name="phone" value="<?=h($v['phone'])?>" placeholder="+302109641120">
    <button type="submit" class="btn btn-primary btn-block">💾 Αποθήκευση</button>
  </form>
</main>
</body>
</html>
