// SPDX-License-Identifier: GPL-2.0-or-later
// Copyright (c) 2026 Clint and Liz DuBois. See LICENSE and NOTICE.md.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('admin/story-studio/index.html','utf8');
const code=html.slice(html.indexOf('async function request('),html.indexOf('function applyDraft('));
async function check(response,options={}){
  let sent;const context={URL,blocked:false,fetch:async(path,opts)=>{sent={path,opts};return response}};
  vm.createContext(context);vm.runInContext(code,context);
  const result=context.request('/draft',options);
  return {result,sent};
}
(async()=>{
  const headers={get:()=> 'v1'};
  const success=await check({ok:true,status:200,headers,json:async()=>({id:'draft'})},{method:'PUT',headers:{'If-Match':'v1','Content-Type':'application/json'}});
  assert.equal((await success.result).etag,'v1');assert.equal(success.sent.opts.credentials,'include');assert.equal(success.sent.opts.headers.Accept,'application/json');assert.equal(success.sent.opts.headers['If-Match'],'v1');
  for(const status of [401,403,413]){const r=await check({status,ok:false,json:async()=>{throw Error('HTML')}});await assert.rejects(r.result,new RegExp('HTTP '+status));}
  const r=await check({status:200,redirected:true,url:'https://example/.auth/login/aad?secret=never-show',json:async()=>{throw Error('HTML')}});
  await assert.rejects(r.result,e=>e.message.includes('HTTP 200')&&e.message.includes('/.auth/login/aad')&&!e.message.includes('never-show'));
  console.log('Request checks passed: session credentials, preserved save headers, HTTP failures, sanitized redirects.');
})().catch(e=>{console.error(e);process.exitCode=1});
