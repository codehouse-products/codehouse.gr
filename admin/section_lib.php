<?php
// ===== Section editor: εντοπισμός & διαχείριση ενοτήτων σελίδας =====
// Εντοπίζει top-level δομικά μπλοκ (<section>, <header>, <footer> κ.λπ.)
// και εικόνες (<img>). Υποστηρίζει: hide/show (μέσω style), move up/down, delete.

const BLOCK_TAGS = ['section', 'header', 'footer', 'nav', 'aside', 'article'];
const HIDE_MARK = 'data-ch-hidden="1"';

// Βρίσκει top-level μπλοκ μέσα στο <body>, με σωστό ζευγάρωμα nested tags
function sections_parse($html) {
  $blocks = [];
  $bodyStart = stripos($html, '<body');
  if ($bodyStart === false) return $blocks;
  $bodyOpenEnd = strpos($html, '>', $bodyStart) + 1;
  $bodyClose = strripos($html, '</body>');
  if ($bodyClose === false) $bodyClose = strlen($html);

  $tagPattern = implode('|', BLOCK_TAGS);
  $offset = $bodyOpenEnd;
  $idx = 0;
  while (preg_match('#<(' . $tagPattern . ')(\s[^>]*)?>#i', $html, $m, PREG_OFFSET_CAPTURE, $offset)) {
    $tag = strtolower($m[1][0]);
    $start = $m[0][1];
    if ($start >= $bodyClose) break;
    // βρες το matching κλείσιμο (nested aware)
    $depth = 0;
    $pos = $start;
    $end = false;
    while (preg_match('#<(/?)(' . preg_quote($tag, '#') . ')(\s[^>]*)?>#i', $html, $mm, PREG_OFFSET_CAPTURE, $pos)) {
      if ($mm[1][0] === '/') { $depth--; } else { $depth++; }
      $pos = $mm[0][1] + strlen($mm[0][0]);
      if ($depth === 0) { $end = $pos; break; }
    }
    if ($end === false) { $offset = $start + 1; continue; }

    $content = substr($html, $start, $end - $start);
    $attrs = $m[2][0] ?? '';

    // Μόνο top-level: παράλειψη αν είναι μέσα σε προηγούμενο μπλοκ
    $isNested = false;
    foreach ($blocks as $b) {
      if ($start > $b['start'] && $start < $b['end']) { $isNested = true; break; }
    }
    if (!$isNested) {
      $blocks[] = [
        'key'    => $idx++,
        'tag'    => $tag,
        'id'     => preg_match('/id="([^"]+)"/', $attrs, $im) ? $im[1] : '',
        'class'  => preg_match('/class="([^"]+)"/', $attrs, $cm) ? $cm[1] : '',
        'title'  => section_title($content, $tag),
        'hidden' => strpos($content, HIDE_MARK) !== false || (preg_match('#^<' . $tag . '[^>]*style="[^"]*display:\s*none#i', $content) === 1),
        'imgs'   => section_imgs($content),
        'start'  => $start,
        'end'    => $end,
        'hash'   => md5($content),
      ];
    }
    $offset = $end;
  }
  return $blocks;
}

// Εξάγει φιλικό τίτλο μπλοκ (πρώτο heading ή aria-label ή id)
function section_title($content, $tag) {
  if (preg_match('#<h[1-4][^>]*>(.*?)</h[1-4]>#s', $content, $m)) {
    $t = trim(strip_tags($m[1]));
    if ($t !== '') return mb_substr(html_entity_decode($t, ENT_QUOTES|ENT_HTML5, 'UTF-8'), 0, 60);
  }
  if (preg_match('/aria-label="([^"]+)"/', $content, $m)) return $m[1];
  $names = ['header'=>'Κεφαλίδα (μενού πλοήγησης)', 'footer'=>'Υποσέλιδο', 'nav'=>'Μενού πλοήγησης'];
  return $names[$tag] ?? ucfirst($tag);
}

// Βρίσκει εικόνες μέσα σε μπλοκ
function section_imgs($content) {
  $imgs = [];
  if (preg_match_all('#<img[^>]*src="([^"]+)"[^>]*>#i', $content, $m)) {
    foreach ($m[1] as $src) $imgs[] = basename($src);
  }
  return array_slice(array_unique($imgs), 0, 6);
}

// Εφαρμόζει πράξεις: order = λίστα από keys με νέα σειρά, hidden = keys που κρύβονται, deleted = keys που σβήνονται
function sections_rebuild($html, $blocks, $order, $hidden, $deleted) {
  if (!$blocks) return $html;
  // περιοχή που καλύπτουν τα top-level μπλοκ: από start του πρώτου έως end του τελευταίου
  $first = $blocks[0]; $last = $blocks[count($blocks)-1];
  foreach ($blocks as $b) { if ($b['start'] < $first['start']) $first = $b; if ($b['end'] > $last['end']) $last = $b; }

  // κείμενο ΜΕΤΑΞΥ των μπλοκ (πρέπει να διατηρηθεί — scripts, σχόλια κ.λπ.)
  $byStart = $blocks;
  usort($byStart, fn($a,$b)=>$a['start']-$b['start']);
  $glue = [];
  for ($i = 0; $i < count($byStart) - 1; $i++) {
    $glue[] = substr($html, $byStart[$i]['end'], $byStart[$i+1]['start'] - $byStart[$i]['end']);
  }

  // χτίσε νέο μπλοκ-κείμενο με τη νέα σειρά
  $byKey = [];
  foreach ($blocks as $b) $byKey[$b['key']] = $b;
  $parts = [];
  foreach ($order as $key) {
    if (in_array($key, $deleted)) continue;
    if (!isset($byKey[$key])) continue;
    $b = $byKey[$key];
    $content = substr($html, $b['start'], $b['end'] - $b['start']);
    $isHidden = in_array($key, $hidden);
    // καθάρισε προηγούμενο hide state
    $content = preg_replace('#^(<' . $b['tag'] . ')([^>]*?)\s*' . preg_quote(HIDE_MARK, '#') . '\s*style="display:none!important;"#i', '$1$2', $content, 1);
    if ($isHidden) {
      $content = preg_replace('#^(<' . $b['tag'] . ')#i', '$1 ' . HIDE_MARK . ' style="display:none!important;"', $content, 1);
    }
    $parts[] = $content;
  }

  $newBlockArea = implode("\n", $parts);
  // αντικατέστησε την παλιά περιοχή με τη νέα (glue μπαίνει στο τέλος για να μη χαθούν scripts)
  $glueText = trim(implode('', array_map('trim', $glue)));
  if ($glueText !== '') $newBlockArea .= "\n" . $glueText;

  return substr($html, 0, $first['start']) . $newBlockArea . substr($html, $last['end']);
}
