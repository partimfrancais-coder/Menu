'use strict';
(function(root){
 const defaults=[
  ['Vegetarian','label'],['Spicy','label'],['New menu','label'],
  ['Takes more than 15 mins','serving'],['With jasmine rice','serving'],
  ['Choice of white or red rice','serving'],['With baby potatoes','serving'],
  ['With mashed potato','serving'],['With French or Belgian fries','serving'],
  ['With mixed salad','serving'],['With baguette','serving']
 ];
 const items=r=>r.categories.flatMap(c=>c.items);
 const key=name=>name.trim().toLowerCase();
 function initialize(r){
  // Only migrate restaurants that predate the manager; an empty catalog is intentional.
  if(!Array.isArray(r.tagCatalog)){
   r.tagCatalog=defaults.map(([name,kind])=>({name,kind}));
   for(const item of items(r))for(const name of item.tags){
    if(!r.tagCatalog.some(t=>key(t.name)===key(name)))r.tagCatalog.push({name:name.trim(),kind:'label'});
   }
   for(const item of items(r))item.tags=[...new Set(item.tags.map(name=>r.tagCatalog.find(t=>key(t.name)===key(name)).name))];
  }
  for(const tag of r.tagCatalog){
   if(tag.icon===undefined)tag.icon='';
   if(tag.iconImage===undefined)tag.iconImage='';
  }
  return r.tagCatalog;
 }
 function validate(rows){
  const names=new Set();
  for(const row of rows){
   if(!row.name.trim()||row.name.trim().length>200)throw Error('Enter a name of 1–200 characters for every option.');
   if(!['label','serving'].includes(row.kind))throw Error('Choose Labels or Serving details for every option.');
   if(row.icon!==undefined&&(typeof row.icon!=='string'||row.icon.length>32))throw Error('Choose a valid icon.');
   if(row.iconImage!==undefined&&(typeof row.iconImage!=='string'||row.iconImage.length>400000||(row.iconImage&&!/^data:image\/(png|jpeg|webp);base64,/.test(row.iconImage))))throw Error('Choose a PNG, JPG or WebP icon smaller than 256 KB.');
   if(names.has(key(row.name)))throw Error('Each label or serving detail must have a unique name.');
   names.add(key(row.name));
  }
 }
 function apply(r,rows){
  validate(rows);
  const original=initialize(r),oldNames=new Set(original.map(t=>t.name));
  const renamed=new Map(rows.filter(t=>t.original).map(t=>[t.original,t.name.trim()]));
  const next=rows.map(t=>{
   const previous=original.find(old=>old.name===t.original);
   return {name:t.name.trim(),kind:t.kind,icon:t.icon??previous?.icon??'',iconImage:t.iconImage??previous?.iconImage??''};
  });
  for(const item of items(r))item.tags=[...new Set(item.tags.flatMap(name=>oldNames.has(name)?(renamed.has(name)?[renamed.get(name)]:[]):[name]))];
  r.tagCatalog=next;
 }
 function addCustom(r,names){
  for(const name of names)validate([{name,kind:'label'}]);
  const catalog=initialize(r);
  return names.map(name=>{
   const existing=catalog.find(t=>key(t.name)===key(name));
   if(existing)return existing.name;
   const value=name.trim();validate([{name:value,kind:'label'}]);
   catalog.push({name:value,kind:'label'});return value;
  });
 }
 const api={initialize,validate,apply,addCustom};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.MenuCatalog=api;
})(globalThis);
