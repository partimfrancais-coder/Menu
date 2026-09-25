const {chromium}=require(process.env.NODE_PATH+'/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));
 const data=JSON.parse(fs.readFileSync('tmp/category-rename-fixture.json','utf8'));let fail=false;
 await page.route('http://menu.test/**',async route=>{
  const p=new URL(route.request().url()).pathname;requests.push({path:p,method:route.request().method()});
  if(p==='/api/menus')return route.fulfill({json:data});
  if(p==='/api/runtime')return route.fulfill({json:{hosted:true}});
  if(p==='/api/ai/key')return route.fulfill({json:{configured:false,canManage:false}});
  if(p.endsWith('/reference'))return route.fulfill({path:'Kemang Lunch & Dinner 20260605A.pdf',contentType:'application/pdf',headers:{'Content-Disposition':'attachment; filename=reference.pdf'}});
  if(p.endsWith('/design-skill')){
   if(fail)return route.fulfill({status:404,json:{error:'The design skill is unavailable.'}});
   const r=data.restaurants.find(r=>p.includes(r.id));
   return route.fulfill({json:{restaurantName:r.name,skillName:'koi-menu-pdf',reference:{name:'reference.pdf'},designPrompt:'Saved prompt for '+r.name,documents:[{name:'SKILL.md',content:fs.readFileSync('ai-skills/koi-menu-pdf/SKILL.md','utf8')+'\n<script>window.injected=true</script>\n'+r.name},{name:'references/workflow.md',content:'Supporting workflow'}]}});
  }
  const file=path.join('dist',p==='/'?'index.html':p.slice(1));return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});
 });
 await page.goto('http://menu.test/');
 for(const r of data.restaurants){
  await page.locator(`[data-action=restaurant][data-id="${r.id}"]`).click();
  await page.getByRole('button',{name:'View design skill',exact:true}).click();await page.locator('#design-skill-document').waitFor();
  assert.equal(await page.locator('.skill-context strong').innerText(),r.name);
  const view=page.getByRole('link',{name:'View reference PDF'});assert.equal(await view.getAttribute('href'),'/api/ai/restaurants/'+r.id+'/reference');assert.equal(await view.getAttribute('target'),'_blank');
  const pdfDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Download reference PDF'}).click();assert.equal((await pdfDownload).suggestedFilename(),'reference.pdf');
  assert((await page.locator('.skill-content').innerText()).includes('<script>'));assert.equal(await page.evaluate(()=>window.injected),undefined);
  await page.locator('#design-skill-document').selectOption('1');assert.equal(await page.locator('.skill-content').innerText(),'Supporting workflow');
  await page.locator('#design-skill-document').selectOption('prompt');assert.equal(await page.locator('.skill-content').innerText(),'Saved prompt for '+r.name);
  const downloaded=page.waitForEvent('download');await page.getByRole('button',{name:'Download document'}).click();assert.equal((await downloaded).suggestedFilename(),'restaurant-design-prompt.md');
  await page.getByRole('button',{name:'Close',exact:true}).click();
 }
 await page.getByRole('button',{name:'View design skill',exact:true}).click();await page.locator('#design-skill-document').waitFor();await page.screenshot({path:'tmp/reference-viewer-desktop.png'});
 await page.setViewportSize({width:390,height:844});await page.screenshot({path:'tmp/reference-viewer-mobile.png'});assert(await page.evaluate(()=>document.querySelector('#dialog').scrollWidth<=innerWidth));
 await page.keyboard.press('Escape');fail=true;await page.getByRole('button',{name:'View design skill',exact:true}).click();await page.getByRole('button',{name:'Try again'}).waitFor();fail=false;await page.getByRole('button',{name:'Try again'}).click();await page.locator('#design-skill-document').waitFor();
 assert(requests.every(r=>r.method==='GET'));assert.deepEqual(errors,[]);console.log('PASS: per-restaurant viewer, document switching/download, safe text, mobile layout, error/retry, no writes or generation, no browser errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
