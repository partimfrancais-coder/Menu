'use strict';
const $ = (s, root=document) => root.querySelector(s);
const app=$('#app'), modal=$('#dialog');
let data, restaurantId, categoryId, itemId, search='', filter='all', dirty=false, busy=false, unsaved=false, saveError='';
const labels=['Vegetarian','Spicy','New menu','Takes more than 15 mins','With jasmine rice','Choice of white or red rice','With baby potatoes','With mashed potato','With French or Belgian fries','With mixed salad','With baguette'];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const id=()=>crypto.randomUUID();
const restaurant=()=>data.restaurants.find(r=>r.id===restaurantId);
const category=()=>restaurant().categories.find(c=>c.id===categoryId);
const item=()=>category()?.items.find(i=>i.id===itemId);
const allItems=()=>restaurant().categories.flatMap(c=>c.items);
const fmt=n=>new Intl.NumberFormat('en-US',{maximumFractionDigits:2}).format(n);
const button=(action,text,extra='',cls='')=>`<button type="button" data-action="${action}" ${extra} class="${cls}">${text}</button>`;
const input=(name,label,value='',type='text',extra='')=>`<label class="field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('visible');setTimeout(()=>$('#toast').classList.remove('visible'),3500);}
function canLeave(){return !dirty||confirm('You have unsaved item edits. Discard those edits?');}
function selectRestaurant(rid){restaurantId=rid;categoryId=restaurant().categories[0]?.id;itemId=category()?.items[0]?.id;search='';filter='all';dirty=false;}
function selectCategory(cid){categoryId=cid;itemId=category()?.items[0]?.id;search='';dirty=false;}
function status(){return busy?'Saving…':saveError?'Save failed':unsaved?'Changes not saved':'Saved to this computer';}
function render(){
 const r=restaurant(),c=category(),i=item(),items=allItems(),review=items.filter(i=>!i.reviewed).length;
 app.innerHTML=`<aside class="sidebar"><a class="brand" href="/" aria-label="Menu Studio home"><span class="brand-mark">KOI</span><span>Menu Studio<small>RESTAURANT WORKSPACE</small></span></a>
 <div class="nav-label">RESTAURANTS ${button('add-restaurant','+','aria-label="Add restaurant"','icon-button')}</div>
 <nav aria-label="Restaurants">${data.restaurants.map(x=>`<button class="restaurant ${x.id===r.id?'selected':''}" data-action="restaurant" data-id="${x.id}" aria-current="${x.id===r.id?'true':'false'}"><span class="restaurant-initial">${esc(x.location.slice(0,1)||x.name.slice(0,1))}</span><span>${esc(x.name)}<small>${esc(x.menuTitle)}</small></span>${x.id===r.id?'<span class="active-bar"></span>':''}</button>`).join('')}</nav>
 <div class="sidebar-bottom"><p>YOUR MENUS, IN ONE PLACE</p><span>Each restaurant has its own dishes, prices and details.</span><div class="backup-actions">${button('backup','Export backup')}${button('restore','Restore backup')}</div><small>Stored on this computer</small></div></aside>
 <div class="workspace"><header class="topbar"><div class="breadcrumb">Restaurants <span>/</span> ${esc(r.name)}</div><div class="save-status ${saveError?'error':''}" role="status">${status()}${saveError?button('retry','Retry save'):''}</div></header>
 ${saveError?`<div class="error-banner" role="alert">${esc(saveError)} Export a backup to keep a copy of your changes.</div>`:''}
 <main><div class="page-heading"><div><div class="eyebrow">MENU EDITOR</div><h1>${esc(r.name)}</h1><p>${esc(r.menuTitle)} <span class="dot-sep">·</span> ${items.length} items <span class="dot-sep">·</span> ${r.categories.length} categories</p></div><div class="heading-actions">${button('settings','Restaurant settings','','secondary')}${button('preview','Preview menu','','primary')}</div></div>
 <div class="menu-strip"><div><strong>${esc(r.currency)} × ${fmt(r.priceUnit)}</strong><span>Price 95 = ${esc(r.currency)} ${fmt(95*r.priceUnit)}</span></div><div><strong>${fmt(r.serviceCharge)}% service · ${fmt(r.tax)}% tax</strong><span>${esc(r.dietaryNote||'No menu-wide dietary note')}</span></div><div class="review-summary"><strong>${review?review+' items to review':'All items reviewed'}</strong><span>${r.source?'Imported from the supplied menu':'Your restaurant menu'}</span></div>${r.source?`<a class="source-link" target="_blank" rel="noopener" href="/sources/${encodeURIComponent(r.source)}">Original PDF ↗</a>`:''}</div>
 <div class="editor-grid"><section class="categories"><div class="section-heading"><h2>Categories</h2>${button('add-category','+','aria-label="Add category"','icon-button')}</div><nav aria-label="Menu categories">${r.categories.map(cat=>`<button data-action="category" data-id="${cat.id}" class="category ${cat.id===categoryId?'active':''}" aria-current="${cat.id===categoryId?'true':'false'}"><span>${esc(cat.name)}</span><span>${cat.items.length}</span></button>`).join('')||'<p class="empty-small">Add your first category.</p>'}</nav></section>
 <section class="items-panel"><div class="section-heading"><div><div class="eyebrow">CATEGORY</div><h2>${esc(c?.name||'Create a category')}</h2></div>${c?button('edit-category','Edit','','text-button'):''}</div>${c?.notes?`<p class="category-note">${esc(c.notes)}</p>`:''}<div class="item-tools"><label class="search"><span class="sr-only">Search this restaurant’s items</span><input id="search" type="search" placeholder="Search all items…" value="${esc(search)}"></label><select id="filter" aria-label="Filter items"><option value="all" ${filter==='all'?'selected':''}>All items</option><option value="review" ${filter==='review'?'selected':''}>To review</option><option value="hidden" ${filter==='hidden'?'selected':''}>Hidden</option></select></div>
 <div class="list-caption"><span>ITEM</span><span>PRICE</span></div><div id="item-list">${listHTML()}</div>${c?button('add-item','+ Add item','','add-item'):''}</section>
 <section class="details-panel">${i?detailHTML(i):`<div class="empty"><span class="empty-symbol">＋</span><h2>${c?'Your menu starts here':'Organize your menu'}</h2><p>${c?'Add an item to set its price, description and details.':'Create a category, then add your dishes.'}</p>${button(c?'add-item':'add-category',c?'Add first item':'Add category','','primary')}</div>`}</section></div>
 <footer class="workspace-footer">Menu content workspace <span>PDF design and export will be added in the next phase.</span></footer></main></div>`;
 app.classList.toggle('saving',busy);
 if(busy)app.querySelectorAll('button,input,select,textarea').forEach(control=>control.disabled=true);
}
function listHTML(){
 let pairs=search?restaurant().categories.flatMap(c=>c.items.map(i=>({c,i}))):(category()?.items||[]).map(i=>({c:category(),i}));
 pairs=pairs.filter(({i})=>(!search||[i.name,i.description,...i.tags].join(' ').toLowerCase().includes(search.toLowerCase()))&&(filter==='all'||filter==='review'&&!i.reviewed||filter==='hidden'&&!i.available));
 return pairs.map(({c,i})=>`<button class="item-row ${i.id===itemId?'selected':''}" data-action="item" data-id="${i.id}" data-category="${c.id}"><span><strong>${esc(i.name)}</strong><small>${search?esc(c.name)+' · ':''}${esc(i.description||'No description')}</small><span class="row-tags">${!i.available?'<span class="mini-tag">Hidden</span>':''}${!i.reviewed?'<span class="review-dot">To review</span>':''}${i.tags.includes('Vegetarian')?'<span class="mini-tag green">Vegetarian</span>':''}</span></span><span class="item-price">${fmt(i.price)}</span></button>`).join('')||'<div class="empty-small">No items here. Try another filter or add an item.</div>';
}
function detailHTML(i){return `<form id="item-form"><div class="detail-heading"><span class="eyebrow">ITEM DETAILS</span><div>${button('duplicate-item','Duplicate','','text-button')}${button('delete-item','Delete','','text-button danger')}</div></div><h2>${esc(i.name)}</h2><div class="review-notice">${i.reviewed?'Reviewed and ready for your menu.':'Check the imported details against your original menu.'}</div>
 ${input('name','Item name',i.name,'text','required maxlength="200"')}<label class="field">Description<textarea name="description" rows="3" maxlength="3000">${esc(i.description)}</textarea></label>
 <div class="two-fields">${input('price',`Price (${esc(restaurant().currency)} × ${fmt(restaurant().priceUnit)})`,i.price,'number','min="0" step="0.01" required')}<label class="field">Category<select name="category">${restaurant().categories.map(c=>`<option value="${c.id}" ${c.id===categoryId?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label></div>
 <div class="subheading"><h3>Options & add-ons</h3>${button('add-option','+ Add','','text-button')}</div><p class="hint">Variants have their own price. Add-ons are extra.</p><div id="options">${i.options.map(optionHTML).join('')}</div>
 <fieldset><legend>Labels & serving details</legend><div class="tags">${[...new Set([...labels,...i.tags])].map(t=>`<label class="tag"><input type="checkbox" name="tag" value="${esc(t)}" ${i.tags.includes(t)?'checked':''}><span>${esc(t)}</span></label>`).join('')}</div></fieldset>${input('customTags','Additional labels (comma separated)','','text','placeholder="e.g. Contains nuts, Gluten-free option"')}
 <div class="subheading"><h3>Item image</h3>${i.image?button('remove-image','Remove','','text-button danger'):''}</div><label class="image-upload">${i.image?`<img src="${esc(i.image)}" alt="${esc(i.name)}">`:'<span>＋</span>'}<span>${i.image?'Replace image':'Upload a dish image'}<small>JPG, PNG or WebP · up to 3 MB</small></span><input type="file" id="item-image" accept="image/png,image/jpeg,image/webp"><input type="hidden" name="image" value="${esc(i.image)}"></label>
 <label class="field">Notes / specifics<textarea name="notes" rows="2" placeholder="Preparation details, portion size, or notes for the next revision">${esc(i.notes)}</textarea></label>
 <label class="check-row"><input type="checkbox" name="available" ${i.available?'checked':''}><span>Show this item on the menu</span></label><label class="check-row"><input type="checkbox" name="reviewed" ${i.reviewed?'checked':''}><span>I have reviewed this item’s details</span></label>
 <div class="detail-bottom"><div class="reorder">${button('item-up','↑','aria-label="Move item up" title="Move up"','icon-button')}${button('item-down','↓','aria-label="Move item down" title="Move down"','icon-button')}</div><span id="edit-state">No unsaved edits</span><button class="primary" type="submit">Save item</button></div></form>`;}
function optionHTML(o={name:'',price:0,kind:'Variant'}){return `<div class="option-row"><input aria-label="Option name" class="option-name" placeholder="Option name" value="${esc(o.name)}" required><select aria-label="Option type" class="option-kind"><option ${o.kind==='Variant'?'selected':''}>Variant</option><option ${o.kind==='Add-on'?'selected':''}>Add-on</option></select><input aria-label="Option price" class="option-price" type="number" min="0" step="0.01" value="${esc(o.price)}" required>${button('remove-option','×','aria-label="Remove option"','icon-button')}</div>`;}
async function save(){
 busy=true;unsaved=true;saveError='';render();
 try{const res=await fetch('/api/menus',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const out=await res.json();if(!res.ok)throw Error(out.error||'Unable to save.');data.revision=out.revision;unsaved=false;}
 catch(e){saveError=e.message;}
 finally{busy=false;render();}
 return !saveError;
}
function openDialog(title,body,submit='Save changes',wide=false){modal.className=wide?'wide':'';modal.innerHTML=`<form id="modal-form"><header><h2>${esc(title)}</h2>${button('close-dialog','×','aria-label="Close dialog"','icon-button')}</header><div class="modal-body">${body}</div><footer>${button('close-dialog','Cancel','','secondary')}<button class="primary" type="submit">${esc(submit)}</button></footer></form>`;modal.showModal();}
function finishDialog(){modal.close();modal.innerHTML='';}
function newItem(){return {id:id(),name:'New item',description:'',price:0,tags:[],options:[],notes:'',image:'',available:true,reviewed:true};}
function cloneRestaurant(r){const copy=structuredClone(r);copy.id=id();copy.categories.forEach(c=>{c.id=id();c.items.forEach(i=>i.id=id());});return copy;}
function backup(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download=`menu-studio-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
async function imageData(file){if(!file)return '';if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>3*1024*1024)throw Error('Choose a JPG, PNG or WebP image smaller than 3 MB.');return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Could not read this image.'));reader.readAsDataURL(file);});}
let dialogAction='';
async function action(name,el){
 if(busy){toast('Please wait for the current save to finish.');return;}
 if(name==='close-dialog'){finishDialog();return;}
 if(name==='backup'){backup();return;}
 if(name==='retry'){await save();return;}
 if(name==='add-option'){$('#options').insertAdjacentHTML('beforeend',optionHTML());setDirty();return;}
 if(name==='remove-option'){el.closest('.option-row').remove();setDirty();return;}
 if(name==='remove-image'){$('[name=image]').value='';const img=$('.image-upload img');if(img)img.remove();setDirty();return;}
 if(!canLeave())return;
 dirty=false;render();
 const r=restaurant(),c=category(),i=item();
 if(name==='restaurant'){selectRestaurant(el.dataset.id);render();return;}
 if(name==='category'){selectCategory(el.dataset.id);render();return;}
 if(name==='item'){categoryId=el.dataset.category;itemId=el.dataset.id;render();return;}
 if(name==='add-item'){if(!c)return;const x=newItem();c.items.push(x);itemId=x.id;await save();$('[name=name]').focus();$('[name=name]').select();return;}
 if(name==='duplicate-item'){const x=structuredClone(i);x.id=id();x.name+=' (copy)';c.items.splice(c.items.indexOf(i)+1,0,x);itemId=x.id;await save();return;}
 if(name==='delete-item'){if(!confirm(`Delete “${i.name}” from ${r.name}?`))return;c.items=c.items.filter(x=>x.id!==i.id);itemId=c.items[0]?.id;await save();return;}
 if(name==='item-up'||name==='item-down'){const pos=c.items.indexOf(i),next=pos+(name==='item-up'?-1:1);if(next>=0&&next<c.items.length){[c.items[pos],c.items[next]]=[c.items[next],c.items[pos]];await save();}return;}
 if(name==='category-up'||name==='category-down'){const pos=r.categories.indexOf(c),next=pos+(name==='category-up'?-1:1);if(next>=0&&next<r.categories.length){[r.categories[pos],r.categories[next]]=[r.categories[next],r.categories[pos]];finishDialog();await save();}return;}
 if(name==='delete-category'){if(!confirm(`Delete “${c.name}” and its ${c.items.length} items?`))return;r.categories=r.categories.filter(x=>x.id!==c.id);selectCategory(r.categories[0]?.id);finishDialog();await save();return;}
 if(name==='delete-restaurant'){if(data.restaurants.length===1){toast('Keep at least one restaurant.');return;}if(!confirm(`Delete ${r.name} and its entire menu? Export a backup first if you need to keep it.`))return;data.restaurants=data.restaurants.filter(x=>x.id!==r.id);selectRestaurant(data.restaurants[0].id);finishDialog();await save();return;}
 render();dialogAction=name;
 if(name==='add-restaurant'){openDialog('Add restaurant',`${input('name','Restaurant name','','text','required maxlength="200"')}${input('location','Location')}<label class="field">Starting menu<select name="template"><option value="">Start with an empty menu</option>${data.restaurants.map(r=>`<option value="${r.id}">Copy ${esc(r.name)}’s menu</option>`).join('')}</select></label><p class="hint">Copied menus are independent. Changes won’t affect the original restaurant.</p>`,'Create restaurant');}
 if(name==='settings'){openDialog('Restaurant settings',`${input('name','Restaurant name',r.name,'text','required')}${input('location','Location',r.location)}${input('menuTitle','Menu title',r.menuTitle,'text','required')}<div class="two-fields">${input('currency','Currency',r.currency,'text','required maxlength="12"')}${input('priceUnit','Price multiplier',r.priceUnit,'number','required min="1" step="1"')}</div><div class="two-fields">${input('serviceCharge','Service charge (%)',r.serviceCharge,'number','required min="0" max="100" step="0.01"')}${input('tax','Tax (%)',r.tax,'number','required min="0" max="100" step="0.01"')}</div>${input('dietaryNote','Menu-wide dietary note',r.dietaryNote)}<label class="field">Footer / pricing note<textarea name="footer" rows="3">${esc(r.footer)}</textarea></label><p class="hint">Update the footer wording if you change the price multiplier, tax or service charge.</p><label class="field">Restaurant logo<input type="file" id="logo-file" accept="image/png,image/jpeg,image/webp"></label>${r.logo?'<label class="check-row"><input type="checkbox" name="removeLogo">Remove current logo</label>':''}<hr>${button('delete-restaurant','Delete restaurant','','text-button danger')}`);}
 if(name==='add-category'||name==='edit-category'){openDialog(name==='add-category'?'Add category':'Edit category',`${input('name','Category name',name==='edit-category'?c.name:'','text','required maxlength="200"')}<label class="field">Category notes<textarea name="notes" rows="3">${esc(name==='edit-category'?c.notes:'')}</textarea></label>${name==='edit-category'?`<div class="dialog-actions">${button('category-up','↑ Move up','','secondary')}${button('category-down','↓ Move down','','secondary')}${button('delete-category','Delete category','','text-button danger')}</div>`:''}`);}
 if(name==='preview'){modal.className='wide';modal.innerHTML=`<header><div><span class="eyebrow">CONTENT PREVIEW</span><h2>${esc(r.name)}</h2></div>${button('close-dialog','×','aria-label="Close preview"','icon-button')}</header><div class="preview"><div class="preview-heading">${r.logo?`<img src="${esc(r.logo)}" alt="${esc(r.name)} logo">`:''}<h2>${esc(r.menuTitle)}</h2><p>${esc(r.dietaryNote)}</p><small>Prices in ${esc(r.currency)} × ${fmt(r.priceUnit)}. This is a content preview; the final PDF layout comes later.</small></div><div class="preview-grid">${r.categories.map(c=>`<section><h3>${esc(c.name)}</h3>${c.notes?`<p class="hint">${esc(c.notes)}</p>`:''}${c.items.filter(i=>i.available).map(i=>`<article>${i.image?`<img class="dish-thumb" src="${esc(i.image)}" alt="${esc(i.name)}">`:''}<div class="preview-item"><strong>${esc(i.name)}</strong><b>${fmt(i.price)}</b></div><p>${esc(i.description)}</p>${i.options.map(o=>`<p class="preview-option">${esc(o.name)} <b>${o.kind==='Add-on'?'+':''}${fmt(o.price)}</b></p>`).join('')}<small>${esc(i.tags.join(' · '))}</small></article>`).join('')||'<p class="hint">No visible items</p>'}</section>`).join('')}</div><p class="preview-footer">${esc(r.footer)}</p></div>`;modal.showModal();}
 if(name==='restore'){openDialog('Restore a backup','<p>This replaces all restaurants and menu data with a previously exported backup. Export your current data first if you want to keep a copy.</p><label class="field">Menu Studio backup<input type="file" name="backup" accept="application/json,.json" required></label>','Restore backup');}
}
function setDirty(){dirty=true;const state=$('#edit-state');if(state)state.textContent='Unsaved edits';}
document.addEventListener('click',e=>{const el=e.target.closest('[data-action]');if(el)action(el.dataset.action,el).catch(err=>toast(err.message));});
app.addEventListener('input',e=>{if(e.target.id==='search'){search=e.target.value;$('#item-list').innerHTML=listHTML();return;}if(e.target.closest('#item-form'))setDirty();});
app.addEventListener('change',async e=>{if(e.target.id==='filter'){filter=e.target.value;$('#item-list').innerHTML=listHTML();return;}if(e.target.id==='item-image'){const form=e.target.closest('form');try{const image=await imageData(e.target.files[0]);if(!image||!form.isConnected)return;$('[name=image]',form).value=image;let img=$('.image-upload img',form);if(!img){img=document.createElement('img');$('.image-upload',form).prepend(img);}img.src=image;img.alt='Selected dish image';setDirty();}catch(err){toast(err.message);}}});
app.addEventListener('submit',async e=>{if(e.target.id!=='item-form')return;e.preventDefault();if(busy)return;const form=e.target,fields=new FormData(form),i=item(),old=category();
 const name=fields.get('name').trim();if(!name){toast('Enter an item name.');return;}
 const options=[...form.querySelectorAll('.option-row')].map(row=>({name:$('.option-name',row).value.trim(),price:Number($('.option-price',row).value),kind:$('.option-kind',row).value}));
 if(options.some(o=>!o.name)){toast('Enter a name for every option.');return;}
 Object.assign(i,{name,description:fields.get('description').trim(),price:Number(fields.get('price')),notes:fields.get('notes').trim(),image:fields.get('image'),available:fields.has('available'),reviewed:fields.has('reviewed'),tags:[...new Set([...fields.getAll('tag'),...fields.get('customTags').split(',').map(s=>s.trim()).filter(Boolean)])],options});
 if(fields.get('category')!==categoryId){old.items=old.items.filter(x=>x.id!==i.id);categoryId=fields.get('category');category().items.push(i);}dirty=false;await save();if(!saveError)toast('Item saved');
});
modal.addEventListener('submit',async e=>{e.preventDefault();if(busy)return;const f=new FormData(e.target),r=restaurant();
 try{
 if(['settings','add-restaurant','add-category','edit-category'].includes(dialogAction)&&!f.get('name').trim()){toast('Enter a name.');return;}
 if(dialogAction==='settings'){
  const logoFile=$('#logo-file').files[0],logo=logoFile?await imageData(logoFile):f.has('removeLogo')?'':r.logo;
  Object.assign(r,{name:f.get('name').trim(),location:f.get('location').trim(),menuTitle:f.get('menuTitle').trim(),currency:f.get('currency').trim(),priceUnit:Number(f.get('priceUnit')),serviceCharge:Number(f.get('serviceCharge')),tax:Number(f.get('tax')),dietaryNote:f.get('dietaryNote').trim(),footer:f.get('footer').trim(),logo});
 }
 if(dialogAction==='add-restaurant'){
  const template=data.restaurants.find(r=>r.id===f.get('template'));
  const x=template?cloneRestaurant(template):{id:id(),menuTitle:'Lunch & Dinner',currency:'IDR',priceUnit:1000,serviceCharge:10,tax:10,footer:'',dietaryNote:'',logo:'',source:'',categories:[]};
  x.name=f.get('name').trim();x.location=f.get('location').trim();x.source='';data.restaurants.push(x);selectRestaurant(x.id);
 }
 if(dialogAction==='add-category'){const c={id:id(),name:f.get('name').trim(),notes:f.get('notes').trim(),items:[]};r.categories.push(c);selectCategory(c.id);}
 if(dialogAction==='edit-category'){category().name=f.get('name').trim();category().notes=f.get('notes').trim();}
 if(dialogAction==='restore'){
  const file=f.get('backup');if(file.size>25*1024*1024)throw Error('Backup is too large.');
  const restored=JSON.parse(await file.text());
  if(restored.version!==1||!Array.isArray(restored.restaurants)||!restored.restaurants.length)throw Error('This is not a Menu Studio backup.');
  if(!confirm('Replace every restaurant with the menus in this backup?'))return;
  restored.revision=data.revision;busy=true;
  let response,out;
  try{response=await fetch('/api/menus',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(restored)});out=await response.json();}finally{busy=false;}
  if(!response.ok)throw Error(out.error||'Restore failed.');
  restored.revision=out.revision;data=restored;unsaved=false;saveError='';selectRestaurant(data.restaurants[0].id);finishDialog();render();toast('Backup restored');return;
 }
 finishDialog();await save();
 }catch(err){toast(err.message||'Could not read the backup.');}
});
window.addEventListener('beforeunload',e=>{if(dirty||unsaved||busy){e.preventDefault();e.returnValue='';}});
fetch('/api/menus').then(async res=>{if(!res.ok)throw Error('Could not load saved menus.');return res.json();}).then(result=>{data=result;selectRestaurant(data.restaurants[0].id);render();}).catch(e=>{app.innerHTML=`<div class="load-error"><h1>Unable to open your menus</h1><p>${esc(e.message)}</p><p>Start the local Menu Studio server and reload this page.</p><a href="/">Reload</a></div>`;});
