// High Hope menu editor
let data = JSON.parse(JSON.stringify(DATA));
const app = document.getElementById('app');

function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML;}

function render(){
  app.innerHTML = '';
  data.forEach((sec, si) => {
    const secEl = document.createElement('section');
    secEl.className = 'msec';
    secEl.innerHTML = `
      <div class="msec-head">
        <input class="msec-title" value="${esc(sec.title)}" data-si="${si}" placeholder="Όνομα κατηγορίας">
        <div class="msec-actions">
          <button type="button" class="icon-btn" data-act="up" data-si="${si}" title="Πάνω">↑</button>
          <button type="button" class="icon-btn" data-act="down" data-si="${si}" title="Κάτω">↓</button>
          <button type="button" class="icon-btn icon-del" data-act="delsec" data-si="${si}" title="Διαγραφή κατηγορίας">🗑</button>
        </div>
      </div>
      <div class="mitems"></div>
      <button type="button" class="btn btn-ghost btn-sm btn-additem" data-si="${si}">+ Προϊόν</button>`;
    const wrap = secEl.querySelector('.mitems');
    sec.items.forEach((it, ii) => {
      const el = document.createElement('div');
      el.className = 'mitem';
      el.dataset.name = (it.name||'').toLowerCase();
      el.innerHTML = `
        <div class="mitem-row">
          <input class="mi-name" value="${esc(it.name)}" placeholder="Όνομα" data-si="${si}" data-ii="${ii}" data-f="name">
          <input class="mi-price" value="${esc(it.price)}" placeholder="Τιμή π.χ. 2,50€" data-si="${si}" data-ii="${ii}" data-f="price">
          <button type="button" class="icon-btn icon-del" data-act="delitem" data-si="${si}" data-ii="${ii}" title="Διαγραφή">🗑</button>
        </div>
        <div class="mitem-row2">
          <input class="mi-desc" value="${esc(it.desc)}" placeholder="Περιγραφή (προαιρετική)" data-si="${si}" data-ii="${ii}" data-f="desc">
          <select class="mi-badge" data-si="${si}" data-ii="${ii}" data-f="badge">
            <option value="" ${!it.badge?'selected':''}>— χωρίς badge —</option>
            <option value="Best Seller" ${it.badge==='Best Seller'?'selected':''}>Best Seller</option>
            <option value="Νέο" ${it.badge==='Νέο'?'selected':''}>Νέο</option>
            <option value="Vegan" ${it.badge==='Vegan'?'selected':''}>Vegan</option>
          </select>
        </div>`;
      wrap.appendChild(el);
    });
    app.appendChild(secEl);
  });
  updateCount();
}

function updateCount(){
  const t = data.reduce((a,s)=>a+s.items.length,0);
  const el = document.getElementById('totalCount');
  if (el) el.textContent = t;
}

app.addEventListener('input', e => {
  const {si, ii, f} = e.target.dataset;
  if (e.target.classList.contains('msec-title')) { data[si].title = e.target.value; return; }
  if (f !== undefined && si !== undefined && ii !== undefined) data[si].items[ii][f] = e.target.value;
});
app.addEventListener('change', e => {
  const {si, ii, f} = e.target.dataset;
  if (f === 'badge') data[si].items[ii][f] = e.target.value;
});

app.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const si = +b.dataset.si, ii = +b.dataset.ii;
  switch (b.dataset.act) {
    case 'delsec':
      if (confirm(`Διαγραφή κατηγορίας «${data[si].title}» με ${data[si].items.length} προϊόντα;`)) { data.splice(si,1); render(); }
      return;
    case 'delitem':
      if (confirm(`Διαγραφή «${data[si].items[ii].name}»;`)) { data[si].items.splice(ii,1); render(); }
      return;
    case 'up':
      if (si>0) { [data[si-1],data[si]]=[data[si],data[si-1]]; render(); }
      return;
    case 'down':
      if (si<data.length-1) { [data[si+1],data[si]]=[data[si],data[si+1]]; render(); }
      return;
  }
  if (b.classList.contains('btn-additem')) {
    data[b.dataset.si].items.push({name:'', badge:'', desc:'', price:''});
    render();
    const secs = app.querySelectorAll('.msec');
    const inputs = secs[b.dataset.si].querySelectorAll('.mi-name');
    inputs[inputs.length-1].focus();
  }
});

document.getElementById('addSection').addEventListener('click', () => {
  data.push({id:'', title:'', items:[]});
  render();
  const titles = app.querySelectorAll('.msec-title');
  titles[titles.length-1].focus();
});

document.getElementById('filter').addEventListener('input', e => {
  const q = e.target.value.toLowerCase().trim();
  app.querySelectorAll('.mitem').forEach(el => {
    el.style.display = !q || el.dataset.name.includes(q) ? '' : 'none';
  });
});

document.getElementById('menuForm').addEventListener('submit', () => {
  document.getElementById('menuJson').value = JSON.stringify(data);
});

render();
