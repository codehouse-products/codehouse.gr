<?php
// ===== High Hope QR menu — parse & rebuild =====
// Δομή HTML:
// <section class="qr-section" id="qr-slug"><h2 class="qr-section-title">Τίτλος</h2>
//   <div class="qr-item"><div class="qr-item-info"><span class="qr-item-name">Όνομα</span>[<span class="qr-badge">Badge</span>][<p class="qr-item-desc">Περιγραφή</p>]</div><span class="qr-dots"></span><span class="qr-price">Τιμή</span></div>
// </section>

function menu_parse($html) {
  $sections = [];
  if (!preg_match_all('#<section class="qr-section" id="([^"]+)">\s*<h2 class="qr-section-title">(.*?)</h2>(.*?)</section>#s', $html, $sm, PREG_SET_ORDER)) {
    return $sections;
  }
  foreach ($sm as $s) {
    $items = [];
    if (preg_match_all('#<div class="qr-item"><div class="qr-item-info"><span class="qr-item-name">(.*?)</span>(?:<span class="qr-badge">(.*?)</span>)?(?:<p class="qr-item-desc">(.*?)</p>)?</div><span class="qr-dots"></span><span class="qr-price">(.*?)</span></div>#s', $s[3], $im, PREG_SET_ORDER)) {
      foreach ($im as $i) {
        $items[] = [
          'name'  => html_entity_decode($i[1], ENT_QUOTES|ENT_HTML5, 'UTF-8'),
          'badge' => html_entity_decode($i[2] ?? '', ENT_QUOTES|ENT_HTML5, 'UTF-8'),
          'desc'  => html_entity_decode($i[3] ?? '', ENT_QUOTES|ENT_HTML5, 'UTF-8'),
          'price' => html_entity_decode($i[4], ENT_QUOTES|ENT_HTML5, 'UTF-8'),
        ];
      }
    }
    $sections[] = [
      'id'    => $s[1],
      'title' => html_entity_decode($s[2], ENT_QUOTES|ENT_HTML5, 'UTF-8'),
      'items' => $items,
    ];
  }
  return $sections;
}

function e_html($s) { return htmlspecialchars($s, ENT_QUOTES|ENT_HTML5, 'UTF-8'); }

function menu_item_html($it) {
  $h = '    <div class="qr-item"><div class="qr-item-info"><span class="qr-item-name">' . e_html($it['name']) . '</span>';
  if ($it['badge'] !== '') $h .= '<span class="qr-badge">' . e_html($it['badge']) . '</span>';
  if ($it['desc'] !== '')  $h .= '<p class="qr-item-desc">' . e_html($it['desc']) . '</p>';
  $h .= '</div><span class="qr-dots"></span><span class="qr-price">' . e_html($it['price']) . '</span></div>';
  return $h;
}

function menu_section_html($sec) {
  $h = '  <section class="qr-section" id="' . e_html($sec['id']) . '"><h2 class="qr-section-title">' . e_html($sec['title']) . "</h2>\n";
  foreach ($sec['items'] as $it) $h .= menu_item_html($it) . "\n";
  $h .= '  </section>';
  return $h;
}

// Αντικαθιστά ΟΛΑ τα sections μέσα στο <main>…</main> και ξαναχτίζει το qr-nav
function menu_rebuild($html, $sections) {
  // sections block
  $newSections = implode("\n", array_map('menu_section_html', $sections));
  $html = preg_replace('#(<main>).*?(</main>)#s', "$1\n" . $newSections . "\n$2", $html, 1);
  // nav chips
  $nav = '';
  foreach ($sections as $sec) $nav .= '  <a href="#' . e_html($sec['id']) . '">' . e_html($sec['title']) . "</a>\n";
  $html = preg_replace('#(<nav class="qr-nav"[^>]*>).*?(</nav>)#s', "$1\n" . $nav . "$2", $html, 1);
  return $html;
}

function slugify($t) {
  $g = ['α'=>'a','β'=>'b','γ'=>'g','δ'=>'d','ε'=>'e','ζ'=>'z','η'=>'i','θ'=>'th','ι'=>'i','κ'=>'k','λ'=>'l','μ'=>'m','ν'=>'n','ξ'=>'x','ο'=>'o','π'=>'p','ρ'=>'r','σ'=>'s','ς'=>'s','τ'=>'t','υ'=>'y','φ'=>'f','χ'=>'ch','ψ'=>'ps','ω'=>'o','ά'=>'a','έ'=>'e','ή'=>'i','ί'=>'i','ό'=>'o','ύ'=>'y','ώ'=>'o','ϊ'=>'i','ϋ'=>'y'];
  $t = strtr(mb_strtolower($t, 'UTF-8'), $g);
  $t = preg_replace('/[^a-z0-9]+/', '-', $t);
  return 'qr-' . trim($t, '-');
}
