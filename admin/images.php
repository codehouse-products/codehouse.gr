<?php
require __DIR__ . '/config.php';
admin_session_start();
require_login();

// Φάκελοι εικόνων ανά site (whitelist — μόνο αυτοί επιτρέπονται)
$GALLERIES = [
  'highhope-img'  => ['label' => 'High Hope — Φωτογραφίες site', 'dir' => SITE_ROOT . '/clients/highhope/assets/img',  'url' => '/clients/highhope/assets/img'],
  'highhope-menu' => ['label' => 'High Hope — Φωτογραφίες μενού', 'dir' => SITE_ROOT . '/clients/highhope/assets/menu', 'url' => '/clients/highhope/assets/menu'],
  'codehouse-img' => ['label' => 'Codehouse — Εικόνες & Λογότυπα', 'dir' => SITE_ROOT . '/assets/img', 'url' => '/assets/img'],
];

$ALLOWED_EXT = ['jpg','jpeg','png','webp','svg','gif','ico'];
$MAX_SIZE = 8 * 1024 * 1024; // 8MB

$gal = $_GET['g'] ?? 'highhope-img';
if (!isset($GALLERIES[$gal])) $gal = 'highhope-img';
$G = $GALLERIES[$gal];

$msg = ''; $err = '';

function safe_name($name) {
  $name = basename($name);
  $name = preg_replace('/[^a-zA-Z0-9._-]/', '-', $name);
  return $name;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  check_csrf();
  $action = $_POST['action'] ?? '';

  if ($action === 'replace' && isset($_FILES['newfile'])) {
    $target = safe_name($_POST['target'] ?? '');
    $path = $G['dir'] . '/' . $target;
    $f = $_FILES['newfile'];
    $ext = strtolower(pathinfo($f['name'], PATHINFO_EXTENSION));
    $targetExt = strtolower(pathinfo($target, PATHINFO_EXTENSION));
    if (!file_exists($path)) { $err = 'Το αρχείο δεν βρέθηκε.'; }
    elseif ($f['error'] !== UPLOAD_ERR_OK) { $err = 'Σφάλμα στο ανέβασμα.'; }
    elseif ($f['size'] > $MAX_SIZE) { $err = 'Πολύ μεγάλο αρχείο (max 8MB).'; }
    elseif (!in_array($ext, $ALLOWED_EXT)) { $err = 'Μη επιτρεπτός τύπος αρχείου.'; }
    elseif ($ext !== $targetExt && !($ext==='jpeg' && $targetExt==='jpg') && !($ext==='jpg' && $targetExt==='jpeg')) {
      $err = "Το νέο αρχείο πρέπει να είναι ίδιου τύπου (.$targetExt) για να μη χαλάσει το site.";
    } else {
      make_backup($path);
      move_uploaded_file($f['tmp_name'], $path);
      chmod($path, 0644);
      $msg = "✅ Η εικόνα «{$target}» αντικαταστάθηκε! (Ίσως χρειαστεί refresh στο site για να τη δεις)";
    }
  }

  if ($action === 'upload' && isset($_FILES['newfile'])) {
    $f = $_FILES['newfile'];
    $name = safe_name($f['name']);
    $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
    if ($f['error'] !== UPLOAD_ERR_OK) { $err = 'Σφάλμα στο ανέβασμα.'; }
    elseif ($f['size'] > $MAX_SIZE) { $err = 'Πολύ μεγάλο αρχείο (max 8MB).'; }
    elseif (!in_array($ext, $ALLOWED_EXT)) { $err = 'Μη επιτρεπτός τύπος. Επιτρέπονται: ' . implode(', ', $ALLOWED_EXT); }
    else {
      if (file_exists($G['dir'] . '/' . $name)) $name = pathinfo($name, PATHINFO_FILENAME) . '-' . date('His') . '.' . $ext;
      move_uploaded_file($f['tmp_name'], $G['dir'] . '/' . $name);
      chmod($G['dir'] . '/' . $name, 0644);
      $msg = "✅ Ανέβηκε ως «{$name}». Για να εμφανιστεί στο site, πες μου να τη συνδέσω ή αντικατέστησε μια υπάρχουσα.";
    }
  }
}

$files = [];
foreach (glob($G['dir'] . '/*') as $f) {
  $ext = strtolower(pathinfo($f, PATHINFO_EXTENSION));
  if (in_array($ext, $ALLOWED_EXT)) $files[] = basename($f);
}
sort($files);
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Εικόνες & Γραφιστικά</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="dashboard.php" class="back">←</a> <span>Εικόνες & Γραφιστικά</span></div>
</header>
<main class="wrap">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?></div><?php endif; ?>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>

  <div class="tabs">
    <?php foreach ($GALLERIES as $key => $g): ?>
      <a href="?g=<?=h($key)?>" class="tab <?=$key===$gal?'active':''?>"><?=h($g['label'])?></a>
    <?php endforeach; ?>
  </div>

  <form method="post" enctype="multipart/form-data" class="upload-bar">
    <input type="hidden" name="csrf" value="<?=csrf_token()?>">
    <input type="hidden" name="action" value="upload">
    <label class="btn btn-primary btn-sm upload-label">
      ⬆ Ανέβασμα νέας εικόνας
      <input type="file" name="newfile" accept=".jpg,.jpeg,.png,.webp,.svg,.gif" onchange="this.form.submit()" hidden>
    </label>
    <span class="note-inline">ή πάτα «Αντικατάσταση» σε υπάρχουσα εικόνα για να τη αλλάξεις στο site</span>
  </form>

  <div class="grid-imgs">
    <?php foreach ($files as $f): $u = h($G['url'] . '/' . $f); ?>
    <div class="img-card">
      <a href="<?=$u?>" target="_blank" class="img-thumb" style="background-image:url('<?=$u?>?t=<?=time()?>')"></a>
      <div class="img-meta">
        <span class="img-name" title="<?=h($f)?>"><?=h($f)?></span>
        <div class="img-actions">
          <a href="<?=$u?>" download class="icon-btn" title="Λήψη">⬇</a>
          <form method="post" enctype="multipart/form-data" class="inline-form">
            <input type="hidden" name="csrf" value="<?=csrf_token()?>">
            <input type="hidden" name="action" value="replace">
            <input type="hidden" name="target" value="<?=h($f)?>">
            <label class="icon-btn icon-swap" title="Αντικατάσταση">
              ⇄
              <input type="file" name="newfile" accept=".jpg,.jpeg,.png,.webp,.svg,.gif" onchange="if(confirm('Αντικατάσταση της «<?=h($f)?>» με τη νέα εικόνα;')) this.form.submit(); else this.value='';" hidden>
            </label>
          </form>
        </div>
      </div>
    </div>
    <?php endforeach; ?>
  </div>
  <p class="note">💡 Η «Αντικατάσταση» αλλάζει την εικόνα <strong>παντού στο site αυτόματα</strong> (ίδιο όνομα αρχείου). Κρατιέται πάντα backup της παλιάς.</p>
</main>
</body>
</html>
