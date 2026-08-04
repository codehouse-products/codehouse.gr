// Γενικός text editor — track μόνο τα αλλαγμένα πεδία
const app = document.getElementById('app');
const changed = new Map(); // key -> new text

const TAG_LABELS = {h1:'Τίτλος (μεγάλος)',h2:'Τίτλος',h3:'Υπότιτλος',h4:'Υπότιτλος',p:'Παράγραφος',span:'Κείμενο',a:'Σύνδεσμος',li:'Στοιχείο λίστας',button:'Κουμπί',strong:'Έντονο',em:'Πλάγιο',td:'Κελί',th:'Κεφαλίδα',figcaption:'Λεζάντα',blockquote:'Παράθεση',title:'Τίτλος σελίδας (tab)',label:'Ετικέτα',summary:'Σύνοψη'};

function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}

FIELDS.forEach(f => {
  const el = document.createElement('div');
  el.className = 'tfield';
  el.dataset.search = f.text.toLowerCase();
  const long = f.text.length > 80;
  el.innerHTML = `
    <label class="tfield-label">${TAG_LABELS[f.tag]||f.tag} <code>&lt;${f.tag}&gt;</code></label>
    ${long
      ? `<textarea class="tfield-input" data-key="${f.key}" rows="${Math.min(6, Math.ceil(f.text.length/60))}">${esc(f.text)}</textarea>`
      : `<input class="tfield-input" data-key="${f.key}" value="${esc(f.text)}">`}
  `;
  app.appendChild(el);
});

app.addEventListener('input', e => {
  const key = +e.target.dataset.key;
  if (isNaN(key)) return;
  const f = FIELDS[key];
  if (e.target.value !== f.text) {
    changed.set(key, e.target.value);
    e.target.classList.add('tfield-changed');
  } else {
    changed.delete(key);
    e.target.classList.remove('tfield-changed');
  }
  document.getElementById('chCount').textContent = changed.size;
});

document.getElementById('filter').addEventListener('input', e => {
  const q = e.target.value.toLowerCase().trim();
  app.querySelectorAll('.tfield').forEach(el => {
    el.style.display = !q || el.dataset.search.includes(q) ? '' : 'none';
  });
});

document.getElementById('txtForm').addEventListener('submit', e => {
  const out = [];
  changed.forEach((text, key) => {
    const f = FIELDS[key];
    // orig = το αρχικό ENCODED κείμενο όπως είναι στο αρχείο — server-side επαλήθευση
    out.push({offset: f.offset, len: f.len, text: text, orig: encodeHtml(f.text, f)});
  });
  document.getElementById('changesJson').value = JSON.stringify(out);
});

// Αναπαράγει το αρχικό encoded κείμενο: ο server μας έδωσε decoded text + len σε bytes.
// Αντί να μαντέψουμε το encoding, στέλνουμε placeholder και ο server συγκρίνει με substr βάσει offset/len.
// Οπότε: στέλνουμε ένα sentinel που ο server αντικαθιστά — απλούστερα: ο server συγκρίνει hash.
function encodeHtml(s, f) {
  // Ο server έχει το αυθεντικό αρχείο. Στέλνουμε το decoded original για διπλή επαλήθευση:
  // ο server θα το κάνει decode(substr(html, offset, len)) και θα συγκρίνει.
  return s;
}
