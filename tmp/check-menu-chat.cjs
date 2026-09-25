const {chromium}=require('C:/Users/Owner/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const context=await browser.newContext({ignoreHTTPSErrors:true,viewport:{width:1440,height:1100}});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://127.0.0.1:8779/');
  await page.locator('[name=username]').fill('alain');await page.locator('[name=password]').fill('browser-test-only');await page.locator('button[type=submit]').click();
  await page.getByRole('button',{name:'Generate menu',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Preview menu',exact:true}).count(),0);
  await page.locator('#account-api-key').fill('sk-browser-test-only-1234567890');await page.getByRole('button',{name:'Save key',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#api-key-help').textContent.includes('Key saved securely'));
  assert.equal(await page.locator('#account-api-key').inputValue(),'');
  await page.getByRole('button',{name:'Generate menu',exact:true}).click();
  await page.locator('.chat-pdf').waitFor({timeout:20000});
  await page.locator('.menu-chat textarea').fill('Increase the space between categories.');await page.getByRole('button',{name:'Send adjustment',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.chat-pdf').length===2,{},{timeout:20000});
  await page.screenshot({path:'tmp/menu-chat-desktop.png'});
  await page.getByRole('button',{name:'Close conversation'}).click();await page.reload();
  await page.getByRole('button',{name:'Generate menu',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('.chat-pdf').length===2);
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'tmp/menu-chat-mobile.png'});
  assert(await page.evaluate(()=>document.querySelector('.menu-chat').scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);console.log('PASS: key save/clear, first generation, follow-up PDF, reload recovery, mobile layout, no browser errors. Fake provider only.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
