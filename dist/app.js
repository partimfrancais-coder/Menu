'use strict';
const $ = (s, root=document) => root.querySelector(s);
const app=$('#app'), modal=$('#dialog');
let data, restaurantId, categoryId, itemId, search='', filter='all', dirty=false, busy=false, unsaved=false, saveError='', hosted=false, currentUser=null;
let view='restaurants', productId=null, productSearch='', productCategoryId='';
let catalogDirty=false, pendingIconReads=0;
let apiKeyDraft='';
let designSkillView=null, designChatTurns=[], designChatTimer=null, designChatBusy=false, designStudioEpoch=0;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const id=()=>crypto.randomUUID();
const restaurant=()=>data.restaurants.find(r=>r.id===restaurantId);
const category=()=>restaurant().categories.find(c=>c.id===categoryId);
const item=()=>view==='products'?data.products.find(p=>p.id===productId):category()?.items.find(i=>i.id===itemId);
const labelContext=()=>({name:'all products',tagCatalog:data.productTags,categories:[{items:data.products}]});
const allItems=()=>restaurant().categories.flatMap(c=>c.items);
const fmt=n=>new Intl.NumberFormat('en-US',{maximumFractionDigits:2}).format(n);
const button=(action,text,extra='',cls='')=>`<button type="button" data-action="${action}" ${extra} class="${cls}">${text}</button>`;
const input=(name,label,value='',type='text',extra='')=>`<label class="field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('visible');setTimeout(()=>$('#toast').classList.remove('visible'),3500);}
function canLeave(){return !dirty||confirm('You have unsaved item edits. Discard those edits?');}
function selectRestaurant(rid){view='restaurants';restaurantId=rid;categoryId=restaurant().categories[0]?.id;itemId=category()?.items[0]?.id;search='';filter='all';dirty=false;}
function selectCategory(cid){categoryId=cid;itemId=category()?.items[0]?.id;search='';dirty=false;}
function status(){return busy?'Saving…':saveError?'Save failed':unsaved?'Changes not saved':hosted?'Saved online':'Saved to this computer';}
function render(){
 const r=restaurant(),c=category(),i=item(),items=allItems(),review=items.filter(i=>!i.reviewed).length;
 MenuCatalog.initialize(r);
 app.innerHTML=`<aside class="sidebar"><a class="brand" href="/" aria-label="Menu Studio home"><span class="brand-mark">KOI</span><span>Menu Studio<small>RESTAURANT WORKSPACE</small></span></a>
 ${button('products','Products',`aria-current="${view==='products'}"`,'restaurant products-nav '+(view==='products'?'selected':''))}
 <div class="nav-label">RESTAURANTS ${button('add-restaurant','+','aria-label="Add restaurant"','icon-button')}</div>
 <nav aria-label="Restaurants">${data.restaurants.map(x=>`<button class="restaurant ${view==='restaurants'&&x.id===r.id?'selected':''}" data-action="restaurant" data-id="${x.id}" aria-current="${view==='restaurants'&&x.id===r.id?'true':'false'}"><span class="restaurant-initial">${esc(x.location.slice(0,1)||x.name.slice(0,1))}</span><span>${esc(x.name)}<small>${esc(x.menuTitle)}</small></span>${view==='restaurants'&&x.id===r.id?'<span class="active-bar"></span>':''}</button>`).join('')}</nav>
 <div class="sidebar-bottom"><p>YOUR MENUS, IN ONE PLACE</p><span>One product catalog, used across your restaurants.</span><div class="backup-actions">${button('backup','Export backup')}${button('restore','Restore backup')}${hosted?button('logout','Sign out'):''}</div><small>${hosted?'Saved in your private workspace':'Stored on this computer'}</small></div></aside>
 <div class="workspace"><header class="topbar"><div class="breadcrumb">${currentUser?.role==='admin'?'<a href="/users">Manage users</a> <span>/</span> ':''}Restaurants <span>/</span> ${esc(r.name)}</div><div class="save-status ${saveError?'error':''}" role="status">${status()}${saveError?button('retry','Retry save'):''}</div></header>
 ${currentUser?.canManageApiKey?`<section class="api-key-placeholder" aria-label="API key"><label class="field" for="account-api-key">OpenAI API key<input id="account-api-key" type="password" placeholder="Insert your API key" autocomplete="off" spellcheck="false" autocapitalize="none" aria-describedby="api-key-help"></label>${button('save-api-key','Save key','','primary')}${button('remove-api-key','Remove key','','secondary')}<p id="api-key-help">${esc(MenuChat.keyHelp())}</p></section>`:''}
 ${saveError?`<div class="error-banner" role="alert">${esc(saveError)} Export a backup to keep a copy of your changes.</div>`:''}
 <main><div class="page-heading"><div><div class="eyebrow">MENU EDITOR</div><h1>${esc(r.name)}</h1><p>${esc(r.menuTitle)} <span class="dot-sep">·</span> ${items.length} items <span class="dot-sep">·</span> ${r.categories.length} categories</p></div><div class="heading-actions"><a class="secondary customer-menu-link" href="/menu/${encodeURIComponent(r.id)}" target="_blank" rel="noopener">Customer menu ↗</a>${button('copy-customer-link','Copy menu link','','secondary')}${button('view-design-skill','View design skill','','secondary')}${button('design-prompt','Edit design prompt','','secondary')}${button('manage-data','Manage data','','secondary')}${button('settings','Restaurant settings','','secondary')}${button('generate-menu','Generate menu','','primary')}</div></div>
 <div class="menu-strip"><div><strong>${esc(r.currency)} × ${fmt(r.priceUnit)}</strong><span>Price 95 = ${esc(r.currency)} ${fmt(95*r.priceUnit)}</span></div><div><strong>${fmt(r.serviceCharge)}% service · ${fmt(r.tax)}% tax</strong><span>${esc(r.dietaryNote||'No menu-wide dietary note')}</span></div><div class="review-summary"><strong>${review?review+' items to review':'All items reviewed'}</strong><span>${r.source?'Imported from the supplied menu':'Your restaurant menu'}</span></div>${r.source?`<a class="source-link" target="_blank" rel="noopener" href="/sources/${encodeURIComponent(r.source)}">Original PDF ↗</a>`:''}</div>
 <div class="editor-grid"><section class="categories"><div class="section-heading"><h2>Categories</h2>${button('add-category','+','aria-label="Add category"','icon-button')}</div><nav aria-label="Menu categories">${r.categories.map(cat=>`<div class="category-row" data-category-id="${cat.id}"><button data-action="category" data-id="${cat.id}" class="category ${cat.id===categoryId?'active':''}" aria-current="${cat.id===categoryId?'true':'false'}" title="${cat.id===categoryId?'Drag to reorder. Use arrow keys when focused.':'Select category'}"><span>${esc(cat.name)}</span><span>${cat.items.length}</span></button></div>`).join('')||'<p class="empty-small">Add your first category.</p>'}</nav></section>
 <section class="items-panel"><div class="section-heading"><div><div class="eyebrow">CATEGORY</div><h2>${esc(c?.name||'Create a category')}</h2></div>${c?button('edit-category','Edit','','text-button'):''}</div>${c?.notes?`<p class="category-note">${esc(c.notes)}</p>`:''}<div class="item-tools"><label class="search"><span class="sr-only">Search this restaurant’s items by name or product code</span><input id="search" type="search" placeholder="Search items or product codes…" value="${esc(search)}"></label><select id="filter" aria-label="Filter items"><option value="all" ${filter==='all'?'selected':''}>All items</option><option value="review" ${filter==='review'?'selected':''}>To review</option><option value="hidden" ${filter==='hidden'?'selected':''}>Hidden</option></select></div>
 <div class="list-caption"><span>ITEM</span><span>PRICE</span></div><div id="item-list">${listHTML()}</div>${c?button('add-item','+ Add products','','add-item'):''}</section>
 <section class="details-panel">${i?placementHTML(i):`<div class="empty"><span class="empty-symbol">＋</span><h2>${c?'Your menu starts here':'Organize your menu'}</h2><p>${c?'Choose a product from the shared catalog.':'Create a category, then add your dishes.'}</p>${button(c?'add-item':'add-category',c?'Add products':'Add category','','primary')}</div>`}</section></div>
 <footer class="workspace-footer">Menu content workspace <span>Generate a PDF, then refine it in a conversation.</span></footer></main></div>`;
 if(view==='products'){ $('.breadcrumb').textContent='Products';$('main').innerHTML=productsHTML();}
 if($('#account-api-key'))$('#account-api-key').value=apiKeyDraft;
 app.classList.toggle('saving',busy);
 if(busy)app.querySelectorAll('button,input,select,textarea').forEach(control=>control.disabled=true);
}
function listHTML(){
 let pairs=search?restaurant().categories.flatMap(c=>c.items.map(i=>({c,i}))):(category()?.items||[]).map(i=>({c:category(),i}));
 pairs=pairs.filter(({i})=>(!search||[i.name,i.productCode??'',i.description,...i.tags].join(' ').toLowerCase().includes(search.toLowerCase()))&&(filter==='all'||filter==='review'&&!i.reviewed||filter==='hidden'&&!i.available));
 return pairs.map(({c,i})=>`<div role="button" tabindex="0" class="item-row ${i.id===itemId?'selected':''} ${!search&&filter==='all'?'reorderable':''}" title="${!search&&filter==='all'?'Select this item, then drag to reorder. Use arrow keys when focused.':'Clear search and choose All items to reorder.'}" data-action="item" data-id="${i.id}" data-category="${c.id}"><span><strong>${esc(i.name)}</strong><small>${search?esc(c.name)+' · ':''}${esc(i.description||'No description')}</small>${i.productCode?`<small>Code: ${esc(i.productCode)}</small>`:''}<span class="row-tags">${!i.available?'<span class="mini-tag">Hidden</span>':''}${!i.reviewed?'<span class="review-dot">To review</span>':''}${i.tags.slice(0,2).map(tag=>`<span class="mini-tag">${tagDisplay(tag)}</span>`).join('')}</span></span><span class="item-row-actions"><span class="item-price">${fmt(i.price)}</span>${button('edit-product','Edit',`data-product-id="${esc(i.productId)}"`,'text-button')}</span></div>`).join('')||'<div class="empty-small">No items here. Try another filter or add an item.</div>';
}
function detailHTML(i){return `<form id="item-form"><div class="detail-heading"><span class="eyebrow">PRODUCT DETAILS</span><div>${button('back-to-menu','Back to restaurant','','text-button')}${button('delete-product','Delete product','','text-button danger')}</div></div><h2>${esc(i.name)}</h2><div class="review-notice">${i.reviewed?'Reviewed and ready for your menu.':'Check the imported details against your original menu.'}</div>
 ${productCategoryField(i)}<label class="field">Cuisine<select name="cuisine" required><option value="" disabled ${!i.cuisine?'selected':''}>Choose cuisine</option><option value="European" ${i.cuisine==='European'?'selected':''}>European</option><option value="Asian" ${i.cuisine==='Asian'?'selected':''}>Asian</option></select></label>${input('name','Item name',i.name,'text','required maxlength="200"')}${input('productCode','Product code',i.productCode??'','text','maxlength="100" autocomplete="off" placeholder="e.g. KOI-001"')}<label class="field">Description<textarea name="description" rows="3" maxlength="3000">${esc(i.description)}</textarea></label>
 ${input('price','Price (IDR × 1,000)',i.price,'number','min="0" step="0.01" required')}
 <div class="subheading"><h3>Options & add-ons</h3>${button('add-option','+ Add','','text-button')}</div><p class="hint">Variants have their own price. Add-ons are extra.</p><div id="options">${i.options.map(optionHTML).join('')}</div>
 <div class="subheading"><h3>Labels & serving details</h3>${button('manage-labels','Manage','','text-button')}</div>${tagChoices(i,'label','Labels')}${tagChoices(i,'serving','Serving details')}${input('customTags','New labels (comma separated)','','text','placeholder="e.g. Contains nuts, Gluten-free option"')}<p class="hint">New labels are available to every product.</p>
 <div class="subheading"><h3>Item image</h3>${i.image?button('remove-image','Remove','','text-button danger'):''}</div><label class="image-upload">${i.image?`<img src="${esc(i.image)}" alt="${esc(i.name)}">`:'<span>＋</span>'}<span>${i.image?'Replace image':'Upload a dish image'}<small>JPG, PNG or WebP · up to 3 MB</small></span><input type="file" id="item-image" accept="image/png,image/jpeg,image/webp"><input type="hidden" name="image" value="${esc(i.image)}"></label>
 <label class="field">Notes / specifics<textarea name="notes" rows="2" placeholder="Preparation details, portion size, or notes for the next revision">${esc(i.notes)}</textarea></label>
 <label class="check-row"><input type="checkbox" name="reviewed" ${i.reviewed?'checked':''}><span>I have reviewed this item’s details</span></label>
 <div class="detail-bottom"><span id="edit-state">No unsaved edits</span><button class="primary" type="submit">Save product</button></div></form>`;}
function optionHTML(o={name:'',price:0,kind:'Variant'}){return `<div class="option-row"><input aria-label="Option name" class="option-name" placeholder="Option name" value="${esc(o.name)}" required><select aria-label="Option type" class="option-kind"><option ${o.kind==='Variant'?'selected':''}>Variant</option><option ${o.kind==='Add-on'?'selected':''}>Add-on</option></select><input aria-label="Option price" class="option-price" type="number" min="0" step="0.01" value="${esc(o.price)}" required>${button('remove-option','×','aria-label="Remove option"','icon-button')}</div>`;}
async function save(){
 syncProducts();busy=true;unsaved=true;saveError='';render();
 try{const res=await fetch('/api/menus',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const out=await res.json();if(!res.ok)throw Error(out.error||'Unable to save.');data.revision=out.revision;unsaved=false;}
 catch(e){saveError=e.message;}
 finally{busy=false;render();}
 return !saveError;
}
function openDialog(title,body,submit='Save changes',wide=false){modal.className=wide?'wide':'';modal.innerHTML=`<form id="modal-form"><header><h2>${esc(title)}</h2>${button('close-dialog','×','aria-label="Close dialog"','icon-button')}</header><div class="modal-body">${body}</div><footer>${button('close-dialog','Cancel','','secondary')}<button class="primary" type="submit">${esc(submit)}</button></footer></form>`;modal.showModal();}
function finishDialog(){catalogDirty=false;designStudioEpoch++;clearTimeout(designChatTimer);modal.close();modal.innerHTML='';}
async function viewDesignSkill(){
 const rid=restaurantId,epoch=++designStudioEpoch;
 designSkillView=null;designChatTurns=[];catalogDirty=false;clearTimeout(designChatTimer);
 modal.className='wide design-skill-dialog';
 modal.innerHTML=`<header><h2>Design skill</h2>${button('close-dialog','×','aria-label="Close design skill"','icon-button')}</header><div class="modal-body" data-skill-loading><p role="status">Loading current design skill…</p></div><footer>${button('close-dialog','Close','','secondary')}</footer>`;
 modal.showModal();
 const loading=$('[data-skill-loading]',modal);
 try{
  const base=`/api/ai/restaurants/${encodeURIComponent(rid)}`;
  const [res,chatRes]=await Promise.all([fetch(base+'/design-skill',{cache:'no-store'}),fetch(base+'/design-chat',{cache:'no-store'})]);
  if(!res.ok){let message='Unable to load the design skill. Please try again.';try{message=(await res.json()).error||message;}catch{}throw Error(message);}
  if(!chatRes.ok)throw Error('Unable to load design conversation. Please try again.');
  const result=await res.json();if(epoch!==designStudioEpoch||!modal.open||!loading.isConnected)return;
  designChatTurns=(await chatRes.json()).turns;showDesignStudio(result);
  if(designChatTurns.some(t=>['queued','running'].includes(t.status)))scheduleDesignChatRefresh();
 }catch(err){if(modal.open&&loading.isConnected)loading.innerHTML=err.message.includes('before versioning')?`<div class="design-create"><h3>Create v1</h3><p>This restaurant needs an initial skill and reference PDF.</p><label class="field">SKILL.md<input id="design-upload-skill" type="file" accept=".md,text/markdown,text/plain"></label><label class="field">Reference PDF<input id="design-upload-reference" type="file" accept=".pdf,application/pdf"></label>${button('initialize-design-version','Create v1 from files','','primary')}<p class="design-studio-error" role="alert"></p></div>`:`<p role="alert">${esc(err.message)}</p>${button('view-design-skill','Try again','','secondary')}`;}
}
function showDesignStudio(result,showDetails=false){
 designSkillView=result;
 const rid=restaurantId,active=result.activeVersion,selected=result.version;
 $('[data-skill-loading]',modal).innerHTML=`<div class="skill-context"><strong>${esc(result.restaurantName)}</strong><span class="mini-tag">Active v${active}</span></div><p class="skill-intro">Each version has a skill and reference PDF. Generate menu uses the active version.</p><div class="design-version-list" aria-label="Design versions">${result.versions.map(v=>button('view-design-version',`v${v.number}${v.active?' · Active':''}`,`data-version="${v.number}" aria-current="${showDetails&&v.number===selected?'true':'false'}"`,'design-version '+(showDetails&&v.number===selected?'selected':''))).join('')}</div>${showDetails?'':'<p class="hint">Choose a version to view its skill and reference PDF.</p>'}<div class="design-version-details" ${showDetails?'':'hidden'}><div class="design-version-heading"><div><strong>v${selected}</strong><span>${selected===active?'Active for Generate menu':'Available to activate'}</span></div>${selected===active?'':button('activate-design-version','Activate v'+selected,`data-version="${selected}"`,'primary')}</div><p class="skill-name">${esc(result.skillName)} · SKILL.md + reference.pdf</p>${designReferenceHTML(result,rid)}<div class="skill-toolbar"><label class="field">Document<select id="design-skill-document">${result.documents.map((doc,index)=>`<option value="${index}">${index===0?'Main skill':esc(doc.name)}</option>`).join('')}<option value="prompt">Restaurant design prompt</option></select></label>${button('download-design-skill','Download document','','secondary')}</div><pre class="skill-content" tabindex="0" aria-label="Design skill document"></pre></div><section class="design-create"><h3>Create a new version</h3><p>Describe a change to create a new skill and reference PDF together. The result stays inactive until you activate it. Uses Alain’s API key; AI usage is billed.</p><label class="field">Design change<textarea id="design-version-message" rows="3" maxlength="6000" placeholder="For example, make the category headings more prominent in the skill and reference layout."></textarea></label>${button('send-design-change','Create next version with AI',`data-version="${selected}"`,'primary')}<details><summary>Upload a prepared skill and reference PDF</summary><p>Both files are required. They will be saved together as the next version.</p><label class="field">SKILL.md<input id="design-upload-skill" type="file" accept=".md,text/markdown,text/plain"></label><label class="field">Reference PDF<input id="design-upload-reference" type="file" accept=".pdf,application/pdf"></label>${button('upload-design-version','Create version from files',`data-version="${selected}"`,'secondary')}</details><p class="design-studio-error" role="alert"></p></section><section class="design-chat"><h3>Version conversation</h3><div class="design-chat-turns" role="log"></div></section>`;
 showDesignSkillDocument();drawDesignChat();
 const body=$('[data-skill-loading]',modal);body.closest('.modal-body').scrollTop=0;
}
function drawDesignChat(){
 const log=$('.design-chat-turns',modal);if(!log)return;
 log.innerHTML=designChatTurns.map(t=>`<article class="design-chat-turn"><strong>You · from v${t.parent}</strong><p>${esc(t.prompt)}</p><div><strong>Design assistant</strong><p>${t.status==='completed'?esc(t.answer):t.status==='failed'?`<span class="danger">${esc(t.error)}</span>`:'Creating skill and reference PDF…'}</p>${t.version?button('view-design-version','View v'+t.version,`data-version="${t.version}"`,'text-button'):''}</div></article>`).join('')||'<p class="hint">No versions have been created in this conversation yet.</p>';
 const submit=$('[data-action=send-design-change]',modal);if(submit)submit.disabled=designChatBusy||designChatTurns.some(t=>['queued','running'].includes(t.status));
}
function scheduleDesignChatRefresh(){clearTimeout(designChatTimer);if(modal.open)designChatTimer=setTimeout(refreshDesignChat,4000);}
async function refreshDesignChat(){
 if(!modal.open||!designSkillView)return;
 const rid=restaurantId,epoch=designStudioEpoch;
 try{
  const res=await fetch(`/api/ai/restaurants/${encodeURIComponent(rid)}/design-chat`,{cache:'no-store'});
  if(!res.ok)throw Error('Could not check design status.');
  if(epoch!==designStudioEpoch||rid!==restaurantId||!modal.open)return;
  const previous=designChatTurns;designChatTurns=(await res.json()).turns;drawDesignChat();
  const completed=designChatTurns.find(t=>t.version&&!previous.some(old=>old.id===t.id&&old.version));
  if(completed)await loadDesignVersion(completed.version);
 }catch(err){const error=epoch===designStudioEpoch&&rid===restaurantId?$('.design-studio-error',modal):null;if(error)error.textContent=err.message;}
 if(designChatTurns.some(t=>['queued','running'].includes(t.status)))scheduleDesignChatRefresh();
}
async function loadDesignVersion(number){
 const rid=restaurantId,epoch=designStudioEpoch;
 const res=await fetch(`/api/ai/restaurants/${encodeURIComponent(rid)}/design-skill?version=${encodeURIComponent(number)}`,{cache:'no-store'});
 const result=await res.json();if(!res.ok)throw Error(result.error||'Could not load the version.');
 if(epoch===designStudioEpoch&&rid===restaurantId&&modal.open&&$('[data-skill-loading]',modal))showDesignStudio(result,true);
}
async function activateDesignVersion(number){
 const res=await fetch(`/api/ai/restaurants/${encodeURIComponent(restaurantId)}/design-versions/${encodeURIComponent(number)}/activate`,{method:'POST'});
 const result=await res.json();if(!res.ok)throw Error(result.error||'Could not activate the version.');
 await loadDesignVersion(number);toast(`v${number} is active for new menu generation`);
}
async function sendDesignChange(number){
 const message=$('#design-version-message',modal)?.value.trim();
 if(!message){$('.design-studio-error',modal).textContent='Describe the change you want.';return;}
 designChatBusy=true;drawDesignChat();
 try{
  const res=await fetch(`/api/ai/restaurants/${encodeURIComponent(restaurantId)}/design-chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({parent:number,message,requestId:crypto.randomUUID()})});
  const result=await res.json();if(!res.ok)throw Error(result.error||'Could not start design creation.');
  designChatTurns=result.turns;$('#design-version-message',modal).value='';$('.design-studio-error',modal).textContent='';drawDesignChat();scheduleDesignChatRefresh();
 }catch(err){$('.design-studio-error',modal).textContent=err.message;}finally{designChatBusy=false;drawDesignChat();}
}
async function uploadDesignVersion(number){
 const skill=$('#design-upload-skill',modal)?.files[0],reference=$('#design-upload-reference',modal)?.files[0];
 if(!skill||!reference){$('.design-studio-error',modal).textContent='Choose both SKILL.md and a reference PDF.';return;}
 const body=new FormData();body.set('parent',number);body.set('skill',skill);body.set('reference',reference);
 const res=await fetch(`/api/ai/restaurants/${encodeURIComponent(restaurantId)}/design-versions`,{method:'POST',body});
 const result=await res.json();if(!res.ok)throw Error(result.error||'Could not create the version.');
 await loadDesignVersion(result.version);toast(`v${result.version} is ready to review`);
}
async function initializeDesignVersion(){
 const skill=$('#design-upload-skill',modal)?.files[0],reference=$('#design-upload-reference',modal)?.files[0];
 if(!skill||!reference){$('.design-studio-error',modal).textContent='Choose both SKILL.md and a reference PDF.';return;}
 const body=new FormData();body.set('skill',skill);body.set('reference',reference);
 const res=await fetch(`/api/ai/restaurants/${encodeURIComponent(restaurantId)}/design-versions/initialize`,{method:'POST',body});
 const result=await res.json();if(!res.ok)throw Error(result.error||'Could not create v1.');
 await loadDesignVersion(1);toast('v1 is active and ready');
}
function designReferenceHTML(result,rid){
 if(!result.reference)return '<div class="skill-reference"><strong>Reference document</strong><p>No reference PDF is available for this restaurant.</p></div>';
 const url=`/api/ai/restaurants/${encodeURIComponent(rid)}/reference?version=${encodeURIComponent(result.version)}`;
 return `<div class="skill-reference"><strong>Reference document · v${result.version}</strong><p>${esc(result.reference.name)}</p><div><a class="secondary" href="${url}" target="_blank" rel="noopener">View reference PDF ↗</a><a class="secondary" href="${url}&download=1" download="${esc(result.reference.name)}">Download reference PDF</a></div><small>The reference paired with this skill version. Current products and prices come from your saved menu data.</small></div>`;
}
function currentDesignSkillDocument(){return $('#design-skill-document',modal)?.value==='prompt'?{name:'restaurant-design-prompt.md',content:designSkillView.designPrompt||'No saved design prompt.'}:designSkillView.documents[Number($('#design-skill-document',modal)?.value)||0];}
function showDesignSkillDocument(){const doc=currentDesignSkillDocument();$('.skill-content',modal).textContent=doc.content;$('.skill-content',modal).scrollTop=0;}
modal.addEventListener('change',e=>{if(e.target.id==='design-skill-document')showDesignSkillDocument();});
modal.addEventListener('close',()=>{designStudioEpoch++;clearTimeout(designChatTimer);});
function newItem(){return {id:id(),name:'New item',cuisine:'',productCode:'',description:'',price:0,tags:[],options:[],notes:'',image:'',available:true,reviewed:true};}
function cloneRestaurant(r){const copy=structuredClone(r);copy.id=id();copy.categories.forEach(c=>{c.id=id();c.items.forEach(i=>i.id=id());});return copy;}
function backup(){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download=`menu-studio-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
async function imageData(file){if(!file)return '';if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>3*1024*1024)throw Error('Choose a JPG, PNG or WebP image smaller than 3 MB.');return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Could not read this image.'));reader.readAsDataURL(file);});}
let dialogAction='';
async function action(name,el){
 if(busy){toast('Please wait for the current save to finish.');return;}
 if(name==='view-design-skill'){if(!hosted){toast('Design skills are available in the online workspace.');return;}await viewDesignSkill();return;}
 if(name==='view-design-version'){await loadDesignVersion(Number(el.dataset.version));return;}
 if(name==='activate-design-version'){await activateDesignVersion(Number(el.dataset.version));return;}
 if(name==='send-design-change'){await sendDesignChange(Number(el.dataset.version));return;}
 if(name==='upload-design-version'){try{await uploadDesignVersion(Number(el.dataset.version));}catch(err){$('.design-studio-error',modal).textContent=err.message;}return;}
 if(name==='initialize-design-version'){try{await initializeDesignVersion();}catch(err){$('.design-studio-error',modal).textContent=err.message;}return;}
 if(name==='download-design-skill'){if(!designSkillView)return;const doc=currentDesignSkillDocument(),a=document.createElement('a');a.href=URL.createObjectURL(new Blob([doc.content],{type:'text/markdown;charset=utf-8'}));a.download=doc.name.split('/').pop();a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);return;}
 if(name==='cancel-category-rename'){closeCategoryRename(el.closest('form').dataset.categoryId);return;}
 if(name==='close-dialog'){if(catalogDirty&&!confirm('Discard unsaved changes in this dialog?'))return;finishDialog();return;}
 if(name==='add-catalog-row'){$('#catalog-rows').insertAdjacentHTML('beforeend',catalogRowHTML({name:'',kind:el.dataset.kind},true));catalogDirty=true;$('#catalog-rows .catalog-row:last-child input').focus();return;}
 if(name==='clear-catalog-icon'){const row=el.closest('.catalog-row');$('.catalog-icon',row).value='';$('.catalog-icon-image',row).value='';$('.catalog-icon-file',row).value='';$('.icon-sample',row).textContent='—';catalogDirty=true;return;}
 if(name==='remove-catalog-row'){el.closest('.catalog-row').remove();catalogDirty=true;return;}
 if(name==='copy-customer-link'){await navigator.clipboard.writeText(location.origin+'/menu/'+encodeURIComponent(restaurantId));toast('Customer menu link copied');return;}
 if(name==='backup'){backup();return;}
 if(name==='download-restaurant'){
  try{const res=await fetch(`/api/restaurants/${encodeURIComponent(restaurantId)}/data`),out=await res.json();if(!res.ok)throw Error(out.error||'Download failed.');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:'application/json'}));a.download=`${out.restaurant.name.replace(/[^a-z0-9]+/gi,'-')}-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}catch(err){toast(err.message);}return;
 }
 if(name==='logout'){if(!canLeave())return;if(unsaved&&!confirm('Some changes have not reached the server. Sign out anyway? Export a backup first to keep them.'))return;await fetch('/logout',{method:'POST'});dirty=false;unsaved=false;location.href='/login';return;}
 if(name==='save-api-key'){el.disabled=true;try{await MenuChat.saveKey(apiKeyDraft);apiKeyDraft='';$('#account-api-key').value='';toast('API key saved securely.');}finally{el.disabled=false;}return;}
 if(name==='remove-api-key'){if(!confirm('Remove the saved API key? New menu generation will stop until Alain saves a key again.'))return;await MenuChat.removeKey();apiKeyDraft='';$('#account-api-key').value='';toast('API key removed.');return;}
 if(name==='generate-menu'){if(!hosted){toast('AI menu generation is available in the signed-in hosted workspace.');return;}if(dirty||unsaved||saveError){toast('Save your menu changes before generating a PDF.');return;}await MenuChat.open(restaurant(),()=>data.revision);return;}
 if(name==='retry'){await save();return;}
 if(name==='add-option'){$('#options').insertAdjacentHTML('beforeend',optionHTML());setDirty();return;}
 if(name==='remove-option'){el.closest('.option-row').remove();setDirty();return;}
 if(name==='remove-image'){$('[name=image]').value='';const img=$('.image-upload img');if(img)img.remove();setDirty();return;}
 if(!canLeave())return;
 dirty=false;render();
 const r=restaurant(),c=category(),i=item();
 if(name==='rename-product-category'){openCategoryRename(el.dataset.id);return;}
 if(name==='products'||name==='edit-product'||name==='select-product'){view='products';productId=el.dataset.productId||el.dataset.id||data.products.find(p=>!productCategoryId||p.categoryId===productCategoryId)?.id;if(name==='edit-product'){productCategoryId=item()?.categoryId||'';productSearch='';}render();return;}
 if(name==='product-category'){productCategoryId=el.dataset.id||'';productSearch='';productId=data.products.find(p=>!productCategoryId||p.categoryId===productCategoryId)?.id;view='products';render();return;}
 if(name==='delete-product-category'){if(data.products.some(p=>p.categoryId===productCategoryId)){toast('Move all products to another category before deleting this category.');return;}if(!confirm('Delete this empty category from all restaurants?'))return;data.productCategories=data.productCategories.filter(c=>c.id!==productCategoryId);productCategoryId='';finishDialog();await save();return;}
 if(name==='back-to-menu'){view='restaurants';render();return;}
 if(name==='add-product'){if(!data.productCategories.length){toast('Create a category first.');return;}const p=newItem();p.categoryId=productCategoryId||data.productCategories[0].id;p.name='New product';data.products.push(p);productId=p.id;view='products';await save();$('[name=name]')?.focus();return;}
 if(name==='delete-product'){
  if(data.restaurants.some(r=>r.categories.some(c=>c.items.some(i=>i.productId===productId)))){toast('Remove this product from restaurant menus before deleting it.');return;}
  if(!confirm(`Delete product “${i.name}”?`))return;data.products=data.products.filter(p=>p.id!==productId);productId=data.products[0]?.id;await save();return;
 }
 if(name==='restaurant'){selectRestaurant(el.dataset.id);render();return;}
 if(name==='category'){selectCategory(el.dataset.id);render();return;}
 if(name==='item'){categoryId=el.dataset.category;itemId=el.dataset.id;render();return;}
 if(name==='add-item'){if(!c)return;dialogAction='add-item';openDialog('Add products',`<p>Select existing products for <strong>${esc(c.name)}</strong>. Create new dishes in Products first.</p><label class="field">Search products<input type="search" id="product-picker-search" placeholder="Name or product code"></label><div id="product-picker">${productPickerHTML()}</div>`,'Add selected products',true);return;}
 if(name==='delete-item'){if(!confirm(`Delete “${i.name}” from ${r.name}?`))return;c.items=c.items.filter(x=>x.id!==i.id);itemId=c.items[0]?.id;await save();return;}


 if(name==='delete-category'){if(!confirm(`Delete “${c.name}” and its ${c.items.length} items?`))return;r.categories=r.categories.filter(x=>x.id!==c.id);selectCategory(r.categories[0]?.id);finishDialog();await save();return;}
 if(name==='delete-restaurant'){if(data.restaurants.length===1){toast('Keep at least one restaurant.');return;}if(!confirm(`Delete ${r.name} and its entire menu? Export a backup first if you need to keep it.`))return;data.restaurants=data.restaurants.filter(x=>x.id!==r.id);selectRestaurant(data.restaurants[0].id);finishDialog();await save();return;}
 render();dialogAction=name;
 if(name==='add-restaurant'){openDialog('Add restaurant',`${input('name','Restaurant name','','text','required maxlength="200"')}${input('location','Location')}<label class="field">Starting menu<select name="template"><option value="">Start with an empty menu</option>${data.restaurants.map(r=>`<option value="${r.id}">Copy ${esc(r.name)}’s menu</option>`).join('')}</select></label><p class="hint">Categories and order are copied. Product details remain shared across restaurants.</p>`,'Create restaurant');}
 if(name==='manage-labels'){catalogDirty=false;openDialog('Product labels & serving details',`<p>Shared across all products and restaurants.</p><div class="catalog-toolbar">${button('add-catalog-row','+ Label','data-kind="label"','secondary')}${button('add-catalog-row','+ Serving detail','data-kind="serving"','secondary')}</div><div id="catalog-rows">${MenuCatalog.initialize(labelContext()).map(t=>catalogRowHTML(t)).join('')}</div>`,'Save labels & details',true);}
 if(name==='design-prompt'){catalogDirty=false;openDialog('Menu design prompt',`<div class="prompt-context"><strong>${esc(r.name)}</strong><span class="mini-tag">AI design instructions</span></div><p>Save instructions for matching this restaurant’s menu design. Generate menu uses these instructions with your saved menu content.</p>${r.source?`<p><a target="_blank" rel="noopener" href="/sources/${encodeURIComponent(r.source)}">Open reference PDF ↗</a></p>`:''}<label class="field">Design instructions<textarea class="design-prompt-editor" name="designPrompt" maxlength="30000" rows="24" spellcheck="true">${esc(r.designPrompt??MenuDesignPrompts.create(r))}</textarea></label><p class="hint">Changes apply only to ${esc(r.name)}. Use Generate menu to create a PDF and request adjustments.</p>`,'Save prompt',true);}
 if(name==='manage-data'){openDialog('Manage restaurant data',`<p><strong>${esc(r.name)}</strong></p><p>Download this restaurant's saved data as an editable JSON file, including categories, dishes, prices, labels, icons, settings and design prompt.</p>${button('download-restaurant','Download restaurant data','','secondary')}<hr><h3>Upload replacement data</h3><p>This erases this restaurant's current data and replaces it entirely with the file. Only existing products can be added. Uploaded product details are resolved from the shared Products catalog; edit prices, labels and descriptions in Products. Other restaurants and user accounts are unaffected.</p><label class="field">Restaurant JSON file<input type="file" name="restaurantFile" accept="application/json,.json" required></label><label class="check-row"><input type="checkbox" name="replaceConfirmed" required>I understand that the existing data for this restaurant will be replaced.</label>`,'Replace restaurant data');}
 if(name==='settings'){openDialog('Restaurant settings',`${input('name','Restaurant name',r.name,'text','required')}${input('location','Location',r.location)}${input('menuTitle','Menu title',r.menuTitle,'text','required')}<div class="two-fields">${input('currency','Currency',r.currency,'text','required maxlength="12"')}${input('priceUnit','Price multiplier',r.priceUnit,'number','required min="1" step="1"')}</div><div class="two-fields">${input('serviceCharge','Service charge (%)',r.serviceCharge,'number','required min="0" max="100" step="0.01"')}${input('tax','Tax (%)',r.tax,'number','required min="0" max="100" step="0.01"')}</div>${input('dietaryNote','Menu-wide dietary note',r.dietaryNote)}<label class="field">Footer / pricing note<textarea name="footer" rows="3">${esc(r.footer)}</textarea></label><p class="hint">Update the footer wording if you change the price multiplier, tax or service charge.</p><label class="field">Restaurant logo<input type="file" id="logo-file" accept="image/png,image/jpeg,image/webp"></label>${r.logo?'<label class="check-row"><input type="checkbox" name="removeLogo">Remove current logo</label>':''}<hr>${button('delete-restaurant','Delete restaurant','','text-button danger')}`);}
 if(name==='add-category'||name==='edit-category'){openDialog(name==='add-category'?'Add category':'Edit category',`${name==='add-category'?`<label class="field">Category<select name="catalogCategoryId" required>${data.productCategories.filter(pc=>!r.categories.some(rc=>rc.catalogCategoryId===pc.id)).map(pc=>`<option value="${esc(pc.id)}">${esc(pc.name)}</option>`).join('')}</select></label><p class="hint">Create and rename categories in Products.</p>`:`<p><strong>${esc(c.name)}</strong></p><p class="hint">The category name is shared. Rename it in Products.</p>`}<label class="field">Category notes<textarea name="notes" rows="3">${esc(name==='edit-category'?c.notes:'')}</textarea></label>${name==='edit-category'?`<div class="dialog-actions">${button('delete-category','Delete category','','text-button danger')}</div>`:''}`);}
 if(name==='add-product-category'||name==='edit-product-category'){const cat=data.productCategories.find(c=>c.id===productCategoryId);openDialog(name==='add-product-category'?'New product category':'Edit product category',`${input('name','Category name',cat&&name==='edit-product-category'?cat.name:'','text','required maxlength="200"')}<p class="hint">Category names are shared across all restaurants.</p>${name==='edit-product-category'?button('delete-product-category','Delete empty category','','text-button danger'):''}`);}
 if(name==='preview'){modal.className='wide';modal.innerHTML=`<header><div><span class="eyebrow">CONTENT PREVIEW</span><h2>${esc(r.name)}</h2></div>${button('close-dialog','×','aria-label="Close preview"','icon-button')}</header><div class="preview"><div class="preview-heading">${r.logo?`<img src="${esc(r.logo)}" alt="${esc(r.name)} logo">`:''}<h2>${esc(r.menuTitle)}</h2><p>${esc(r.dietaryNote)}</p><small>Prices in ${esc(r.currency)} × ${fmt(r.priceUnit)}. This is a content preview; the final PDF layout comes later.</small></div><div class="preview-grid">${r.categories.map(c=>`<section><h3>${esc(c.name)}</h3>${c.notes?`<p class="hint">${esc(c.notes)}</p>`:''}${c.items.filter(i=>i.available).map(i=>`<article>${i.image?`<img class="dish-thumb" src="${esc(i.image)}" alt="${esc(i.name)}">`:''}<div class="preview-item"><strong>${esc(i.name)}</strong><b>${fmt(i.price)}</b></div><p>${esc(i.description)}</p>${i.options.map(o=>`<p class="preview-option">${esc(o.name)} <b>${o.kind==='Add-on'?'+':''}${fmt(o.price)}</b></p>`).join('')}<small class="preview-tags">${i.tags.map(tag=>`<span>${tagDisplay(tag)}</span>`).join('')}</small></article>`).join('')||'<p class="hint">No visible items</p>'}</section>`).join('')}</div><p class="preview-footer">${esc(r.footer)}</p></div>`;modal.showModal();}
 if(name==='restore'){openDialog('Restore a backup','<p>This replaces all restaurants and menu data with a previously exported backup. Export your current data first if you want to keep a copy.</p><label class="field">Menu Studio backup<input type="file" name="backup" accept="application/json,.json" required></label>','Restore backup');}
}
function setDirty(){dirty=true;const state=$('#edit-state');if(state)state.textContent='Unsaved edits';}
document.addEventListener('click',e=>{const el=e.target.closest('[data-action]');if((el?.dataset.action==='category'&&Date.now()<suppressCategoryClickUntil)||(el?.dataset.action==='item'&&Date.now()<suppressItemClickUntil)){e.preventDefault();return;}if(el)action(el.dataset.action,el).catch(err=>toast(err.message));});
app.addEventListener('keydown',e=>{const form=e.target.closest('.category-rename');if(form&&e.key==='Escape'){e.preventDefault();closeCategoryRename(form.dataset.categoryId);}});
app.addEventListener('submit',async e=>{
 if(!e.target.matches('.category-rename'))return;
 e.preventDefault();if(busy)return;
 const form=e.target,field=$('[name=categoryName]',form),name=field.value.trim(),cid=form.dataset.categoryId;
 const key=value=>value.toLowerCase().replaceAll('&',' and ').split(/\s+/).filter(Boolean).join(' ');
 const error=!name?'Enter a category name.':data.productCategories.some(c=>c.id!==cid&&key(c.name)===key(name))?'This category already exists.':'';
 if(error){$('.category-rename-error',form).textContent=error;field.setAttribute('aria-invalid','true');field.focus();return;}
 const cat=data.productCategories.find(c=>c.id===cid);
 if(cat.name===name){closeCategoryRename(cid);return;}
 if(!canLeave())return;
 dirty=false;cat.name=name;
 try{if(await save())toast('Category renamed across all restaurants');focusCategoryRename(cid);}catch(err){toast(err.message);}
});
app.addEventListener('input',e=>{if(e.target.id==='account-api-key'){apiKeyDraft=e.target.value;return;}if(e.target.id==='product-search'){productSearch=e.target.value;$('#product-list').innerHTML=productListHTML();return;}if(e.target.id==='search'){search=e.target.value;$('#item-list').innerHTML=listHTML();return;}if(e.target.closest('#item-form,#placement-form'))setDirty();});
app.addEventListener('change',async e=>{if(e.target.id==='filter'){filter=e.target.value;$('#item-list').innerHTML=listHTML();return;}if(e.target.id==='item-image'){const form=e.target.closest('form');try{const image=await imageData(e.target.files[0]);if(!image||!form.isConnected)return;$('[name=image]',form).value=image;let img=$('.image-upload img',form);if(!img){img=document.createElement('img');$('.image-upload',form).prepend(img);}img.src=image;img.alt='Selected dish image';setDirty();}catch(err){toast(err.message);}}});
app.addEventListener('submit',async e=>{if(e.target.id==='placement-form'){e.preventDefault();if(busy)return;const f=new FormData(e.target),i=item(),old=category();i.available=f.has('available');dirty=false;await save();return;}if(e.target.id!=='item-form')return;e.preventDefault();if(busy)return;const form=e.target,fields=new FormData(form),i=item(),old=category();
 const code=fields.get('productCode').trim();if(code&&data.products.some(p=>p.id!==i.id&&p.productCode?.trim().toLowerCase()===code.toLowerCase())){toast('This product code already exists.');return;}
 const name=fields.get('name').trim();if(!name){toast('Enter an item name.');return;}
 const options=[...form.querySelectorAll('.option-row')].map(row=>({name:$('.option-name',row).value.trim(),price:Number($('.option-price',row).value),kind:$('.option-kind',row).value}));
 if(options.some(o=>!o.name)){toast('Enter a name for every option.');return;}
 let selectedTags;try{selectedTags=[...new Set([...fields.getAll('tag'),...MenuCatalog.addCustom(labelContext(),fields.get('customTags').split(',').map(s=>s.trim()).filter(Boolean))])];}catch(err){toast(err.message);return;}
 Object.assign(i,{categoryId:fields.get('productCategory'),cuisine:fields.get('cuisine'),name,productCode:fields.get('productCode').trim(),description:fields.get('description').trim(),price:Number(fields.get('price')),notes:fields.get('notes').trim(),image:fields.get('image'),available:true,reviewed:fields.has('reviewed'),tags:selectedTags,options});
 if(productCategoryId)productCategoryId=i.categoryId;dirty=false;await save();if(!saveError)toast('Product saved across all restaurant menus');
});
modal.addEventListener('submit',async e=>{e.preventDefault();if(busy||pendingIconReads)return;const f=new FormData(e.target),r=restaurant();
 try{
 if(['settings','add-restaurant','add-product-category','edit-product-category'].includes(dialogAction)&&!f.get('name').trim()){toast('Enter a name.');return;}
 if(dialogAction==='manage-labels'){
  const rows=[...modal.querySelectorAll('.catalog-row')].map(row=>({original:row.dataset.original,name:$('.catalog-name',row).value.trim(),kind:$('.catalog-kind',row).value,icon:$('.catalog-icon',row).value,iconImage:$('.catalog-icon-image',row).value}));
  MenuCatalog.validate(rows);
  const kept=new Set(rows.map(row=>row.original));
  const shared=labelContext();const removed=shared.tagCatalog.filter(tag=>!kept.has(tag.name));
  const affected=data.products.filter(item=>item.tags.some(tag=>removed.some(removed=>removed.name===tag))).length;
  if(affected&&!confirm(`Remove ${removed.length} option(s) from ${affected} product(s) across all restaurants?`))return;
  MenuCatalog.apply(shared,rows);data.productTags=shared.tagCatalog;
 }
 if(dialogAction==='add-item'){
  const chosen=f.getAll('product');if(!chosen.length){toast('Select at least one product.');return;}
  for(const pid of chosen){const p=data.products.find(p=>p.id===pid);if(!p||p.categoryId!==category().catalogCategoryId||category().items.some(i=>i.productId===pid))continue;const placement={...structuredClone(p),id:id(),productId:pid,available:true};category().items.push(placement);itemId=placement.id;}
 }
 if(dialogAction==='design-prompt'){r.designPrompt=f.get('designPrompt');}
 if(dialogAction==='settings'){
  const logoFile=$('#logo-file').files[0],logo=logoFile?await imageData(logoFile):f.has('removeLogo')?'':r.logo;
  Object.assign(r,{name:f.get('name').trim(),location:f.get('location').trim(),menuTitle:f.get('menuTitle').trim(),currency:f.get('currency').trim(),priceUnit:Number(f.get('priceUnit')),serviceCharge:Number(f.get('serviceCharge')),tax:Number(f.get('tax')),dietaryNote:f.get('dietaryNote').trim(),footer:f.get('footer').trim(),logo});
 }
 if(dialogAction==='add-restaurant'){
  const template=data.restaurants.find(r=>r.id===f.get('template'));
  const x=template?cloneRestaurant(template):{id:id(),menuTitle:'Lunch & Dinner',currency:'IDR',priceUnit:1000,serviceCharge:10,tax:10,footer:'',dietaryNote:'',logo:'',source:'',categories:[]};
  x.name=f.get('name').trim();x.location=f.get('location').trim();x.source='';data.restaurants.push(x);selectRestaurant(x.id);
 }
 if(dialogAction==='add-category'){const pc=data.productCategories.find(c=>c.id===f.get('catalogCategoryId'));if(!pc)throw Error('Choose an existing category.');const c={id:id(),catalogCategoryId:pc.id,name:pc.name,notes:f.get('notes').trim(),items:[]};r.categories.push(c);selectCategory(c.id);}
 if(dialogAction==='add-product-category'||dialogAction==='edit-product-category'){const name=f.get('name').trim();if(data.productCategories.some(c=>c.id!==(dialogAction==='edit-product-category'?productCategoryId:null)&&c.name.toLowerCase().replaceAll('&',' and ').split(/\s+/).filter(Boolean).join(' ')===name.toLowerCase().replaceAll('&',' and ').split(/\s+/).filter(Boolean).join(' ')))throw Error('This category already exists.');if(dialogAction==='add-product-category'){const c={id:id(),name};data.productCategories.push(c);productCategoryId=c.id;productId=null;}else data.productCategories.find(c=>c.id===productCategoryId).name=name;}

 if(dialogAction==='edit-category'){category().notes=f.get('notes').trim();}
 if(dialogAction==='manage-data'){
  if(unsaved)throw Error('Save or resolve your existing changes before replacing restaurant data.');
  const file=f.get('restaurantFile');if(!file?.size||file.size>25*1024*1024)throw Error('Choose a restaurant JSON file smaller than 25 MB.');
  const upload=JSON.parse(await file.text());
  if(upload.format!=='menu-studio-restaurant'||upload.version!==1||!upload.restaurant||!Array.isArray(upload.restaurant.categories))throw Error('Use a restaurant JSON file downloaded from Manage data.');
  const count=upload.restaurant.categories.reduce((n,c)=>n+(Array.isArray(c.items)?c.items.length:0),0);
  if(!f.has('replaceConfirmed')||!confirm(`Replace ALL data for ${r.name} with “${upload.restaurant.name}” (${upload.restaurant.categories.length} categories, ${count} items)? Existing dishes not in the file will be removed.`))return;
  busy=true;const submit=$('#modal-form button[type=submit]');submit.disabled=true;
  let response,out;
  try{response=await fetch(`/api/restaurants/${encodeURIComponent(r.id)}/data`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:data.revision,upload})});out=await response.json();}finally{busy=false;if(submit.isConnected)submit.disabled=false;}
  if(!response.ok)throw Error(out.error||'Replacement failed.');
  data=out;unsaved=false;saveError='';selectRestaurant(r.id);finishDialog();render();toast('Restaurant data replaced');return;
 }
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
window.addEventListener('beforeunload',e=>{if(dirty||unsaved||busy||catalogDirty){e.preventDefault();e.returnValue='';}});
Promise.all([fetch('/api/menus').then(async res=>{if(res.status===401){location.href='/login';throw Error('Please sign in.');}if(!res.ok)throw Error('Could not load saved menus.');return res.json();}),fetch('/api/runtime').then(res=>res.ok?res.json():{hosted:false}).catch(()=>({hosted:false}))]).then(([result,runtime])=>{data=result;hosted=runtime.hosted;currentUser=runtime.user||null;selectRestaurant(data.restaurants[0].id);render();MenuChat.initialize(hosted);}).catch(e=>{app.innerHTML=`<div class="load-error"><h1>Unable to open your menus</h1><p>${esc(e.message)}</p><p>Check your connection and reload this page.</p><a href="/">Reload</a></div>`;});

function tagChoices(item,kind,title){
 const choices=MenuCatalog.initialize(labelContext()).filter(t=>t.kind===kind);
 return `<fieldset class="tag-group"><legend>${title}</legend><div class="tags">${choices.map(t=>`<label class="tag"><input type="checkbox" name="tag" value="${esc(t.name)}" ${item.tags.includes(t.name)?'checked':''}><span>${iconHTML(t)}${esc(t.name)}</span></label>`).join('')||'<span class="hint">No options yet. Use Manage to add one.</span>'}</div></fieldset>`;
}
function catalogRowHTML(tag,isNew=false){
 const count=isNew?0:data.products.filter(item=>item.tags.includes(tag.name)).length;
 return `<div class="catalog-row" data-original="${esc(isNew?'':tag.name)}"><label class="field">Name<input class="catalog-name" value="${esc(tag.name)}" maxlength="200" required placeholder="e.g. Spicy or With jasmine rice"></label><label class="field">Type<select class="catalog-kind"><option value="label" ${tag.kind==='label'?'selected':''}>Label</option><option value="serving" ${tag.kind==='serving'?'selected':''}>Serving detail</option></select></label>${iconPickerHTML(tag)}<span class="catalog-usage">${count} ${count===1?'dish':'dishes'}</span>${button('remove-catalog-row','×','aria-label="Remove option"','icon-button danger')}</div>`;
}
modal.addEventListener('input',()=>{if(['manage-labels','design-prompt'].includes(dialogAction))catalogDirty=true;});
modal.addEventListener('change',()=>{if(['manage-labels','design-prompt'].includes(dialogAction))catalogDirty=true;});
modal.addEventListener('cancel',e=>{if(catalogDirty&&!confirm('Discard unsaved changes in this dialog?'))e.preventDefault();else catalogDirty=false;});

const iconChoices=[...Object.entries(globalThis.MenuIconSet||{}).map(([key,value])=>[key,'Menu · '+value.name]),['','No icon'],['🌿','Leaf'],['🌶️','Chilli'],['🔥','Flame'],['⭐','Star'],['✨','Sparkles'],['🆕','New'],['⏱️','Timer'],['🍚','Rice'],['🥔','Potato'],['🍟','Fries'],['🥗','Salad'],['🥖','Bread'],['🍞','Toast'],['🍜','Noodles'],['🍲','Soup'],['🧀','Cheese'],['🥚','Egg'],['🐟','Fish'],['🦐','Shrimp'],['🥜','Nuts'],['🌾','Wheat'],['🥛','Milk'],['🍋','Lemon'],['🍷','Wine'],['☕','Coffee'],['✓','Check']];
function iconHTML(tag){
 const preset=globalThis.MenuIconSet?.[tag?.icon];
 if(preset&&!tag?.iconImage)return `<img class="label-icon" src="${esc(preset.image)}" alt="" aria-hidden="true">`;
 if(tag?.iconImage&&/^data:image\/(png|jpeg|webp);base64,/.test(tag.iconImage))return `<img class="label-icon" src="${esc(tag.iconImage)}" alt="" aria-hidden="true">`;
 return tag?.icon?`<span class="label-icon symbol" aria-hidden="true">${esc(tag.icon)}</span>`:'';
}
function tagDisplay(name){return iconHTML(data.productTags?.find(t=>t.name===name))+esc(name);}
function iconPickerHTML(tag){
 const choices=iconChoices.some(([value])=>value===(tag.icon||''))?iconChoices:[...iconChoices,[tag.icon,'Saved icon']];
 return `<div class="catalog-icon-control"><label class="field">Icon<select class="catalog-icon" aria-label="Icon for ${esc(tag.name||'new option')}">${choices.map(([value,label])=>`<option value="${esc(value)}" ${(tag.icon||'')===value?'selected':''}>${esc(value.startsWith('menu:')?label:value?value+' '+label:label)}</option>`).join('')}</select></label><div class="icon-upload-row"><span class="icon-sample">${iconHTML(tag)||'<span aria-hidden="true">—</span>'}</span><label class="icon-upload"><span>Upload icon</span><input class="catalog-icon-file" type="file" accept="image/png,image/jpeg,image/webp" aria-label="Upload icon for ${esc(tag.name||'new option')}"></label>${button('clear-catalog-icon','Clear','aria-label="Clear icon"','text-button')}<input type="hidden" class="catalog-icon-image" value="${esc(tag.iconImage||'')}"></div><small>PNG, JPG, WebP · 256 KB max</small></div>`;
}
modal.addEventListener('change',async e=>{
 const row=e.target.closest('.catalog-row');if(!row)return;
 if(e.target.matches('.catalog-icon')){
  $('.catalog-icon-image',row).value='';$('.catalog-icon-file',row).value='';
  $('.icon-sample',row).innerHTML=iconHTML({icon:e.target.value})||'<span aria-hidden="true">—</span>';catalogDirty=true;
 }
 if(e.target.matches('.catalog-icon-file')){
  const file=e.target.files[0];if(!file)return;
  if(file.size>256*1024){toast('Choose an icon smaller than 256 KB.');e.target.value='';return;}
  const submit=$('#modal-form button[type=submit]');pendingIconReads++;submit.disabled=true;
  try{
   const encoded=await imageData(file);if(!row.isConnected)return;
   $('.catalog-icon-image',row).value=encoded;$('.catalog-icon',row).value='';
   $('.icon-sample',row).innerHTML=iconHTML({iconImage:encoded});catalogDirty=true;
  }catch(err){toast(err.message);}finally{pendingIconReads--;if(submit.isConnected)submit.disabled=pendingIconReads>0;}
 }
});

// Drag the selected category box; other categories retain normal click/scroll behavior.
let categoryDrag=null, suppressCategoryClickUntil=0;
function restoreCategoryRows(nav){
 for(const cat of restaurant().categories){const row=[...nav.children].find(row=>row.dataset.categoryId===cat.id);if(row)nav.append(row);}
}
async function commitCategoryOrder(ids,focusId){
 const r=restaurant();
 if(ids.join('|')===r.categories.map(c=>c.id).join('|'))return;
 if(busy||!canLeave())return false;
 if(ids.length!==r.categories.length||new Set(ids).size!==ids.length||ids.some(id=>!r.categories.some(c=>c.id===id)))return false;
 r.categories=ids.map(id=>r.categories.find(c=>c.id===id));dirty=false;
 await save();
 $(`.category-row[data-category-id="${CSS.escape(focusId)}"] .category`)?.focus();
 return true;
}
app.addEventListener('pointerdown',e=>{
 const handle=e.target.closest('.category.active');if(!handle||handle.dataset.action!=='category'||busy||e.button!==0||categoryDrag)return;
 const row=handle.closest('.category-row'),nav=row.parentElement;
 categoryDrag={row,nav,handle,pointerId:e.pointerId,startX:e.clientX,startY:e.clientY,moved:false};
 handle.setPointerCapture(e.pointerId);handle.focus();e.preventDefault();
});
app.addEventListener('pointermove',e=>{
 const d=categoryDrag;if(!d||d.pointerId!==e.pointerId)return;
 if(!d.moved&&Math.hypot(e.clientX-d.startX,e.clientY-d.startY)<5)return;
 d.moved=true;suppressCategoryClickUntil=Date.now()+400;d.row.classList.add('dragging');e.preventDefault();
 const horizontal=getComputedStyle(d.nav).display==='flex';
 if(horizontal){const box=d.nav.getBoundingClientRect();if(e.clientX<box.left+30)d.nav.scrollLeft-=16;else if(e.clientX>box.right-30)d.nav.scrollLeft+=16;}
 else if(e.clientY<65)window.scrollBy(0,-18);else if(e.clientY>innerHeight-65)window.scrollBy(0,18);
 const over=document.elementFromPoint(e.clientX,e.clientY)?.closest('.category-row');
 if(!over||over===d.row||over.parentElement!==d.nav)return;
 const rect=over.getBoundingClientRect(),after=horizontal?e.clientX>rect.left+rect.width/2:e.clientY>rect.top+rect.height/2;
 d.nav.insertBefore(d.row,after?over.nextSibling:over);
});
async function endCategoryDrag(e,cancel=false){
 const d=categoryDrag;if(!d||e.pointerId!==d.pointerId)return;categoryDrag=null;
 if(d.moved)suppressCategoryClickUntil=Date.now()+400;d.row.classList.remove('dragging');if(d.handle.hasPointerCapture(e.pointerId))d.handle.releasePointerCapture(e.pointerId);
 if(cancel||!d.moved||!d.nav.contains(document.elementFromPoint(e.clientX,e.clientY))){restoreCategoryRows(d.nav);return;}
 const ids=[...d.nav.children].map(row=>row.dataset.categoryId);
 if(await commitCategoryOrder(ids,d.row.dataset.categoryId)===false)restoreCategoryRows(d.nav);
}
app.addEventListener('pointerup',e=>endCategoryDrag(e).catch(err=>toast(err.message)));
app.addEventListener('pointercancel',e=>endCategoryDrag(e,true));
app.addEventListener('keydown',async e=>{
 if(e.key==='Escape'&&categoryDrag){const d=categoryDrag;categoryDrag=null;d.row.classList.remove('dragging');if(d.handle.hasPointerCapture(d.pointerId))d.handle.releasePointerCapture(d.pointerId);restoreCategoryRows(d.nav);return;}
 const handle=e.target.closest('.category.active');if(!handle||handle.dataset.action!=='category'||busy||categoryDrag||!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))return;
 e.preventDefault();const cid=handle.closest('.category-row').dataset.categoryId,ids=restaurant().categories.map(c=>c.id),pos=ids.indexOf(cid),next=pos+(['ArrowUp','ArrowLeft'].includes(e.key)?-1:1);
 if(next<0||next>=ids.length)return;[ids[pos],ids[next]]=[ids[next],ids[pos]];await commitCategoryOrder(ids,cid);
});

// Reorder selected item rows within the complete, unfiltered category list.
let itemDrag=null, suppressItemClickUntil=0;
function restoreItemRows(nav){
 for(const cat of category().items){const row=[...nav.children].find(row=>row.dataset.id===cat.id);if(row)nav.append(row);}
}
async function commitItemOrder(ids,focusId){
 const r=category();
 if(ids.join('|')===r.items.map(c=>c.id).join('|'))return;
 if(busy||!canLeave())return false;
 if(ids.length!==r.items.length||new Set(ids).size!==ids.length||ids.some(id=>!r.items.some(c=>c.id===id)))return false;
 r.items=ids.map(id=>r.items.find(c=>c.id===id));dirty=false;
 await save();
 $(`.item-row[data-id="${CSS.escape(focusId)}"]`)?.focus();
 return true;
}
app.addEventListener('pointerdown',e=>{
 const handle=e.target.closest('.item-row.selected.reorderable');if(!handle||e.target.closest('button')||busy||search||filter!=='all'||e.button!==0||itemDrag||categoryDrag)return;
 const row=handle.closest('.item-row'),nav=row.parentElement;
 itemDrag={row,nav,handle,pointerId:e.pointerId,startX:e.clientX,startY:e.clientY,moved:false};
 handle.setPointerCapture(e.pointerId);handle.focus();e.preventDefault();
});
app.addEventListener('pointermove',e=>{
 const d=itemDrag;if(!d||d.pointerId!==e.pointerId)return;
 if(!d.moved&&Math.hypot(e.clientX-d.startX,e.clientY-d.startY)<5)return;
 d.moved=true;suppressItemClickUntil=Date.now()+400;d.row.classList.add('dragging');e.preventDefault();
 const horizontal=false;
 const box=d.nav.getBoundingClientRect();
 if(e.clientY<box.top+35)d.nav.scrollTop-=20;else if(e.clientY>box.bottom-35)d.nav.scrollTop+=20;
 if(e.clientY<65)window.scrollBy(0,-18);else if(e.clientY>innerHeight-65)window.scrollBy(0,18);
 const over=document.elementFromPoint(e.clientX,e.clientY)?.closest('.item-row');
 if(!over||over===d.row||over.parentElement!==d.nav)return;
 const rect=over.getBoundingClientRect(),after=horizontal?e.clientX>rect.left+rect.width/2:e.clientY>rect.top+rect.height/2;
 d.nav.insertBefore(d.row,after?over.nextSibling:over);
});
async function endItemDrag(e,cancel=false){
 const d=itemDrag;if(!d||e.pointerId!==d.pointerId)return;itemDrag=null;
 if(d.moved)suppressItemClickUntil=Date.now()+400;d.row.classList.remove('dragging');if(d.handle.hasPointerCapture(e.pointerId))d.handle.releasePointerCapture(e.pointerId);
 if(cancel||!d.moved||!d.nav.contains(document.elementFromPoint(e.clientX,e.clientY))){restoreItemRows(d.nav);return;}
 const ids=[...d.nav.children].map(row=>row.dataset.id);
 if(await commitItemOrder(ids,d.row.dataset.id)===false)restoreItemRows(d.nav);
}
app.addEventListener('pointerup',e=>endItemDrag(e).catch(err=>toast(err.message)));
app.addEventListener('pointercancel',e=>endItemDrag(e,true));
app.addEventListener('keydown',async e=>{
 if(e.key==='Escape'&&itemDrag){const d=itemDrag;itemDrag=null;d.row.classList.remove('dragging');if(d.handle.hasPointerCapture(d.pointerId))d.handle.releasePointerCapture(d.pointerId);restoreItemRows(d.nav);return;}
 const handle=e.target.closest('.item-row.selected.reorderable');if(!handle||e.target.closest('button')||busy||search||filter!=='all'||itemDrag||!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))return;
 e.preventDefault();const cid=handle.closest('.item-row').dataset.id,ids=category().items.map(c=>c.id),pos=ids.indexOf(cid),next=pos+(['ArrowUp','ArrowLeft'].includes(e.key)?-1:1);
 if(next<0||next>=ids.length)return;[ids[pos],ids[next]]=[ids[next],ids[pos]];await commitItemOrder(ids,cid);
});

// Products are the source of truth; materialized fields keep PDF and exports compatible.
function syncProducts(){
 syncProductCategories();const products=new Map(data.products.map(p=>[p.id,p]));
 for(const r of data.restaurants){r.tagCatalog=structuredClone(data.productTags);for(const c of r.categories)for(const i of c.items){const p=products.get(i.productId);if(!p)throw Error('Select an existing product.');for(const key of ['name','productCode','description','price','tags','options','notes','image','reviewed'])i[key]=structuredClone(p[key]);i.cuisine=p.cuisine||'';}}
}
function productListHTML(){return data.products.filter(p=>(!productCategoryId||p.categoryId===productCategoryId)).filter(p=>[p.name,p.productCode,p.description].join(' ').toLowerCase().includes(productSearch.toLowerCase())).map(p=>`<button class="item-row ${p.id===productId?'selected':''}" data-action="select-product" data-id="${esc(p.id)}"><span><strong>${esc(p.name)}</strong><small>${esc(p.productCode||'No product code')}</small>${!p.reviewed?'<span class="product-review-label">To review</span>':''}</span><span class="item-price">${fmt(p.price)}</span></button>`).join('')||'<p class="empty-small">No products found.</p>';}
function productsHTML(){const p=item();return `<div class="page-heading"><div><div class="eyebrow">SHARED CATALOG</div><h1>Products</h1><p>${data.products.length} products · Changes apply to every restaurant using the product.</p></div><div class="heading-actions">${button('manage-labels','Labels & serving details','','secondary')}${button('add-product','+ New product','','primary')}</div></div><div class="products-grid">${productCategoriesHTML()}<section class="items-panel"><div class="item-tools"><label class="search"><span class="sr-only">Search products</span><input type="search" id="product-search" placeholder="Name or product code…" value="${esc(productSearch)}"></label></div><div id="product-list">${productListHTML()}</div></section><section class="details-panel">${p?`<p class="hint">Used by: ${esc(data.restaurants.filter(r=>r.categories.some(c=>c.items.some(i=>i.productId===p.id))).map(r=>r.name).join(', ')||'No restaurants yet')}</p>${detailHTML(p)}`:'<p>Create a product to get started.</p>'}</section></div>`;}
function placementHTML(i){return `<div class="detail-heading"><span class="eyebrow">MENU PRODUCT</span>${button('edit-product','Edit',`data-product-id="${esc(i.productId)}"`,'secondary')}</div><h2>${esc(i.name)}</h2><p>${esc(i.description)}</p><p>${esc(i.productCode)} · ${fmt(i.price)}</p><p>${i.tags.map(tagDisplay).join(' · ')}</p><p class="hint">Edit this product in Products. Changes apply to all restaurants using it.</p><form id="placement-form"><p class="hint">Category: ${esc(data.productCategories.find(c=>c.id===data.products.find(p=>p.id===i.productId)?.categoryId)?.name)} · Change in Products to move it in every restaurant.</p><label class="check-row"><input type="checkbox" name="available" ${i.available?'checked':''}>Show on this restaurant’s menu</label><div class="detail-bottom">${button('delete-item','Remove from menu','','text-button danger')}<button class="primary" type="submit">Save placement</button></div></form>`;}
function productPickerHTML(){return data.products.filter(p=>p.categoryId===category().catalogCategoryId).filter(p=>!category().items.some(i=>i.productId===p.id)).map(p=>`<label class="check-row picker-product" data-search="${esc((p.name+' '+p.productCode).toLowerCase())}"><input type="checkbox" name="product" value="${esc(p.id)}"><span>${esc(p.name)}<small>${esc(p.productCode||'No code')} · ${fmt(p.price)}</small></span></label>`).join('')||'<p>No more products available in this category. Create or recategorize products in Products.</p>';}
modal.addEventListener('input',e=>{if(e.target.id==='product-picker-search')for(const row of modal.querySelectorAll('.picker-product'))row.hidden=!row.dataset.search.includes(e.target.value.toLowerCase());});
app.addEventListener('keydown',e=>{if(e.target.matches('div.item-row')&&['Enter',' '].includes(e.key)){e.preventDefault();action('item',e.target);}});

function productCategoryField(p){return `<label class="field">Category<select name="productCategory" required>${data.productCategories.map(c=>`<option value="${esc(c.id)}" ${p.categoryId===c.id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><p class="hint">One category across all restaurants. Changing it moves this product wherever it is used.</p>`;}
function productCategoriesHTML(){return `<section class="categories product-categories"><div class="section-heading"><h2>Categories</h2>${button('add-product-category','+','aria-label="Add product category"','icon-button')}</div><nav aria-label="Product categories">${button('product-category',`<span>All products</span><span>${data.products.length}</span>`,'data-id=""','category '+(!productCategoryId?'active':''))}${data.productCategories.map(c=>`<div class="product-category-row ${c.id===productCategoryId?'selected':''}">${button('product-category',`<span>${esc(c.name)}</span><span>${data.products.filter(p=>p.categoryId===c.id).length}</span>`,`data-id="${esc(c.id)}"`,'category '+(c.id===productCategoryId?'active':''))}${button('rename-product-category','<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m16 3 5 5-12 12-6 1 1-6Z"/><path d="m14 5 5 5"/></svg>',`data-id="${esc(c.id)}" aria-label="Rename ${esc(c.name)}" title="Rename category"`,'category-rename-button')}</div>`).join('')}</nav>${productCategoryId?button('edit-product-category','Edit category','','text-button'):''}</section>`;}
function focusCategoryRename(cid){[...app.querySelectorAll('[data-action="rename-product-category"]')].find(el=>el.dataset.id===cid)?.focus();}
function closeCategoryRename(cid){$('.product-categories').outerHTML=productCategoriesHTML();focusCategoryRename(cid);}
function openCategoryRename(cid){
 const cat=data.productCategories.find(c=>c.id===cid);if(!cat)return;
 const trigger=[...app.querySelectorAll('[data-action="rename-product-category"]')].find(el=>el.dataset.id===cid);
 trigger.closest('.product-category-row').outerHTML=`<form class="category-rename" data-category-id="${esc(cid)}" aria-label="Rename category"><label for="category-rename-name">Category name</label><input id="category-rename-name" name="categoryName" value="${esc(cat.name)}" required maxlength="200" autocomplete="off" aria-describedby="category-rename-help category-rename-error"><p id="category-rename-help">Updates all restaurants.</p><p id="category-rename-error" class="category-rename-error" role="alert"></p><div><button type="submit" class="primary">Save</button>${button('cancel-category-rename','Cancel','','text-button')}</div></form>`;
 $('#category-rename-name').focus();$('#category-rename-name').select();$('.category-rename').scrollIntoView({block:'nearest',inline:'nearest'});
}
function syncProductCategories(){
 const masters=new Map(data.productCategories.map(c=>[c.id,c])),products=new Map(data.products.map(p=>[p.id,p]));
 for(const r of data.restaurants){const groups=new Map(),ordered=[],placements=r.categories.flatMap(c=>c.items);
  for(const c of r.categories){if(masters.has(c.catalogCategoryId)&&!groups.has(c.catalogCategoryId)){c.name=masters.get(c.catalogCategoryId).name;c.items=[];groups.set(c.catalogCategoryId,c);ordered.push(c);}}
  for(const i of placements){const cid=products.get(i.productId)?.categoryId;if(!masters.has(cid))throw Error('Choose a product category.');if(!groups.has(cid)){const c={id:id(),catalogCategoryId:cid,name:masters.get(cid).name,notes:'',items:[]};groups.set(cid,c);const rank=data.productCategories.findIndex(c=>c.id===cid),pos=ordered.findIndex(c=>data.productCategories.findIndex(x=>x.id===c.catalogCategoryId)>rank);ordered.splice(pos<0?ordered.length:pos,0,c);}groups.get(cid).items.push(i);}
  r.categories=ordered;
 }
 const r=restaurant(),selected=r.categories.find(c=>c.items.some(i=>i.id===itemId));if(selected)categoryId=selected.id;else if(!r.categories.some(c=>c.id===categoryId)){categoryId=r.categories[0]?.id;itemId=category()?.items[0]?.id;}
}
