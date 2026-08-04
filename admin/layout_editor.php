<?php
require __DIR__ . '/config.php';
require __DIR__ . '/sites_lib.php';
require __DIR__ . '/section_lib.php';
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
  $data = json_decode($_POST['layout_json'] ?? '', true);
  if (!is_array($data) || !isset($data['order'], $data['hidden'], $data['deleted'], $data['stateHash'])) {
    $err = 'Δεν ελήφθησαν δεδομένα.';
  } else {
    $html = file_get_contents($file);
    $blocks = sections_parse($html);
    $stateHash = md5(json_encode(array_map(fn($b)=>$b['hash'], $blocks)));
    if ($stateHash !== $data['stateHash']) {
      $err = 'Η σελίδα άλλαξε στο μεταξύ. Κάνε ανανέωση και ξαναδοκίμασε.';
    } elseif (count($data['deleted']) >= count($blocks)) {
      $err = 'Δεν γίνεται να διαγραφούν όλες οι ενότητες.';
    } else {
      make_backup($file);
      $new = sections_rebuild($html, $blocks, $data['order'], $data['hidden'], $data['deleted']);
      if (strlen($new) < strlen($html) * 0.2) {
        $err = 'Κάτι πήγε στραβά — ΔΕΝ αποθηκεύτηκε.';
      } else {
        file_put_contents($file, $new, LOCK_EX);
        $acts = [];
        if ($data['deleted']) $acts[] = count($data['deleted']) . ' διαγραφές';
        if ($data['hidden']) $acts[] = count($data['hidden']) . ' κρυμμένες';
        $msg = '✅ Αποθηκεύτηκε! ' . implode(', ', $acts);
      }
    }
  }
}

$html = file_get_contents($file);
$blocks = sections_parse($html);
$stateHash = md5(json_encode(array_map(fn($b)=>$b['hash'], $blocks)));
$clientBlocks = array_map(fn($b) => [
  'key' => $b['key'], 'tag' => $b['tag'], 'id' => $b['id'],
  'title' => $b['title'], 'hidden' => $b['hidden'], 'imgs' => $b['imgs'],
], $blocks);
$viewUrl = 'https://codehouse.gr' . ($S['url'] ?? '') . '/' . ($page === 'index.html' ? '' : $page);
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Διάταξη — <?=h($S['label'])?></title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="sites.php" class="back">←</a> <span>Διάταξη · <?=h($S['label'])?></span></div>
  <button form="layoutForm" type="submit" class="btn btn-primary btn-sm">💾 Αποθήκευση</button>
</header>
<main class="wrap wrap-narrow">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?> <a href="<?=h($viewUrl)?>" target="_blank">Δες το ↗</a></div><?php endif; ?>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>
  <p class="note">Οι <strong><?=count($blocks)?></strong> ενότητες της σελίδας, με τη σειρά που εμφανίζονται. Μπορείς να τις <strong>μετακινήσεις</strong> (↑↓), να τις <strong>κρύψεις</strong> (👁 — επανέρχονται όποτε θες) ή να τις <strong>διαγράψεις</strong> (🗑 οριστικά, με backup).</p>
  <form method="post" id="layoutForm">
    <input type="hidden" name="csrf" value="<?=csrf_token()?>">
    <input type="hidden" name="site" value="<?=h($siteKey)?>">
    <input type="hidden" name="page" value="<?=h($page)?>">
    <input type="hidden" name="layout_json" id="layoutJson">
  </form>
  <div id="app"></div>
  <div class="savebar"><button form="layoutForm" type="submit" class="btn btn-primary btn-block">💾 Αποθήκευση διάταξης</button></div>
</main>
<script>
const BLOCKS = <?=json_encode($clientBlocks, JSON_UNESCAPED_UNICODE)?>;
const STATE_HASH = <?=json_encode($stateHash)?>;
</script>
<script src="layout_editor.js"></script>
</body>
</html>
