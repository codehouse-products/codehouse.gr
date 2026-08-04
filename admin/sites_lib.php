<?php
// ===== Αυτόματη ανίχνευση sites + γενικός text editor =====

// Σκανάρει τον server και βρίσκει όλα τα sites (τρέχοντα ΚΑΙ μελλοντικά).
// Ένα "site" = φάκελος που περιέχει index.html ή menu.html.
function discover_sites() {
  $sites = [];
  // 1. Το κεντρικό codehouse.gr
  if (file_exists(SITE_ROOT . '/index.html')) {
    $sites['_root'] = ['label' => 'Codehouse.gr (κεντρικό)', 'dir' => SITE_ROOT, 'url' => '', 'group' => 'Κεντρικό'];
  }
  // 2. Sites σε clients/, preview/, demo/
  $groups = ['clients' => 'Πελάτες (live)', 'preview' => 'Preview', 'demo' => 'Demo'];
  foreach ($groups as $folder => $glabel) {
    $base = SITE_ROOT . '/' . $folder;
    if (!is_dir($base)) continue;
    foreach (scandir($base) as $d) {
      if ($d[0] === '.' || !is_dir("$base/$d")) continue;
      $htmls = glob("$base/$d/*.html");
      if (!$htmls) continue;
      $sites["$folder/$d"] = [
        'label' => ucfirst($d) . " ($glabel)",
        'dir'   => "$base/$d",
        'url'   => "/$folder/$d",
        'group' => $glabel,
      ];
    }
  }
  return $sites;
}

// Βρίσκει τα .html αρχεία ενός site
function site_pages($dir) {
  $pages = [];
  foreach (glob($dir . '/*.html') as $f) $pages[] = basename($f);
  sort($pages);
  // index πρώτο
  usort($pages, fn($a,$b) => ($a==='index.html'?-1:($b==='index.html'?1:strcmp($a,$b))));
  return $pages;
}

// Βρίσκει φακέλους εικόνων ενός site
function site_image_dirs($dir) {
  $found = [];
  foreach (['assets/img', 'assets/menu', 'assets/images', 'img', 'images'] as $sub) {
    if (is_dir("$dir/$sub")) $found[] = $sub;
  }
  return $found;
}

// ===== Γενικός text editor: εξαγωγή επεξεργάσιμων κειμένων από HTML =====
// Βρίσκει κείμενα σε συγκεκριμένα tags, με μοναδικό δείκτη θέσης ώστε
// να μπορεί να τα ξαναγράψει με ακρίβεια χωρίς να πειράξει τη δομή.

const EDITABLE_TAGS = ['h1','h2','h3','h4','p','span','a','li','button','strong','em','td','th','figcaption','blockquote','title','label','summary'];

function text_extract($html) {
  $fields = [];
  $tagPattern = implode('|', EDITABLE_TAGS);
  // Ταιριάζει tags που περιέχουν ΜΟΝΟ απλό κείμενο (όχι εμφωλευμένα tags)
  if (preg_match_all('#<(' . $tagPattern . ')((?:\s[^>]*)?)>([^<>]+)</\1>#u', $html, $m, PREG_OFFSET_CAPTURE | PREG_SET_ORDER)) {
    foreach ($m as $i => $match) {
      $text = html_entity_decode($match[3][0], ENT_QUOTES|ENT_HTML5, 'UTF-8');
      $trimmed = trim($text);
      if ($trimmed === '' || mb_strlen($trimmed) < 2) continue;
      // παράλειψη καθαρά τεχνικών κειμένων
      if (preg_match('/^[\s\d\W]*$/u', $trimmed) && mb_strlen($trimmed) < 4) continue;
      $fields[] = [
        'key'    => $i,
        'tag'    => $match[1][0],
        'text'   => $text,
        'offset' => $match[3][1],       // θέση του κειμένου στο αρχείο
        'len'    => strlen($match[3][0]), // μήκος σε bytes του encoded κειμένου
      ];
    }
  }
  return $fields;
}

// Εφαρμόζει αλλαγές: [{offset, len, text}, ...] — από το τέλος προς την αρχή
function text_apply($html, $changes) {
  usort($changes, fn($a,$b) => $b['offset'] - $a['offset']);
  foreach ($changes as $c) {
    $new = htmlspecialchars($c['text'], ENT_QUOTES|ENT_HTML5, 'UTF-8');
    // επιτρέπουμε τα ήδη-encoded & σύμβολα να μην διπλο-κωδικοποιούνται άσχημα
    $html = substr($html, 0, $c['offset']) . $new . substr($html, $c['offset'] + $c['len']);
  }
  return $html;
}

// Ομαδοποίηση πεδίων για φιλική εμφάνιση
function tag_label($tag) {
  return match($tag) {
    'h1' => 'Τίτλος (μεγάλος)', 'h2' => 'Τίτλος', 'h3' => 'Υπότιτλος', 'h4' => 'Υπότιτλος',
    'p' => 'Παράγραφος', 'span' => 'Κείμενο', 'a' => 'Σύνδεσμος', 'li' => 'Στοιχείο λίστας',
    'button' => 'Κουμπί', 'strong' => 'Έντονο', 'em' => 'Πλάγιο', 'td' => 'Κελί', 'th' => 'Κεφαλίδα',
    'figcaption' => 'Λεζάντα', 'blockquote' => 'Παράθεση', 'title' => 'Τίτλος σελίδας (tab)',
    'label' => 'Ετικέτα', 'summary' => 'Σύνοψη', default => $tag,
  };
}
