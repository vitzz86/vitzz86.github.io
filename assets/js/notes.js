(function(){
  'use strict';
  if(/^https?:$/.test(location.protocol)&&/\/index\.html$/i.test(location.pathname)){
    history.replaceState(null,'',location.pathname.replace(/index\.html$/i,'')+location.search+location.hash);
  }
  const nav=document.getElementById('nav');
  const toggle=document.getElementById('navToggle');
  const links=document.getElementById('navLinks');
  const progress=document.getElementById('progress');
  const isIndonesian=()=>document.documentElement.lang==='id';
  const article=document.querySelector('.article-body');

  function slugify(value){
    return value.toLowerCase().trim().replace(/[^a-z0-9\s-]/g,'').replace(/\s+/g,'-').replace(/-+/g,'-')||'section';
  }

  let toc=null;
  let tocObserver=null;
  function buildArticleNavigation(){
    if(!article)return;
    const headings=[...article.querySelectorAll(':scope > h2')].filter(heading=>!heading.closest('.article-sources'));
    if(headings.length<2)return;
    headings.forEach((heading,index)=>{
      if(!heading.id)heading.id=heading.dataset.i18n||`${slugify(heading.textContent)}-${index+1}`;
    });
    if(!toc){
      toc=document.createElement('nav');
      toc.className='article-toc';
      article.before(toc);
    }
    toc.setAttribute('aria-label',isIndonesian()?'Daftar isi':'Table of contents');
    toc.innerHTML=`<div class="article-toc-head"><span>${isIndonesian()?'Dalam catatan ini':'In this article'}</span><span aria-hidden="true">${String(headings.length).padStart(2,'0')} ${isIndonesian()?'bagian':'sections'}</span></div><ol>${headings.map(heading=>`<li><a href="#${heading.id}">${heading.textContent.trim()}</a></li>`).join('')}</ol>`;
    if(tocObserver)tocObserver.disconnect();
    if('IntersectionObserver' in window){
      const links=new Map([...toc.querySelectorAll('a')].map(link=>[link.getAttribute('href').slice(1),link]));
      tocObserver=new IntersectionObserver(entries=>{
        const visible=entries.filter(entry=>entry.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
        if(!visible)return;
        links.forEach(link=>link.removeAttribute('aria-current'));
        links.get(visible.target.id)?.setAttribute('aria-current','true');
      },{rootMargin:'-18% 0px -68% 0px',threshold:0});
      headings.forEach(heading=>tocObserver.observe(heading));
    }
  }

  function localizeArticleDetails(){
    document.querySelectorAll('.citation a,.source-number').forEach(link=>{
      link.setAttribute('aria-label',isIndonesian()?`Buka sumber ${link.textContent.trim()} di tab baru`:`Open source ${link.textContent.trim()} in a new tab`);
    });
    document.querySelectorAll('.article-figure').forEach(figure=>{
      const image=figure.querySelector('img');
      const caption=figure.querySelector('figcaption');
      if(image&&caption)image.alt=caption.textContent.trim();
    });
  }

  function setMenu(open){
    if(!nav||!toggle)return;
    nav.classList.toggle('menu-open',open);
    toggle.setAttribute('aria-expanded',String(open));
    toggle.setAttribute('aria-label',open?(isIndonesian()?'Tutup navigasi':'Close navigation'):(isIndonesian()?'Buka navigasi':'Open navigation'));
  }
  if(toggle&&links){
    toggle.addEventListener('click',()=>setMenu(!nav.classList.contains('menu-open')));
    links.addEventListener('click',event=>{if(event.target.closest('a'))setMenu(false);});
    document.addEventListener('click',event=>{if(nav.classList.contains('menu-open')&&!nav.contains(event.target))setMenu(false);});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&nav.classList.contains('menu-open')){setMenu(false);toggle.focus();}});
  }
  setMenu(false);

  let ticking=false;
  function updateScroll(){
    if(nav)nav.classList.toggle('scrolled',scrollY>20);
    if(progress){const height=document.documentElement.scrollHeight-innerHeight;progress.style.width=(height>0?scrollY/height*100:0)+'%';}
  }
  addEventListener('scroll',()=>{if(ticking)return;ticking=true;requestAnimationFrame(()=>{updateScroll();ticking=false;});},{passive:true});
  updateScroll();
  buildArticleNavigation();
  localizeArticleDetails();

  const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealItems=[...document.querySelectorAll('.article-body > h2,.article-body > h3,.article-body > p,.article-body > blockquote,.article-body > .article-sources,.article-body > .article-author,.article-end')];
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
        if(copyStatus)copyStatus.textContent=isIndonesian()?'Tersalin':'Copied';
      }
      catch(error){if(copyStatus)copyStatus.textContent=isIndonesian()?'Gagal menyalin':'Copy failed';}
      setTimeout(()=>{if(copyStatus)copyStatus.textContent='';},1800);
    });
  }

  const shareButton=document.querySelector('[data-share]');
  if(shareButton&&navigator.share){
    shareButton.hidden=false;
    shareButton.addEventListener('click',()=>navigator.share({title:document.title,url:location.href}).catch(()=>{}));
  }
  document.addEventListener('vito:languagechange',()=>{
    if(toggle)setMenu(nav?.classList.contains('menu-open')||false);
    buildArticleNavigation();
    localizeArticleDetails();
  });
})();
