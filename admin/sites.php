<?php
require __DIR__ . '/config.php';
require __DIR__ . '/sites_lib.php';
admin_session_start();
require_login();

$sites = discover_sites();
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Όλα τα Sites</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><a href="dashboard.php" class="back">←</a> <span>Όλα τα Sites</span></div>
</header>
<main class="wrap">
  <p class="note">Το panel βρίσκει <strong>αυτόματα</strong> κάθε site στον server. Όταν ανεβαίνει νέο site, εμφανίζεται εδώ από μόνο του — χωρίς καμία ρύθμιση.</p>
  <?php
  $byGroup = [];
  foreach ($sites as $key => $s) $byGroup[$s['group']][$key] = $s;
  foreach ($byGroup as $group => $items): ?>
  <h2 class="group-title"><?=h($group)?></h2>
  <div class="cards">
    <?php foreach ($items as $key => $s):
      $pages = site_pages($s['dir']);
      $imgs = site_image_dirs($s['dir']); ?>
    <div class="card">
      <span class="card-icon">🌐</span>
      <h2><?=h($s['label'])?></h2>
      <p><?=count($pages)?> σελίδες<?=$imgs ? ' · εικόνες ✓' : ''?></p>
      <div class="card-links">
        <?php foreach ($pages as $p): ?>
          <a class="chip-link" href="text_editor.php?site=<?=urlencode($key)?>&page=<?=urlencode($p)?>">✏️ <?=h($p === 'index.html' ? 'Αρχική' : ($p === 'menu.html' ? 'Μενού' : $p))?></a>
          <a class="chip-link" href="layout_editor.php?site=<?=urlencode($key)?>&page=<?=urlencode($p)?>">🧱 Διάταξη <?=h($p === 'index.html' ? '' : $p)?></a>
        <?php endforeach; ?>
        <?php if ($imgs): ?>
          <a class="chip-link" href="site_images.php?site=<?=urlencode($key)?>">🎨 Εικόνες</a>
        <?php endif; ?>
        <?php if ($s['url'] !== null): ?>
          <a class="chip-link" href="https://codehouse.gr<?=h($s['url'])?>/" target="_blank">👁 Προβολή</a>
        <?php endif; ?>
      </div>
    </div>
    <?php endforeach; ?>
  </div>
  <?php endforeach; ?>
  <p class="note">💡 Για το μενού του High Hope, χρησιμοποίησε τον ειδικό <a href="menu_editor.php">επεξεργαστή μενού</a> — είναι πιο βολικός για τιμές/προϊόντα.</p>
</main>
</body>
</html>
