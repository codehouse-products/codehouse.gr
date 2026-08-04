<?php
require __DIR__ . '/config.php';
require __DIR__ . '/sites_lib.php';
admin_session_start();
require_login();

$sites = discover_sites();
$siteKey = $_GET['site'] ?? ($_POST['site'] ?? '');
if (!isset($sites[$siteKey])) { header('Location: sites.php'); exit; }
$S = $sites[$siteKey];

$page = basename($_GET['page'] ?? ($_POST['page'] ?? 'index.html'));
if (!in_array($page, site_pages($S['dir']))) { header('Location: sites.php'); exit; }
$file = $S['dir'] . '/' . $page;

$msg = ''; $err = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  check_csrf();
  $changes = json_decode($_POST['changes_json'] ?? '', true);
  if (!is_array($changes)) {
    $err = 'Δεν ελήφθησαν δεδομένα.';
  } elseif (!$changes) {
    $msg = 'Καμία αλλαγή για αποθήκευση.';
  } else {
    $html = file_get_contents($file);
    // επαλήθευση: κάθε αλλαγή πρέπει να ταιριάζει με το τρέχον αρχείο (offset + αρχικό encoded κείμενο)
    $valid = [];
    foreach ($changes as $c) {
      if (!isset($c['offset'], $c['len'], $c['text'], $c['orig'])) continue;
      $current = html_entity_decode(substr($html, (int)$c['offset'], (int)$c['len']), ENT_QUOTES|ENT_HTML5, 'UTF-8');
      if ($current === $c['orig']) {
        $valid[] = ['offset'=>(int)$c['offset'], 'len'=>(int)$c['len'], 'text'=>(string)$c['text']];
      }
    }
    if (count($valid) !== count($changes)) {
      $err = 'Το αρχείο άλλαξε στο μεταξύ (ή έγινε refresh). Φόρτωσε ξανά τη σελίδα και ξαναδοκίμασε.';
    } else {
      make_backup($file);
      $new = text_apply($html, $valid);
      file_put_contents($file, $new, LOCK_EX);
      $msg = '✅ Αποθηκεύτηκαν ' . count($valid) . ' αλλαγές!';
    }
  }
}

$html = file_get_contents($file);
$fields = text_extract($html);
$viewUrl = 'https://codehouse.gr' . ($S['url'] ?? '') . '/' . ($page === 'index.html' ? '' : $page);
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Κείμενα — <?=h($S['label'])?></title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="sites.php" class="back">←</a> <span><?=h($S['label'])?> · <?=h($page)?></span></div>
  <button form="txtForm" type="submit" class="btn btn-primary btn-sm">💾 Αποθήκευση</button>
</header>
<main class="wrap wrap-narrow">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?> <a href="<?=h($viewUrl)?>" target="_blank">Δες το ↗</a></div><?php endif; ?>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>
  <p class="note">Βρέθηκαν <strong><?=count($fields)?></strong> επεξεργάσιμα κείμενα. Άλλαξε όσα θες και πάτα <strong>Αποθήκευση</strong>. Ό,τι αλλάξεις μαρκάρεται με πράσινο.</p>
  <input type="search" id="filter" class="filter" placeholder="🔍 Αναζήτηση κειμένου…">
  <form method="post" id="txtForm">
    <input type="hidden" name="csrf" value="<?=csrf_token()?>">
    <input type="hidden" name="site" value="<?=h($siteKey)?>">
    <input type="hidden" name="page" value="<?=h($page)?>">
    <input type="hidden" name="changes_json" id="changesJson">
  </form>
  <div id="app"></div>
  <div class="savebar"><button form="txtForm" type="submit" class="btn btn-primary btn-block">💾 Αποθήκευση αλλαγών (<span id="chCount">0</span>)</button></div>
</main>
<script>
const FIELDS = <?=json_encode($fields, JSON_UNESCAPED_UNICODE)?>;
</script>
<script src="text_editor.js"></script>
</body>
</html>
