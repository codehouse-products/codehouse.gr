(() => {
  const $=(s,c=document)=>c.querySelector(s), $$=(s,c=document)=>[...c.querySelectorAll(s)];
  const menu=$('.menu-panel'),toggle=$('.menu-toggle'),brand=$('.brand');let priorFocus=null,inertBefore=new Map();
  function closeMenu(restoreFocus=true){if(!menu)return;menu.classList.remove('open');menu.setAttribute('aria-hidden','true');document.body.classList.remove('menu-open');toggle?.setAttribute('aria-expanded','false');inertBefore.forEach((value,node)=>node.inert=value);inertBefore.clear();if(restoreFocus){const target=priorFocus&&priorFocus.offsetParent!==null?priorFocus:brand;target?.focus()}priorFocus=null}
  toggle?.addEventListener('click',()=>{
    if(menu.classList.contains('open'))return closeMenu();
    priorFocus=toggle;
    menu.classList.add('open');
    menu.setAttribute('aria-hidden','false');
    document.body.classList.add('menu-open');
    toggle.setAttribute('aria-expanded','true');
    [...document.body.children].forEach(node=>{
      if(node!==menu){inertBefore.set(node,node.inert);node.inert=true}
    });
    const close=menu.querySelector('.menu-close');
    let attempts=0;
    // Inherited visibility transitions can briefly make the close control
    // unfocusable, even with reduced motion. Do not leave focus on inert body.
    const focusClose=()=>{
      if(!close||!menu.classList.contains('open'))return;
      if(document.activeElement!==document.body&&document.activeElement!==toggle)return;
      close.focus();
      if(document.activeElement!==close&&++attempts<60)requestAnimationFrame(focusClose);
    };
    focusClose();
  });
  $('.menu-close',menu)?.addEventListener('click',closeMenu);
  // Clear the modal state before following links or entering the back/forward cache.
  menu?.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>closeMenu(false)));
  window.addEventListener('pagehide',()=>closeMenu(false));
  menu?.addEventListener('keydown',e=>{if(e.key==='Escape'){closeMenu();return}if(e.key==='Tab'){const nodes=$$('a,button',menu).filter(x=>!x.disabled&&x.getClientRects().length&&getComputedStyle(x).visibility==='visible');if(!nodes.length)return;const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu?.classList.contains('open'))closeMenu()});
  const mobileMenuQuery=matchMedia('(max-width: 760px)');mobileMenuQuery.addEventListener?.('change',e=>{if(!e.matches&&menu?.classList.contains('open'))closeMenu(true)});window.addEventListener('resize',()=>{if(window.innerWidth>760&&menu?.classList.contains('open'))closeMenu(true)});
  const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
  function syncRail(rail){const controls=$$(`[data-rail-control="#${rail.id}"]`);controls.forEach(b=>{const atStart=rail.scrollLeft<=2,atEnd=rail.scrollLeft+rail.clientWidth>=rail.scrollWidth-2;b.disabled=b.dataset.dir==='prev'?atStart:atEnd});const pos=$(`[data-rail-position="#${rail.id}"]`);if(pos){const cards=$$('.project-card',rail);const first=cards[0];const index=first?Math.min(cards.length,Math.max(1,Math.floor((rail.scrollLeft+2)/(first.offsetWidth+20))+1)):1;pos.textContent=`${String(index).padStart(2,'0')} / ${String(cards.length).padStart(2,'0')}`}}
  $$('[data-rail-control]').forEach(b=>b.addEventListener('click',()=>{const rail=$(b.dataset.railControl);if(rail)rail.scrollBy({left:b.dataset.dir==='next'?rail.clientWidth*.8:-rail.clientWidth*.8,behavior:reducedMotion.matches?'auto':'smooth'})}));
  $$('.horizontal-rail[id]').forEach(rail=>{syncRail(rail);rail.addEventListener('scroll',()=>syncRail(rail),{passive:true});if('ResizeObserver'in window)new ResizeObserver(()=>syncRail(rail)).observe(rail);else window.addEventListener('resize',()=>syncRail(rail))});
  $$('.service-rail').forEach(rail=>{const cards=$$('.service-card',rail);const activate=card=>{rail.classList.add('is-hovering');cards.forEach(c=>c.classList.toggle('is-active',c===card))};const clear=()=>{rail.classList.remove('is-hovering');cards.forEach(c=>c.classList.remove('is-active'))};cards.forEach(card=>{if(matchMedia('(hover:hover) and (pointer:fine)').matches){card.addEventListener('mouseenter',()=>activate(card));card.addEventListener('mouseleave',clear)}card.addEventListener('focusin',()=>activate(card));card.addEventListener('focusout',e=>{if(!rail.contains(e.relatedTarget))clear()})})});
  // Native scrolling provides one-swipe touch navigation; arrow keys make rails keyboard-operable.
  $$('.horizontal-rail').forEach(rail=>rail.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();rail.scrollBy({left:(e.key==='ArrowRight'?1:-1)*rail.clientWidth*.75,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}}));
  const form=$('[data-contact-form]');
  if(form){
    const status=$('.form-status',form),button=$('[type=submit]',form);
    const name=$('[name=name]',form),description=$('[name=description]',form);
    const english=form.dataset.locale==='en';
    [name,description].forEach(field=>field.addEventListener('input',()=>field.setCustomValidity('')));
    form.addEventListener('submit',async e=>{
      e.preventDefault();
      // requestSubmit()/Enter must not create a second request while one is pending.
      if(button.disabled)return;
      status.textContent='';
      name.setCustomValidity(name.value.trim()?'':(english?'Please enter your name.':'Γράψε το όνομά σου.'));
      // Match the server's Unicode character minimum, not UTF-16 code units.
      description.setCustomValidity(Array.from(description.value.trim()).length>=10?'':(english?'Please enter at least 10 characters.':'Γράψε τουλάχιστον 10 χαρακτήρες.'));
      if(!form.reportValidity())return;
      button.disabled=true;
      const label=button.textContent;
      button.textContent=english?'SENDING…':'ΑΠΟΣΤΟΛΗ…';
      try{
        const payload=Object.fromEntries(new FormData(form));
        payload._form='studio';
        const r=await fetch('/lead.php',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        let data={};
        try{data=await r.json()}catch{}
        if(r.ok&&data.ok&&data.saved&&data.mail===true){
          status.textContent=english?'Message sent. We’ll be in touch.':'Το μήνυμα στάλθηκε. Θα επικοινωνήσουμε σύντομα.';
          status.setAttribute('role','status');
          form.reset();
          window.dispatchEvent(new CustomEvent('studio:lead-accepted'));
        }else if(r.status===202&&data.ok&&data.saved&&data.mail===false){
          status.textContent=english?'Your message was saved, but email delivery could not be confirmed. Please also contact hello@codehouse.gr.':'Το μήνυμα αποθηκεύτηκε, αλλά η αποστολή email δεν επιβεβαιώθηκε. Επικοινώνησε και στο hello@codehouse.gr.';
          status.setAttribute('role','status');
        }else throw Error('submit');
      }catch{
        status.textContent=english?'We couldn’t send your message. Your details are still here—please try again or email hello@codehouse.gr.':'Δεν ήταν δυνατή η αποστολή. Τα στοιχεία σου παραμένουν στη φόρμα· δοκίμασε ξανά ή γράψε στο hello@codehouse.gr.';
        status.setAttribute('role','alert');
      }finally{
        button.disabled=false;
        button.textContent=label;
      }
    });
  }
  const reveal=$$('.reveal');if('IntersectionObserver'in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){const io=new IntersectionObserver(entries=>entries.forEach(x=>{if(x.isIntersecting){x.target.classList.add('revealed');io.unobserve(x.target)}}),{threshold:.08});reveal.forEach(e=>io.observe(e))}
  $$('[data-athens-clock]').forEach(el=>{const update=()=>el.textContent=new Intl.DateTimeFormat(document.documentElement.lang==='en'?'en-GB':'el-GR',{timeZone:'Europe/Athens',hour:'2-digit',minute:'2-digit'}).format(new Date());update();setInterval(update,60000)});
})();