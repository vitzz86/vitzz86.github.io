/* Keep directory pages on their canonical, extension-free public URLs. */
if(/^https?:$/.test(location.protocol)&&/\/index\.html$/i.test(location.pathname)){
  history.replaceState(null,'',location.pathname.replace(/index\.html$/i,'')+location.search+location.hash);
}

const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
/* Narrated pitch audio per deck. Playback drives the slides. */
const DECK_AUDIO = { rs: 'assets/audio/raisesea-pitch.m4a', outlook: 'assets/audio/outlook-pitch.m4a', nexus: 'assets/audio/nexus-pitch.m4a' };
/* Authored cue maps (from the narration timeline): [seconds, slideIndex].
   Cue times are scaled by audioDuration/total at runtime, so replacing an
   audio file keeps the structure aligned. Decks without a map use an even
   split (RaiseSEA's narration is already evenly paced). */
const DECK_SYNC = {
  nexus: { total: 603, cues: [[0,0],[3,1],[6,2],[9,3],[79,4],[114,5],[189,6],[229,7],[264,8],[304,9],[339,10],[342,11],[345,12],[365,13],[368,14],[371,15],[374,16],[396,17],[436,18],[439,19],[474,20],[514,21],[544,22]] },
  outlook: { total: 484, cues: [[0,0],[3,1],[6,2],[9,3],[12,4],[15,5],[44,6],[56,7],[66,8],[69,9],[92,10],[95,11],[120,12],[138,13],[150,14],[187,15],[190,16],[209,17],[248,18],[273,19],[307,20],[338,21],[364,22],[404,23],[429,24],[432,25],[435,26],[475,27],[478,28],[481,29]] }
};
const DECKS = {
  nex: Array.from({length:14},(_,k)=>'assets/decks/nexcatalyst/nexcatalyst-'+String(k+1).padStart(2,'0')+'.jpg'),
  rs: Array.from({length:11},(_,k)=>'assets/decks/raisesea/raisesea-'+String(k+1).padStart(2,'0')+'.jpg'),
  outlook: Array.from({length:31},(_,k)=>'assets/decks/outlook/outlook-'+String(k+1).padStart(2,'0')+'.jpg'),
  nexus: Array.from({length:23},(_,k)=>'assets/decks/nexus/nexus-'+String(k+1).padStart(2,'0')+'.jpg')
};

/* ---------- hero constellation ---------- */
(function(){
  const c=document.getElementById('net'),hero=c.closest('.hero'),x=c.getContext('2d');let W,H,DPR,nodes,mouse={x:-999,y:-999},raf,inView=true;
  function size(){ DPR=Math.min(devicePixelRatio||1,2); const r=c.getBoundingClientRect(); W=r.width;H=r.height; c.width=W*DPR;c.height=H*DPR; x.setTransform(DPR,0,0,DPR,0,0);
    const n=Math.min(72,Math.round(W*H/15000)); nodes=Array.from({length:n},()=>({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.25,vy:(Math.random()-.5)*.25})); }
  function step(){
    x.clearRect(0,0,W,H);
    for(const n of nodes){ n.x+=n.vx;n.y+=n.vy; if(n.x<0||n.x>W)n.vx*=-1; if(n.y<0||n.y>H)n.vy*=-1;
      const dx=n.x-mouse.x,dy=n.y-mouse.y,d=Math.hypot(dx,dy);if(d>0&&d<140){const f=(140-d)/140*.6;n.x+=dx/d*f;n.y+=dy/d*f;} }
    for(let i=0;i<nodes.length;i++){ for(let j=i+1;j<nodes.length;j++){ const a=nodes[i],b=nodes[j],d=Math.hypot(a.x-b.x,a.y-b.y);
      if(d<128){ x.strokeStyle='rgba(15,91,80,'+(1-d/128)*.22+')'; x.lineWidth=1; x.beginPath();x.moveTo(a.x,a.y);x.lineTo(b.x,b.y);x.stroke(); } } }
    for(const n of nodes){ const dm=Math.hypot(n.x-mouse.x,n.y-mouse.y);
      if(dm<150){ x.strokeStyle='rgba(10,66,57,'+(1-dm/150)*.35+')'; x.lineWidth=1; x.beginPath();x.moveTo(n.x,n.y);x.lineTo(mouse.x,mouse.y);x.stroke(); }
      x.fillStyle='rgba(21,23,15,.30)'; x.beginPath();x.arc(n.x,n.y,1.6,0,7);x.fill(); }
    raf=requestAnimationFrame(step);
  }
  function start(){if(!raf&&!RM&&inView&&!document.hidden)step();}
  function stop(){ cancelAnimationFrame(raf); raf=null; }
  addEventListener('resize',size); size();
  if(RM){ /* draw a single static frame */ for(let i=0;i<22;i++){x.fillStyle='rgba(21,23,15,.18)';x.beginPath();x.arc(Math.random()*W,Math.random()*H,1.6,0,7);x.fill();} }
  else start();
  hero.addEventListener('pointermove',e=>{const r=c.getBoundingClientRect();mouse.x=e.clientX-r.left;mouse.y=e.clientY-r.top;});
  hero.addEventListener('pointerleave',()=>{mouse.x=-999;mouse.y=-999;});
  // pause when hero scrolled away
  new IntersectionObserver(es=>es.forEach(e=>{inView=e.isIntersecting;e.isIntersecting?start():stop();})).observe(c);
  document.addEventListener('visibilitychange',()=>document.hidden?stop():start());
})();

/* ---------- marquee ---------- */
(function(){
  const words=['Climate-tech','Early-stage venture','Southeast Asia','Fintech','Impact','AI tooling','Deal screening','Fund building','Founder-first'];
  const html=words.map(w=>'<span>'+w+'</span><i>◆</i>').join('');
  document.getElementById('mq').innerHTML=html+html;
})();

/* ---------- count up ---------- */
(function(){
  function fmt(v,el){ let s; const dec=+el.dataset.dec||0; v=dec?v.toFixed(dec):Math.round(v);
    if(el.dataset.comma) v=(+v).toLocaleString('en-US'); s=(el.dataset.prefix||'')+v+(el.dataset.suffix||''); return s; }
  const io=new IntersectionObserver(es=>es.forEach(e=>{ if(!e.isIntersecting)return; io.unobserve(e.target);
    const el=e.target,t=+el.dataset.count; if(RM){el.textContent=fmt(t,el);return;}
    let s=null; (function a(ts){ s=s||ts; const p=Math.min((ts-s)/1300,1); const e2=1-Math.pow(1-p,3);
      el.textContent=fmt(t*e2,el); if(p<1)requestAnimationFrame(a); })(performance.now()); },{threshold:.6}));
  document.querySelectorAll('[data-count]').forEach(el=>io.observe(el));
})();

/* ---------- decks ---------- */
function buildDeck(el){
  const slides=DECKS[el.dataset.deck]; let i=0, timer=null, pitch=null;
  let renderToken=0;
  const sync=DECK_SYNC[el.dataset.deck]||null;
  const audioScale=()=>sync&&pitch&&pitch.duration?pitch.duration/sync.total:1;
  function slideAtTime(t){
    if(!sync)return Math.min(slides.length-1,Math.floor(t/pitch.duration*slides.length));
    const s=audioScale(); let cur=sync.cues[0][1];
    for(const c of sync.cues){ if(t>=c[0]*s-0.05)cur=c[1]; else break; }
    return cur; }
  function seekTimeFor(n){
    if(!sync)return n/slides.length*pitch.duration;
    const c=sync.cues.find(c=>c[1]===n); return c?c[0]*audioScale():null; }
  el.innerHTML=`
    <div class="stagewrap"><div class="stage" tabindex="0" aria-label="Presentation. Arrow keys to navigate, click to expand.">
      <img alt="" loading="eager" decoding="async" fetchpriority="high" draggable="false"><div class="glow"></div>
      <button class="snav prev" aria-label="Previous">&lsaquo;</button>
      <button class="snav next" aria-label="Next">&rsaquo;</button>
      <button class="fs" aria-label="Fullscreen">&#10530;</button>
    </div></div>
    <div class="dbar"><div class="ticks"></div><button class="auto" aria-label="Autoplay" aria-pressed="false">&#9658; Auto</button><div class="count"><span class="cur">1</span> / <span class="tot">${slides.length}</span></div></div>
    <div class="strip"></div>`;
  const stage=el.querySelector('.stage'),img=el.querySelector('img'),ticks=el.querySelector('.ticks'),
        cur=el.querySelector('.cur'),strip=el.querySelector('.strip'),auto=el.querySelector('.auto');
  slides.forEach((s,k)=>{ const t=document.createElement('button');t.type='button';t.className='tick';t.setAttribute('aria-label',`Go to slide ${k+1}`);t.onclick=()=>go(k);ticks.appendChild(t);
    const th=document.createElement('img');th.className='thumb';th.dataset.src=s;th.alt='';th.loading='lazy';th.decoding='async';th.fetchPriority='low';th.draggable=false;th.tabIndex=0;th.setAttribute('role','button');th.setAttribute('aria-label',`Go to slide ${k+1}`);th.onclick=()=>go(k);th.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go(k);}});strip.appendChild(th); });
  const tk=[...ticks.children], th=[...strip.children];
  if('IntersectionObserver' in window){
    const thumbObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{if(!entry.isIntersecting)return;const thumb=entry.target;thumb.src=thumb.dataset.src;delete thumb.dataset.src;thumbObserver.unobserve(thumb);}),{root:strip,rootMargin:'0px 180px'});
    th.forEach(thumb=>thumbObserver.observe(thumb));
  }else th.forEach(thumb=>{thumb.src=thumb.dataset.src;delete thumb.dataset.src;});
  function render(){ const token=++renderToken;stage.classList.remove('has-image');img.style.opacity=0;setTimeout(()=>{if(token!==renderToken)return;img.onload=()=>stage.classList.add('has-image');img.src=slides[i];img.alt=`Presentation slide ${i+1} of ${slides.length}`;img.style.opacity=1;},120);cur.textContent=i+1;
    tk.forEach((t,k)=>{t.classList.toggle('on',k===i);t.toggleAttribute('aria-current',k===i);});th.forEach((t,k)=>{t.classList.toggle('on',k===i);t.setAttribute('aria-current',k===i?'true':'false');});
    strip.scrollTo({left:th[i].offsetLeft-strip.clientWidth/2+th[i].clientWidth/2,behavior:RM?'auto':'smooth'});
    [i+1,i-1].forEach(n=>{if(slides[n]){const p=new Image();p.src=slides[n];}}); }
  function go(n){ i=(n+slides.length)%slides.length;
    if(pitch&&!pitch.paused&&pitch.duration){const t=seekTimeFor(i);
      if(t!==null&&Math.abs(pitch.currentTime-t)>0.6)pitch.currentTime=t+0.05;}
    render(); }
  el.querySelector('.prev').onclick=e=>{e.stopPropagation();stopAuto();go(i-1);};
  el.querySelector('.next').onclick=e=>{e.stopPropagation();stopAuto();go(i+1);};
  el.querySelector('.fs').onclick=e=>{e.stopPropagation();stopAuto();openLB(slides,i,n=>{i=n;render();});};
  img.onclick=()=>{openLB(slides,i,n=>{i=n;render();});};
  stage.addEventListener('keydown',e=>{ if(e.key==='ArrowRight'){e.preventDefault();stopAuto();go(i+1);} if(e.key==='ArrowLeft'){e.preventDefault();stopAuto();go(i-1);} });
  // autoplay
  function startAuto(){ if(pitch&&!pitch.paused)pitch.pause(); timer=setInterval(()=>go(i+1),4200); auto.classList.add('on');auto.setAttribute('aria-pressed','true');auto.innerHTML='&#10074;&#10074; Auto'; }
  function stopAuto(){ if(timer){clearInterval(timer);timer=null;} auto.classList.remove('on');auto.setAttribute('aria-pressed','false');auto.innerHTML='&#9658; Auto'; }
  auto.onclick=()=>timer?stopAuto():startAuto();
  // Narrated pitch audio drives the slides. Slide navigation seeks the audio.
  const aSrc=DECK_AUDIO[el.dataset.deck];
  if(aSrc){
    const pBtn=document.createElement('button'); pBtn.className='auto pitch';
    pBtn.innerHTML='&#9658; Pitch';pBtn.setAttribute('aria-label','Play narrated pitch');pBtn.setAttribute('aria-pressed','false');
    auto.parentNode.insertBefore(pBtn,auto);
    pBtn.onclick=()=>{
      if(pitch){ pitch.paused?pitch.play():pitch.pause(); return; }
      pBtn.disabled=true; pBtn.innerHTML='&hellip; Pitch';
      const wire=a=>{ pitch=a;
        pitch.addEventListener('play',()=>{stopAuto();pBtn.classList.add('on');pBtn.setAttribute('aria-pressed','true');pBtn.innerHTML='&#10074;&#10074; Pitch';});
        pitch.addEventListener('pause',()=>{pBtn.classList.remove('on');pBtn.setAttribute('aria-pressed','false');pBtn.innerHTML='&#9658; Pitch';});
        pitch.addEventListener('ended',()=>{pitch.currentTime=0;go(0);});
        pitch.addEventListener('timeupdate',()=>{ if(!pitch.duration)return;
          const n=slideAtTime(pitch.currentTime);
          if(n!==i){ i=n; render(); } });
        pBtn.disabled=false;
        pitch.play().catch(err=>{ console.error('pitch playback blocked',err);
          pBtn.classList.remove('on'); pBtn.innerHTML='&#9658; Pitch'; });
      };
      // preferred: blob-load so seeking never depends on server range-request
      // support; force an audio MIME for servers that send octet-stream (Safari)
      fetch(aSrc).then(r=>{if(!r.ok)throw new Error(r.status);return r.blob();})
        .then(b=>{ // retype: dev servers mislabel .m4a (octet-stream / mp4a-latm)
          wire(new Audio(URL.createObjectURL(new Blob([b],{type:'audio/mp4'})))); })
        .catch(e=>{ // file:// pages block fetch. Play the file directly instead.
          console.warn('blob route unavailable, using direct audio:',e);
          wire(new Audio(aSrc)); });
    };
  }
  // tilt + glow
  if(!RM){ stage.addEventListener('mousemove',e=>{ const r=stage.getBoundingClientRect(); const px=(e.clientX-r.left)/r.width, py=(e.clientY-r.top)/r.height;
      stage.style.transform=`rotateY(${(px-.5)*6}deg) rotateX(${(.5-py)*6}deg)`; stage.style.setProperty('--mx',px*100+'%'); stage.style.setProperty('--my',py*100+'%'); });
    stage.addEventListener('mouseleave',()=>{stage.style.transform='';}); }
  // swipe / drag
  let sx=0,sy=0,down=false;
  stage.addEventListener('pointerdown',e=>{down=true;sx=e.clientX;sy=e.clientY;stage.classList.add('drag');});
  addEventListener('pointerup',e=>{if(!down)return;down=false;stage.classList.remove('drag');const dx=e.clientX-sx,dy=e.clientY-sy;if(Math.abs(dx)>45&&Math.abs(dx)>Math.abs(dy)*1.2){stopAuto();go(i+(dx<0?1:-1));}});
  stage.addEventListener('pointercancel',()=>{down=false;stage.classList.remove('drag');});
  el.classList.add('is-ready');
  render();
}
function ensureDeck(el){if(!el||el.dataset.deckBuilt==='true')return;el.dataset.deckBuilt='true';buildDeck(el);}
const workCarouselRoot=document.querySelector('[data-work-carousel]');
let workDecksReady=false;
if(workCarouselRoot&&'IntersectionObserver' in window){
  const workDeckObserver=new IntersectionObserver(entries=>entries.forEach(entry=>{if(!entry.isIntersecting)return;workDecksReady=true;ensureDeck(workCarouselRoot.querySelector('.work-slide.on .deck'));workDeckObserver.unobserve(workCarouselRoot);}),{rootMargin:'650px 0px'});
  workDeckObserver.observe(workCarouselRoot);
}else{
  workDecksReady=true;
  ensureDeck(document.querySelector('.work-slide.on .deck'));
}

/* ---------- lightbox ---------- */
const lb=document.getElementById('lb'),lbImg=document.getElementById('lbImg'),lbCount=document.getElementById('lbCount'),lbCap=document.getElementById('lbCap');
let lbS=[],lbI=0,lbSync=null,lbC=null,lbReturnFocus=null;
function renderLB(){const cap=(lbC&&lbC[lbI])||'';lbImg.src=lbS[lbI];lbImg.alt=cap||`Expanded media ${lbI+1} of ${lbS.length}`;lbCount.textContent=(lbI+1)+' / '+lbS.length;lbCap.textContent=cap;if(lbSync)lbSync(lbI);}
function openLB(s,idx,sync,caps){lbReturnFocus=document.activeElement;lbS=s;lbI=idx;lbSync=sync;lbC=caps||null;lb.classList.add('open');lb.setAttribute('aria-hidden','false');document.body.classList.add('lb-lock');renderLB();requestAnimationFrame(()=>document.getElementById('lbClose').focus());}
function closeLB(){if(!lb.classList.contains('open'))return;lb.classList.remove('open');lb.setAttribute('aria-hidden','true');document.body.classList.remove('lb-lock');lbImg.removeAttribute('src');if(lbReturnFocus&&document.contains(lbReturnFocus))lbReturnFocus.focus();}
function lbGo(n){lbI=(n+lbS.length)%lbS.length;renderLB();}
document.getElementById('lbPrev').onclick=()=>lbGo(lbI-1);
document.getElementById('lbNext').onclick=()=>lbGo(lbI+1);
document.getElementById('lbClose').onclick=closeLB;
lb.addEventListener('click',e=>{if(e.target===lb)closeLB();});
document.addEventListener('keydown',e=>{if(!lb.classList.contains('open'))return;if(e.key==='Escape')closeLB();if(e.key==='ArrowRight')lbGo(lbI+1);if(e.key==='ArrowLeft')lbGo(lbI-1);if(e.key==='Tab'){const focusable=[...lb.querySelectorAll('button')];const first=focusable[0],last=focusable.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});

/* ---------- photo gallery ---------- */
(function(){
  const CATS={events:'Deal flow & events',field:'In the field',community:'Community & mentoring',milestones:'Milestones'};
  const CATS_ID={events:'Deal flow & acara',field:'Kegiatan lapangan',community:'Komunitas & mentoring',milestones:'Pencapaian'};
  const PHOTO_DIMS={
    'dex-connex':[1400,1050],'field-efishery':[1400,1050],'field-jala':[1400,1050],'founder-plus':[1280,720],
    'graduation-itb':[852,1280],'investor-speed-dating':[1600,1066],'jewel-changi':[1280,957],'judge-startup-arena':[1600,836],
    'kadin-cofounders':[1400,787],'llv-office':[960,1280],'mentored-startup':[960,1280],'midyear-outlook':[1050,1400],
    'nus-business-school':[960,1280],'nus-lift-off':[1200,799],'social-innovator-hub':[1200,799],'team-llv':[1050,1400],
    'vc-networking-evening':[1400,787],'vc-networking-qapita':[1600,900],'with-sandiaga-uno':[1050,1400]
  };
  const PHOTOS=[
    {s:'with-sandiaga-uno',k:'community',c:'With Sandiaga Uno, former Indonesian Minister of Tourism & Creative Economy',ci:'Bersama Sandiaga Uno, mantan Menteri Pariwisata dan Ekonomi Kreatif Indonesia'},
    {s:'judge-startup-arena',k:'events',c:'Judging Startup Arena 2025 at Meet Ventures × SMU in Singapore',ci:'Menjadi juri Startup Arena 2025 di Meet Ventures × SMU, Singapura'},
    {s:'field-jala',k:'field',c:'Pond-side diligence with JALA and Forte Biotech across shrimp farms in coastal Java',ci:'Uji tuntas langsung di tambak bersama JALA dan Forte Biotech di pesisir Jawa'},
    {s:'midyear-outlook',k:'events',c:'Living Lab Ventures media briefing for the Mid-Year 2025 VC Investment Outlook',ci:'Media briefing Living Lab Ventures untuk Mid-Year 2025 VC Investment Outlook'},
    {s:'graduation-itb',k:'milestones',c:'Graduating cum laude in Information Systems & Technology at ITB in October 2024',ci:'Lulus cum laude dari Sistem dan Teknologi Informasi ITB pada Oktober 2024'},
    {s:'investor-speed-dating',k:'events',c:'Investor speed-dating with a curated Asia-Pacific startup shortlist',ci:'Sesi pertemuan singkat investor dengan startup Asia Pasifik yang telah dikurasi'},
    {s:'field-efishery',k:'field',c:'At eFishery HQ, learning from Indonesia’s aquaculture unicorn',ci:'Berkunjung ke kantor pusat eFishery untuk mempelajari perjalanan unicorn akuakultur Indonesia'},
    {s:'team-llv',k:'milestones',c:'The Living Lab Ventures investment team',ci:'Tim investasi Living Lab Ventures'},
    {s:'vc-networking-qapita',k:'events',c:'Jakarta’s venture community at an equity and cap-table night with Qapita',ci:'Komunitas modal ventura Jakarta dalam acara ekuitas dan cap table bersama Qapita'},
    {s:'mentored-startup',k:'community',c:'With a founder I mentored through the Astranauts program',ci:'Bersama founder yang saya dampingi melalui program Astranauts'},
    {s:'nus-business-school',k:'milestones',c:'NUS Overseas Colleges during a venture creation year in Singapore',ci:'NUS Overseas Colleges selama satu tahun mempelajari venture creation di Singapura'},
    {s:'kadin-cofounders',k:'community',c:'Founder roundtable at KADIN Indonesia, Jakarta',ci:'Diskusi meja bundar founder di KADIN Indonesia, Jakarta'},
    {s:'dex-connex',k:'events',c:'DEX Connex Indonesia 2025 with the Living Lab Ventures team',ci:'DEX Connex Indonesia 2025 bersama tim Living Lab Ventures'},
    {s:'llv-office',k:'milestones',c:'At the Living Lab Ventures office, BSD City',ci:'Di kantor Living Lab Ventures, BSD City'},
    {s:'social-innovator-hub',k:'milestones',c:'Social Innovator Hub at Tohoku University, Best Team and Best Participant',ci:'Social Innovator Hub di Tohoku University, meraih Tim Terbaik dan Peserta Terbaik'},
    {s:'founder-plus',k:'community',c:'Founder+ incubation batch, mentoring and judging',ci:'Batch inkubasi Founder+, sebagai mentor dan juri'},
    {s:'jewel-changi',k:'field',c:'Between meetings at Jewel Changi with co-workers on a business trip',ci:'Di sela pertemuan bisnis bersama rekan kerja di Jewel Changi'},
    {s:'nus-lift-off',k:'milestones',c:'NUS Lift-Off Day with the NOC cohort',ci:'NUS Lift-Off Day bersama cohort NOC'},
    {s:'vc-networking-evening',k:'events',c:'An evening with Jakarta’s investor community',ci:'Malam bersama komunitas investor Jakarta'}
  ];
  const gal=document.getElementById('gallery'),fl=document.getElementById('gfilters');
  if(!gal)return;
  let cur='all',shown=[];
  const isID=()=>document.documentElement.lang==='id';
  const catLabel=k=>k==='all'?(isID()?'Semua':'Everything'):(isID()?CATS_ID[k]:CATS[k]);
  const caption=p=>isID()?p.ci:p.c;
  const btns=[['all','Everything']].concat(Object.entries(CATS)).map(([k])=>{
    const n=k==='all'?PHOTOS.length:PHOTOS.filter(p=>p.k===k).length;
    const b=document.createElement('button'); b.className='gfilter'+(k==='all'?' on':'');
    b.dataset.category=k;
    b.innerHTML=catLabel(k)+'<span class="gn">'+n+'</span>';
    b.onclick=()=>{cur=k;btns.forEach(x=>x.classList.remove('on'));b.classList.add('on');render();};
    fl.appendChild(b); return b;
  });
  function render(){
    shown=PHOTOS.filter(p=>cur==='all'||p.k===cur);
    gal.innerHTML='';
    shown.forEach((p,i)=>{
      const d=document.createElement('div'); d.className='gitem'; d.tabIndex=0;
      d.style.animationDelay=Math.min(i*45,500)+'ms';
      const cap=caption(p);
      d.setAttribute('role','button'); d.setAttribute('aria-label',cap);
      const dims=PHOTO_DIMS[p.s];
      d.innerHTML='<img src="assets/photos/'+p.s+'.jpg" alt="'+cap.replace(/"/g,'&quot;')+'" width="'+dims[0]+'" height="'+dims[1]+'" loading="lazy" decoding="async"><div class="gcap"><span class="gtag">'+catLabel(p.k)+'</span>'+cap+'</div>';
      const open=()=>openLB(shown.map(x=>'assets/photos/'+x.s+'.jpg'),i,null,shown.map(caption));
      d.onclick=open;
      d.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}});
      gal.appendChild(d);
    });
  }
  render();
  document.addEventListener('vito:languagechange',()=>{
    btns.forEach(b=>{const n=b.querySelector('.gn')?.outerHTML||'';b.innerHTML=catLabel(b.dataset.category)+n;});
    render();
    if(lb.classList.contains('open')){lbC=shown.map(caption);renderLB();}
  });
})();

/* ---------- selected work carousel ---------- */
(function(){
  const root=document.querySelector('[data-work-carousel]');
  if(!root)return;
  const slides=[...root.querySelectorAll('[data-work-slide]')];
  const steps=[...root.querySelectorAll('[data-work-go]')];
  const status=root.querySelector('[data-work-status]');
  let current=0,startX=null,initialized=false;
  const statusText=()=>document.documentElement.lang==='id'?`Proyek ${current+1} dari ${slides.length}`:`Project ${current+1} of ${slides.length}`;
  function show(index,focus=false){
    current=(index+slides.length)%slides.length;
    slides.forEach((slide,i)=>{const on=i===current;slide.classList.toggle('on',on);slide.setAttribute('aria-hidden',String(!on));slide.toggleAttribute('inert',!on);});
    steps.forEach((step,i)=>{const on=i===current;step.classList.toggle('on',on);step.setAttribute('aria-selected',String(on));step.tabIndex=on?0:-1;});
    status.textContent=statusText();
    if(workDecksReady)ensureDeck(slides[current].querySelector('.deck'));
    if(initialized)steps[current].scrollIntoView({behavior:RM?'auto':'smooth',block:'nearest',inline:'nearest'});
    if(focus)steps[current].focus();
    requestAnimationFrame(()=>dispatchEvent(new Event('resize')));
    initialized=true;
  }
  steps.forEach((step,i)=>{
    step.addEventListener('click',()=>show(i));
    step.addEventListener('keydown',e=>{if(e.key==='ArrowRight'){e.preventDefault();show(i+1,true);}if(e.key==='ArrowLeft'){e.preventDefault();show(i-1,true);}if(e.key==='Home'){e.preventDefault();show(0,true);}if(e.key==='End'){e.preventDefault();show(slides.length-1,true);}});
  });
  root.querySelector('[data-work-prev]').addEventListener('click',()=>show(current-1));
  root.querySelector('[data-work-next]').addEventListener('click',()=>show(current+1));
  root.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'&&!e.target.closest('.nx-shell,.deck,a,button,input'))startX=e.clientX;});
  root.addEventListener('pointerup',e=>{if(startX==null)return;const delta=e.clientX-startX;startX=null;if(Math.abs(delta)>60)show(current+(delta<0?1:-1));});
  document.addEventListener('vito:languagechange',()=>{status.textContent=statusText();});
  show(0);
})();

/* ---------- big five radar ---------- */
(function(){
  const svg=document.getElementById('radar'); if(!svg)return;
  const data=[['OPENNESS',88],['CONSCIENTIOUSNESS',81],['EXTRAVERSION',71],['AGREEABLENESS',53],['NEUROTICISM',69]];
  const cx=130,cy=106,R=74,N=data.length,MAX=120;
  const pt=(k,r)=>{const a=-Math.PI/2+k*2*Math.PI/N;return [cx+r*Math.cos(a),cy+r*Math.sin(a)];};
  const poly=r=>data.map((_,k)=>pt(k,r).map(v=>v.toFixed(1)).join(',')).join(' ');
  let g='';
  [0.25,0.5,0.75,1].forEach(f=>{g+='<polygon class="rgrid" points="'+poly(R*f)+'"/>';});
  data.forEach((_,k)=>{const[x,y]=pt(k,R);g+='<line class="raxis" x1="'+cx+'" y1="'+cy+'" x2="'+x.toFixed(1)+'" y2="'+y.toFixed(1)+'"/>';});
  g+='<polygon class="rpoly" points="'+data.map((d,k)=>pt(k,R*d[1]/MAX).map(v=>v.toFixed(1)).join(',')).join(' ')+'"/>';
  data.forEach((d,k)=>{const[x,y]=pt(k,R*d[1]/MAX);g+='<circle class="rdot" cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="3"/>';});
  data.forEach((d,k)=>{const[x,y]=pt(k,R+15);const lab=(k===1?'CONSC.':k===2?'EXTRAV.':k===3?'AGREE.':k===4?'NEURO.':d[0]);
    g+='<text class="rlab" x="'+x.toFixed(1)+'" y="'+(y+3).toFixed(1)+'" text-anchor="middle">'+lab+' '+d[1]+'</text>';});
  svg.innerHTML=g;
})();

/* ---------- hero portrait tilt ---------- */
(function(){
  const f=document.getElementById('pframe'); if(!f||RM||matchMedia('(pointer:coarse)').matches)return;
  const hero=document.querySelector('.hero');
  hero.addEventListener('mousemove',e=>{ const r=f.getBoundingClientRect();
    const dx=(e.clientX-(r.left+r.width/2))/innerWidth, dy=(e.clientY-(r.top+r.height/2))/innerHeight;
    f.style.transform='rotate(2.2deg) rotateY('+(dx*7)+'deg) rotateX('+(-dy*7)+'deg) translateZ(0)'; });
  hero.addEventListener('mouseleave',()=>{f.style.transform='';});
})();

/* ---------- magnetic buttons ---------- */
if(!RM && !matchMedia('(pointer:coarse)').matches){
  document.querySelectorAll('.mag').forEach(b=>{
    b.addEventListener('mousemove',e=>{const r=b.getBoundingClientRect();b.style.transform=`translate(${(e.clientX-r.left-r.width/2)*.25}px,${(e.clientY-r.top-r.height/2)*.3}px)`;});
    b.addEventListener('mouseleave',()=>b.style.transform='');
  });
}

/* ---------- nav + progress + reveal ---------- */
const nav=document.getElementById('nav'),prog=document.getElementById('progress');
const navToggle=document.getElementById('navToggle'),navLinks=document.getElementById('navLinks');
function setMenu(open){nav.classList.toggle('menu-open',open);navToggle.setAttribute('aria-expanded',String(open));navToggle.setAttribute('aria-label',open?'Close navigation':'Open navigation');}
navToggle.addEventListener('click',()=>setMenu(!nav.classList.contains('menu-open')));
navLinks.addEventListener('click',e=>{if(e.target.closest('a'))setMenu(false);});
document.addEventListener('click',e=>{if(nav.classList.contains('menu-open')&&!nav.contains(e.target))setMenu(false);});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&nav.classList.contains('menu-open')){setMenu(false);navToggle.focus();}});
function onScroll(){ nav.classList.toggle('scrolled',scrollY>20);
  const h=document.documentElement.scrollHeight-innerHeight; prog.style.width=(h>0?scrollY/h*100:0)+'%'; }
let scrollTick=false;
addEventListener('scroll',()=>{if(scrollTick)return;scrollTick=true;requestAnimationFrame(()=>{onScroll();scrollTick=false;});},{passive:true});onScroll();
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('seen');io.unobserve(e.target);}}),{threshold:.12});
document.querySelectorAll('[data-reveal]').forEach(el=>io.observe(el));
addEventListener('load',()=>document.getElementById('herorev').classList.add('reveal'));
document.getElementById('herorev').classList.add('reveal');
