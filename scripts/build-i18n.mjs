import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const root=path.resolve(import.meta.dirname,'..');
const context={window:{}};
vm.createContext(context);

for(const file of ['assets/js/i18n-data.js','assets/js/i18n-editorial-id.js']){
  vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),context,{filename:file});
}

const source=context.window.VITO_I18N;
for(const page of Object.keys(source.pages)){
  const bundle={meta:{[page]:source.meta[page]||{}},pages:{[page]:source.pages[page]}};
  const output=`window.VITO_I18N=${JSON.stringify(bundle)};\n`;
  fs.writeFileSync(path.join(root,`assets/js/i18n-page-${page}.js`),output);
}
