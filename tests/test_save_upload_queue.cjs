// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (c) 2026 Clint and Liz DuBois. See LICENSE and NOTICE.md.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('admin/story-studio/index.html','utf8');
const source=html.slice(html.indexOf('async function save()'),html.indexOf('function schedule()'));
(async()=>{
 let release;const prior=new Promise(resolve=>{release=resolve});
 let snapshots=0,requests=0;const elements={status:{},'save-notice':{hidden:true}};
 const context={draftId:'draft',editor:{},saveTimer:null,clearTimeout,uploading:0,blocked:false,saveChain:prior,lastSaved:'',lastSaveIssue:'',etag:'v1',Date,
  $:id=>elements[id],toast:()=>{},snapshot:()=>{snapshots++;return {html:'<p>Ready</p>'}},request:async()=>{requests++;return {etag:'v2'}}};
 vm.createContext(context);vm.runInContext(source,context);
 const queued=context.save();context.uploading=1;release();await queued;
 assert.equal(snapshots,0);assert.equal(requests,0);
 context.uploading=0;await context.save();assert.equal(requests,1);assert.equal(context.etag,'v2');
 context.lastSaved='';context.request=async()=>{throw Error('Temporary issue')};
 await assert.rejects(context.save(),/Temporary issue/);assert.equal(elements['save-notice'].hidden,false);assert.match(elements['save-notice'].textContent,/Temporary issue/);
 context.request=async()=>({etag:'v3'});await context.save();assert.match(elements['save-notice'].textContent,/Saved successfully.*Temporary issue/);
 console.log('Queued save pauses before snapshot during uploads; later save and persistent recovery messages verified.');
})().catch(e=>{console.error(e);process.exitCode=1});
