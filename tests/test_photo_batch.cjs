const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html=fs.readFileSync('admin/story-studio/index.html','utf8');
const start=html.indexOf("$('upload').onchange=");
const end=html.indexOf("let editImage",start);
assert(start>=0 && end>start);
const handler=html.slice(start,end);
async function scenario(saveFails=false){
  const elements={upload:{disabled:false,value:'chosen'},'upload-status':{},'upload-errors':{items:[],replaceChildren(){this.items=[]},append(item){this.items.push(item)}}};
  let attempts=0,renders=0,schedules=0;
  const context={$:id=>elements[id],document:{createElement:()=>({})},photos:[],selected:new Set(),uploading:0,saveTimer:null,clearTimeout,
    save:async()=>{if(saveFails)throw Error('Title is required');},
    webPhoto:async(file,fromEditor)=>{assert.equal(fromEditor,true);assert.equal(renders,context.photos.length);attempts++;if(file.name==='3.jpg')throw Error('<bad file>');return {id:file.name};},
    renderPhotos:()=>{renders++;},schedule:()=>{schedules++;}};
  vm.createContext(context);vm.runInContext(handler,context);
  elements.upload.files=Array.from({length:8},(_,i)=>({name:(i+1)+'.jpg'}));
  await elements.upload.onchange({target:elements.upload});
  assert.equal(elements.upload.disabled,false);assert.equal(elements.upload.value,'');assert.equal(context.uploading,0);
  if(saveFails){assert.equal(attempts,0);assert.match(elements['upload-status'].textContent,/Title is required/);}
  else{assert.equal(attempts,8);assert.equal(renders,7);assert.equal(context.photos.length,7);assert.equal(schedules,1);assert.match(elements['upload-status'].textContent,/7 of 8/);assert.equal(elements['upload-errors'].items[0].textContent,'3.jpg: <bad file>');}
}
(async()=>{await scenario();await scenario(true);console.log('Batch checks passed: eight files, incremental rendering, one failure continues, errors retained, preparation failure reported.');})().catch(e=>{console.error(e);process.exitCode=1});
