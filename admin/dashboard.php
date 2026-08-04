<?php
require __DIR__ . '/config.php';
admin_session_start();
require_login();

if (isset($_GET['logout'])) { session_destroy(); header('Location: index.php'); exit; }

$backups = glob(BACKUP_DIR . '/*.bak') ?: [];
usort($backups, fn($a,$b)=>filemtime($b)-filemtime($a));
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Codehouse Admin</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-brand"><img src="../assets/img/logo-ch-mark.png" alt=""> <span>Πίνακας Διαχείρισης</span></div>
  <a href="?logout=1" class="btn btn-ghost btn-sm">Αποσύνδεση</a>
</header>
<main class="wrap">
  <h1>Τι θες να αλλάξεις;</h1>
  <div class="cards">
    <a class="card card-featured" href="sites.php">
      <span class="card-icon">🌐</span>
      <h2>Όλα τα Sites</h2>
      <p>Αυτόματη λίστα όλων των sites — επεξεργασία κειμένων & εικόνων σε καθένα. Νέα sites εμφανίζονται εδώ αυτόματα.</p>
      <span class="card-cta">Άνοιγμα →</span>
    </a>
    <a class="card" href="menu_editor.php">
      <span class="card-icon">☕</span>
      <h2>High Hope — Μενού</h2>
      <p>Τιμές, ονόματα, περιγραφές, badges. Προσθήκη & διαγραφή προϊόντων και κατηγοριών.</p>
      <span class="card-cta">Άνοιγμα →</span>
    </a>
    <a class="card" href="info_editor.php">
      <span class="card-icon">🕐</span>
      <h2>High Hope — Στοιχεία</h2>
      <p>Ωράριο, διεύθυνση, WiFi κωδικός, τηλέφωνο παραγγελιών.</p>
      <span class="card-cta">Άνοιγμα →</span>
    </a>
    <a class="card" href="contact_editor.php">
      <span class="card-icon">📞</span>
      <h2>Codehouse — Επικοινωνία</h2>
      <p>Τηλέφωνο και email που εμφανίζονται στο codehouse.gr.</p>
      <span class="card-cta">Άνοιγμα →</span>
    </a>
    <a class="card" href="images.php">
      <span class="card-icon">🎨</span>
      <h2>Εικόνες & Γραφιστικά</h2>
      <p>Ανέβασμα και αντικατάσταση φωτογραφιών, λογότυπα για λήψη (PNG), εικόνες μενού.</p>
      <span class="card-cta">Άνοιγμα →</span>
    </a>
    <a class="card" href="backups.php">
      <span class="card-icon">🛟</span>
      <h2>Backups</h2>
      <p>Κάθε αλλαγή κρατά αντίγραφο. Επαναφορά με ένα κλικ. (<?=count($backups)?> διαθέσιμα)</p>
      <span class="card-cta">Άνοιγμα →</span>
    </a>
  </div>
  <p class="note">💡 Κάθε αποθήκευση κρατάει αυτόματα backup. Αν κάτι πάει στραβά, πήγαινε στα Backups και πάτα «Επαναφορά».</p>
</main>
</body>
</html>
