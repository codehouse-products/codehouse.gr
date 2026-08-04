<?php
require __DIR__ . '/config.php';
require __DIR__ . '/sites_lib.php';
admin_session_start();
require_login();

$sites = discover_sites();
$siteKey = $_GET['site'] ?? ($_POST['site'] ?? '');
if (!isset($sites[$siteKey])) { header('Location: sites.php'); exit; }
$S = $sites[$siteKey];

$imgDirs = site_image_dirs($S['dir']);
if (!$imgDirs) { header('Location: sites.php'); exit; }

$sub = $_GET['d'] ?? ($_POST['d'] ?? $imgDirs[0]);
if (!in_array($sub, $imgDirs)) $sub = $imgDirs[0];
$dir = $S['dir'] . '/' . $sub;
$urlBase = ($S['url'] ?? '') . '/' . $sub;

$ALLOWED_EXT = ['jpg','jpeg','png','webp','svg','gif','ico'];
$MAX_SIZE = 8 * 1024 * 1024;

$msg = ''; $err = '';

function safe_name2($name) {
  return preg_replace('/[^a-zA-Z0-9._-]/', '-', basename($name));
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  check_csrf();
  $action = $_POST['action'] ?? '';
  if ($action === 'replace' && isset($_FILES['newfile'])) {
    $target = safe_name2($_POST['target'] ?? '');
    $path = $dir . '/' . $target;
    $f = $_FILES['newfile'];
    $ext = strtolower(pathinfo($f['name'], PATHINFO_EXTENSION));
    $tExt = strtolower(pathinfo($target, PATHINFO_EXTENSION));
    $jpg = ['jpg','jpeg'];
    if (!file_exists($path)) $err = 'Το αρχείο δεν βρέθηκε.';
    elseif ($f['error'] !== UPLOAD_ERR_OK) $err = 'Σφάλμα στο ανέβασμα.';
    elseif ($f['size'] > $MAX_SIZE) $err = 'Πολύ μεγάλο αρχείο (max 8MB).';
    elseif (!in_array($ext, $ALLOWED_EXT)) $err = 'Μη επιτρεπτός τύπος.';
    elseif ($ext !== $tExt && !(in_array($ext,$jpg) && in_array($tExt,$jpg)))
      $err = "Το νέο αρχείο πρέπει να είναι ίδιου τύπου (.$tExt).";
    else {
      make_backup($path);
      move_uploaded_file($f['tmp_name'], $path);
      chmod($path, 0644);
      $msg = "✅ Η «{$target}» αντικαταστάθηκε!";
    }
  }
  if ($action === 'upload' && isset($_FILES['newfile'])) {
    $f = $_FILES['newfile'];
    $name = safe_name2($f['name']);
    $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
    if ($f['error'] !== UPLOAD_ERR_OK) $err = 'Σφάλμα στο ανέβασμα.';
    elseif ($f['size'] > $MAX_SIZE) $err = 'Πολύ μεγάλο αρχείο (max 8MB).';
    elseif (!in_array($ext, $ALLOWED_EXT)) $err = 'Μη επιτρεπτός τύπος.';
    else {
      if (file_exists("$dir/$name")) $name = pathinfo($name, PATHINFO_FILENAME) . '-' . date('His') . '.' . $ext;
      move_uploaded_file($f['tmp_name'], "$dir/$name");
      chmod("$dir/$name", 0644);
      $msg = "✅ Ανέβηκε ως «{$name}».";
    }
  }
}

$files = [];
foreach (glob($dir . '/*') as $f) {
  if (in_array(strtolower(pathinfo($f, PATHINFO_EXTENSION)), $ALLOWED_EXT)) $files[] = basename($f);
}
sort($files);
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Εικόνες — <?=h($S['label'])?></title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="sites.php" class="back">←</a> <span>Εικόνες — <?=h($S['label'])?></span></div>
</header>
<main class="wrap">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?></div><?php endif; ?>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>

  <?php if (count($imgDirs) > 1): ?>
  <div class="tabs">
    <?php foreach ($imgDirs as $d): ?>
      <a href="?site=<?=urlencode($siteKey)?>&d=<?=urlencode($d)?>" class="tab <?=$d===$sub?'active':''?>"><?=h($d)?></a>
    <?php endforeach; ?>
  </div>
  <?php endif; ?>

  <form method="post" enctype="multipart/form-data" class="upload-bar">
    <input type="hidden" name="csrf" value="<?=csrf_token()?>">
    <input type="hidden" name="action" value="upload">
    <input type="hidden" name="site" value="<?=h($siteKey)?>">
    <input type="hidden" name="d" value="<?=h($sub)?>">
    <label class="btn btn-primary btn-sm upload-label">
      ⬆ Ανέβασμα νέας εικόνας
      <input type="file" name="newfile" accept=".jpg,.jpeg,.png,.webp,.svg,.gif" onchange="this.form.submit()" hidden>
    </label>
  </form>

  <div class="grid-imgs">
    <?php foreach ($files as $f): $u = h($urlBase . '/' . $f); ?>
    <div class="img-card">
      <a href="<?=$u?>" target="_blank" class="img-thumb" style="background-image:url('<?=$u?>?t=<?=time()?>')"></a>
      <div class="img-meta">
        <span class="img-name" title="<?=h($f)?>"><?=h($f)?></span>
        <div class="img-actions">
          <a href="<?=$u?>" download class="icon-btn" title="Λήψη">⬇</a>
          <form method="post" enctype="multipart/form-data" class="inline-form">
            <input type="hidden" name="csrf" value="<?=csrf_token()?>">
            <input type="hidden" name="action" value="replace">
            <input type="hidden" name="site" value="<?=h($siteKey)?>">
            <input type="hidden" name="d" value="<?=h($sub)?>">
            <input type="hidden" name="target" value="<?=h($f)?>">
            <label class="icon-btn icon-swap" title="Αντικατάσταση">
              ⇄
              <input type="file" name="newfile" accept=".jpg,.jpeg,.png,.webp,.svg,.gif" onchange="if(confirm('Αντικατάσταση της «<?=h($f)?>»;')) this.form.submit(); else this.value='';" hidden>
            </label>
          </form>
        </div>
      </div>
    </div>
    <?php endforeach; ?>
  </div>
  <p class="note">💡 Η «Αντικατάσταση» αλλάζει την εικόνα παντού στο site αυτόματα. Κρατιέται πάντα backup.</p>
</main>
</body>
</html>
