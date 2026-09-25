const {chromium}=require(process.env.NODE_PATH+'/playwright');
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let data=JSON.parse(fs.readFileSync('tmp/category-rename-fixture.json','utf8')),writes=0,fail=false;
  await page.route('http://menu.test/**',async route=>{
   const p=new URL(route.request().url()).pathname;
   if(p==='/api/runtime')return route.fulfill({json:{hosted:false}});
   if(p==='/api/menus'){
    if(route.request().method()==='POST'){if(fail)return route.fulfill({status:500,json:{error:'Test save failure'}});data=route.request().postDataJSON();data.revision++;writes++;}
    return route.fulfill({json:data});
   }
   const file=path.join('dist',p==='/'?'index.html':p.slice(1));
   return fs.existsSync(file)?route.fulfill({path:file}):route.fulfill({status:404,body:''});
  });
  await page.goto('http://menu.test/');await page.getByRole('button',{name:'Products',exact:true}).click();
  const cat=data.productCategories[0],old=cat.name,originalProducts=JSON.stringify(data.products);
  const open=()=>page.locator(`[data-action="rename-product-category"][data-id="${cat.id}"]`).click();
  await open();assert.equal(await page.locator('#category-rename-name').inputValue(),old);
  await page.locator('#category-rename-name').fill('Cancelled name');await page.locator('#category-rename-name').press('Escape');assert.equal(writes,0);
  await open();await page.locator('#category-rename-name').fill(data.productCategories[1].name);await page.locator('.category-rename button[type=submit]').click();
  assert.match(await page.locator('.category-rename-error').innerText(),/already exists/);assert.equal(writes,0);
  await page.locator('#category-rename-name').fill('   ');await page.locator('.category-rename button[type=submit]').click();assert.match(await page.locator('.category-rename-error').innerText(),/Enter/);
  await page.locator('#category-rename-name').fill('Elegant category');await page.locator('#category-rename-name').press('Enter');
  await page.getByRole('button',{name:'Rename Elegant category',exact:true}).waitFor();assert.equal(writes,1);assert.equal(JSON.stringify(data.products),originalProducts);
  for(const r of data.restaurants)for(const c of r.categories)if(c.catalogCategoryId===cat.id)assert.equal(c.name,'Elegant category');
  await page.reload();await page.getByRole('button',{name:'Products',exact:true}).click();await open();
  await page.screenshot({path:'tmp/category-rename-desktop.png'});
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Cancel',exact:true}).click();await open();await page.screenshot({path:'tmp/category-rename-mobile.png'});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.getByRole('button',{name:'Cancel',exact:true}).click();assert.equal(writes,1);
  await open();await page.locator('#category-rename-name').fill('Retry category');fail=true;await page.locator('#category-rename-name').press('Enter');
  await page.getByRole('button',{name:'Retry save',exact:true}).waitFor();assert.equal(writes,1);
  fail=false;await page.getByRole('button',{name:'Retry save',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.save-status').textContent.includes('Saved to this computer'));assert.equal(writes,2);
  assert.deepEqual(errors,[]);console.log('PASS: rename, Escape/Cancel, duplicates, blank names, reload, shared propagation, product preservation, mobile overflow, save failure/retry, no browser errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
