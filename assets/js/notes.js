(function(){
  'use strict';
  if(/^https?:$/.test(location.protocol)&&/\/index\.html$/i.test(location.pathname)){
    history.replaceState(null,'',location.pathname.replace(/index\.html$/i,'')+location.search+location.hash);
  }
  const nav=document.getElementById('nav');
  const toggle=document.getElementById('navToggle');
  const links=document.getElementById('navLinks');
  const progress=document.getElementById('progress');

  function setMenu(open){
    if(!nav||!toggle)return;
    nav.classList.toggle('menu-open',open);
    toggle.setAttribute('aria-expanded',String(open));
    toggle.setAttribute('aria-label',open?'Close navigation':'Open navigation');
  }
  if(toggle&&links){
    toggle.addEventListener('click',()=>setMenu(!nav.classList.contains('menu-open')));
    links.addEventListener('click',event=>{if(event.target.closest('a'))setMenu(false);});
    document.addEventListener('click',event=>{if(nav.classList.contains('menu-open')&&!nav.contains(event.target))setMenu(false);});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&nav.classList.contains('menu-open')){setMenu(false);toggle.focus();}});
  }

  let ticking=false;
  function updateScroll(){
    if(nav)nav.classList.toggle('scrolled',scrollY>20);
    if(progress){const height=document.documentElement.scrollHeight-innerHeight;progress.style.width=(height>0?scrollY/height*100:0)+'%';}
  }
  addEventListener('scroll',()=>{if(ticking)return;ticking=true;requestAnimationFrame(()=>{updateScroll();ticking=false;});},{passive:true});
  updateScroll();

  const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealItems=[...document.querySelectorAll('.article-body > h2,.article-body > h3,.article-body > p,.article-body > blockquote,.article-body > figure,.article-body > .article-sources,.article-body > .article-author,.article-end')];
  if(revealItems.length&&!reduceMotion){
    revealItems.forEach((item,index)=>{
      item.classList.add('note-reveal');
      item.style.setProperty('--reveal-delay',`${(index%3)*45}ms`);
    });
    if('IntersectionObserver' in window){
      const observer=new IntersectionObserver(entries=>{
        entries.forEach(entry=>{
          if(!entry.isIntersecting)return;
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        });
      },{rootMargin:'0px 0px -8% 0px',threshold:.08});
      revealItems.forEach(item=>observer.observe(item));
    }else revealItems.forEach(item=>item.classList.add('is-visible'));
  }

  const copyButton=document.querySelector('[data-copy-link]');
  const copyStatus=document.querySelector('[data-copy-status]');
  if(copyButton){
    copyButton.addEventListener('click',async()=>{
      try{
        if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(location.href);
        else{const field=document.createElement('textarea');field.value=location.href;field.setAttribute('readonly','');field.style.position='fixed';field.style.opacity='0';document.body.appendChild(field);field.select();document.execCommand('copy');field.remove();}
        if(copyStatus)copyStatus.textContent='Copied';
      }
      catch(error){if(copyStatus)copyStatus.textContent='Copy failed';}
      setTimeout(()=>{if(copyStatus)copyStatus.textContent='';},1800);
    });
  }

  const shareButton=document.querySelector('[data-share]');
  if(shareButton&&navigator.share){
    shareButton.hidden=false;
    shareButton.addEventListener('click',()=>navigator.share({title:document.title,url:location.href}).catch(()=>{}));
  }
})();
