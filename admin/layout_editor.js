// Layout editor — μετακίνηση/απόκρυψη/διαγραφή ενοτήτων
const app = document.getElementById('app');
let order = BLOCKS.map(b => b.key);
let hidden = BLOCKS.filter(b => b.hidden).map(b => b.key);
let deleted = [];
const byKey = {};
BLOCKS.forEach(b => byKey[b.key] = b);

const TAG_ICONS = {header:'🧭', footer:'⬇️', nav:'🧭', section:'🧱', aside:'📌', article:'📄'};

function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}

function render(){
  app.innerHTML = '';
  order.forEach((key, pos) => {
    if (deleted.includes(key)) return;
    const b = byKey[key];
    const isHidden = hidden.includes(key);
    const el = document.createElement('div');
    el.className = 'lblock' + (isHidden ? ' lblock-hidden' : '');
    el.innerHTML = `
      <div class="lblock-main">
        <span class="lblock-icon">${TAG_ICONS[b.tag]||'🧱'}</span>
        <div class="lblock-info">
          <strong>${esc(b.title)}</strong>
          <span class="lblock-meta">&lt;${b.tag}&gt;${b.id ? ' #'+esc(b.id) : ''}${isHidden ? ' · ΚΡΥΜΜΕΝΗ' : ''}</span>
          ${b.imgs.length ? `<span class="lblock-imgs">🖼 ${b.imgs.map(esc).join(', ')}</span>` : ''}
        </div>
      </div>
      <div class="lblock-actions">
        <button type="button" class="icon-btn" data-act="up" data-key="${key}" title="Πάνω" ${pos===0?'disabled':''}>↑</button>
        <button type="button" class="icon-btn" data-act="down" data-key="${key}" title="Κάτω" ${pos===visibleCount()-1?'disabled':''}>↓</button>
        <button type="button" class="icon-btn ${isHidden?'icon-show':''}" data-act="hide" data-key="${key}" title="${isHidden?'Εμφάνιση':'Απόκρυψη'}">${isHidden?'🙈':'👁'}</button>
        <button type="button" class="icon-btn icon-del" data-act="del" data-key="${key}" title="Διαγραφή">🗑</button>
      </div>`;
    app.appendChild(el);
  });
}

function visibleCount(){ return order.filter(k => !deleted.includes(k)).length; }

app.addEventListener('click', e => {
  const btn = e.target.closest('button'); if (!btn) return;
  const key = +btn.dataset.key;
  const visOrder = order.filter(k => !deleted.includes(k));
  const vi = visOrder.indexOf(key);
  switch (btn.dataset.act) {
    case 'up':
      if (vi > 0) swapInOrder(key, visOrder[vi-1]);
      break;
    case 'down':
      if (vi < visOrder.length - 1) swapInOrder(key, visOrder[vi+1]);
      break;
    case 'hide':
      if (hidden.includes(key)) hidden = hidden.filter(k => k !== key);
      else hidden.push(key);
      break;
    case 'del':
      const b = byKey[key];
      if (confirm(`Οριστική διαγραφή της ενότητας «${b.title}»;\n(Υπάρχει backup για επαναφορά)`)) deleted.push(key);
      break;
  }
  render();
});

function swapInOrder(a, b){
  const ia = order.indexOf(a), ib = order.indexOf(b);
  [order[ia], order[ib]] = [order[ib], order[ia]];
}

document.getElementById('layoutForm').addEventListener('submit', () => {
  document.getElementById('layoutJson').value = JSON.stringify({order, hidden, deleted, stateHash: STATE_HASH});
});

render();
