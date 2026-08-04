<?php
require __DIR__ . '/config.php';
admin_session_start();
require_login();

$file = $SITES['codehouse-contact']['file'];
$msg = ''; $err = '';

function ch_get($html) {
  $out = ['phone'=>'', 'email'=>''];
  if (preg_match('#href="tel:([^"]+)"#', $html, $m)) $out['phone'] = $m[1];
  if (preg_match('#href="mailto:([^"]+)"#', $html, $m)) $out['email'] = $m[1];
  return $out;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  check_csrf();
  $html = file_get_contents($file);
  $old = ch_get($html);
  $phone = preg_replace('/[^0-9+ ]/', '', $_POST['phone'] ?? '');
  $email = filter_var(trim($_POST['email'] ?? ''), FILTER_VALIDATE_EMAIL);
  if (!$phone && !$email) {
    $err = 'Συμπλήρωσε τουλάχιστον ένα πεδίο σωστά.';
  } else {
    make_backup($file);
    if ($phone && $old['phone']) {
      $telClean = str_replace(' ', '', $phone);
      // 1) όλα τα tel: links -> νέο νούμερο, και το κείμενο μέσα τους -> μορφοποιημένο
      $html = preg_replace('#(href="tel:)[^"]*("[^>]*>)([^<]*)(</a>)#u', '${1}' . $telClean . '${2}' . h(format_phone($phone)) . '${4}', $html);
      // 2) σκέτες αναφορές του παλιού νούμερου σε κείμενο (με ή χωρίς κενά)
      $oldClean = str_replace(' ', '', preg_replace('/^\+30/', '', $old['phone']));
      foreach ([format_phone($oldClean), $oldClean, $old['phone']] as $variant) {
        if ($variant) $html = str_replace($variant, format_phone($phone), $html);
      }
    }
    if ($email && $old['email']) $html = str_replace($old['email'], $email, $html);
    file_put_contents($file, $html, LOCK_EX);
    $msg = '✅ Αποθηκεύτηκε!';
  }
}

function chunk_split_phone($p) {
  $p = str_replace(' ', '', $p);
  if (strlen($p) === 10) return substr($p,0,3) . ' ' . substr($p,3,3) . ' ' . substr($p,6);
  return $p;
}
function format_phone($p) {
  $p = str_replace(' ', '', preg_replace('/^\+30/', '', $p));
  if (strlen($p) === 10) return substr($p,0,3) . ' ' . substr($p,3,3) . ' ' . substr($p,6);
  return $p;
}

$v = ch_get(file_get_contents($file));
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Codehouse — Επικοινωνία</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="dashboard.php" class="back">←</a> <span>Codehouse — Επικοινωνία</span></div>
</header>
<main class="wrap wrap-narrow">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?> <a href="https://codehouse.gr/" target="_blank">Δες το site ↗</a></div><?php endif; ?>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>
  <form method="post" class="form-card">
    <input type="hidden" name="csrf" value="<?=csrf_token()?>">
    <label>Τηλέφωνο</label>
    <input name="phone" value="<?=h($v['phone'])?>" placeholder="π.χ. 6912345678">
    <label>Email</label>
    <input name="email" type="email" value="<?=h($v['email'])?>" placeholder="π.χ. info@codehouse.gr">
    <button type="submit" class="btn btn-primary btn-block">💾 Αποθήκευση</button>
  </form>
  <p class="note">Οι αλλαγές εφαρμόζονται παντού στο codehouse.gr (footer, κουμπιά κλήσης, mailto links).</p>
</main>
</body>
</html>
