'use strict';
// The API key is never placed in a URL, localStorage, a cookie, or conversation data.
globalThis.MenuChat=(()=>{
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let keyStatus={configured:false,canManage:false},dialog,context,timer,loading=false,sending=false,stopping=false,turns=[],draft='',error='',epoch=0,pendingRequest=null,logSignature='';
 async function api(path,options={}){
  const response=await fetch(path,options);
  let result;try{result=await response.json();}catch{throw Error('The server could not be reached. Reopen this conversation to check its status.');}
  if(!response.ok)throw Error(result.error||(response.status===401?'Sign in again to continue.':'The request failed. Please try again.'));
  return result;
 }
 const freshPrompt='Create the menu PDF entirely from the current saved back-office data and saved design instructions, using this restaurant’s skill and reference artwork. Include all currently visible items and their current prices. Start a new design without using earlier PDFs or chat adjustments.';
 const endpoint=()=>`/api/ai/restaurants/${encodeURIComponent(context.id)}/conversation`;
 const active=()=>turns.some(t=>['queued','running','cancelling'].includes(t.status));
 function diagnosticsHtml(t){
  const d=t.diagnostics;
  if(!d||!Object.keys(d).length)return '';
  const u=d.usage||{};
  const rows=[['Provider status',d.providerStatus],['Incomplete reason',d.incompleteReason],['Error code',d.errorCode],['Failure type',d.failureKind],['HTTP status',d.httpStatus],['Elapsed seconds',d.elapsedSeconds],['Code steps completed',d.codeStepsCompleted==null?null:`${d.codeStepsCompleted} / ${d.codeStepsStarted}`],['Input tokens',u.input_tokens],['Output tokens',u.output_tokens],['Reasoning tokens',u.reasoning_tokens],['Cached input tokens',u.cached_tokens],['Total tokens',u.total_tokens],['Output token limit',d.maxOutputTokens]];
  return `<details class="chat-diagnostics"><summary>Generation details</summary><ul>${rows.filter(([,value])=>value!=null).map(([label,value])=>`<li>${esc(label)}: ${esc(value)}</li>`).join('')}</ul><p>Usage is shown when reported by OpenAI; it is not a billing receipt.</p></details>`;
 }
 function keyHelp(){return keyStatus.configured?'Key saved securely. Used for menu generation in this workspace.':'Save Alain’s OpenAI API key to enable menu generation. API usage is billed to that account.';}
 function updateHelp(){const el=document.querySelector('#api-key-help');if(el)el.textContent=keyHelp();}
 async function initialize(isHosted){if(!isHosted)return;try{keyStatus=await api('/api/ai/key');updateHelp();}catch{/* The generation dialog displays actionable connection errors. */}}
 async function saveKey(key){
  keyStatus=await api('/api/ai/key',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
  updateHelp();
 }
 async function removeKey(){keyStatus=await api('/api/ai/key',{method:'DELETE'});updateHelp();}
 function draw(){
  if(!dialog?.open)return;
  const log=dialog.querySelector('.menu-chat-messages');
  const nearBottom=log.scrollHeight-log.scrollTop-log.clientHeight<100;
  const signature=JSON.stringify([turns,turns.length?false:loading]);
  if(signature!==logSignature){
  logSignature=signature;
  log.innerHTML=turns.map((t,index)=>`<article class="menu-chat-turn"><div class="chat-message user"><strong>You</strong><p>${esc(t.prompt)}</p></div><div class="chat-message assistant"><strong>Menu designer</strong>${['queued','running','cancelling'].includes(t.status)?`<p class="chat-progress" role="status">${esc(t.progress||'Generation is in progress.')}<br>Elapsed: ${Math.floor(Math.max(0,Date.now()/1000-t.created)/60)} min ${Math.floor(Math.max(0,Date.now()/1000-t.created)%60)} sec.${t.updated?` Last server update: ${Math.floor(Math.max(0,Date.now()/1000-t.updated))} seconds ago.`:''}<br>You can close this window and return. Requests stop after 20 minutes of OpenAI processing.</p>`:t.status==='failed'?`<p class="chat-error" role="alert">${esc(t.error)}</p>`:`<p>${esc(t.answer)}</p>`}${t.pdf?`<div class="chat-pdf"><div class="chat-pdf-heading"><strong>Menu PDF · version ${turns.slice(0,index+1).filter(x=>x.pdf).length}</strong><a href="${esc(t.pdf)}" download>Download PDF ↓</a></div>${t.previews.map((url,page)=>`<a href="${esc(url)}" target="_blank" rel="noopener" aria-label="Enlarge page ${page+1}"><img src="${esc(url)}" alt="Generated menu, page ${page+1}" loading="lazy"></a>`).join('')}</div>`:''}${t.warnings?.length?`<ul class="chat-review">${t.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul>`:''}${diagnosticsHtml(t)}</div></article>`).join('')||`<div class="chat-empty"><h3>${loading?'Opening your conversation…':'Design your menu with AI'}</h3><p>The first PDF uses your saved menu, design instructions and reference artwork. Ask for layout adjustments here, and each revision appears as a new PDF.</p></div>`;
  if(nearBottom){
   log.scrollTop=log.scrollHeight;
   log.querySelectorAll('img').forEach(img=>img.addEventListener('load',()=>{log.scrollTop=log.scrollHeight;},{once:true}));
  }
  }
  dialog.querySelector('.menu-chat-error').textContent=error;
  dialog.querySelector('.menu-chat-key-note').textContent=keyStatus.configured?'Uses Alain’s API key. Each generation is billed by OpenAI.':keyHelp();
  const submit=dialog.querySelector('[type=submit]');submit.disabled=loading||sending||active()||!keyStatus.configured;
  submit.textContent=sending||active()?'Generating…':turns.length?'Send adjustment':'Generate menu';
  const stop=dialog.querySelector('[data-chat-stop]');
  stop.hidden=!active();stop.disabled=stopping||turns.some(t=>t.status==='cancelling');
  stop.textContent=stop.disabled?'Stopping…':'Stop generation';
  dialog.querySelector('[data-chat-refresh]').disabled=loading||sending||stopping;
  const regenerate=dialog.querySelector('[data-chat-regenerate]');
  regenerate.hidden=!turns.length;regenerate.disabled=loading||sending||active()||!keyStatus.configured;
  if(nearBottom)log.scrollTop=log.scrollHeight;
 }
 function ensureDialog(){
  if(dialog)return;
  dialog=document.createElement('dialog');dialog.className='menu-chat';
  dialog.innerHTML='<header><div><span class="eyebrow">MENU DESIGN CONVERSATION</span><h2></h2></div><button type="button" data-chat-close class="icon-button" aria-label="Close conversation">×</button></header><div class="menu-chat-messages" role="log" aria-label="Menu design conversation"></div><div class="menu-chat-error" role="alert"></div><form class="menu-chat-form"><label class="field">Ask for an adjustment<textarea name="message" rows="3" maxlength="6000" placeholder="For example: give the categories more space and make the prices easier to read."></textarea></label><div class="menu-chat-controls"><p class="menu-chat-key-note"></p><button type="button" data-chat-refresh class="secondary">Check status</button><button type="button" data-chat-regenerate class="secondary" hidden>Regenerate from saved menu</button><button type="button" data-chat-stop class="secondary" hidden>Stop generation</button><button type="submit" class="primary">Generate menu</button></div></form>';
  document.body.append(dialog);
  dialog.querySelector('[data-chat-close]').onclick=()=>dialog.close();
  dialog.querySelector('[data-chat-stop]').onclick=stopGeneration;
  dialog.querySelector('[data-chat-refresh]').onclick=()=>refresh(epoch);
  dialog.querySelector('[data-chat-regenerate]').onclick=()=>send(freshPrompt,'fresh');
  dialog.addEventListener('close',()=>{if(!dialog.open){clearTimeout(timer);epoch++;}});
  dialog.querySelector('textarea').addEventListener('input',e=>draft=e.target.value);
  dialog.querySelector('form').addEventListener('submit',e=>{e.preventDefault();send(draft.trim()||(!turns.length?freshPrompt:''),turns.length?'adjust':'fresh');});
 }
 async function refresh(token){
  clearTimeout(timer);loading=true;draw();
  try{
   const [status,chat]=await Promise.all([api('/api/ai/key'),api(endpoint())]);
   if(token!==epoch)return;
   keyStatus=status;turns=chat.turns;error='';
  }catch(e){if(token===epoch)error=e.message;}
  finally{if(token===epoch){loading=false;draw();if(active()&&dialog.open)timer=setTimeout(()=>refresh(token),4000);}}
 }
 async function stopGeneration(){
  const turn=turns.find(t=>['queued','running'].includes(t.status));
  if(!turn||stopping)return;
  const token=++epoch;clearTimeout(timer);loading=false;stopping=true;error='';draw();
  try{
   const result=await api(`${endpoint()}/${encodeURIComponent(turn.id)}/cancel`,{method:'POST'});
   if(token===epoch)turns=result.turns;
  }catch(e){if(token===epoch)error=e.message;}
  finally{if(token===epoch){stopping=false;draw();if(active())timer=setTimeout(()=>refresh(token),1000);}}
 }
 async function send(message,mode='adjust'){
  if(!message||sending||loading||active())return;
  const token=epoch;
  sending=true;error='';clearTimeout(timer);draw();
  if(!pendingRequest||pendingRequest.mode!==mode||pendingRequest.message!==message||pendingRequest.restaurant!==context.id){pendingRequest={message,mode,restaurant:context.id,requestId:crypto.randomUUID(),revision:context.revision()};}
  try{
   const result=await api(endpoint(),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(pendingRequest)});
   if(token!==epoch)return;
   turns=result.turns;draft='';dialog.querySelector('textarea').value='';pendingRequest=null;
  }catch(e){if(token===epoch)error=e.message;}
  finally{if(token===epoch){sending=false;draw();if(active())timer=setTimeout(()=>refresh(token),2000);}}
 }
 async function open(restaurant,revision){
  ensureDialog();if(dialog.open)return;
  const changed=context?.id!==restaurant.id;
  if(changed){draft='';pendingRequest=null;}
  context={id:restaurant.id,revision};turns=[];error='';sending=false;stopping=false;logSignature='';
  dialog.querySelector('h2').textContent=restaurant.name;
  dialog.querySelector('textarea').value=draft;
  dialog.showModal();const token=++epoch;
  await refresh(token);
 }
 return {initialize,keyHelp,saveKey,removeKey,open};
})();
