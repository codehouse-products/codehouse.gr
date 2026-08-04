<?php
require __DIR__ . '/config.php';
require __DIR__ . '/menu_lib.php';
admin_session_start();
require_login();

$file = $SITES['highhope-menu']['file'];
$msg = ''; $err = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  check_csrf();
  $data = json_decode($_POST['menu_json'] ?? '', true);
  if (!is_array($data) || !$data) {
    $err = 'Δεν ελήφθησαν έγκυρα δεδομένα. Δοκίμασε ξανά.';
  } else {
    // sanitize + rebuild
    $sections = [];
    foreach ($data as $sec) {
      $title = trim($sec['title'] ?? '');
      if ($title === '') continue;
      $items = [];
      foreach (($sec['items'] ?? []) as $it) {
        $name = trim($it['name'] ?? '');
        if ($name === '') continue;
        $items[] = [
          'name'  => $name,
          'badge' => trim($it['badge'] ?? ''),
          'desc'  => trim($it['desc'] ?? ''),
          'price' => trim($it['price'] ?? ''),
        ];
      }
      $sections[] = ['id' => ($sec['id'] ?? '') ?: slugify($title), 'title' => $title, 'items' => $items];
    }
    if (!$sections) {
      $err = 'Το μενού δεν μπορεί να μείνει άδειο.';
    } else {
      $html = file_get_contents($file);
      make_backup($file);
      $new = menu_rebuild($html, $sections);
      if (strlen($new) < 5000) { $err = 'Κάτι πήγε στραβά (πολύ μικρό αποτέλεσμα) — ΔΕΝ αποθηκεύτηκε.'; }
      else { file_put_contents($file, $new, LOCK_EX); $msg = '✅ Αποθηκεύτηκε! Οι αλλαγές είναι live στο μενού.'; }
    }
  }
}

$sections = menu_parse(file_get_contents($file));
$total = array_sum(array_map(fn($s)=>count($s['items']), $sections));
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>High Hope — Μενού</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="dashboard.php" class="back">←</a> <span>High Hope — Μενού</span></div>
  <button form="menuForm" type="submit" class="btn btn-primary btn-sm">💾 Αποθήκευση</button>
</header>
<main class="wrap wrap-narrow">
  <?php if ($msg): ?><div class="alert alert-ok"><?=h($msg)?> <a href="https://codehouse.gr/clients/highhope/menu.html" target="_blank">Δες το μενού ↗</a></div><?php endif; ?>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>
  <p class="note">Σύνολο: <strong id="totalCount"><?=$total?></strong> προϊόντα σε <?=count($sections)?> κατηγορίες. Πάτα σε ένα προϊόν για επεξεργασία. Μην ξεχάσεις την <strong>Αποθήκευση</strong> πάνω δεξιά!</p>
  <input type="search" id="filter" class="filter" placeholder="🔍 Αναζήτηση προϊόντος…">
  <form method="post" id="menuForm">
    <input type="hidden" name="csrf" value="<?=csrf_token()?>">
    <input type="hidden" name="menu_json" id="menuJson">
  </form>
  <div id="app"></div>
  <button type="button" class="btn btn-ghost btn-block" id="addSection">+ Νέα κατηγορία</button>
  <div class="savebar"><button form="menuForm" type="submit" class="btn btn-primary btn-block">💾 Αποθήκευση αλλαγών</button></div>
</main>
<script>
const DATA = <?=json_encode($sections, JSON_UNESCAPED_UNICODE)?>;
</script>
<script src="menu_editor.js"></script>
</body>
</html>
