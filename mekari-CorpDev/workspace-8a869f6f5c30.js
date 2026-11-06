'use strict';
const D=snapshot, view=document.querySelector('#view'),modal=document.querySelector('#detail');
const pages={brief:['◈','Decision brief'],pipeline:['▤','Research pipeline'],atlas:['⌖','Regional atlas'],compare:['⇆','Compare companies'],queue:['☷','Diligence queue'],competitors:['▦','Competitors'],benchmarks:['◎','Global benchmarks'],signals:['◷','News & updates'],markets:['◫','Policy & economy'],strategy:['◇','Mekari strategy'],channels:['⇄','Partner channels'],coverage:['◌','Coverage desk'],saved:['☆','My watchlist']};
const pillars={P1:'Strategic partnerships',P2:'Operational capabilities',P3:'Regional expansion',P4:'AI & workflow',C0:'Ecosystem monitor'};
const countries={Indonesia:'id',Singapore:'sg',Malaysia:'my',Thailand:'th',Vietnam:'vn',Philippines:'ph',Cambodia:'kh',Laos:'la',Myanmar:'mm','South Korea':'kr'};
const clean=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const key=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
const list=x=>Array.isArray(x)?x:[x].filter(Boolean);
const cmp=(a,b)=>a.name.localeCompare(b.name);
const all=D.companies, acq=all.filter(x=>x.potential_acquisition_research),focused=x=>x.strategic_fit?.startsWith('Focused');
const events=[...D.events].sort((a,b)=>date(b).localeCompare(date(a)));
function date(x){return /^\d{4}-\d{2}-\d{2}/.exec(x.publication_date||'')?.[0]||''}
function links(urls){return [...new Set(list(urls))].filter(x=>/^https?:\/\//.test(x)).map(x=>`<p><a target="_blank" rel="noopener" href="${clean(x)}">${clean(new URL(x).hostname)} ↗</a></p>`).join('')}
function flag(s){return Object.entries(countries).filter(([n])=>String(s).includes(n)).map(([,code])=>`<img class="flag" alt="" src="assets/flags/${code}.png">`).join('')}
function mark(x){let alias={'fileAI / formerly bluesheets':'fileai','Sprout Solutions':'sprout','Gani AI':'gani','ASUENE Inc.':'asuene'}[x.name];let slug=[alias,key(x.name),key(x.id?.replace(/^benchmark-|^p[1-4]-/g,''))].find(v=>D.logos.includes(v));return slug?`<span class="mark"><img alt="" src="assets/logos/${slug}.png"></span>`:''}
const pool=[...all,...D.peers,...D.benchmarks,...D.banks],getId=x=>pool.indexOf(x);
let watch;try{watch=JSON.parse(localStorage.getItem('mekari-watch-v1')||'[]')}catch{watch=[]}if(!Array.isArray(watch))watch=[];
const identity=x=>`<button class="identity" data-company="${getId(x)}">${mark(x)}${clean(x.name)}</button>`;
const link=(page,params={})=>'#'+page+(Object.keys(params).length?'?'+new URLSearchParams(params):'');
function route(){let [page,q]=(location.hash.slice(1)||'brief').split('?');return {page:pages[page]?page:'brief',p:new URLSearchParams(q)}}
function band(k,h,t){return `<div class="heading"><span class="eyebrow">${k}</span><h1>${h}</h1><p>${t}</p></div>`}
function eventRow(e){return `<div class="ev"><small>${clean(date(e)||'Date unconfirmed')} · ${clean(e.type||e.event_type||'Update')}</small><div><button data-event="${events.indexOf(e)}"><strong>${clean(e.company)}</strong> ↗</button></div><p class="compact">${clean(e.summary||e.reported_facts)}</p></div>`}
function brief(){
const stats=[[all.length,'Companies monitored','pipeline'],[acq.length,'Mapped competitors','pipeline?scope=Acquisition'],[all.filter(focused).length,'Financing profiles','pipeline?scope=Focused'],[events.length,'Selected developments','signals']];
const markets=D.markets.map(x=>x.country);
return `<div class="hero"><span class="eyebrow">Corporate development · Southeast Asia</span><h1>Decision brief</h1><p>Where should Mekari partner, acquire or enter a new market?</p></div><div class="stats">${stats.map(([v,t,path])=>`<button class="stat" data-route="${path}"><b>${v}</b><span>${t} →</span></button>`).join('')}</div>
${briefMap()}${briefWorkbench()}${peerWatch()}<div class="grid"><section class="panel"><small>Thesis coverage</small><h2>Where the research sits</h2>${Object.entries(pillars).map(([k,v])=>{let n=all.filter(x=>x.primary_thesis_pillar===k).length;return `<button class="lane" data-route="pipeline?pillar=${k}"><span class="row"><span>${v}</span><strong>${n}</strong></span><div class="bar"><i style="width:${100*n/all.length}%"></i></div></button>`}).join('')}<p class="compact">Company counts by primary thesis. Seller interest is unverified.</p></section><section class="panel"><small>Evidence feed</small><h2>Latest developments</h2>${events.filter(e=>e.type!=='Economic release').slice(0,2).map(eventRow).join('')}<a href="#signals">All updates →</a></section></div>
<section class="panel"><small>Regional sourcing</small><h2>Which markets cover each thesis?</h2><div class="tablebox"><table class="heat"><thead><tr><th>Research market</th>${Object.keys(pillars).slice(0,4).map(k=>`<th>${pillars[k]}</th>`).join('')}</tr></thead><tbody>${markets.map(m=>`<tr><th>${flag(m)}${m}</th>${Object.keys(pillars).slice(0,4).map(k=>{let n=all.filter(x=>x.research_country?.includes(m)&&x.primary_thesis_pillar===k).length;return `<td><button style="background:rgba(119,81,204,${Math.min(.38,.04+n/100)})" data-route="pipeline?market=${m}&pillar=${k}" aria-label="${m}, ${pillars[k]}, ${n} companies">${n}</button></td>`}).join('')}</tr>`).join('')}</tbody></table></div><p class="compact">Select a cell to explore companies. Cross-border records can appear in multiple markets.</p></section><section class="section"><small>Research desk</small><h2>Companies to examine</h2><div class="cards">${['MileApp','Bukku','Hukumonline'].map(n=>all.find(x=>x.name===n)).filter(Boolean).map(x=>`<div class="card">${identity(x)}<p>${clean(x.product_summary)}</p><span class="pill">${pillars[x.primary_thesis_pillar]}</span></div>`).join('')}</div></section>`}
function select(k,title,values,p){return `<label>${title}<select data-filter="${k}"><option value="">All</option>${values.map(([v,t])=>`<option value="${clean(v)}" ${p.get(k)===v?'selected':''}>${clean(t)}</option>`).join('')}</select></label>`}
function pageSlice(rows,p){const max=Math.max(1,Math.ceil(rows.length/20)),page=Math.max(1,Math.min(max,Number(p.get('page'))||1));return {items:rows.slice((page-1)*20,page*20),pager:`<div class="row pagination"><span>${rows.length} records · Page ${page} of ${max}</span><span><button data-page="${page-1}" ${page===1?'disabled':''}>Previous</button> <button data-page="${page+1}" ${page===max?'disabled':''}>Next</button></span></div>`}}
function directory(page,p){let rows=page==='benchmarks'?D.benchmarks:page==='competitors'?[...all.filter(x=>x.primary_thesis_pillar==='C0'),...D.peers]:page==='saved'?pool.filter(x=>watch.includes(x.website||x.id)):all;
const q=p.get('q')?.toLowerCase()||'',scope=p.get('scope'),bench=page==='benchmarks';
const area=x=>x.research_country||x.continent||x.benchmark_market||'';
const options=bench?[...new Set(rows.map(area).filter(Boolean))].sort():Object.keys(countries);
rows=rows.filter(x=>(!p.get('coverage')||profileEvidence(x).label===p.get('coverage'))&&meetsEvidenceFilter(x,p.get('evidence'))&&(!p.get('market')||area(x).includes(p.get('market')))&&(!p.get('pillar')||x.primary_thesis_pillar===p.get('pillar'))&&(!scope||(scope==='Strategy'?Boolean(D.alignment.screens[x.id]):scope==='Focused'?focused(x):scope==='Acquisition'?x.potential_acquisition_research:x.recommended_mode?.toLowerCase().includes('partner')&&!x.potential_acquisition_research))&&[x.name,x.product_summary,...list(x.category),area(x),x.candidate_thesis].join(' ').toLowerCase().includes(q)).sort((a,b)=>Number(!!focused(b))-Number(!!focused(a))||cmp(a,b));
let {items,pager}=pageSlice(rows,p);
return band('Company intelligence',pages[page][1],{pipeline:'Screen companies by thesis, market and research priority.',competitors:'Track ecosystem operators and their relationship to Mekari products.',benchmarks:'Study how other platforms distribute, localize and integrate software.',saved:'Companies you have saved in this browser.'}[page])+`<div class="filters"><label>Company or workflow<input data-filter="q" value="${clean(p.get('q')||'')}" placeholder="Search companies, payroll, field service…"></label>${select('market',bench?'Region':'Research market',options.map(v=>[v,v]),p)}${page==='pipeline'?select('pillar','Thesis',Object.entries(pillars),p)+select('scope','Research focus',[['Focused','Financing profiles'],['Acquisition','Mapped competitors'],['Partnership','Partnership research']],p)+select('evidence','Evidence available',[['funding','Sourced financing'],['news','Reviewed developments'],['people','Sourced leadership'],['uncovered','News research gap']],p)+select('coverage','Profile coverage',['Enriched','Partial','Basic'].map(v=>[v,v]),p):''}<button data-reset>Reset</button></div>${pager}<div class="tablebox"><table><thead><tr><th>Company</th><th>Market</th><th>${bench?'Lesson for Mekari':'Capability'}</th><th>${bench?'Source':'Research lens'}</th></tr></thead><tbody>${items.map(x=>`<tr><td>${identity(x)}${websiteLink(x,true)}</td><td>${flag(area(x))}${clean(area(x)||'Unspecified')}</td><td>${clean(bench?x.candidate_thesis:list(x.category).join(' · ')||x.product_summary)}</td><td>${bench?links([x.website]):clean(D.alignment.screens[x.id]?.action||pillars[x.primary_thesis_pillar]||x.role||'Monitor')}</td></tr>`).join('')}</tbody></table>${items.length?'':'<p class="empty">No matching companies.</p>'}</div>`}
function signals(p){const types=[...new Set(events.map(x=>x.type||x.event_type).filter(Boolean))].sort(),rows=events.filter(x=>(!p.get('type')||(x.type||x.event_type)===p.get('type'))&&[x.company,x.summary||x.reported_facts].join(' ').toLowerCase().includes((p.get('q')||'').toLowerCase()));
let {items,pager}=pageSlice(rows,p);return band('Monitoring','News & updates','Selected developments, with the reported facts, source and implications for Mekari.')+`<div class="filters"><label>Find news<input data-filter="q" value="${clean(p.get('q')||'')}" placeholder="Company or keyword"></label>${select('type','Event type',types.map(v=>[v,v]),p)}<button data-reset>Reset</button></div>${pager}<div class="panel">${items.map(eventRow).join('')||'No matching updates.'}</div>`}
function markets(){return band('Market entry','Policy & economy','Assess regulatory demand, local product requirements and the evidence behind each market.')+macroPulse()+rateTrend()+`<h2>Policy triggers</h2><div class="cards">${D.policy.map(x=>`<div class="card"><small>${flag(x.country)}${clean(x.country)}</small><h3>${clean(x.topic)}</h3><p>${clean(x.scope)}</p><div class="compact"><strong>Mekari implication</strong><p>${clean(x.implication)}</p><p>Effective · ${clean(x.effective_date)}</p></div>${links(x.source_url)}</div>`).join('')}</div><section class="section"><h2>Economic & adoption sources</h2><div class="cards">${D.economy.map(x=>`<div class="card"><h3>${clean(x.source)}</h3><p>${clean(x.use)}</p><small>${clean(x.status)}</small>${links(x.url)}</div>`).join('')}</div></section><section class="section"><h2>Market entry tests</h2><div class="cards">${D.markets.map(x=>`<div class="card"><h3>${flag(x.country)}${clean(x.country)}</h3><p>${clean(x.qualification_tests)}</p><a href="${link('pipeline',{market:x.country})}">Explore companies →</a></div>`).join('')}</div></section>`}
function field(title,t){return t?`<h3>${title}</h3><p>${clean(t)}</p>`:''}
function show(html){modal.querySelector('article').innerHTML=html;if(!modal.open)modal.showModal();modal.scrollTop=0}
function peerWatch(mode='capital'){
  const tracks={capital:['Capital moves',e=>/acquisition|m&a|investment|funding|carve.out/i.test(e.type||e.event_type)],product:['Product updates',e=>/product|launch|partnership/i.test(e.type||e.event_type)],policy:['Policy & economy',e=>/regulat|policy|economic release/i.test(e.type||e.event_type)]};
  const items=events.filter(tracks[mode][1]).slice(0,3);
  return `<section id="peer-watch" class="section panel"><small>Global watch</small><h2>What Mekari can learn from recent moves</h2><div class="profile-tabs">${Object.entries(tracks).map(([k,[title]])=>`<button data-watch-mode="${k}" aria-pressed="${mode===k}">${title}</button>`).join('')}</div><div class="watch-stories">${items.map(e=>`<section>${eventRow(e)}<small>Mekari implication</small><p>${clean(e.mekari_implication||e.mekari_lesson||'Review the event evidence.')}</p><button data-event="${events.indexOf(e)}">Open evidence →</button></section>`).join('')}</div></section>`;
}
function render(){const {page,p}=route();document.querySelector('#menu').textContent=pages[page][1]+' ☰';document.querySelector('#nav').innerHTML=Object.entries(pages).map(([id,[ico,name]])=>`${({brief:'Decision desk',pipeline:'Deal sourcing',competitors:'Intelligence',strategy:'Mandate'})[id]?'<div class="navgroup">'+({brief:'Decision desk',pipeline:'Deal sourcing',competitors:'Intelligence',strategy:'Mandate'})[id]+'</div>':''}<a href="#${id}" class="${page===id?'active':''}" ${page===id?'aria-current="page"':''}><i aria-hidden="true">${ico}</i>${name}</a>`).join('');view.innerHTML=page==='brief'?brief():page==='atlas'?atlas(p):page==='queue'?queue(p):page==='compare'?compareView() :page==='competitors'?competitors(p):page==='markets'?markets():page==='signals'?signals(p):page==='coverage'?coverageDesk():page==='channels'?channels():page==='strategy'?strategy():directory(page,p)}
function change(k,v){let {page,p}=route();if(k!=='page')p.delete('page');v?p.set(k,v):p.delete(k);history.replaceState(null,'',link(page,Object.fromEntries(p)));render()}
view.addEventListener('change',e=>{if(e.target.matches('select[data-filter]'))change(e.target.dataset.filter,e.target.value)});
let filterTimer;
view.addEventListener('input',e=>{if(!e.target.matches('input[data-filter]')||e.target.type==='date')return;clearTimeout(filterTimer);const k=e.target.dataset.filter,value=e.target.value,pos=e.target.selectionStart;filterTimer=setTimeout(()=>{change(k,value);const el=view.querySelector('input[data-filter="'+k+'"]');if(el){el.focus();el.setSelectionRange(pos,pos)}},220)});
view.addEventListener('change',e=>{if(e.target.matches('input[type=date][data-filter]'))change(e.target.dataset.filter,e.target.value)});
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;let d=b.dataset;if(d.route)location.hash=d.route;if('reset' in d){history.replaceState(null,'','#'+route().page);render()}if(d.page)change('page',d.page);if(d.company!==undefined)company(+d.company);if(d.event!==undefined){const x=events[+d.event];show(`<small>${clean(date(x)||'Date unconfirmed')} · ${clean(x.type||x.event_type)}</small><h2>${clean(x.company)}</h2>${field('Reported development',x.summary||x.reported_facts)}${field('Event or observation date',x.event_date)}${field('Status',x.status)}${field('Implication for Mekari',x.mekari_implication||x.mekari_lesson)}${field('Next check',x.next_research_action)}${links(x.source_url||x.source_urls)}`)}if(d.note!==undefined){let i=+d.note;const form=modal.querySelector('.research-note');const state={stage:form.querySelector('select').value,note:form.querySelector('textarea').value,review:form.querySelector('input').value};try{localStorage.setItem(noteKey(pool[i]),JSON.stringify(state));company(i,'diligence');if(route().page==='queue')render();modal.querySelector('.research-note').open=true;modal.querySelector('.note-status').textContent='Saved in this browser.'}catch{modal.querySelector('.note-status').textContent='Storage unavailable in this browser.'}}if(d.save!==undefined){let i=+d.save,k=pool[i].website||pool[i].id;watch=watch.includes(k)?watch.filter(v=>v!==k):[...watch,k];try{localStorage.setItem('mekari-watch-v1',JSON.stringify(watch))}catch{}company(i,currentTab);if(['saved','queue'].includes(route().page))render()}});
window.addEventListener('hashchange',()=>{modal.close();document.querySelector('aside').classList.remove('expanded');document.querySelector('#menu').setAttribute('aria-expanded','false');render();window.scrollTo(0,0)});

function channels(){return band('Partner research','Bank distribution channels','Examine distribution rights, commercial terms and the next question for each bank.')+`<div class="cards">${D.banks.map(x=>`<section class="card"><small>${clean(x.research_markets.join(' · '))}</small><h3>${mark(x)} ${clean(x.name)}</h3><p>${clean(x.public_evidence)}</p><strong>Next check</strong><p>${clean(x.next_research_action)}</p>${links(x.source_urls)}</section>`).join('')}</div>`}
function related(x){let names=[x.name,x.name.split(' / ')[0]].map(key);let matches=events.filter(e=>e.company.split(/\s+\/\s+/).some(a=>names.includes(key(a))));return matches.length?'<h3>Linked developments</h3>'+matches.map(eventRow).join(''):''}
function noteKey(x){return 'mekari-diligence-v1:'+x.id}
function researchNote(i){let note={};try{note=JSON.parse(localStorage.getItem(noteKey(pool[i]))||'{}')}catch{}return `<details class="research-note"><summary>My diligence tracker</summary><label>Research stage<select>${['Monitoring','Screening','Diligence','On hold','Archived'].map(v=>`<option ${note.stage===v?'selected':''}>${v}</option>`).join('')}</select></label><label>Next review<input type="date" value="${clean(note.review||'')}"></label><label>Analyst note<textarea rows="3">${clean(note.note||'')}</textarea></label><button data-note="${i}">Save research note</button> <span class="note-status" role="status"></span></details>`}
function macroPulse(){return `<div class="cards macro">${[['Indonesia','Headline inflation','3.23%','October · year over year','id-cpi-oct26'],['Indonesia','Policy rate','5.75%','21 October · unchanged','id-bi-rate-oct26'],['Vietnam','New or returning businesses','243.6k+','Jan–Oct · down 4.8% YoY','vn-enterprises-oct'],['Philippines','Real GDP growth','2.3%','Q2 · August release, YoY','ph-q2-gdp'],['Thailand','Policy rate','1.00%','28 October · unchanged','th-policy-oct26'],['Malaysia','Real GDP growth','5.3%','Q3 · advance estimate, YoY','my-gdp-q326'],['Singapore','Real GDP growth','5.4%','Q3 · advance estimate, YoY','sg-gdp-q326']].map(([country,title,value,period,id])=>`<button class="stat" data-event="${events.findIndex(e=>e.id===id)}"><small>${flag(country)}${country}</small><h3>${title}</h3><b>${value}</b><span>${period} ↗</span></button>`).join('')}</div>`}
function coverageDesk(){
const f=typeof feeds==='undefined'?{checked:'Pending',rows:[]}:feeds;
const leads=f.rows.flatMap(x=>x.leads.map(l=>({...l,publisher:x.publisher}))).sort((a,b)=>b.date.localeCompare(a.date));
return band('Evidence operations','Coverage desk','Publication feeds are matched locally. A headline enters the decision brief only after source review.')+`<div class="stats"><div class="stat"><b>${all.length}</b>Company profiles</div><div class="stat"><b>${D.benchmarks.length}</b>Global benchmarks</div><div class="stat"><b>${events.length}</b>Reviewed records*</div><div class="stat"><b>${f.rows.filter(x=>x.status==='Checked').length}/${f.rows.length}</b>Feeds accessible</div></div><p class="compact">*Includes historical case evidence and dated company announcements. Company-by-month archives are incomplete.</p>${profileCoverage()}<section class="section"><h2>Publisher checks</h2><p>Last run · ${clean(f.checked)}. Feeds expose a recent window. A missing match does not establish inactivity.</p><div class="tablebox"><table><tr><th>Publisher</th><th>Result</th><th>Items scanned</th><th>Last success</th></tr>${f.rows.map(x=>`<tr><td><a href="${clean(x.url)}" target="_blank" rel="noopener">${clean(x.publisher)} ↗</a></td><td>${clean(x.status)}</td><td>${x.items}</td><td>${clean(x.last_success||'—')}</td></tr>`).join('')}</table></div></section>${leads.length?`<section class="section"><h2>Headlines awaiting review</h2><div class="cards">${leads.map(x=>`<div class="card"><small>${clean(x.date)} · ${clean(x.publisher)}</small><h3>${clean(x.title)}</h3><p>Possible entity · ${clean(x.matched.join(', '))}</p>${links(x.url)}</div>`).join('')}</div></section>`:''}`}
function strategy(){return band('2027–2029 mandate','Mekari strategy','Complete the back office, extend it across Southeast Asia and connect workflows with AI.')+`<section class="panel"><small>Product baseline</small><h2>What Mekari already runs</h2><div class="products">${[['talenta','People & payroll'],['jurnal','Accounting & inventory'],['klikpajak','Tax & compliance'],['qontak','Customer operations'],['mekarisign','Documents'],['officeless','Workflow execution']].map(([img,title])=>`<div><img src="assets/logos/${img}.png" alt="${img}"><p>${title}</p></div>`).join('')}</div></section><section class="section"><h2>Corporate development mandate</h2><div class="cards">${D.mandate.map(x=>`<div class="card"><small>${clean(x.id)} · ${clean(x.default_mode)}</small><h3>${clean(x.name)}</h3><p>${clean(x.workflows.join(' · '))}</p><a href="${link('pipeline',{pillar:x.id})}">Screen companies →</a></div>`).join('')}</div></section><section class="section"><h2>Capabilities to test before buying</h2><div class="cards">${D.capabilities.map(x=>`<div class="card"><small>Build, partner or acquire</small><h3>${clean(x.theme)}</h3><p>${clean(x.public_evidence)}</p><strong>Diligence test</strong><p>${clean(x.next_test)}</p>${links(x.source_url)}</div>`).join('')}</div></section>`}
function rateTrend(){const values=[4.75,4.75,4.75,5.25,5.5,5.75,5.75,5.75,5.75,5.75],labels=['19 Feb','17 Mar','22 Apr','20 May','9 Jun','18 Jun','22 Jul','19 Aug','23 Sep','21 Oct'];return `<section class="panel trend"><small>${flag('Indonesia')} Monetary policy · 2026</small><h2>Policy rate at each decision</h2><div class="rate-chart">${values.map((v,i)=>`<div><b>${v.toFixed(2)}%</b><i style="height:${v*16}px"></i><small>${labels[i]}</small></div>`).join('')}</div><p>Higher funding costs can affect SME bank-channel economics. Check partner lending appetite and referral conversion.</p><a href="https://www.bi.go.id/id/statistik/indikator/bi-rate.aspx" target="_blank" rel="noopener">Bank Indonesia decisions ↗</a></section>`}

let currentTab='overview';
function localRead(key, fallback){
  try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}
}
let basket=localRead('mekari-compare-v1',[]);
if(!Array.isArray(basket))basket=[];
const recordId=x=>x.website||x.id;
const members=()=>basket.map(id=>pool.find(x=>recordId(x)===id)).filter(Boolean);
function persistBasket(){try{localStorage.setItem('mekari-compare-v1',JSON.stringify(basket))}catch{}}
function jump(page){modal.close();if(route().page===page)render();else location.hash=page}
function thesis(x){
  const t=x.candidate_thesis||x.mekari_fit_hypothesis||x.learning_test||'';
  return t.replace(/^(Research hypothesis|Analyst hypothesis|Analyst research lesson):\s*/i,'').replace(/^Analyst screen of [^:]+:\s*/,'')
}
function websiteLink(x,compact=false){
  let site;try{site=new URL(x.website)}catch{return ''}
  if(!['https:','http:'].includes(site.protocol))return '';
  return `<a class="site-link ${compact?'site-inline':''}" href="${clean(site.href)}" target="_blank" rel="noopener noreferrer" aria-label="Visit ${clean(x.name)} website (opens in new tab)">${compact?clean(site.hostname.replace(/^www\./,'')):'Visit company website'} ↗</a>`;
}
function evidenceUrls(x){return [...new Set([x.website,...list(x.source_urls),x.ownership_source_url,...(x.findings||[]).map(f=>f.url)].filter(Boolean))]}
function peerSet(x){
  const cats=new Set(list(x.category)), products=new Set(String(x.mekari_connection||'').toLowerCase().split(/[,;/]/).map(v=>v.trim()).filter(Boolean));
  return all.filter(y=>y!==x&&y.primary_thesis_pillar===x.primary_thesis_pillar).map(y=>{
    const shared=list(y.category).filter(c=>cats.has(c));
    const sharedProducts=String(y.mekari_connection||'').toLowerCase().split(/[,;/]/).map(v=>v.trim()).filter(v=>v&&products.has(v));
    return {y,shared,score:shared.length*3+sharedProducts.length*2+(x.research_country===y.research_country?1:0)};
  }).filter(v=>v.score>1).sort((a,b)=>b.score-a.score||cmp(a.y,b.y)).slice(0,3);
}
const linkedEvents = new WeakMap();
function companyEvents(company){
  if(!linkedEvents.has(company)){
    const names=[company.name,company.name.split(' / ')[0],...list(company.aliases)].map(key);
    const matched=events.filter(event=>event.company_id===company.id || String(event.company||'').split(/\s+\/\s+/).some(n=>names.includes(key(n))));
    linkedEvents.set(company,matched);
  }
  return linkedEvents.get(company);
}
function meetsEvidenceFilter(company, filter){
  if(!filter) return true;
  const funding=Boolean(company.profile?.funding?.length || companyEvents(company).some(e=>/fund|growth investment/i.test(e.type||e.event_type||'')));
  const news=companyEvents(company).length>0;
  return {funding,news,people:Boolean(company.profile?.leadership?.length),uncovered:!news&&!company.publisher_mentions?.length}[filter]??true;
}
const coverageMemo = new WeakMap();
function profileEvidence(company){
  if(coverageMemo.has(company))return coverageMemo.get(company);
  const p=company.profile||{};
  const dimensions=[
    ['Description',Boolean((p.description||company.product_summary)&&!/(recorded company website|requires further verification|research pending|discovery lead)/i.test(p.description||company.product_summary))],
    ['Product detail',Boolean(p.products?.length||company.publisher?.products?.length)],
    ['Leadership',Boolean(p.leadership?.length)],
    ['Capital history',Boolean(p.funding?.length||companyEvents(company).some(e=>/fund|investment|acquisition/i.test(e.type||e.event_type||'')))],
    ['Dated updates',companyEvents(company).length>0],
    ['Legal identity',Boolean(company.legal_entity&&!/unknown|unverified|to confirm/i.test(company.legal_entity))]
  ];
  const filled=dimensions.filter(([,present])=>present).length;
  const result={dimensions,filled,label:filled>=4?'Enriched':filled>=2?'Partial':'Basic',missing:dimensions.filter(([,present])=>!present).map(([name])=>name)};
  coverageMemo.set(company,result);return result;
}
function profileSource(url,label='Source'){return /^https?:\/\//.test(url||'')?`<a class="source-link" href="${clean(url)}" target="_blank" rel="noopener">${clean(label)} ↗</a>`:''}
function productCards(x){
  const detailed=x.profile?.products||[],navigation=x.publisher?.products||[];
  if(detailed.length)return detailed.map(p=>`<div class="product-tile"><b>${clean(p.name)}</b><p>${clean(p.description)}</p>${profileSource(p.url,'Product source')}</div>`).join('');
  return `<div class="product-tile"><b>Product scope</b><p>${clean(x.product_summary||'Product scope has not yet been verified.')}</p>${profileSource(x.source_urls?.[0]||x.website,'Company source')}</div>${navigation.length?`<div class="product-tile"><b>Explore products & solutions</b><p class="compact">Links discovered on the company website; solution pages may describe use cases as well as products.</p><div class="product-links">${navigation.slice(0,6).map(p=>profileSource(p.url,p.name)).join('')}</div></div>`:''}`;
}
function companyNews(x){
  const reviewed=companyEvents(x),seen=new Set(reviewed.flatMap(e=>list(e.source_url||e.source_urls)));
  const mentions=(x.publisher_mentions||[]).filter(e=>!seen.has(e.url));
  const newsroom=x.publisher?.sections?.news||x.publisher?.sections?.newsroom||x.publisher?.sections?.blog;
  return `<div class="section-heading"><div><small>Company activity</small><h3>News, launches & media coverage</h3></div>${newsroom?profileSource(newsroom,'Official newsroom'):''}</div>${reviewed.length?reviewed.map(e=>`<div class="news-story"><div class="news-date">${clean(date(e)||'Date not confirmed')}<span>${clean(e.type||e.event_type||'Development')}</span></div><div><span class="pill">${clean(e.status||'Source reviewed')}</span><h3>${clean(e.summary||e.reported_facts)}</h3>${e.event_date&&e.event_date!==date(e)?`<p class="compact">Event date · ${clean(e.event_date)}</p>`:''}<p>${clean(e.mekari_implication||e.mekari_lesson||'')}</p><button data-event="${events.indexOf(e)}">Read development →</button> ${profileSource(e.source_url||list(e.source_urls)[0],'Original report')}</div></div>`).join(''):''}${mentions.length?`<section class="section"><h3>From the company newsroom</h3><p class="compact">Dated issuer headlines. Headlines are discovery leads; claims and commercial outcomes still require review. Local-language titles are translated into English where indicated.</p>${mentions.map(e=>`<div class="news-story"><div class="news-date">${clean(e.date)}<span>Issuer headline</span></div><div><h3>${clean(e.title)}</h3>${e.translated?'<p class="compact">English translation of the original headline</p>':''}${profileSource(e.url,'Read announcement')}</div></div>`).join('')}</section>`:''}${!reviewed.length&&!mentions.length?`<div class="research-gap"><b>No dated company update has been captured yet.</b><p>This is a coverage gap, not evidence that the company is inactive.</p>${profileSource(newsroom||x.website,'Check company website')}</div>`:''}`;
}
function fundingPanel(x){
  const capital=x.profile?.funding||[];
  const findings=(x.findings||[]).filter(f=>/fund|capital|investment/i.test(f.kind));
  const updates=companyEvents(x).filter(e=>/fund|financ|investment|acquisition/i.test(e.type||e.event_type||''));
  if(capital.length)return capital.map(f=>`<div class="capital-entry"><small>${clean(f.date)} · ${clean(f.round)}</small><h3>${clean(f.amount)}</h3><b>${clean(f.investors)}</b><p>${clean(f.summary)}</p>${profileSource(f.url,'Funding announcement')}</div>`).join('');
  if(findings.length)return findings.map(f=>`<div class="capital-entry"><small>${clean(f.period||'Date in source')} · ${clean(f.kind)}</small><p>${clean(f.fact)}</p>${profileSource(f.url,'Funding source')}</div>`).join('');
  if(updates.length)return updates.map(e=>`<div class="capital-entry"><small>${clean(e.event_date||date(e))} · ${clean(e.type||e.event_type)}</small><p>${clean(e.summary||e.reported_facts)}</p>${profileSource(e.source_url||list(e.source_urls)[0],'Capital announcement')}</div>`).join('');
  if(x.id==='bizzi')return `<div class="capital-entry"><small>October 2021 · pre-Series A</small><h3>US$3 million</h3><p>Money Forward-led round, with Do Ventures and Qualgro. This disclosed round is not a verified lifetime fundraising total.</p>${profileSource(x.ownership_source_url,'Round announcement')}</div>`;
  return `<div class="research-gap"><b>Funding history not yet verified</b><p>No sourced round is recorded in this profile. Do not infer that the company is bootstrapped or available for sale.</p>${x.ownership_source_url?profileSource(x.ownership_source_url,'Ownership reference'):''}</div>`;
}
function company(i,tab='overview'){
  const x=pool[i];if(!x)return;
  if(tab==='screen')tab='overview';if(tab==='evidence')tab='news';
  currentTab=tab;
  const p=x.profile||{}, saved=watch.includes(recordId(x)),picked=basket.includes(recordId(x)), news=companyEvents(x).length+(x.publisher_mentions?.length||0);
  const tabs=[['overview','Company overview'],['news',`News & updates${news?' · '+news:''}`],['fit','Mekari fit'],['diligence','Diligence']];
  const controls=`<div class="profile-actions">${websiteLink(x)}<button data-save="${i}" aria-pressed="${saved}">${saved?'★ Saved':'☆ Watchlist'}</button><button data-basket="${i}" ${!picked&&basket.length>=3?'disabled':''}>${picked?'Remove comparison':'Compare company'}</button>${basket.length?'<button data-jump="compare">Open comparison ('+basket.length+') →</button>':''}</div>`;
  const leaders=p.leadership||[];
  const overview=`<div class="profile-summary"><section><small>About the business</small><h3>What ${clean(x.name.split(' / ')[0])} does</h3><p>${clean(p.description||x.product_summary||'Company description awaits source review.')}</p>${profileSource(p.source_urls?.[0]||x.source_urls?.[0]||x.website,'Company source')}</section><section class="value-panel"><small>Value proposition</small>${p.value_proposition?`<p>${clean(p.value_proposition)}</p><span class="compact">${clean(p.value_basis)}</span>`:`<p>${clean(x.business_model_scope||'Product positioning has not yet been separately reviewed.')}</p>${profileSource(x.website,'Review company positioning')}`}${p.audience?`<h4>Who it serves</h4><p>${clean(p.audience)}</p>`:''}</section></div><section class="section"><div class="section-heading"><h3>Products & capabilities</h3><span class="compact">Company-described scope</span></div><div class="product-grid">${productCards(x)}</div></section><div class="profile-summary section"><section class="profile-panel"><small>People</small><h3>Leadership</h3>${leaders.length?leaders.map(l=>`<div class="leader"><span class="initials" aria-hidden="true">${clean(l.name.split(' ').slice(0,2).map(n=>n[0]).join(''))}</span><div><b>${clean(l.name)}</b><p>${clean(l.role)}</p><p class="compact">${clean(l.basis)} · checked ${clean(l.checked)}</p>${profileSource(l.url,'Leadership source')}</div></div>`).join(''):`<div class="research-gap"><p>Current leadership has not yet been verified.</p>${profileSource(x.publisher?.sections?.about||x.website,'Company team / about page')}</div>`}</section><section class="profile-panel"><small>Capital history</small><h3>Fundraising & ownership</h3>${fundingPanel(x)}<p class="compact capital-note">Disclosed rounds are not a complete cap table or a lifetime funding total.</p></section></div><details class="profile-sources"><summary>Company identity & sources</summary>${field('Recorded legal operator',x.legal_entity)}${field('Registration / tax identifier',x.registration_or_tax_id)}${field('Operating markets recorded',list(x.operating_markets).join(' · '))}${field('Ownership record',x.ownership_status)}${links([...evidenceUrls(x),...list(p.source_urls)])}</details>`;
  const peers=peerSet(x);
  const reviewedMatches=D.competitorMap.matches.filter(m=>m.company_id===x.id);
  const fit=`${reviewedMatches.length?`<section class="profile-match-links"><h3>Competitive overlap</h3>${reviewedMatches.map(m=>`<button class="overlap ${m.level.toLowerCase()}" data-overlap="${D.competitorMap.matches.indexOf(m)}">Mekari ${clean(m.product)} · ${m.level} →</button>`).join('')}</section>`:''}<div class="decision-box"><small>Analyst research hypothesis</small><h3>${clean(thesis(x)||'Assess capability and customer fit with Mekari.')}</h3></div>${field('Mekari products to compare',x.mekari_connection)}${field('Product overlap to test',x.overlap_risk)}${findingCards(x)}${field('Integration references',typeof x.integrations_vendor_stated==='string'?x.integrations_vendor_stated:JSON.stringify(x.integrations_vendor_stated||x.integration_claims||''))}${peers.length?`<div class="neighbors"><small>Related company screens</small>${peers.map(({y})=>identity(y)).join('')}</div>`:''}`;
  show(`<div class="profile-head"><small>${clean(pillars[x.primary_thesis_pillar]||'Company intelligence')}</small><h2>${mark(x)}${clean(x.name)}</h2><div class="profile-meta"><span>${flag(x.research_country||x.benchmark_market)}${clean(x.research_country||x.benchmark_market||x.continent||'Global')}</span><span>${clean(list(x.category).join(' · ')||x.role||'Research company')}</span></div>${controls}</div><div class="profile-tabs" aria-label="Company profile sections">${tabs.map(([k,t])=>`<button data-profile-tab="${k}" data-record="${i}" aria-pressed="${k===tab}">${t}</button>`).join('')}</div><div class="profile-body">${tab==='overview'?overview+(typeof strategyScreen==='function'?strategyScreen(x):''):tab==='news'?companyNews(x):tab==='fit'?(typeof strategyScreen==='function'?strategyScreen(x):'')+fit:(typeof strategyScreen==='function'?strategyScreen(x):'')+field('Next diligence question',x.next_evidence_needed||list(x.open_questions).join(' '))+researchNote(i)}</div>`);
  if(tab==='diligence'&&modal.querySelector('.research-note'))modal.querySelector('.research-note').open=true;
}

function compareView(){
  const rows=members();
  const dimensions=[['Company description',x=>x.profile?.description||x.product_summary],['Value proposition',x=>x.profile?.value_proposition],['Leadership',x=>(x.profile?.leadership||[]).map(l=>l.name+' — '+l.role).join('; ')],['Funding / capital history',x=>x.profile?.funding?.map(f=>f.date+' · '+f.round+' · '+f.amount).join('; ')||(x.findings||[]).filter(f=>/fund|capital/i.test(f.kind)).map(f=>f.fact).join(' ')],['Checked finding',x=>x.findings?.[0]?.fact],['Source-based diligence test',x=>x.findings?.[0]?.test],['Research market',x=>x.research_country||x.benchmark_market],['Product',x=>x.product_summary],['Mekari connection',x=>x.mekari_connection],['Investment question',thesis],['Overlap with Mekari',x=>x.overlap_risk],['Ownership evidence',x=>x.ownership_status],['Next diligence test',x=>x.next_evidence_needed||x.learning_test]];
  const selector=`<label class="chooser">Add a company<select id="compare-picker" ${rows.length>=3?'disabled':''}><option value="">Choose a company…</option>${pool.filter(x=>x.website&&!basket.includes(recordId(x))).sort(cmp).map(x=>`<option value="${getId(x)}">${clean(x.name)}</option>`).join('')}</select></label>`;
  return band('Investment workbench','Compare companies','Compare up to three companies against the same acquisition questions.')+selector+(rows.length?`<div class="tablebox compare-table"><table><thead><tr><th>Screening criteria</th>${rows.map(x=>`<td>${identity(x)} <button data-basket="${getId(x)}" aria-label="Remove ${clean(x.name)}">×</button>${websiteLink(x,true)}</td>`).join('')}</tr></thead><tbody>${dimensions.map(([label,fn])=>`<tr><th>${label}</th>${rows.map(x=>`<td>${clean(fn(x)||'Not established in this profile')}</td>`).join('')}</tr>`).join('')}<tr><th>Sources</th>${rows.map(x=>`<td>${links(evidenceUrls(x))}</td>`).join('')}</tr></tbody></table></div>`:'<div class="panel"><h2>Start a comparison</h2><p>Select a company above or add one from its profile.</p></div>');
}
function toggleBasket(x){
  const id=recordId(x);
  if(basket.includes(id))basket=basket.filter(v=>v!==id);else if(basket.length<3)basket.push(id);
  persistBasket();
}
function queue(p){
  const rows=pool.map(x=>({x,n:localRead(noteKey(x),{})})).filter(({x,n})=>watch.includes(recordId(x))||n.stage||n.note||n.review).sort((a,b)=>(a.n.review||'9999').localeCompare(b.n.review||'9999')||cmp(a.x,b.x));
  const stage=p.get('stage'),selected=rows.filter(({n})=>!stage||(n.stage||'Monitoring')===stage);
  return band('Research operations','Diligence queue','Saved companies and analyst follow-ups, ordered by review date.')+`<div class="stage-strip">${['Monitoring','Screening','Diligence','On hold','Archived'].map(v=>`<a href="${link('queue',stage===v?{}:{stage:v})}" class="${stage===v?'selected':''}"><small>${v}</small><b>${rows.filter(({n})=>(n.stage||'Monitoring')===v).length}</b></a>`).join('')}</div><div class="tablebox"><table><thead><tr><th>Company</th><th>Stage</th><th>Review date</th><th>Analyst note</th></tr></thead><tbody>${selected.map(({x,n})=>`<tr><td><button class="identity" data-profile-tab="diligence" data-record="${getId(x)}">${mark(x)}${clean(x.name)}</button></td><td>${clean(n.stage||'Monitoring')}</td><td>${clean(n.review||'Unscheduled')}</td><td>${clean(n.note||'—')}</td></tr>`).join('')}</tbody></table>${selected.length?'':'<div class="empty">No companies in this queue yet. <a href="#pipeline?scope=Focused">Open focused research →</a></div>'}</div>`;
}
const atlasAnchors = {mm:[50,92], th:[96,142], la:[128,105], vn:[160,152], kh:[132,174], my:[160,238], sg:[118,277], id:[244,316], ph:[298,166]};

function atlasMap(selected, expanded = false) {
  const iso = countries[selected];
  const names = Object.keys(atlasAnchors);
  const marketName = code => Object.keys(countries).find(name => countries[name] === code);
  const counts = Object.fromEntries(names.map(code => [code, all.filter(x => x.research_country?.includes(marketName(code))).length]));
  const destination = code => link('atlas', {market: marketName(code)});
  const states = Object.entries(D.mapPaths).map(([code, path]) => {
    const state = `<path d="${path}" class="${code === iso ? 'selected' : counts[code] ? 'covered' : ''}"></path>`;
    return counts[code] ? `<a href="${destination(code)}" aria-label="Select ${marketName(code)}, ${counts[code]} companies"><title>${marketName(code)} · ${counts[code]} companies</title>${state}</a>` : state;
  }).join('');
  const labels = names.filter(code => counts[code] && (expanded || code===iso)).map(code => {
    const [x,y] = atlasAnchors[code];
    return `<a href="${destination(code)}" aria-label="Select ${marketName(code)}"><g transform="translate(${x} ${y})" class="map-pin ${iso === code ? 'selected' : ''}"><circle r="${expanded ? 10 : 9}"/><text text-anchor="middle" dy="3.5">${code.toUpperCase()}</text></g></a>`;
  }).join('');
  return `<svg viewBox="0 25 505 378" class="geo-map" role="group" aria-label="Southeast Asia research markets">${states}${labels}</svg>`;
}

function atlas(p) {
  const markets = Object.keys(countries).filter(name => all.some(x => x.research_country?.includes(name)));
  const country = markets.includes(p.get('market')) ? p.get('market') : 'Malaysia';
  const rows = all.filter(x => x.research_country?.includes(country)).sort((a,b) => Number(focused(b)) - Number(focused(a)) || cmp(a,b));
  const screens = rows.filter(focused);
  const proposal = D.alignment.countries[country];
  const nominated = (proposal?.targets||[]).map(id=>rows.find(x=>x.id===id)).filter(Boolean);
  const mode = p.get('list') || (nominated.length?'strategy':screens.length?'focused':'all');
  const onlyFocused = mode==='focused';
  const shortlist = mode==='strategy'?nominated:onlyFocused?screens:rows;
  const market = D.markets.find(x => x.country === country);
  const pipeline = link('pipeline', {market:country});
  const picker = `<label class="country-picker">Market<select id="atlas-market">${markets.map(n => `<option ${country === n ? 'selected' : ''}>${clean(n)}</option>`).join('')}</select></label>`;
  const metric = (value, label) => `<div><strong>${value}</strong><span>${label}</span></div>`;
  const getList = mode => link('atlas', {market:country,list:mode});
  const items = shortlist.slice(0,5).map(x => `<button class="prospect-row" data-company="${getId(x)}"><span class="prospect-brand">${mark(x)||'<span class="brand-initial">'+clean(x.name[0])+'</span>'}</span><span class="prospect-name"><b>${clean(x.name)}</b><span>${clean(list(x.category).slice(0,2).join(' · ')||x.product_summary)}</span></span><span class="prospect-thesis">${clean(pillars[x.primary_thesis_pillar]||'Research')}</span><span aria-hidden="true">→</span></button>`).join('');
  return `<div class="atlas-title"><div><h1>Regional atlas</h1><p>Find companies by market and review the case for entry.</p></div>${picker}</div>
  <div class="market-overview"><section class="market-summary">${proposal?`<small class="market-route-tag">Priority ${proposal.priority} · ${clean(proposal.action)}</small>`:''}<div class="market-identity">${flag(country)}<h2>${clean(country)}</h2></div><div class="market-numbers">${metric(rows.length,'Companies')}${metric(screens.length,'Financing profiles')}</div><a class="market-primary" href="${link('pipeline',{market:country})}">Open ${clean(country)} pipeline <span aria-hidden="true">→</span></a></section>
  <div class="locator-map">${atlasMap(country)}<button data-atlas-expand aria-label="Expand regional map">⛶ <span>Expand map</span></button></div></div>
  <div class="atlas-body"><section class="atlas-companies"><div class="atlas-section-head"><h2>Company shortlist</h2><div class="list-switch">${nominated.length?`<a href="${getList('strategy')}" ${mode==='strategy'?'aria-current="true"':''}>Market examples</a>`:''}<a href="${getList('focused')}" ${onlyFocused?'aria-current="true"':''}>Focused · ${screens.length}</a><a href="${getList('all')}" ${mode==='all'?'aria-current="true"':''}>All · ${rows.length}</a></div></div><div class="prospect-list">${items||'<p>No financing profiles in this market. Choose All to browse the monitored companies.</p>'}</div><a class="market-list-link" href="${pipeline}">Browse all ${rows.length} companies →</a></section>
  <section class="entry-memo"><h2>Market entry</h2>${typeof countryMandate==='function'?countryMandate(country):''}${market?`<h3>What to verify</h3><p>${clean(market.qualification_tests)}</p><details><summary>Next diligence step</summary><p>${clean(market.next_action)}</p>${links(market.policy_sources)}</details>`:'<p>A market-entry assessment is still open for this country.</p>'}<a href="${link('markets',{market:country})}">Policy & economic signals →</a></section></div>`;
}

view.addEventListener('change', e => {
  if (e.target.id === 'atlas-market') location.hash = link('atlas', {market:e.target.value});
});
view.addEventListener('click', e => {
  if (!e.target.closest('[data-atlas-expand]')) return;
  const country = document.querySelector('#atlas-market').value;
  show(`<div class="expanded-atlas"><h2>Regional markets</h2><p>Select a country to view its companies.</p>${atlasMap(country,true)}<small>Boundaries · Natural Earth</small></div>`);
});

function briefWorkbench(){
  return `<div class="workbench">${[['atlas','01','Regional atlas','Explore company coverage and country entry tests'],['compare','02','Company comparison','Compare product depth, overlap and evidence'],['queue','03','Diligence queue','Track stages, next reviews and analyst notes']].map(([id,n,t,sub])=>`<a href="#${id}"><small>${n} / WORKBENCH</small><b>${t} ↗</b><span>${sub}</span></a>`).join('')}</div>`;
}
document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;
  if(b.dataset.profileTab)company(+b.dataset.record,b.dataset.profileTab);
  if(b.dataset.jump)jump(b.dataset.jump);
  if(b.dataset.basket!==undefined){const i=+b.dataset.basket;toggleBasket(pool[i]);if(modal.open)company(i,currentTab);else render()}
});
view.addEventListener('change',e=>{if(e.target.id==='compare-picker'&&e.target.value){toggleBasket(pool[+e.target.value]);render()}});
const workflowLenses=[
 ['people','People & payroll','\\bHR\\b|payroll|attendance|recruit|talent|shift','Talenta'],
 ['finance','Accounting & spend','account|ERP|tax|spend|procure|invoice|finance','Jurnal · Expense · Klikpajak'],
 ['commerce','Customers & commerce','\\bCRM\\b|commerce|\\bPOS\\b|customer|retail|sales','Qontak · Desty · POS'],
 ['operations','Field & supply chain','field|warehouse|logistic|fleet|manufactur|maintenance|supply|asset','Jurnal · Officeless'],
 ['documents','Documents & compliance','document|legal|compliance|signature|regulat|OCR','Sign · Klikpajak'],
 ['automation','AI & automation','\\bAI\\b|workflow|automat|data intelligence|low.code','Airene · Flow · Officeless'],
 ['climate','Carbon & sustainability','carbon|ESG|climate|sustainab','Partnership research'],
 ['learning','Learning & training','learning|training|education|LMS','Talenta · University']
];
function companyLenses(x){const text=list(x.category).join(' ')+' '+(x.product_summary||'')+' '+(x.profile?.description||'');return workflowLenses.filter(([, ,pattern])=>new RegExp(pattern,'i').test(text)).map(([id])=>id)}
function competitiveUniverse(){const seen=new Set();return [...all,...D.peers,...D.benchmarks].filter(x=>{const id=key(x.website?.replace(/^https?:\/\/(www\.)?/,'').replace(/\/$/,'')||x.name);if(seen.has(id))return false;seen.add(id);return true})}
function competitiveRows(p){
  return competitiveUniverse().filter(x=>{
    const matches=D.competitorMap.matches.filter(m=>m.company_id===x.id);
    const markets=[x.research_country,x.benchmark_market,...matches.map(m=>m.market)].join(' ');
    const terms=[x.name,x.product_summary,...list(x.category),...matches.map(m=>m.product+' '+m.workflow)].join(' ');
    return (!p.get('market')||markets.includes(p.get('market')))&&(!p.get('capability')||companyLenses(x).includes(p.get('capability')))&&key(terms).includes(key(p.get('q')));
  });
}
function competitorDirectory(rows,p){const {items,pager}=pageSlice(rows.sort(cmp),p);return pager+`<div class="tablebox"><table><thead><tr><th>Company / website</th><th>Research market</th><th>Product scope</th><th>Mekari overlap to assess</th></tr></thead><tbody>${items.map(x=>`<tr><td>${identity(x)}${websiteLink(x,true)}</td><td>${flag(x.research_country)}${clean(x.research_country||x.benchmark_market||x.continent||'Unspecified')}</td><td>${clean(x.product_summary||list(x.category).join(' · '))}</td><td>${clean(x.mekari_connection||'Mapping pending')}<div class="compact">${clean((x.role||pillars[x.primary_thesis_pillar]||'Ecosystem monitor').replaceAll('_',' '))}</div></td></tr>`).join('')}</tbody></table>${items.length?'':'<p class="empty">No matching companies. Clear a filter to broaden the view.</p>'}</div>`}
function competitorHeatmap(rows,p){
  const markets=Object.keys(countries).filter(m=>rows.some(x=>String(x.research_country||'').includes(m)));
  const max=Math.max(1,...markets.flatMap(m=>workflowLenses.map(([id])=>rows.filter(x=>String(x.research_country||'').includes(m)&&companyLenses(x).includes(id)).length)));
  return `<section class="panel"><div class="section-heading"><div><small>Service landscape</small><h2>Where capabilities overlap</h2></div><span class="pill">Select a cell to inspect companies</span></div><p class="compact">Counts of companies with catalogued product capabilities, grouped by research market. A company can cover several workflows; these counts do not measure market share or competitive strength.</p><div class="tablebox landscape-table"><table><thead><tr><th>Market</th>${workflowLenses.map(([,name,,connection])=>`<th>${name}<span class="matrix-sub">${connection}</span></th>`).join('')}</tr></thead><tbody>${markets.map(m=>`<tr><th>${flag(m)}${m}</th>${workflowLenses.map(([id,name])=>{const n=rows.filter(x=>String(x.research_country||'').includes(m)&&companyLenses(x).includes(id)).length;return `<td><button class="heat-cell" style="--heat:${n/max}" data-market-cell="${m}" data-lens="${id}" ${n?'':'disabled'} aria-label="${m}, ${name}, ${n} catalogued companies">${n||'—'}</button></td>`}).join('')}</tr>`).join('')}</tbody></table></div><div class="heat-legend"><span>Fewer companies</span><i></i><span>More companies</span></div></section><section class="section"><div class="section-heading"><div><small>Comparable workflows</small><h2>Company capability matrix</h2></div><a href="${link('competitors',{...Object.fromEntries(p),view:'directory'})}">All matching companies →</a></div><p class="compact">Filled cells indicate a capability recorded in the company description. A dash means it is not mapped in this dataset, not that the product is absent.</p>${companyCapabilityMatrix(rows)}</section>`;
}
function companyCapabilityMatrix(rows){
  const names=['MISA','FlowAccount','Bizzi','BrioHR','Sprout','Hukumonline','Humanica','MileApp','Prieds','fileAI'];
  const picks=[...rows].sort((a,b)=>{const rank=x=>{let i=names.findIndex(n=>x.name.toLowerCase().includes(n.toLowerCase()));return i<0?100:i};return rank(a)-rank(b)||cmp(a,b)}).slice(0,12);
  return `<div class="tablebox landscape-table"><table><thead><tr><th>Company</th>${workflowLenses.slice(0,6).map(([,n])=>`<th>${n}</th>`).join('')}</tr></thead><tbody>${picks.map(x=>`<tr><td>${identity(x)}${websiteLink(x,true)}</td>${workflowLenses.slice(0,6).map(([id,name])=>`<td>${companyLenses(x).includes(id)?`<button class="capability-present" data-company="${getId(x)}" aria-label="Open ${clean(x.name)} ${name} product profile">● <span>Mapped</span></button>`:'<span class="unmapped" aria-label="Not mapped">—</span>'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function competitorRelationships(p){
  const q=(p.get('q')||'').toLowerCase(),rows=D.relationships.filter(r=>[r.from,r.to,r.relationship].join(' ').toLowerCase().includes(q));
  return `<section class="section"><h2>Documented ecosystem relationships</h2><p class="compact">Acquisitions, integrations and partnerships retain their original relationship type and date. These selected links are not a complete ownership graph.</p><div class="relationship-grid">${rows.map(r=>`<section class="relationship-card"><div class="relationship-path"><b>${clean(r.from)}</b><span aria-hidden="true">→</span><b>${clean(r.to)}</b></div><p>${clean(r.relationship)}</p><small>${clean(r.source_date_or_event_date||'Source undated')} · checked ${clean(r.checked_at)}</small>${profileSource(r.source_url,'Relationship source')}</section>`).join('')}</div>${rows.length?'':'<div class="empty">No documented relationship matches this search.</div>'}</section>`;
}
function mappedCompetitors(p) {
  const {matches, products} = D.competitorMap;
  const query = key(p.get('q'));
  const visible = matches.filter(match => {
    const company = pool.find(x => x.id === match.company_id);
    const searchable = [company.name, match.product, match.workflow, products[match.product].workflow, match.market].join(' ');
    return (!p.get('product') || p.get('product') === match.product) && (!p.get('market') || p.get('market') === match.market) && (!query || key(searchable).includes(query));
  });
  const ids = [...new Set(visible.map(m => m.company_id))];
  const columns = Object.keys(products).filter(product => visible.some(m => m.product === product));
  const explain = (match, label) => `<button class="overlap ${match.level.toLowerCase()}" data-overlap="${matches.indexOf(match)}" aria-label="${clean(match.product + ': ' + match.level + ' overlap. ' + match.workflow)}">${label}</button>`;
  const filters = `<div class="match-filters"><label>Company or workflow<input data-filter="q" placeholder="Xero, Paper.id, payroll…" value="${clean(p.get('q')||'')}"></label>${select('product','Mekari product',Object.entries(products).map(([n,x])=>[n,n+' · '+x.workflow]),p)}${select('market','Market scope',[...new Set(matches.map(x=>x.market))].map(x=>[x,x]),p)}<button data-reset>Clear</button></div>`;
  const legend = `<div class="match-legend"><span><i class="core"></i>Core alternative</span><span><i class="partial"></i>Specific workflow</span><span>— No reviewed match</span></div>`;
  const table = `<div class="tablebox overlap-table"><table><thead><tr><th>Company / market</th>${columns.map(n=>`<th title="${clean(products[n].workflow)}">${n}</th>`).join('')}</tr></thead><tbody>${ids.map(id=>{const company=pool.find(x=>x.id===id),records=visible.filter(m=>m.company_id===id);return `<tr><th>${identity(company)}<span class="scope-label">${flag(records[0].market)}${clean(records[0].market)}</span></th>${columns.map(n=>{const m=records.find(x=>x.product===n);return `<td>${m?explain(m,m.level==='Core'?'●':'◐'):'<span class="absent">—</span>'}</td>`}).join('')}</tr>`}).join('')}</tbody></table></div>`;
  const cards = `<div class="overlap-cards">${ids.map(id=>{const company=pool.find(x=>x.id===id),records=visible.filter(m=>m.company_id===id);return `<section><div>${identity(company)}<span class="scope-label">${flag(records[0].market)}${clean(records[0].market)}</span></div>${records.map(m=>`<div class="overlap-mobile-row">${explain(m,clean(m.product)+' · '+m.level)}<p>${clean(m.workflow)}</p></div>`).join('')}</section>`}).join('')}</div>`;
  return filters+`<div class="match-summary"><b>${ids.length} ${ids.length===1?'company':'companies'}</b><span>${visible.length} product comparisons · select a match to see its basis</span></div>`+legend+(ids.length?table+cards:'<div class="empty"><h3>No reviewed match for these filters</h3><button data-reset>Show all comparisons</button></div>')+`<details class="map-method"><summary>How to read the map</summary><p>Core means the products serve the same primary job. Specific workflow means part of the job overlaps. Market scope identifies the market assessed. Global rows use global product evidence. The map records selected comparisons and does not measure customer switching or market share.</p></details>`;
}
function competitors(p) {
  const modes=[['map','Product map'],['directory','Research directory'],['relationships','Relationships'],['updates','Company news']];
  const mode=modes.some(([k])=>k===p.get('view'))?p.get('view'):'map';
  const intro=band('Market intelligence','Competitors','Choose a Mekari product to see which companies overlap and why.');
  const nav=`<div class="experience-tabs" aria-label="Competitor views">${modes.map(([id,label])=>`<a href="${link('competitors',{view:id})}" ${mode===id?'aria-current="page"':''}>${label}</a>`).join('')}</div>`;
  if(mode==='map')return intro+nav+mappedCompetitors(p);
  const search=`<label>Search companies or products<input data-filter="q" value="${clean(p.get('q')||'')}" placeholder="Company or keyword"></label>`;
  if(mode==='relationships')return intro+nav+`<div class="filters">${search}<button data-reset>Clear</button></div>`+competitorRelationships(p);
  const filters=`<div class="filters">${search}${select('market','Research market',Object.keys(countries).map(v=>[v,v]),p)}${select('capability','Research workflow',workflowLenses.map(([id,n])=>[id,n]),p)}<button data-reset>Clear</button></div>`;
  const rows=competitiveRows(p);
  if(mode==='directory')return intro+nav+filters+`<p class="compact">${rows.length} research profiles across prospects, peers and benchmarks. The Product map lists reviewed competitive overlaps.</p>`+competitorDirectory(rows,p);
  const linked=new Set(rows.flatMap(companyEvents)),updates=[...linked].sort((a,b)=>date(b).localeCompare(date(a)));
  const leads=rows.flatMap(x=>(x.publisher_mentions||[]).map(l=>({x,l}))).sort((a,b)=>b.l.date.localeCompare(a.l.date));
  const items=[...updates.map(e=>({d:date(e),e})),...leads.map(({x,l})=>({d:l.date,x,l}))].sort((a,b)=>b.d.localeCompare(a.d));
  const page=pageSlice(items,p);
  return intro+nav+filters+page.pager+`<div class="panel">${page.items.map(({e,x,l})=>e?eventRow(e):`<div class="ev"><small>${clean(l.date)} · Issuer headline awaiting review</small>${identity(x)}<p>${clean(l.title)}</p>${profileSource(l.url,'Announcement')}</div>`).join('')||'<p>No captured updates match these filters.</p>'}</div>`;
}

document.addEventListener('click',e=>{const b=e.target.closest('[data-market-cell]');if(!b)return;const {p}=route();const next=new URLSearchParams(p);next.set('market',b.dataset.marketCell);next.set('capability',b.dataset.lens);next.set('view','directory');next.delete('page');location.hash=link('competitors',Object.fromEntries(next));});

render();
function lookup(query=''){
  const q=query.trim().toLowerCase(),hits=pool.filter(x=>[x.name,x.product_summary,x.research_country].some(s=>s?.toLowerCase().includes(q))).sort((a,b)=>Number(b.name.toLowerCase().startsWith(q))-Number(a.name.toLowerCase().startsWith(q))||cmp(a,b)).slice(0,8);
  const signals=q?events.filter(e=>[e.company,e.summary,e.reported_facts].some(s=>s?.toLowerCase().includes(q))).slice(0,4):[];
  return hits.map(x=>`<button data-company="${getId(x)}"><small>Company · ${clean(x.research_country||x.continent||'Research')}</small>${clean(x.name)}</button>`).join('')+signals.map(e=>`<button data-event="${events.indexOf(e)}"><small>Development · ${clean(date(e))}</small>${clean(e.company)}</button>`).join('')||'<p>No matches. Try a product or market.</p>';
}
function finder(){show('<h2>Search the workspace</h2><input id="lookup" class="lookup" aria-label="Find companies or news" placeholder="Company, product, market or development"><div class="search-list">'+lookup()+'</div>');modal.querySelector('input').focus()}
document.querySelector('#finder').addEventListener('click',finder);
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();finder()}});
modal.addEventListener('input',e=>{if(e.target.id==='lookup')modal.querySelector('.search-list').innerHTML=lookup(e.target.value)});
function briefMap(){
  const names=Object.keys(countries).filter(n=>all.some(x=>x.research_country?.includes(n)));
  return `<section class="brief-atlas"><div class="map-panel"><small>Regional sourcing · Southeast Asia</small><svg viewBox="0 0 505 420" role="group" aria-label="Open market intelligence">${Object.entries(D.mapPaths).map(([iso,path])=>{const n=names.find(c=>countries[c]===iso);return n?`<a href="${link('atlas',{market:n})}" aria-label="Explore ${n}"><path d="${path}"><title>${n}</title></path></a>`:`<path d="${path}"/>`}).join('')}<a href="#atlas?market=Singapore" aria-label="Explore Singapore"><circle cx="118" cy="277" r="5"/></a></svg></div><div class="brief-markets"><small>Origination desk</small><h2>Where to screen next</h2><p>Markets with the most companies flagged for focused research.</p>${names.map(n=>({n,records:all.filter(x=>focused(x)&&x.research_country?.includes(n))})).filter(x=>x.records.length).sort((a,b)=>b.records.length-a.records.length).slice(0,4).map(({n,records})=>`<a href="${link('pipeline',{market:n,scope:'Focused'})}"><span>${flag(n)}${n}</span><b>${records.length} focused →</b></a>`).join('')}<a href="#atlas">Explore all markets →</a></div></section>`;
}
document.querySelector('#menu').addEventListener('click',e=>{const open=document.querySelector('aside').classList.toggle('expanded');e.currentTarget.setAttribute('aria-expanded',String(open))});
function applyTheme(value){document.documentElement.dataset.theme=value;document.querySelector('#theme').textContent=value==='dark'?'☀ Light':'◐ Dark'}
applyTheme(localRead('mekari-theme','light'));
document.querySelector('#theme').addEventListener('click',()=>{const value=document.documentElement.dataset.theme==='dark'?'light':'dark';applyTheme(value);try{localStorage.setItem('mekari-theme',JSON.stringify(value))}catch{}});

document.addEventListener('click',e=>{const button=e.target.closest('[data-watch-mode]');if(button)document.querySelector('#peer-watch').outerHTML=peerWatch(button.dataset.watchMode)});

function findingCards(x){
  return (x.findings||[]).map(f=>`<section class="decision-box"><small>${clean(f.kind)} · Checked ${clean(f.checked)}</small><p>${clean(f.fact)}</p>${f.period?`<p class="compact">Reported period · ${clean(f.period)}</p>`:''}<a href="${clean(f.url)}" target="_blank" rel="noopener">Read underlying source ↗</a>${field('Diligence test',f.test)}</section>`).join('');
}
function profileCoverage(){
  const fields=[['Business description',x=>x.profile?.description||x.product_summary],['Edited value proposition',x=>x.profile?.value_proposition],['Named product / solution links',x=>x.profile?.products?.length||x.publisher?.products?.length],['Sourced leadership',x=>x.profile?.leadership?.length],['Capital record',x=>x.profile?.funding?.length||(x.findings||[]).some(f=>/fund|capital/i.test(f.kind))||companyEvents(x).some(e=>/fund|investment|acquisition/i.test(e.type||e.event_type||''))||x.id==='bizzi'],['Dated news / issuer leads',x=>companyEvents(x).length||x.publisher_mentions?.length]];
  return `<section class="section panel"><small>Research completeness · ${clean(D.asOf)}</small><h2>Field-by-field coverage</h2><p>${all.length} monitored companies. A populated field means a source or research summary is recorded; it does not establish complete funding history, current ownership or seller interest.</p>${fields.map(([title,test])=>{const n=all.filter(test).length;return `<div class="coverage-field"><span>${title}</span><div class="bar"><i style="width:${100*n/all.length}%"></i></div><b>${n} / ${all.length}</b></div>`}).join('')}<p class="compact">News includes separately labelled issuer headline leads. Product links can include solution pages. Unknown fields remain explicit in the company profile.</p><a href="#pipeline?scope=Focused">Inspect focused research →</a></section>`;
}

/* Decision-workspace layer: shared navigation, filters and source-linked drilldowns. */
pages.capital=['↗','Funding & M&A'];
pages.strategy=['◇','Research themes'];
countries.Australia='au';
pages.sources=['▧','Source library'];
const priorBrief=brief, priorDirectory=directory, priorMarkets=markets, priorCoverage=coverageDesk, priorCompany=company;
const checkedDate=D.refreshChecked||D.asOf;
const eventType=e=>e.type||e.event_type||'Update';
const eventDate=e=>date(e)||(/^\d{4}-\d{2}-\d{2}/.exec(e.event_date||'')||[])[0]||'';
const capitalEvent=e=>/funding|investment|acquisition|m&a|carve.out|financing/i.test(eventType(e));
const eventName=e=>e.headline||e.summary||e.reported_facts||e.company;
const issuerByEvent=new WeakMap();
function eventCompany(e){
  if(!issuerByEvent.has(e)) issuerByEvent.set(e,pool.find(x=>x.id===e.company_id)||pool.find(x=>companyEvents(x).includes(e))||null);
  return issuerByEvent.get(e);
}
const eventMarket=e=>e.country||eventCompany(e)?.research_country||eventCompany(e)?.benchmark_market||'';
function sourceHost(e){try{return new URL(list(e.source_url||e.source_urls)[0]).hostname.replace(/^www\./,'')}catch{return 'Source in record'}}
function sectionTitle(k,title,href,label='Explore all'){return `<div class="section-heading"><div><small>${k}</small><h2>${title}</h2></div>${href?`<a href="${href}">${label} →</a>`:''}</div>`}
function tabs(page,items,current,p=new URLSearchParams()){return `<div class="experience-tabs" role="navigation" aria-label="View options">${items.map(([id,title])=>`<a href="${link(page,{...Object.fromEntries(p),view:id,page:1})}" ${current===id?'aria-current="page"':''}>${title}</a>`).join('')}</div>`}
function storyCard(e){const x=eventCompany(e);return `<article class="story-card"><div class="story-meta"><span>${clean(eventDate(e)||'Date not captured')}${!date(e)?' · effective':''}</span><span>${clean(eventType(e))}</span></div><div class="story-company">${x?identity(x):`<b>${clean(e.company)}</b>`}</div><button class="story-title" data-event="${events.indexOf(e)}">${clean(eventName(e))}</button><p>${clean(e.mekari_implication||e.mekari_lesson||'Open the source and assess relevance to the mandate.')}</p><div class="story-bottom"><button data-event="${events.indexOf(e)}">Read & assess →</button><span>${clean(sourceHost(e))}</span></div></article>`}
function filterChips(p){const names={q:'Search',market:'Market',pillar:'Thesis',scope:'Focus',type:'Event',period:'Period',capability:'Workflow',evidence:'Evidence',coverage:'Profile coverage',stage:'Stage',owner:'Owner',due:'Review status',from:'From',to:'To'};return `<div class="filter-chips">${[...p].filter(([k,v])=>names[k]&&v).map(([k,v])=>`<button data-remove-filter="${k}" aria-label="Remove ${names[k]} filter">${names[k]}: ${clean(pillars[v]||v)} <span>×</span></button>`).join('')}</div>`}
function viewTools(p){const saved=localRead('mekari-views-v2',[]).filter(x=>x.page===route().page);return `<div class="view-tools"><div>${filterChips(p)}</div><div class="view-actions"><button data-save-view>☆ Save view</button>${saved.length?`<label class="sr-only" for="saved-view-picker">Open saved view</label><select id="saved-view-picker"><option value="">Saved views (${saved.length})</option>${saved.map((x,i)=>`<option value="${i}">${clean(x.name)}</option>`).join('')}</select>`:''}<button data-copy-view>Copy view link</button></div></div>`}
function eventFilter(p){return `<div class="filter-surface"><div class="filters"><label class="search-field">Search news or company<input data-filter="q" value="${clean(p.get('q')||'')}" placeholder="Company, product, acquisition…"></label>${select('period','Period',[['30','Last 30 days'],['2026','2026 year to date'],['all','All captured history']],p)}${select('market','Market',[...new Set(events.map(eventMarket).filter(Boolean))].sort().map(x=>[x,x]),p)}<button data-reset>Clear all</button></div><details class="more-filters" ${p.get('type')||p.get('from')||p.get('to')?'open':''}><summary>More filters · event type & dates</summary><div class="filters">${select('type','Event type',[...new Set(events.map(eventType))].sort().map(x=>[x,x]),p)}<label>From<input type="date" data-filter="from" value="${clean(p.get('from')||'')}"></label><label>Through<input type="date" data-filter="to" value="${clean(p.get('to')||'')}"></label></div></details>${viewTools(p)}</div>`}
function filteredEvents(p,rows=events){const q=(p.get('q')||'').toLowerCase(),period=p.get('period')||'all';const cutoff=new Date(checkedDate+'T00:00:00Z');cutoff.setUTCDate(cutoff.getUTCDate()-30);return rows.filter(e=>{const d=eventDate(e);return (!p.get('market')||eventMarket(e)===p.get('market'))&&(!p.get('type')||eventType(e)===p.get('type'))&&(!p.get('from')||d>=p.get('from'))&&(!p.get('to')||d<=p.get('to'))&&(period==='all'||period==='2026'&&d.startsWith('2026')&&d<=checkedDate||period==='30'&&d>=cutoff.toISOString().slice(0,10)&&d<=checkedDate)&&[e.company,eventName(e),e.mekari_implication,e.mekari_lesson].join(' ').toLowerCase().includes(q)}).sort((a,b)=>eventDate(b).localeCompare(eventDate(a)))}
function eventTable(rows,p,capital=false){const {items,pager}=pageSlice(rows,p);return `<div class="result-bar"><span><strong>${rows.length}</strong> captured ${capital?'capital events':'developments'} · dates and sources retained</span><button data-export-events="${capital?'capital':'all'}">Export filtered CSV ↓</button></div>${pager}<div class="tablebox event-table"><table><thead><tr><th>Date / company</th><th>${capital?'Capital event':'Development'}</th><th>${capital?'Reported amount':'Evidence / status'}</th><th>Mekari decision lens</th></tr></thead><tbody>${items.map(e=>{const x=eventCompany(e);return `<tr><td><time>${clean(eventDate(e)||'Unconfirmed')}</time>${!date(e)?'<span class="compact">Effective / event date</span>':''}${x?identity(x):`<b>${clean(e.company)}</b>`}<span class="compact">${flag(eventMarket(e))}${clean(eventMarket(e))}</span></td><td><span class="pill">${clean(eventType(e))}</span><button class="text-button" data-event="${events.indexOf(e)}">${clean(eventName(e))}</button></td><td>${capital?`<strong>${clean(e.amount||'See announcement')}</strong><p class="compact">${clean(e.capital_type||eventType(e))}</p>`:`<span class="evidence-label">${clean(e.status||'Source recorded')}</span>`}${profileSource(list(e.source_url||e.source_urls)[0],sourceHost(e))}</td><td><p>${clean(e.mekari_implication||e.mekari_lesson||'Review product, market and ownership fit.')}</p><button data-event="${events.indexOf(e)}">Facts & next action →</button></td></tr>`}).join('')}</tbody></table>${items.length?'':'<div class="empty"><h3>No captured events match these filters.</h3><p>Widen the period or clear a filter. This is not evidence of company inactivity.</p><button data-reset>Clear filters</button></div>'}</div>${pager}`}
signals=function(p){const mode=p.get('view')==='cards'?'cards':'table',rows=filteredEvents(p);return band('Monitoring desk','News & updates','Read the development, understand the implication, then move into company diligence.')+tabs('signals',[['table','News table'],['cards','Story cards']],mode,p)+eventFilter(p)+(mode==='cards'?(()=>{const {items,pager}=pageSlice(rows,p);return pager+`<div class="story-grid">${items.map(storyCard).join('')||'<div class="panel">No captured updates match. Clear a filter or widen the period.</div>'}</div>`+pager})():eventTable(rows,p))+`<p class="data-footnote">Selected reviewed announcements and research records. Issuer headline leads remain separately labelled inside company profiles. Source review does not independently validate company claims.</p>`};
function capitalView(p){const rows=filteredEvents(p,events.filter(capitalEvent));return band('Corporate development','Funding, acquisitions & exits','Follow capital movements and ownership changes without confusing financing raised with the price of an acquisition.')+eventFilter(p)+eventTable(rows,p,true)+`<p class="data-footnote">Disclosed rounds are individual events, not lifetime funding totals. Announcement, approval and completion are distinct statuses.</p>`}
function capitalChart(){const rows=events.filter(e=>capitalEvent(e)&&eventDate(e).startsWith('2026'));const types=[['Funding / investment',e=>!/acquisition|m&a|carve/i.test(eventType(e))],['M&A / carve-out',e=>/acquisition|m&a|carve/i.test(eventType(e))]];const bins=[1,2,3,4].map(q=>types.map(([,fn])=>rows.filter(e=>Math.ceil(Number(eventDate(e).slice(5,7))/3)===q&&fn(e)).length));const max=Math.max(1,...bins.map(x=>x.reduce((a,b)=>a+b,0)));return `<div class="mini-chart" role="img" aria-label="Captured 2026 capital events by quarter: ${bins.map((v,i)=>'Q'+(i+1)+' '+v.reduce((a,b)=>a+b,0)).join(', ')}">${bins.map((values,i)=>`<a href="${link('capital',{from:`2026-${String(i*3+1).padStart(2,'0')}-01`,to:i===3?checkedDate:`2026-${String(i*3+3).padStart(2,'0')}-${i===0||i===3?'31':'30'}`})}"><b>${values.reduce((a,b)=>a+b,0)}</b><div class="chart-column">${values.map((n,j)=>`<span class="series-${j}" style="height:${n/max*120}px" title="${types[j][0]}: ${n}"></span>`).reverse().join('')}</div><span>Q${i+1}${i===3?' to date':''}</span></a>`).join('')}</div><div class="chart-legend"><span><i class="series-0"></i>Funding / investment</span><span><i class="series-1"></i>M&A / carve-out</span></div><p class="compact">Counts in this research set, not total market deal activity. One announcement may contain two separate actions.</p>`}
function decisionBrief(){const p=route().p,selection=p.get('brief')||'all';let rows=filteredEvents(new URLSearchParams({period:p.get('period')||'30'}));if(selection==='capital')rows=rows.filter(capitalEvent);if(selection==='policy')rows=rows.filter(e=>/policy|regulat|economic/i.test(eventType(e)));if(selection==='product')rows=rows.filter(e=>/product|launch|partnership/i.test(eventType(e)));
const news=rows.slice(0,3);return `<div class="brief-title"><div><span class="eyebrow">Mekari · Corporate development</span><h1>Decision brief</h1><p>Complete the back office. Expand regionally. Connect workflows with AI.</p></div><a class="primary-link" href="#pipeline">Explore company profiles →</a></div><div class="brief-status"><span class="status-dot"></span>Source sweep · ${clean(checkedDate)}<span>Independent public-source research</span><a href="#coverage">Research coverage →</a></div><div class="metric-strip">${[[all.length,'Companies monitored','pipeline'],[all.filter(focused).length,'Financing profiles','pipeline?scope=Focused'],[acq.length,'Mapped competitors','pipeline?scope=Acquisition'],[events.filter(capitalEvent).length,'Capital events captured','capital']].map(([n,t,path])=>`<a href="#${path}"><b>${n}</b><span>${t} <i>↗</i></span></a>`).join('')}</div><section class="section">${sectionTitle('What changed','Developments to act on','#signals','All news')}<div class="brief-controls"><div class="segmented">${[['all','All developments'],['capital','Capital moves'],['product','Products & partnerships'],['policy','Policy & economy']].map(([id,n])=>`<button data-brief-mode="${id}" aria-pressed="${selection===id}">${n}</button>`).join('')}</div>${select('period','Window',[['30','Last 30 days'],['2026','2026 year to date'],['all','All captured history']],new URLSearchParams({period:p.get('period')||'30'}))}</div><div class="story-grid">${news.map(storyCard).join('')||'<div class="panel">No captured developments in this window. Open all news or widen the period.</div>'}</div></section><section class="section">${sectionTitle('Research at a glance','Where the opportunity sits','#atlas','Explore markets')}<div class="insight-grid"><section class="panel"><small>Capital activity</small><h3>Transactions in the research set</h3>${capitalChart()}</section><section class="panel"><small>Mandate alignment</small><h3>Companies by primary thesis</h3>${Object.entries(pillars).map(([id,n])=>{let count=all.filter(x=>x.primary_thesis_pillar===id).length;return `<button class="lane" data-route="pipeline?pillar=${id}"><span class="row"><span>${n}</span><b>${count}</b></span><div class="bar"><i style="width:${count/all.length*100}%"></i></div></button>`}).join('')}<p class="compact">Mapped company count; not market share or pipeline conversion.</p></section><section class="panel"><small>Company research</small><h3>Financing profiles by country</h3>${Object.keys(countries).map(n=>({n,count:all.filter(x=>focused(x)&&x.research_country?.includes(n)).length})).filter(x=>x.count).sort((a,b)=>b.count-a.count).slice(0,6).map(({n,count})=>`<a class="market-row" href="${link('pipeline',{market:n,scope:'Focused'})}"><span>${flag(n)}${n}</span><b>${count} →</b></a>`).join('')}<a class="bottom-link" href="#atlas">Open regional atlas →</a></section></div></section>${briefWorkbench()}${learningSection()}<section class="section">${sectionTitle('Operating environment','Policy & entry checkpoints','#markets','All markets')}<div class="checkpoint-grid">${events.filter(e=>/policy|regulat|economic/i.test(eventType(e))).sort((a,b)=>eventDate(b).localeCompare(eventDate(a))).slice(0,3).map(e=>`<article class="checkpoint"><small>${clean(eventDate(e))} · ${clean(e.company)}</small><h3>${clean(e.headline||e.summary||e.reported_facts)}</h3><button data-event="${events.indexOf(e)}">Impact & next check →</button></article>`).join('')}</div></section>`}
brief=decisionBrief;
const caseDefinitions=[{id:'graas-capital-2026',title:'Buy the data layer behind automation',mechanism:'Graas paired financing with Trustana’s product-data capabilities.',application:'Desty + Qontak + Airene',test:'Run an end-to-end catalogue-to-campaign workflow. Compare acquired data rights and quality with a licensed feed.'},{id:'tanda-capital-2026',title:'Local rules can be the product advantage',mechanism:'Tanda combines workforce scheduling, wage rules and payroll.',application:'Talenta regional expansion',test:'Measure payroll exceptions and implementation effort in a target country before assuming the product travels.'},{id:'bipo-capital-2026',title:'Separate software from service delivery',mechanism:'BIPO combines HR software, payroll outsourcing and EOR services.',application:'Talenta + regional distribution',test:'Separate recurring software revenue, service labour, regulatory liability and infrastructure ownership.'},{id:'omnichat-capital-2026',title:'Connect agents to a shared customer record',mechanism:'Omnichat links commerce agents and messaging channels through customer profiles.',application:'Qontak + Airene',test:'Test permissioned identity matching and completed tasks; compare with existing Mekari capabilities.'}];
function caseCard(c){const e=events.find(e=>e.id===c.id);return !e?'':`<article class="case-card"><div class="story-company">${eventCompany(e)?identity(eventCompany(e)):`<b>${clean(e.company)}</b>`}<span class="pill">${clean(eventDate(e))}</span></div><h3>${clean(c.title)}</h3><p>${clean(c.mechanism)}</p><div class="case-application"><small>Mekari application</small><b>${clean(c.application)}</b></div><button data-case="${c.id}">Study the mechanism →</button></article>`}
function learningSection(){return `<section class="section">${sectionTitle('Learn from peers','Patterns worth testing at Mekari','#benchmarks','All benchmarks')}<div class="case-grid">${caseDefinitions.slice(0,3).map(caseCard).join('')}</div></section>`}
function benchmarkView(p){const mode=p.get('view')||'learn';let content;if(mode==='directory')content=priorDirectory('benchmarks',p).replace(/^<div class="heading">.*?<\/div>/s,'');else if(mode==='cases'||mode==='learn')content=`${mode==='learn'?'<div class="learning-intro"><div><small>From observation to action</small><h2>Find a mechanism. Test it in a Mekari workflow.</h2><p>Start with a business problem, then study product, distribution and integration choices from other operators.</p></div><a href="#benchmarks?view=directory">Browse all '+D.benchmarks.length+' benchmarks →</a></div>':''}<div class="case-grid">${caseDefinitions.filter(c=>!p.get('q')||JSON.stringify(c).toLowerCase().includes(p.get('q').toLowerCase())).map(caseCard).join('')}</div>${mode==='learn'?`<section class="section"><h2>Explore by workflow</h2><div class="workflow-links">${[['Payroll','payroll'],['Accounting','accounting'],['AI agents','AI'],['Commerce','commerce'],['Workflow automation','workflow']].map(([label,q])=>`<a href="${link('benchmarks',{view:'directory',q})}">${label} →</a>`).join('')}</div></section>`:''}`;else{const matching=events.filter(e=>D.benchmarks.some(x=>companyEvents(x).includes(e))||caseDefinitions.some(c=>c.id===e.id));content=eventFilter(p)+eventTable(filteredEvents(p,mode==='capital'?matching.filter(capitalEvent):matching),p,mode==='capital')}
return band('Global intelligence','Global benchmarks','Study the evidence, then decide what to build, partner for or acquire.')+tabs('benchmarks',[['learn','Learn from peers'],['updates','Recent developments'],['capital','Capital moves'],['cases','Mekari case studies'],['directory','Company directory']],mode,p)+content}
function policyView(p){const market=p.get('market')||'',rows=D.policy.filter(x=>!market||x.country===market);const updates=events.filter(e=>/policy|regulat|economic/i.test(eventType(e))).filter(e=>!market||eventMarket(e)===market||e.company?.includes(market));return band('Market-entry intelligence','Policy & economic conditions','Connect regulation and SME demand to software distribution, localization and acquisition screening.')+`<div class="country-tabs"><a href="#markets" ${!market?'aria-current="page"':''}>All markets</a>${Object.keys(countries).slice(0,6).map(n=>`<a href="${link('markets',{market:n})}" ${market===n?'aria-current="page"':''}>${flag(n)}${n}</a>`).join('')}</div><section class="section">${sectionTitle('Dated releases','Recent policy & demand signals','#signals?type=Policy','News desk')}<div class="story-grid">${updates.sort((a,b)=>eventDate(b).localeCompare(eventDate(a))).slice(0,3).map(storyCard).join('')||'<p>No captured release matches this country. Review the official resources below.</p>'}</div></section>${!market?macroPulse():''}<section class="section">${sectionTitle('Product demand triggers','Rules that change customer workflows')}<div class="policy-list">${rows.map(x=>`<article><div><small>${flag(x.country)}${clean(x.country)}</small><p class="compact">${clean(x.effective_date)}</p></div><div><h3>${clean(x.topic)}</h3><p>${clean(x.scope)}</p><details><summary>Mekari implication & source</summary><p>${clean(x.implication)}</p>${links(x.source_url)}</details></div><a href="${link('pipeline',{market:x.country})}">Screen local companies →</a></article>`).join('')}</div></section>${!market||market==='Indonesia'?rateTrend():''}<details class="panel section"><summary>Economic data resources & market-entry tests</summary><div class="cards section">${D.economy.map(x=>`<article class="card"><h3>${clean(x.source)}</h3><p>${clean(x.use)}</p>${links(x.url)}</article>`).join('')}${D.markets.filter(x=>!market||x.country===market).map(x=>`<article class="card"><h3>${flag(x.country)}${clean(x.country)}</h3><p>${clean(x.qualification_tests)}</p></article>`).join('')}</div></details>`}
function sourceLibrary(p){const collected=new Map();for(const x of pool)for(const url of [x.website,...evidenceUrls(x),...list(x.profile?.source_urls)])if(/^https?:/.test(url||'')){if(!collected.has(url))collected.set(url,{url,names:new Set(),type:url===x.website?'Company website':'Profile source'});collected.get(url).names.add(x.name)}for(const e of events)for(const url of list(e.source_url||e.source_urls)){if(!/^https?:/.test(url||''))continue;if(!collected.has(url))collected.set(url,{url,names:new Set(),type:'Dated development'});collected.get(url).names.add(e.company)}const rows=[...collected.values()].filter(x=>[x.url,...x.names,x.type].join(' ').toLowerCase().includes((p.get('q')||'').toLowerCase())&&(!p.get('type')||x.type===p.get('type')));const {items,pager}=pageSlice(rows,p);return band('Evidence library','Company websites & research sources','Open the underlying publisher directly. A listed source is not a claim that every page or disclosure has been reviewed.')+`<div class="filters"><label>Find company, publisher or domain<input data-filter="q" value="${clean(p.get('q')||'')}" placeholder="Bizzi, payroll, enterprisesg…"></label>${select('type','Source type',['Company website','Profile source','Dated development'].map(x=>[x,x]),p)}<button data-reset>Clear</button></div>${pager}<div class="tablebox"><table><thead><tr><th>Company / topic</th><th>Source type</th><th>Publisher link</th></tr></thead><tbody>${items.map(x=>`<tr><td>${clean([...x.names].join(' · '))}</td><td>${x.type}</td><td>${profileSource(x.url,new URL(x.url).hostname)}<span class="compact source-path">${clean(new URL(x.url).pathname)}</span></td></tr>`).join('')}</tbody></table></div>${pager}`}
// Preserve profile context while examining a linked event or related company.
let modalTrail=[],activeCompany=null,modalKey='';
const originalShow=show;
show=function(html){originalShow(html);updateModalBar()};
function updateModalBar(){const form=modal.querySelector('form');if(!form.querySelector('.modal-navigation'))form.insertAdjacentHTML('afterbegin','<div class="modal-navigation"></div>');form.querySelector('.modal-navigation').innerHTML=`${modalTrail.length?'<button type="button" data-detail-back>← Back</button>':'<span>Research desk</span>'}<button type="button" data-detail-expand aria-label="Toggle expanded detail view">${modal.classList.contains('expanded-detail')?'↙ Compact':'⛶ Expand'}</button>`}
function rememberModal(){if(modal.open){modalTrail.push({html:modal.querySelector('article').innerHTML,scroll:modal.scrollTop,key:modalKey,company:activeCompany});if(modalTrail.length>12)modalTrail.shift()}}
company=function(i,tab='overview'){if(modal.open&&activeCompany!==i&&modalKey)rememberModal();activeCompany=i;modalKey='company:'+i;priorCompany(i,tab);const x=pool[i];if(!x)return;modal.querySelector('.profile-head').insertAdjacentHTML('beforeend',`<div class="profile-navigation"><span>${companyEvents(x).length} captured developments · ${x.profile?.leadership?.length||0} sourced leaders</span><div><button data-next-company="${(i-1+pool.length)%pool.length}" aria-label="Previous company">←</button><button data-next-company="${(i+1)%pool.length}" aria-label="Next company">→</button></div></div>`);updateModalBar()};
function openDevelopment(i){const e=events[i];if(!e)return;rememberModal();modalKey='event:'+i;activeCompany=null;const x=eventCompany(e);show(`<div class="event-detail-head"><small>${clean(eventType(e))} · ${clean(eventDate(e)||'Date not confirmed')}${date(e)?' · publication':' · effective / event'}</small><h2>${clean(eventName(e))}</h2><div class="event-detail-meta"><span class="pill">${clean(e.status||'Source recorded')}</span>${x?identity(x):`<b>${clean(e.company)}</b>`}</div></div><div class="event-detail-grid"><section><small>Reported facts</small><p>${clean(e.summary||e.reported_facts)}</p>${e.event_date&&e.event_date!==date(e)?field('Event / effective date',e.event_date):''}${links(e.source_url||e.source_urls)}</section><section class="value-panel"><small>Analyst interpretation · Mekari</small><h3>Why it matters</h3><p>${clean(e.mekari_implication||e.mekari_lesson||'Assess fit with the mandate before advancing.')}</p><h3>Next diligence action</h3><p>${clean(e.next_research_action||x?.next_evidence_needed||'Confirm scope and commercial terms in the original source; compare build, partner and acquire.')}</p></section></div><div class="event-detail-footer">${x?`<button data-profile-tab="diligence" data-record="${getId(x)}">Add diligence note →</button>`:''}<span>Source ${e.checked_at?'checked '+clean(e.checked_at):'date retained'} · company claims are not independently audited outcomes.</span></div>`)}
modal.addEventListener('close',()=>{modalTrail=[];modalKey='';activeCompany=null;modal.classList.remove('expanded-detail')});
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const d=b.dataset;
if(d.event!==undefined){e.preventDefault();e.stopImmediatePropagation();openDevelopment(+d.event)}
if(d.detailBack!==undefined){const previous=modalTrail.pop();if(previous){modalKey=previous.key;activeCompany=previous.company;show(previous.html);modal.scrollTop=previous.scroll}}
if(d.detailExpand!==undefined){modal.classList.toggle('expanded-detail');updateModalBar()}
if(d.nextCompany!==undefined){activeCompany=+d.nextCompany;company(+d.nextCompany)}
if(d.removeFilter)change(d.removeFilter,'');if(d.briefMode)change('brief',d.briefMode);
if(d.case){const c=caseDefinitions.find(x=>x.id===d.case),event=events.find(x=>x.id===d.case);rememberModal();modalKey='case:'+d.case;activeCompany=null;show(`<small>Global benchmark · analyst learning case</small><h2>${clean(c.title)}</h2><div class="case-detail"><section><small>Observed mechanism</small><p>${clean(c.mechanism)}</p><button data-event="${events.indexOf(event)}">Read source development →</button></section><section><small>Mekari application</small><h3>${clean(c.application)}</h3><p>${clean(c.test)}</p><p class="compact">Transferability is a research hypothesis. No revenue uplift or acquisition value is inferred.</p></section></div>`)}
if(d.saveView!==undefined){show(`<h2>Save this research view</h2><p>Keep the current page and filters in this browser.</p><label>View name<input id="view-name" maxlength="80" value="${clean(pages[route().page][1])}"></label><button data-confirm-view>Save view</button><span id="view-save-status" role="status"></span>`);modal.querySelector('input').focus()}
if(d.confirmView!==undefined){const name=modal.querySelector('#view-name').value.trim();if(!name){modal.querySelector('#view-save-status').textContent='Add a name.';return}const {page,p}=route(),stored=localRead('mekari-views-v2',[]);stored.push({name,page,params:Object.fromEntries(p)});try{localStorage.setItem('mekari-views-v2',JSON.stringify(stored.slice(-30)));modal.close();render();toast('View saved in this browser.')}catch{toast('This browser cannot save local views.')}}
if(d.copyView!==undefined){navigator.clipboard?.writeText(location.href).then(()=>toast('View link copied.')).catch(()=>{show(`<h2>Copy this view link</h2><input readonly value="${clean(location.href)}" aria-label="View link">`);modal.querySelector('input').select()})}
if(d.exportEvents){const rows=filteredEvents(route().p,d.exportEvents==='capital'?events.filter(capitalEvent):events),cols=['company','publication_date','event_date','type','status','summary','mekari_implication','next_research_action','source_url'];const cell=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const csv=[cols,...rows.map(e=>cols.map(k=>e[k]||''))].map(row=>row.map(cell).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='mekari-'+d.exportEvents+'-'+checkedDate+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
},true);
function toast(message){let el=document.querySelector('#workspace-toast');if(!el){el=document.createElement('div');el.id='workspace-toast';el.setAttribute('role','status');document.body.append(el)}el.textContent=message;el.hidden=false;setTimeout(()=>el.hidden=true,3500)}
document.addEventListener('change',e=>{if(e.target.id==='saved-view-picker'&&e.target.value!==''){const x=localRead('mekari-views-v2',[]).filter(x=>x.page===route().page)[+e.target.value];if(x)location.hash=link(x.page,x.params)}});
const groups=[['Decision desk',['brief']],['Deal sourcing',['pipeline','atlas','compare','queue','saved']],['Market intelligence',['competitors','benchmarks','signals','capital','markets']],['Mandate & evidence',['strategy','channels','coverage','sources']]];
render=function(){const {page,p}=route();document.querySelector('#menu').textContent=pages[page][1]+' ☰';document.querySelector('#nav').innerHTML=groups.map(([title,ids])=>`<details class="nav-section" open><summary>${title}</summary>${ids.map(id=>`<a href="#${id}" class="${page===id?'active':''}" ${page===id?'aria-current="page"':''}><i aria-hidden="true">${pages[id][0]}</i><span>${pages[id][1]}</span>${id==='pipeline'?`<em>${all.length}</em>`:id==='signals'?`<em>${events.length}</em>`:''}</a>`).join('')}</details>`).join('');document.querySelector('header>span').textContent=pages[page][1];document.querySelector('header .date').textContent='Source sweep · '+checkedDate;
view.innerHTML=page==='brief'?brief():page==='atlas'?atlas(p):page==='queue'?queue(p):page==='compare'?compareView():page==='competitors'?competitors(p):page==='benchmarks'?benchmarkView(p):page==='markets'?policyView(p):page==='signals'?signals(p):page==='capital'?capitalView(p):page==='sources'?sourceLibrary(p):page==='coverage'?coverageDesk():page==='channels'?channels():page==='strategy'?strategy():priorDirectory(page,p);
if(['pipeline','competitors','saved'].includes(page)){const filters=view.querySelector('.filters');if(filters)filters.insertAdjacentHTML('afterend',viewTools(p));}
};
render();
const resources=D.resources?.records||[];
const resourceFor=x=>resources.find(r=>r.company_id===x.id);
function sourceHealth(){const checks=resources.flatMap(r=>r.checks||[]),reachable=resources.filter(r=>r.checks.some(c=>c.status==='Reachable')),needs=resources.filter(r=>!r.checks.some(c=>c.status==='Reachable'));return `<section class="section panel"><div class="section-heading"><div><small>Public-source sweep · ${clean(D.resources?.checked||'Not run')}</small><h2>Company resource health</h2></div><a href="#sources">Open source library →</a></div><div class="health-metrics"><div><b>${resources.length}</b><span>Company resource records checked</span></div><div><b>${checks.length}</b><span>Public page checks</span></div><div><b>${reachable.length}</b><span>Companies with readable pages</span></div><div><b>${needs.length}</b><span>Companies needing access review</span></div></div><p class="compact">Reachable means readable content was fetched. It does not mean leadership, fundraising or news claims are verified. Access failures do not establish that a company has closed.</p><details class="section"><summary>Inspect inaccessible sources (${needs.length} companies)</summary><div class="tablebox"><table><thead><tr><th>Company</th><th>Check result</th><th>Website</th></tr></thead><tbody>${needs.map(r=>`<tr><td>${clean(r.company)}</td><td>${clean([...new Set(r.checks.map(c=>c.status))].join(' · '))}</td><td>${profileSource(r.website,'Try company website')}</td></tr>`).join('')}</tbody></table></div></details></section>`}
coverageDesk=function(){return priorCoverage().replace('</div>','</div>'+sourceHealth())};
const baseSourceLibrary=sourceLibrary;
sourceLibrary=function(p){return baseSourceLibrary(p)+`<details class="section panel"><summary>Research method · language coverage & review standards</summary><div class="standards-grid"><section><h3>Discover in local language and English</h3><p>Company resources retain English and local-language search templates. Public company sites are checked directly; findings are summarized in English.</p></section><section><h3>Promote only reviewed claims</h3><p>Funding links and headlines are leads until the original source is reviewed. Record amount, currency, round, investor, publication date and event date separately.</p></section><section><h3>Keep uncertainty visible</h3><p>Undisclosed is not zero. A website is not proof of current ownership, profitability, seller interest or a complete financing history.</p></section></div></details>`};
const companyWithHistory=company;
company=function(i,tab='overview'){companyWithHistory(i,tab);const x=pool[i],r=x&&resourceFor(x);if(!r||!modal.open)return;const target=modal.querySelector('.profile-sources');if(target)target.insertAdjacentHTML('beforeend',`<h3>Latest website check</h3><p class="compact">${clean(r.checked)} · ${r.checks.filter(c=>c.status==='Reachable').length} readable pages out of ${r.checks.length} checked. Content freshness is separate from access status.</p><p class="compact">Research languages: ${clean(r.languages.join(' + '))}</p>${r.checks.map(c=>`<div class="source-check"><span>${clean(c.status)}</span>${profileSource(c.url,c.title||new URL(c.url).hostname)}</div>`).join('')}`)};
const renderExperience=render;
render=function(){renderExperience();const {page,p}=route();if(page==='pipeline'){const filter=view.querySelector('.filters');filter?.insertAdjacentHTML('beforebegin',`<div class="pipeline-presets"><a href="#pipeline" ${!p.get('scope')&&!p.get('pillar')?'aria-current="page"':''}>All companies</a><a href="#pipeline?scope=Focused" ${p.get('scope')==='Focused'?'aria-current="page"':''}>Financing profiles</a><a href="#pipeline?scope=Acquisition" ${p.get('scope')==='Acquisition'?'aria-current="page"':''}>Mapped competitors</a><a href="#pipeline?scope=Partnership" ${p.get('scope')==='Partnership'?'aria-current="page"':''}>Partnerships</a><a href="#queue">My diligence stages →</a></div>`);view.querySelectorAll('tbody tr').forEach(row=>{const button=row.querySelector('[data-company]');if(!button)return;const i=+button.dataset.company;const picked=basket.includes(recordId(pool[i]));row.lastElementChild.insertAdjacentHTML('beforeend',`<button class="inline-compare" data-basket="${i}" ${!picked&&basket.length>=3?'disabled':''}>${picked?'✓ Comparing':'＋ Compare'}</button>`)});if(basket.length)view.insertAdjacentHTML('afterbegin',`<div class="comparison-dock"><span>${basket.length}/3 companies in comparison</span><a href="#compare">Open comparison →</a></div>`)} };
render();
// Keep frequent destinations within reach at preview and phone widths.
const compactWorkspace = window.matchMedia('(max-width: 850px)');
const shortcuts = [['brief','Brief'],['pipeline','Pipeline'],['atlas','Atlas'],['competitors','Competitors'],['signals','News']];
const workspaceAside = document.querySelector('aside');
const mobileTools = document.createElement('div');
mobileTools.className = 'mobile-tools';
workspaceAside.append(mobileTools);
const quickNav = document.createElement('div');
quickNav.className = 'quick-nav';
quickNav.setAttribute('role','navigation');
quickNav.setAttribute('aria-label','Frequent destinations');
workspaceAside.append(quickNav);
function positionTools() {
  const header = document.querySelector('main header');
  const theme = document.querySelector('#theme'), finder = document.querySelector('#finder'), menu = document.querySelector('#menu');
  if (compactWorkspace.matches) mobileTools.append(theme,finder,menu);
  else {
    header.insertBefore(theme,header.querySelector('.date'));
    header.insertBefore(finder,header.querySelector('.date'));
    workspaceAside.insertBefore(menu,workspaceAside.querySelector('small'));
  }
  updateWayfinding();
}
function updateWayfinding(){
  const {page}=route();
  quickNav.innerHTML=shortcuts.map(([target,label])=>`<a href="#${target}" ${page===target?'aria-current="page"':''}>${label}</a>`).join('');
  const menu=document.querySelector('#menu');
  menu.textContent=workspaceAside.classList.contains('expanded')?'Close ×':'Pages ☰';
  menu.setAttribute('aria-label',workspaceAside.classList.contains('expanded')?'Close page navigation':'Open all workspace pages');
  const finder=document.querySelector('#finder');finder.textContent=compactWorkspace.matches?'Search':'Search ⌘K';
  const theme=document.querySelector('#theme');const dark=document.documentElement.dataset.theme==='dark';
  theme.textContent=compactWorkspace.matches?(dark?'☀':'◐'):(dark?'☀ Light':'◐ Dark');theme.setAttribute('aria-label',dark?'Use light theme':'Use dark theme');theme.title=theme.getAttribute('aria-label');
}
compactWorkspace.addEventListener('change',positionTools);
window.addEventListener('hashchange',updateWayfinding);
document.querySelector('#theme').addEventListener('click',updateWayfinding);
document.querySelector('#menu').addEventListener('click',updateWayfinding);
workspaceAside.addEventListener('click',e=>{if(e.target.closest('a')){workspaceAside.classList.remove('expanded');document.querySelector('#menu').setAttribute('aria-expanded','false');updateWayfinding()}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&workspaceAside.classList.contains('expanded')){workspaceAside.classList.remove('expanded');document.querySelector('#menu').setAttribute('aria-expanded','false');updateWayfinding();document.querySelector('#menu').focus()}});
const renderWithWayfinding=render;
render=function(){renderWithWayfinding();updateWayfinding()};
positionTools();
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-overlap]');if(!b)return;
  const m=D.competitorMap.matches[+b.dataset.overlap], x=pool.find(c=>c.id===m.company_id), product=D.competitorMap.products[m.product];
  rememberModal();modalKey='overlap:'+b.dataset.overlap;activeCompany=null;
  show(`<div class="match-detail"><small>Product comparison · ${clean(m.market)}</small><h2>${clean(x.name)} and Mekari ${clean(m.product)}</h2><span class="overlap ${m.level.toLowerCase()}">${m.level==='Core'?'Core alternative':'Specific workflow overlap'}</span><p>${clean(m.workflow)}</p><h3>Product sources</h3><div>${profileSource(m.source_url,x.name)}${profileSource(product.source_url,'Mekari '+m.product)}</div><p class="compact">Analyst comparison · reviewed ${clean(m.checked)}</p>${strategyScreen(x)}<button data-company="${getId(x)}">Open company profile →</button></div>`);
});

// Public workspace: organizing questions are analyst research, not company deal plans.
function strategyScreen(company) {
  const matches=D.competitorMap.matches.filter(item=>item.company_id===company.id);
  if(!matches.length)return '';
  return `<section class="proposal-screen"><small>Reviewed product comparisons</small><h3>Which workflows overlap?</h3>${matches.map(item=>`<p><b>Mekari ${clean(item.product)}</b> · ${clean(item.workflow)}</p>${profileSource(item.source_url,'Product evidence')}`).join('')}</section>`;
}
function countryMandate(market){
  const comparable=D.competitorMap.matches.filter(row=>row.market===market);
  const companies=[...new Set(comparable.map(row=>row.company_id))].map(id=>pool.find(x=>x.id===id)).filter(Boolean);
  if(!companies.length)return '';
  return `<section class="country-route"><small>Product comparisons</small><div class="peer-tags">${companies.map(identity).join('')}</div><a href="${link('competitors',{market})}">Explore ${clean(market)} comparisons →</a></section>`;
}
const publicQuestions={
  P1:'Which specialists could distribute complementary software or content to the same customers?',
  P2:'Which tools capture orders, deliveries, inventory movements and maintenance events outside the ledger?',
  P3:'Which local providers combine accounting, payroll or tax workflows with country-specific distribution?',
  P4:'Which products complete multi-step work with permission controls, audit trails and human review?'
};
strategy=function(){
  const selected=route().p.get('pillar')||'P1';const id=publicQuestions[selected]?selected:'P1';
  const rows=all.filter(x=>x.primary_thesis_pillar===id&&companyEvents(x).length).sort(cmp);
  return band('Independent research','Research themes','Explore companies, products and public developments by workflow.')+`<div class="experience-tabs">${Object.keys(publicQuestions).map(k=>`<a href="${link('strategy',{pillar:k})}" ${k===id?'aria-current="page"':''}>${clean(pillars[k])}</a>`).join('')}</div><div class="roadmap-header"><div><small>Research question</small><h2>${clean(pillars[id])}</h2><p>${publicQuestions[id]}</p></div><div><b>${all.filter(x=>x.primary_thesis_pillar===id).length} profiles</b><a href="${link('pipeline',{pillar:id})}">Browse this theme →</a></div></div><section class="section"><h2>Companies with reviewed developments</h2><div class="case-grid">${rows.slice(0,9).map(x=>`<article class="case-card">${identity(x)}<p>${clean(x.product_summary)}</p><button data-profile-tab="news" data-record="${getId(x)}">Read updates →</button></article>`).join('')||'<p>Explore the directory for company websites and product research.</p>'}</div></section>`;
};
briefWorkbench=function(){return `<section class="section"><div class="section-heading"><h2>Explore by research theme</h2><a href="#strategy">Research themes →</a></div><div class="decision-routes">${Object.entries(publicQuestions).map(([k,v])=>`<a href="${link('strategy',{pillar:k})}"><b>${clean(pillars[k])}</b><span>${clean(v)}</span></a>`).join('')}</div></section>`};
render();

/* Analyst workflow. Notes are local to this browser and never included in deployment data. */
const workflowStages = ['Monitoring','Screening','Diligence','On hold','Archived'];
const decisionRoutes = ['Undecided','Monitor','Partner','Acquire','Build','No action'];
const reviewStates = ['Unreviewed','Supported','Follow-up required'];
const reviewGates = {
  product:'Product fit & overlap',
  customers:'Customers & retention',
  financial:'Recurring revenue & financing',
  ownership:'Ownership & legal perimeter',
  security:'Integration, data rights & security'
};
const dateToday = () => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Jakarta',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
function analystRecord(company){
  const raw=localRead(noteKey(company),{});
  return raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{};
}
function hasWork(company){
  const n=analystRecord(company);
  return Boolean(n.stage||n.note||n.owner||n.nextAction||watch.includes(recordId(company)));
}
function workRows(){return pool.filter(hasWork).map(company=>({company,record:analystRecord(company)}))}
function dueState(record){
  if(!record.review)return 'Unscheduled';
  if(record.stage==='Archived')return 'Archived';
  if(record.review<dateToday())return 'Overdue';
  if(record.review===dateToday())return 'Due today';
  return 'Upcoming';
}
function isTracked(company){return hasWork(company)?'<span class="tracked-label">In worklist</span>':''}
function evidencePill(company){
  const e=profileEvidence(company);
  return `<span class="evidence-coverage ${e.label.toLowerCase()}" title="Fields with recorded evidence: ${e.filled} of 6">${e.label} <b>${e.filled}/6</b></span>`;
}
function researchRule(){return `<details class="research-rule"><summary>What do the evidence labels mean?</summary><p>Enriched profiles have at least four of six fields recorded. Partial profiles have two or three. Basic profiles have zero or one. The fields are description, product detail, leadership, capital history, dated updates and legal identity. Each field retains its source where available.</p><p>Use the profile to review the underlying sources before forming an investment judgment.</p></details>`}
function researchNote(index){
  const company=pool[index], record=analystRecord(company);
  const options=(values,value)=>values.map(v=>`<option ${value===v?'selected':''}>${clean(v)}</option>`).join('');
  return `<div class="analyst-editor" data-editor-company="${index}">
  <div class="editor-intro"><div><h3>Company work item</h3><p>Record your assessment and the next piece of evidence to obtain.</p></div><span class="local-indicator">Saved in this browser</span></div>
  <div class="analyst-fields"><label>Stage<select name="stage">${options(workflowStages,record.stage||'Monitoring')}</select></label><label>Proposed route<select name="decision">${options(decisionRoutes,record.decision||'Undecided')}</select></label><label>Owner<input name="owner" maxlength="80" placeholder="Analyst name" value="${clean(record.owner||'')}"></label><label>Next review<input name="review" type="date" value="${clean(record.review||'')}"></label><label class="full-field">Next action<input name="nextAction" maxlength="300" placeholder="For example, confirm the recurring software share with a source" value="${clean(record.nextAction||'')}"></label><label class="full-field">Assessment<textarea name="note" rows="4" maxlength="10000" placeholder="Why this company matters, what is known, and what remains open">${clean(record.note||'')}</textarea></label></div>
  <details class="gate-editor"><summary>Evidence checklist <span>${Object.values(record.gates||{}).filter(g=>g.state==='Supported').length}/5 supported</span></summary><p>These are your recorded assessments. Add a source or reference when marking a check supported.</p>${Object.entries(reviewGates).map(([id,label])=>{const g=record.gates?.[id]||{};return `<div class="gate-row"><label>${label}<select data-gate="${id}">${options(reviewStates,g.state||'Unreviewed')}</select></label><label>Source or reference<input data-gate-source="${id}" maxlength="500" value="${clean(g.source||'')}" placeholder="Document title, URL or diligence reference"></label></div>`}).join('')}</details>
  <div class="editor-save"><button class="work-primary" data-save-work="${index}">Save work item</button><span class="work-save-message" role="status">${record.updatedAt?'Last saved '+clean(new Date(record.updatedAt).toLocaleString()):''}</span></div>
  <details class="work-history"><summary>Decision history · ${(record.history||[]).length} saved changes</summary><p class="compact">The latest 50 saves are retained in this browser.</p>${(record.history||[]).slice().reverse().map(h=>`<div><time>${clean(new Date(h.at).toLocaleString())}</time><p>${clean(h.summary)}</p>${h.changes?.length?`<details><summary>View changed fields</summary>${h.changes.map(c=>`<p><b>${clean(c.field)}</b><br>${clean(c.before||'Empty')} → ${clean(c.after||'Empty')}</p>`).join('')}</details>`:''}</div>`).join('')||'<p>Changes will appear here after saving.</p>'}</details></div>`;
}
function saveWork(index){
  const entity=pool[index],editor=modal.querySelector('.analyst-editor');
  if(!entity||!editor)return;
  const read=name=>editor.querySelector(`[name="${name}"]`).value.trim();
  const previous=analystRecord(entity);
  const updated={...previous,stage:read('stage'),decision:read('decision'),owner:read('owner'),review:read('review'),nextAction:read('nextAction'),note:read('note'),gates:{}};
  const status=editor.querySelector('.work-save-message');
  if(['Screening','Diligence'].includes(updated.stage)&&!updated.nextAction){status.textContent='Add a next action before advancing this item.';editor.querySelector('[name=nextAction]').focus();return}
  for(const id of Object.keys(reviewGates)){
    const state=editor.querySelector(`[data-gate="${id}"]`).value;
    const source=editor.querySelector(`[data-gate-source="${id}"]`).value.trim();
    if(state==='Supported'&&!source){status.textContent='Add an evidence reference for '+reviewGates[id]+'.';editor.querySelector('.gate-editor').open=true;editor.querySelector(`[data-gate-source="${id}"]`).focus();return}
    updated.gates[id]={state,source};
  }
  const changes=['stage','decision','owner','review','nextAction','note'].filter(k=>(previous[k]||'')!==updated[k]);
  const gatesChanged=JSON.stringify(previous.gates||{})!==JSON.stringify(updated.gates);
  if(!changes.length&&!gatesChanged){status.textContent='No changes to save.';return}
  updated.updatedAt=new Date().toISOString();
  const summary=[...changes.map(k=>({stage:'Stage → '+updated.stage,decision:'Route → '+updated.decision,owner:'Owner → '+(updated.owner||'unassigned'),review:'Review → '+(updated.review||'unscheduled'),nextAction:'Next action updated',note:'Assessment updated'})[k]),...(gatesChanged?['Evidence checklist updated']:[])].join(' · ');
  updated.history=[...(Array.isArray(previous.history)?previous.history:[]),{at:updated.updatedAt,summary,changes:changes.map(field=>({field,before:previous[field]||'',after:updated[field]}))}].slice(-50);
  try{localStorage.setItem(noteKey(entity),JSON.stringify(updated))}catch{status.textContent='Could not save. Export a backup or check browser storage.';return}
  render();company(index,'diligence');modal.querySelector('.work-save-message').textContent='Saved. Your worklist and decision brief have been updated.';
}
function workCard(company,record){
  const due=dueState(record);
  return `<article class="work-item"><div>${identity(company)}<span class="due-label ${due==='Overdue'?'overdue':''}">${due}</span></div><p>${clean(record.nextAction||'Add the next research action.')}</p><div class="work-card-meta"><span>${clean(record.owner||'Unassigned')}</span><time>${clean(record.review||'No review date')}</time></div><button data-profile-tab="diligence" data-record="${getId(company)}">Update work item →</button></article>`;
}
queue=function(p){
  let rows=workRows();
  const allRows=rows;
  const query=key(p.get('q'));
  rows=rows.filter(({company,record})=>(!p.get('stage')||(record.stage||'Monitoring')===p.get('stage'))&&(!p.get('owner')||(record.owner||'Unassigned')===p.get('owner'))&&(!p.get('due')||dueState(record)===p.get('due'))&&key([company.name,record.nextAction,record.owner,record.note].join(' ')).includes(query));
  rows.sort((a,b)=>(a.record.review||'9999').localeCompare(b.record.review||'9999')||cmp(a.company,b.company));
  const board=p.get('view')==='board';
  const content=board?`<div class="work-board">${workflowStages.map(stage=>{const cards=rows.filter(({record})=>(record.stage||'Monitoring')===stage);return `<section><h3>${stage}<span>${cards.length}</span></h3>${cards.map(({company,record})=>workCard(company,record)).join('')||'<p class="board-empty">No items</p>'}</section>`}).join('')}</div>`:`<div class="tablebox work-table"><table><thead><tr><th>Company</th><th>Stage / route</th><th>Next action</th><th>Owner</th><th>Review</th><th></th></tr></thead><tbody>${rows.map(({company,record})=>`<tr><td>${identity(company)}${evidencePill(company)}</td><td>${clean(record.stage||'Monitoring')}<small>${clean(record.decision||'Undecided')}</small></td><td>${clean(record.nextAction||'Add a next action')}</td><td>${clean(record.owner||'Unassigned')}</td><td><span class="due-label ${dueState(record)==='Overdue'?'overdue':''}">${clean(record.review||'Unscheduled')}</span></td><td><button data-profile-tab="diligence" data-record="${getId(company)}">Review →</button></td></tr>`).join('')}</tbody></table></div>`;
  return `<div class="work-page-title"><div><small>Analyst workspace</small><h1>My worklist</h1><p>Manage company screens, evidence requests and follow-ups.</p></div><a class="work-primary" href="#pipeline">Add companies →</a></div><div class="work-totals">${[['All work',allRows.length,''],['Overdue',allRows.filter(x=>dueState(x.record)==='Overdue').length,'Overdue'],['Due today',allRows.filter(x=>dueState(x.record)==='Due today').length,'Due today'],['Unscheduled',allRows.filter(x=>dueState(x.record)==='Unscheduled').length,'Unscheduled']].map(([title,n,due])=>`<a href="${link('queue',due?{due}:{})}"><b>${n}</b><span>${title}</span></a>`).join('')}</div><div class="work-toolbar"><div class="experience-tabs"><a href="${link('queue',{...Object.fromEntries(p),view:'table'})}" ${!board?'aria-current="page"':''}>List</a><a href="${link('queue',{...Object.fromEntries(p),view:'board'})}" ${board?'aria-current="page"':''}>Stage board</a></div><div><button data-backup-work>Export backup</button><label class="import-work">Restore backup<input type="file" id="restore-work" accept="application/json,.json"></label></div></div><div class="filters"><label>Find work<input data-filter="q" value="${clean(p.get('q')||'')}" placeholder="Company, owner or action"></label>${select('stage','Stage',workflowStages.map(v=>[v,v]),p)}${select('owner','Owner',[...new Set(allRows.map(x=>x.record.owner||'Unassigned'))].sort().map(v=>[v,v]),p)}<button data-reset>Clear</button></div>${rows.length?content:`<section class="work-empty"><h2>${allRows.length?'No work matches these filters':'Start with a company you want to investigate'}</h2><p>Open a company, choose Follow-up, and save its owner, next action and review date.</p><a href="#pipeline">Find a company →</a></section>`}<p class="workspace-storage">Work items and decision history are stored in this browser. Export a backup to transfer them. The public website has no shared team database or signed-in access.</p>`;
}
function shortNews(e){const x=eventCompany(e);return `<article class="brief-news-row"><time>${clean(eventDate(e)||'Date pending')}</time><div>${x?identity(x):`<b>${clean(e.company)}</b>`}<button data-event="${events.indexOf(e)}">${clean(eventName(e))}</button><p>${clean(e.mekari_implication||e.mekari_lesson||'Read the source and assess workflow relevance.')}</p></div><span>${clean(eventType(e))}</span></article>`}
brief=function(){
  const rows=workRows().filter(x=>x.record.stage!=='Archived');
  const overdue=rows.filter(x=>dueState(x.record)==='Overdue');
  const due=rows.filter(x=>dueState(x.record)==='Due today');
  const following=[...rows].sort((a,b)=>(a.record.review||'9999').localeCompare(b.record.review||'9999')).slice(0,3);
  const latest=filteredEvents(new URLSearchParams({period:'30'})).slice(0,5);
  const funded=all.filter(x=>meetsEvidenceFilter(x,'funding')).length;
  return `<div class="work-page-title"><div><small>Corporate development</small><h1>Decision brief</h1><p>Public developments, open research and your next decisions.</p></div><div class="snapshot-status"><span>Research snapshot</span><b>${clean(D.refreshChecked||D.asOf)}</b></div></div><div class="brief-action-strip"><a href="#queue"><strong>${rows.length}</strong><span>Active work items →</span></a><a href="#queue?due=Overdue"><strong class="${overdue.length?'attention-number':''}">${overdue.length}</strong><span>Overdue reviews →</span></a><a href="#queue?due=Due+today"><strong>${due.length}</strong><span>Due today →</span></a><a href="#pipeline?evidence=funding"><strong>${funded}</strong><span>Profiles with financing →</span></a></div><div class="decision-layout"><section class="brief-developments"><div class="section-heading"><h2>Latest developments</h2><a href="#signals">News desk →</a></div>${latest.map(shortNews).join('')||'<p>No captured developments in the current window.</p>'}</section><section class="brief-next"><div class="section-heading"><h2>Next actions</h2><a href="#queue">Worklist →</a></div>${following.length?following.map(({company,record})=>workCard(company,record)).join(''):`<div class="start-work"><span aria-hidden="true">↗</span><h3>Build your working shortlist</h3><p>Select a company and record the next evidence request. Its follow-up will appear here.</p><a class="work-primary" href="#pipeline">Find a company</a></div>`}<div class="next-links"><a href="#competitors">Compare product alternatives →</a><a href="#atlas">Explore a regional market →</a><a href="#coverage">Review research gaps →</a></div></section></div>${learningSection()}<section class="section"><div class="section-heading"><h2>Research coverage</h2><a href="#coverage">Inspect all fields →</a></div><div class="coverage-summary">${['Enriched','Partial','Basic'].map(label=>{const count=all.filter(x=>profileEvidence(x).label===label).length;return `<a href="${link('pipeline',{coverage:label})}"><strong>${count}</strong><b>${label} profiles</b><span>${label==='Enriched'?'4–6 fields recorded':label==='Partial'?'2–3 fields recorded':'0–1 fields recorded'} →</span></a>`}).join('')}</div>${researchRule()}</section>`;
}
function downloadBackup(){
  const notes=Object.fromEntries(pool.map(c=>[c.id,analystRecord(c)]).filter(([,n])=>Object.keys(n).length));
  const output={format:'mekari-workspace',version:1,exportedAt:new Date().toISOString(),notes,watchlist:watch,comparison:basket};
  const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json'}));
  const a=document.createElement('a');a.href=url;a.download='mekari-workspace-'+dateToday()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function validateBackup(value){
  if(value?.format!=='mekari-workspace'||value.version!==1||!value.notes||typeof value.notes!=='object'||Array.isArray(value.notes))throw Error('This is not a supported Mekari workspace backup.');
  const accepted={};
  for(const [id,record] of Object.entries(value.notes)){
    if(!pool.some(c=>c.id===id))continue;
    if(!record||typeof record!=='object'||Array.isArray(record))throw Error('A work item is invalid.');
    const n={};
    for(const name of ['stage','decision','owner','review','nextAction','note','updatedAt']){
      const v=record[name];if(v===undefined)continue;
      if(typeof v!=='string'||v.length>10000)throw Error('A work item contains an invalid field.');n[name]=v;
    }
    if(n.stage&&!workflowStages.includes(n.stage))throw Error('A work item has an unknown stage.');
    if(n.decision&&!decisionRoutes.includes(n.decision))throw Error('A work item has an unknown route.');
    if(n.review&&(!/^\d{4}-\d{2}-\d{2}$/.test(n.review)||!Number.isFinite(Date.parse(n.review))))throw Error('A review date is invalid.');
    if(n.updatedAt&&!Number.isFinite(Date.parse(n.updatedAt)))throw Error('A saved timestamp is invalid.');
    n.gates={};
    for(const gate of Object.keys(reviewGates)){
      const g=record.gates?.[gate];if(!g)continue;
      if(!reviewStates.includes(g.state)||typeof g.source!=='string'||g.source.length>500)throw Error('An evidence check is invalid.');
      n.gates[gate]={state:g.state,source:g.source};
    }
    n.history=(Array.isArray(record.history)?record.history:[]).filter(h=>typeof h?.at==='string'&&typeof h.summary==='string'&&h.summary.length<1000).slice(-50).map(h=>({at:h.at,summary:h.summary,changes:Array.isArray(h.changes)?h.changes.filter(c=>['stage','decision','owner','review','nextAction','note'].includes(c?.field)&&typeof c.before==='string'&&typeof c.after==='string'&&c.before.length<=10000&&c.after.length<=10000):[]}));
    accepted[id]=n;
  }
  return accepted;
}
async function restoreBackup(file){
  if(!file)return;
  if(file.size>5000000){toast('Backup is too large. Maximum 5 MB.');return}
  try{
    const input=JSON.parse(await file.text());const notes=validateBackup(input);const changes=[];
    for(const [id,n] of Object.entries(notes)){
      const company=pool.find(c=>c.id===id),previous=analystRecord(company);
      if(previous.updatedAt&&(!n.updatedAt||n.updatedAt<=previous.updatedAt))continue;
      changes.push({key:noteKey(company),value:JSON.stringify(n),previous:localStorage.getItem(noteKey(company))});
    }
    const known=new Set(pool.map(recordId));
    const importedWatch=Array.isArray(input.watchlist)?input.watchlist.filter(v=>typeof v==='string'&&known.has(v)):[];
    const importedCompare=Array.isArray(input.comparison)?input.comparison.filter(v=>typeof v==='string'&&known.has(v)):[];
    const nextWatch=[...new Set([...watch,...importedWatch])];
    const nextBasket=[...new Set([...basket,...importedCompare])].slice(0,3);
    for(const [key,value] of [['mekari-watch-v1',nextWatch],['mekari-compare-v1',nextBasket]])changes.push({key,value:JSON.stringify(value),previous:localStorage.getItem(key)});
    const applied=[];
    try{for(const change of changes){localStorage.setItem(change.key,change.value);applied.push(change)}}catch(error){for(const change of applied){change.previous===null?localStorage.removeItem(change.key):localStorage.setItem(change.key,change.previous)}throw error}
    watch=nextWatch;basket=nextBasket;render();toast(`Restored ${changes.length-2} work items and merged saved companies. Newer local records were retained.`);
  }catch(error){toast('Restore failed: '+error.message)}
}
document.addEventListener('click',event=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.dataset.saveWork!==undefined){event.preventDefault();saveWork(Number(button.dataset.saveWork))}
  if(button.dataset.backupWork!==undefined)downloadBackup();
  if(button.dataset.startWork!==undefined)company(Number(button.dataset.startWork),'diligence');
});
document.addEventListener('change',e=>{if(e.target.id==='restore-work')restoreBackup(e.target.files[0])});
pages.queue=['☷','My worklist'];pages.pipeline=['▤','Company research'];
shortcuts.splice(0,shortcuts.length,['brief','Brief'],['pipeline','Companies'],['queue','Worklist'],['competitors','Competitors'],['signals','News']);
const operationalRender=render;
render=function(){
  operationalRender();
  if(['pipeline','saved'].includes(route().page)){
    const table=view.querySelector('table');
    if(table){
      table.classList.add('company-research-table');
      table.querySelectorAll('tbody tr').forEach(row=>{
        const button=row.querySelector('[data-company]');if(!button)return;const c=pool[+button.dataset.company];
        row.querySelector('td').insertAdjacentHTML('beforeend',`<div class="row-evidence">${evidencePill(c)}${isTracked(c)}</div>`);
        row.lastElementChild.insertAdjacentHTML('beforeend',`<button class="inline-review" data-start-work="${getId(c)}">${hasWork(c)?'Update follow-up':'Add to worklist'} →</button>`);
      });
    }
  }
  document.querySelector('aside footer').innerHTML='Public research · analyst workspace';
  const navSections=document.querySelectorAll('#nav .nav-section');
  if(!['strategy','channels','coverage','sources'].includes(route().page))navSections[navSections.length-1]?.removeAttribute('open');
  const workLink=document.querySelector('#nav a[href="#queue"]');
  if(workLink&&workRows().length)workLink.insertAdjacentHTML('beforeend',`<em>${workRows().length}</em>`);
};
const operationCompany=company;
company=function(i,tab='overview'){
  operationCompany(i,tab);if(!pool[i])return;
  const x=pool[i],e=profileEvidence(x);
  const tabButton=modal.querySelector('[data-profile-tab=diligence]');if(tabButton)tabButton.textContent='Follow-up';
  const facts=modal.querySelector('.profile-navigation');
  if(facts){
    facts.querySelector('span').innerHTML=evidencePill(x)+' <span class="profile-gaps">'+clean(e.missing.length?'Open fields: '+e.missing.join(', '):'Six evidence fields recorded')+'</span>';
    facts.querySelector('div').insertAdjacentHTML('afterbegin',`<button data-copy-profile="${i}" aria-label="Copy company profile link">Copy link</button>`);
  }
  if(tab==='overview'){
    if(!x.profile?.value_proposition&&!x.profile?.audience)modal.querySelector('.value-panel')?.remove();
    const panels=modal.querySelectorAll('.profile-panel');
    if(!x.profile?.leadership?.length)panels[0]?.remove();
    if(!e.dimensions.find(([name])=>name==='Capital history')[1])panels[1]?.remove();
    modal.querySelectorAll('.profile-summary').forEach(node=>{if(!node.children.length)node.remove()});
    if(e.missing.length)modal.querySelector('.profile-body').insertAdjacentHTML('beforeend',`<section class="profile-research-gap"><div><h3>Research still required</h3><p>${clean(e.missing.join(' · '))}</p></div><button data-start-work="${i}">Plan the follow-up →</button></section>`);
  }
};
render();

document.addEventListener('click',async e=>{
  const button=e.target.closest('[data-copy-profile]');if(!button)return;
  const x=pool[Number(button.dataset.copyProfile)];
  const url=new URL(location.href);url.hash=link('pipeline',{company:x.id});
  try{await navigator.clipboard.writeText(url.href);toast('Company profile link copied.')}catch{show(`<h2>Company profile link</h2><input class="copy-profile-url" readonly value="${clean(url.href)}" aria-label="Company profile URL">`);modal.querySelector('input').select()}
});
function openIncomingDetail(){
  const p=route().p;if(!p.has('company'))return;
  const i=pool.findIndex(x=>x.id===p.get('company'));
  if(i>=0)company(i,['overview','news','fit'].includes(p.get('tab'))?p.get('tab'):'overview');
}
window.addEventListener('hashchange',()=>setTimeout(openIncomingDetail,0));
openIncomingDetail();
