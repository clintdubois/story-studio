// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (c) 2026 Clint and Liz DuBois. See LICENSE and NOTICE.md.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('admin/story-studio/index.html','utf8');
const nodes=new Proxy({}, {get:(o,k)=>o[k]??={value:'0',disabled:false}});
const c={$:id=>nodes[id],selected:new Set(['c','a','b']),photos:['a','b','c'].map(id=>({id,src:'/api/story-media/d/'+id})),esc:String,renderOrder(){},draw(){}};vm.createContext(c);
for(const prefix of ['function picked','function figure','function movePicked','function straightenZoom'])vm.runInContext(html.split('\n').find(l=>l.startsWith(prefix)),c);
vm.runInContext(html.slice(html.indexOf('function arrangement('),html.indexOf("$('gallery').onclick=")),c);
assert.deepEqual(Array.from(c.picked(),p=>p.id),['c','a','b']);c.movePicked(0,2);assert.deepEqual(Array.from(c.picked(),p=>p.id),['a','b','c']);c.movePicked(2,0);assert.deepEqual(Array.from(c.picked(),p=>p.id),['c','a','b']);
for(const shape of ['two','three','lead','left','right']){const ps=shape==='left'||shape==='right'?c.picked().slice(0,1):c.picked();const result=c.arrangement(ps,shape);assert.equal((result.match(/<img /g)||[]).length,ps.length);if(shape==='lead')assert(result.includes('colspan="2"'));if(shape==='three')assert.equal((result.match(/<td /g)||[]).length,3)}
// Verify every rotated output corner samples inside the image at portrait/landscape sizes.
for(const [w,h] of [[1800,1200],[1200,1800]])for(const deg of [-15,-7.5,0,7.5,15]){const t=deg*Math.PI/180,z=c.straightenZoom(w,h,t);for(const x of [-w/2,w/2])for(const y of [-h/2,h/2]){const ix=(x*Math.cos(t)+y*Math.sin(t))/z,iy=(-x*Math.sin(t)+y*Math.cos(t))/z;assert(Math.abs(ix)<=w/2+1e-8);assert(Math.abs(iy)<=h/2+1e-8)}}
vm.runInContext(html.slice(html.indexOf('let editImage,'),html.indexOf('function editSize()')),c);
vm.runInContext("angle=90;cropBox={x:3,y:4,w:500,h:600};editShape='1';",c);nodes.brightness.value='110';nodes.contrast.value='120';nodes.straighten.value='5';c.rememberEdit();vm.runInContext('angle=180;cropBox=null;',c);nodes.contrast.value='80';nodes['undo-edit'].onclick();assert.equal(vm.runInContext('angle',c),90);assert.equal(vm.runInContext('cropBox.w',c),500);assert.equal(nodes.contrast.value,'120');assert(nodes['undo-edit'].disabled);
console.log('Photo ordering, five layouts, straightening corner safety and undo restoration pass.');
