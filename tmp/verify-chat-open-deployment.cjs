const fs=require('fs');
const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/Owner/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const c=JSON.parse(fs.readFileSync('.deployment/credentials.json','utf8'));
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage();const errors=[];const posts=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/ai/restaurants/*/conversation',async route=>{
   if(route.request().method()==='POST'){posts.push('generation');await route.abort();return;}
   await route.continue();
  });
  await page.goto(c.url);
  await page.locator('[name=username]').fill(c.username);
  await page.locator('[name=password]').fill(c.password);
  await page.locator('button[type=submit]').click();
  await page.getByRole('button',{name:'Generate menu',exact:true}).waitFor();
  const response=await page.evaluate(async()=>{const r=await fetch('/menu-chat.js');return {ok:r.ok,text:await r.text()};});assert(response.ok);
  assert.equal(response.text.replace(/\r\n/g,'\n'),fs.readFileSync('dist/menu-chat.js','utf8').replace(/\r\n/g,'\n'));
  const health=await page.evaluate(async()=>{const r=await fetch('/health');return {ok:r.ok,body:await r.json()};});assert(health.ok);assert.equal(health.body.status,'ok');
  const tracking=await page.evaluate(async()=>{const r=await fetch('/api/ai/restaurants/c9c779c5fbf843c6ad83aa9190576645/conversation');return {ok:r.ok,body:await r.json()};});
  assert(tracking.ok);assert(tracking.body.turns.length>=2);
  assert(tracking.body.turns.every(t=>t.diagnostics&&typeof t.diagnostics==='object'));
  for(let n=0;n<2;n++){
   const conversation=page.waitForResponse(r=>r.url().includes('/conversation')&&r.request().method()==='GET');
   await page.getByRole('button',{name:'Generate menu',exact:true}).click();
   assert((await conversation).ok());
   await page.locator('.menu-chat[open]').waitFor();
   await page.waitForFunction(()=>!document.querySelector('[data-chat-refresh]').disabled);
   assert.equal(posts.length,0,'Opening chat attempted generation');
   await page.getByRole('button',{name:'Close conversation',exact:true}).click();
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: live health, diagnostics API migration, deployed JavaScript matches tested file, open/reopen chat makes no generation requests, no browser errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exit(1)});
