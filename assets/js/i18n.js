(function(){
  'use strict';

  const storeKey='vito-language';
  const data=window.VITO_I18N||{};
  const pageKey=document.body.dataset.i18nPage;
  const pageStrings=(data.pages&&data.pages[pageKey])||{};
  const meta=(data.meta&&data.meta[pageKey])||{};
  const nodes=[...document.querySelectorAll('[data-i18n]')];
  const englishMeta={title:document.title,description:document.querySelector('meta[name="description"]')?.content||''};

  nodes.forEach(node=>{node.dataset.i18nEnglish=node.innerHTML;});

  function preferredLanguage(){
    const saved=localStorage.getItem(storeKey);
    if(saved==='en'||saved==='id')return saved;
    return /^id\b/i.test(navigator.language||'')?'id':'en';
  }

  function updateMetadata(language){
    const description=document.querySelector('meta[name="description"]');
    if(language==='id'){
      if(meta.title)document.title=meta.title;
      if(description&&meta.description)description.content=meta.description;
    }else{
      document.title=englishMeta.title;
      if(description)description.content=englishMeta.description;
    }
  }

  function setLanguage(language,save=true){
    if(language!=='id')language='en';
    document.documentElement.lang=language;
    document.documentElement.dataset.language=language;
    nodes.forEach(node=>{
      const translation=pageStrings[node.dataset.i18n];
      node.innerHTML=language==='id'&&translation!=null?translation:node.dataset.i18nEnglish;
    });
    document.querySelectorAll('[data-language]').forEach(button=>{
      const active=button.dataset.language===language;
      button.classList.toggle('is-active',active);
      button.setAttribute('aria-pressed',String(active));
    });
    updateMetadata(language);
    if(save)localStorage.setItem(storeKey,language);
    document.dispatchEvent(new CustomEvent('vito:languagechange',{detail:{language}}));
  }

  function addSwitch(){
    const navLinks=document.getElementById('navLinks');
    if(!navLinks||navLinks.querySelector('[data-language-switch]'))return;
    const switcher=document.createElement('div');
    switcher.className='language-switch';
    switcher.dataset.languageSwitch='';
    switcher.setAttribute('role','group');
    switcher.setAttribute('aria-label','Language / Bahasa');
    switcher.innerHTML='<button type="button" data-language="en" aria-pressed="false">EN</button><span aria-hidden="true">/</span><button type="button" data-language="id" aria-pressed="false">ID</button>';
    const target=navLinks.querySelector('.hope-nav,.icobtn');
    navLinks.insertBefore(switcher,target||null);
  }

  function wireSwitches(){
    document.querySelectorAll('[data-language-switch]').forEach(switcher=>{
      if(switcher.dataset.languageReady)return;
      switcher.dataset.languageReady='true';
      switcher.addEventListener('click',event=>{
        const button=event.target.closest('[data-language]');
        if(button)setLanguage(button.dataset.language);
      });
    });
  }

  addSwitch();
  wireSwitches();
  setLanguage(preferredLanguage(),false);
  window.vitoSetLanguage=setLanguage;
})();
