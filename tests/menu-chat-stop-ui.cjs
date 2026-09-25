const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let status='running',cancelCalls=0,fail=false;
  const chat=()=>({turns:[{id:'turn-1',prompt:'Generate menu',status,created:Date.now()/1000,answer:'Generation stopped.',previews:[]}]});
  await page.route('http://menu.test/**',async route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/')return route.fulfill({contentType:'text/html',body:'<html><head><link rel="stylesheet" href="/styles.css"></head><body><script src="/menu-chat.js"></script></body></html>'});
   if(path==='/styles.css'||path==='/menu-chat.js')return route.fulfill({path:'dist'+path,contentType:(path.endsWith('.js')?'text/javascript':'text/css')+'; charset=utf-8'});
   if(path==='/api/ai/key')return route.fulfill({json:{configured:true}});
   if(path.endsWith('/cancel')){
    assert.equal(route.request().method(),'POST');cancelCalls++;
    if(fail)return route.fulfill({status:503,json:{error:'Unable to stop. Try again.'}});
    status='cancelling';return route.fulfill({status:202,json:chat()});
   }
   return route.fulfill({json:chat()});
  });
  await page.goto('http://menu.test/');
  await page.evaluate(()=>MenuChat.open({id:'test',name:'KOI Mahakam'},()=>1));
  const stop=page.getByRole('button',{name:'Stop generation',exact:true});
  await stop.waitFor();
  await page.screenshot({path:'tmp/menu-chat-stop-desktop.png'});
  fail=true;await stop.click();
  await page.getByText('Unable to stop. Try again.').waitFor();
  assert.equal(await stop.isEnabled(),true);
  fail=false;await stop.click();
  const stopping=page.getByRole('button',{name:'Stopping…',exact:true});
  await page.waitForFunction(()=>document.querySelector('[data-chat-stop]').disabled);
  await stopping.waitFor();assert.equal(await stopping.isDisabled(),true);
  assert.equal(cancelCalls,2);
  await page.getByRole('button',{name:'Close conversation'}).click();
  await page.evaluate(()=>MenuChat.open({id:'test',name:'KOI Mahakam'},()=>1));
  await stopping.waitFor();
  status='cancelled';
  await page.getByRole('button',{name:'Check status'}).click();
  await page.getByText('Generation stopped.',{exact:true}).waitFor();
  assert.equal(await page.locator('[data-chat-stop]').isVisible(),false);
  assert.equal(await page.getByRole('button',{name:'Send adjustment',exact:true}).isEnabled(),true);
  status='running';await page.getByRole('button',{name:'Check status'}).click();
  await stop.waitFor();await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'tmp/menu-chat-stop-mobile.png'});
  assert(await page.evaluate(()=>document.querySelector('.menu-chat').scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);
  console.log('PASS: Stop button, retry, stopping state, reopen recovery, completion, mobile layout. Mock API only.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
