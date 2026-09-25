const {chromium}=require(process.env.NODE_PATH+'/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],posts=[];
  page.on('pageerror',e=>errors.push(e.message));
  const data=JSON.parse(fs.readFileSync('tmp/category-rename-fixture.json','utf8'));
  let active=1,latest=1,turns=[],polls=0;
  await page.route('https://menu.test/**',async route=>{
   const request=route.request(),url=new URL(request.url()),p=url.pathname,method=request.method();
   if(method!=='GET')posts.push(p);
   if(p==='/api/menus')return route.fulfill({json:data});
   if(p==='/api/runtime')return route.fulfill({json:{hosted:true}});
   if(p==='/api/ai/key')return route.fulfill({json:{configured:true,canManage:false}});
   if(p.endsWith('/design-skill')){
    const number=Number(url.searchParams.get('version')||active),r=data.restaurants.find(r=>p.includes(r.id));
    return route.fulfill({json:{restaurantName:r.name,skillName:'koi-menu-pdf',version:number,activeVersion:active,
     versions:Array.from({length:latest},(_,index)=>({number:index+1,label:'v'+(index+1),active:index+1===active})),
     reference:{name:'reference.pdf'},designPrompt:'Saved prompt',documents:[{name:'SKILL.md',content:'# Version '+number+'\n\nUse this PDF.'}]}});
   }
   if(p.endsWith('/reference'))return route.fulfill({path:'Kemang Lunch & Dinner 20260605A.pdf',contentType:'application/pdf',headers:{'Content-Disposition':'attachment; filename=reference.pdf'}});
   if(p.endsWith('/design-chat')){
    if(method==='POST'){
     const body=request.postDataJSON();turns.push({id:'chat-'+turns.length,parent:body.parent,prompt:body.message,status:'running',answer:'',error:'',version:null});polls=0;
    }else if(turns.at(-1)?.status==='running'&&++polls>=2){latest++;Object.assign(turns.at(-1),{status:'completed',version:latest,answer:'Created the next skill and PDF.'});}
    return route.fulfill({json:{turns}});
   }
   if(p.endsWith('/design-versions')&&method==='POST'){latest++;return route.fulfill({json:{version:latest,activeVersion:active,versions:[]}});}
   if(p.endsWith('/activate')){active=Number(p.split('/').at(-2));return route.fulfill({json:{activeVersion:active,versions:[]}});}
   const file=path.join('dist',p==='/'?'index.html':p.slice(1));
   return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});
  });
  await page.goto('https://menu.test/');await page.getByRole('button',{name:'View design skill'}).click();
  await page.getByRole('button',{name:'v1 · Active'}).waitFor();
  assert.equal(await page.locator('.skill-content').isVisible(),false);
  assert.equal(await page.locator('.skill-reference').isVisible(),false);
  await page.getByRole('button',{name:'v1 · Active'}).click();
  await page.locator('.skill-content').waitFor({state:'visible'});
  assert.equal(await page.locator('.skill-content').innerText(),'# Version 1\n\nUse this PDF.');
  await page.locator('.design-create summary').click();
  await page.locator('#design-upload-skill').setInputFiles({name:'SKILL.md',mimeType:'text/markdown',buffer:Buffer.from('# New skill')});
  await page.locator('#design-upload-reference').setInputFiles({name:'reference.pdf',mimeType:'application/pdf',buffer:fs.readFileSync('Kemang Lunch & Dinner 20260605A.pdf')});
  await page.getByRole('button',{name:'Create version from files'}).click();
  await page.getByRole('button',{name:'Activate v2'}).waitFor();assert.equal(active,1);
  await page.getByRole('button',{name:'Activate v2'}).click();await page.getByRole('button',{name:'v2 · Active'}).waitFor();assert.equal(active,2);
  await page.locator('#design-version-message').fill('Make the headings bolder.');await page.getByRole('button',{name:'Create next version with AI'}).click();
  await page.getByRole('button',{name:'View v3'}).waitFor({timeout:15000});
  await page.getByRole('button',{name:'View v3'}).click();await page.getByRole('button',{name:'Activate v3'}).waitFor();assert.equal(active,2);
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:'tmp/design-versions-mobile.png'});
  assert(await page.evaluate(()=>document.querySelector('#dialog').scrollWidth<=innerWidth));
  await page.getByRole('button',{name:'v1',exact:true}).click();await page.getByRole('button',{name:'Activate v1'}).waitFor();
  assert.deepEqual(errors,[]);assert(posts.some(p=>p.endsWith('/design-versions'))&&posts.some(p=>p.endsWith('/design-chat')));
  console.log('PASS: v1, upload pair, activate v2, AI chat creates inactive v3, switch versions, mobile layout.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exit(1)});
