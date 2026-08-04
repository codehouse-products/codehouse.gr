<?php
require __DIR__ . '/config.php';
admin_session_start();

if (is_logged_in()) { header('Location: dashboard.php'); exit; }

$err = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $ip = $_SERVER['REMOTE_ADDR'] ?? '0';
  if (too_many_attempts($ip)) {
    $err = 'Πολλές αποτυχημένες προσπάθειες. Δοκίμασε ξανά σε 15 λεπτά.';
  } elseif (password_verify($_POST['password'] ?? '', ADMIN_PASSWORD_HASH)) {
    session_regenerate_id(true);
    $_SESSION['ok'] = true;
    header('Location: dashboard.php'); exit;
  } else {
    record_attempt($ip);
    $err = 'Λάθος κωδικός.';
  }
}
?><!DOCTYPE html>
<html lang="el">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Codehouse Admin — Σύνδεση</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="admin.css">
</head>
<body class="login-body">
<div class="login-card">
  <img src="../assets/img/logo-ch-mark.png" alt="" class="login-logo">
  <h1>Πίνακας Διαχείρισης</h1>
  <p class="login-sub">codehouse.gr</p>
  <?php if ($err): ?><div class="alert alert-err"><?=h($err)?></div><?php endif; ?>
  <form method="post" autocomplete="off">
    <label for="password">Κωδικός</label>
    <input type="password" id="password" name="password" required autofocus>
    <button type="submit" class="btn btn-primary btn-block">Σύνδεση →</button>
  </form>
</div>
</body>
</html>
