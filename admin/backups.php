<?php
require __DIR__ . '/config.php';
admin_session_start();
require_login();

$msg = ''; $err = '';

// map backup filename -> πραγματικό αρχείο προορισμού
function backup_target($bak) {
  // format: {parentdir}-{filename}.{Ymd-His}.bak
  $base = basename($bak);
  if (!preg_match('/^(.+)\.(\d{8}-\d{6})\.bak$/', $base, $m)) return null;
  $key = $m[1]; // π.χ. highhope-menu.html ή artivoai.com-index.html
  $map = [
    'highhope-menu.html' => SITE_ROOT . '/clients/highhope/menu.html',
    'highhope-index.html' => SITE_ROOT . '/clients/highhope/index.html',
    'artivoai.com-index.html' => SITE_ROOT . '/index.html',
    'img' => null,
  ];
  if (isset($map[$key]) && $map[$key]) return $map[$key];
  // εικόνες: {dirname}-{filename}
  foreach ([SITE_ROOT.'/clients/highhope/assets/img', SITE_ROOT.'/clients/highhope/assets/menu', SITE_ROOT.'/assets/img'] as $dir) {
    $dn = basename($dir);
    if (strpos($key, $dn . '-') === 0) {
      $fn = substr($key, strlen($dn) + 1);
      if (file_exists($dir . '/' . $fn) || true) return $dir . '/' . $fn;
    }
  }
  return null;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  check_csrf();
  $bak = BACKUP_DIR . '/' . basename($_POST['bak'] ?? '');
  $target = backup_target($bak);
  if (!file_exists($bak) || !$target) { $err = 'Δεν βρέθηκε το backup.'; }
  else {
    make_backup($target); // κρατάμε και την τρέχουσα έκδοση
    copy($bak, $target);
    chmod($target, 0644);
    $msg = '✅ Επαναφορά ολοκληρώθηκε! Το αρχείο γύρισε στην προηγούμενη έκδοση.';
  }
}

$backups = glob(BACKUP_DIR . '/*.bak') ?: [];
usort($backups, fn($a,$b)=>filemtime($b)-filemtime($a));
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Backups</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="dashboard.php" class="back">←</a> <span>Backups</span></div>
</header>
<main class="wrap wrap-narrow">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?></div><?php endif; ?>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>
  <?php if (!$backups): ?>
    <p class="note">Δεν υπάρχουν backups ακόμα. Δημιουργούνται αυτόματα με κάθε αποθήκευση.</p>
  <?php else: ?>
  <div class="bak-list">
    <?php foreach ($backups as $b): $bn = basename($b); ?>
    <div class="bak-row">
      <div class="bak-info">
        <strong><?=h(preg_replace('/\.\d{8}-\d{6}\.bak$/', '', $bn))?></strong>
        <span><?=date('d/m/Y H:i:s', filemtime($b))?> · <?=round(filesize($b)/1024)?> KB</span>
      </div>
      <form method="post" onsubmit="return confirm('Επαναφορά σε αυτή την έκδοση;');">
        <input type="hidden" name="csrf" value="<?=csrf_token()?>">
        <input type="hidden" name="bak" value="<?=h($bn)?>">
        <button type="submit" class="btn btn-ghost btn-sm">↩ Επαναφορά</button>
      </form>
    </div>
    <?php endforeach; ?>
  </div>
  <?php endif; ?>
</main>
</body>
</html>
