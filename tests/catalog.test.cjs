const test=require('node:test');
const assert=require('node:assert/strict');
const catalog=require('../dist/catalog.js');
const fixture=()=>({categories:[{items:[{tags:['Vegetarian','With baguette','House special']},{tags:['Vegetarian']}]}]});
const rows=r=>r.tagCatalog.map(t=>({...t,original:t.name}));
test('icons survive rename and backup restore and remain independent',()=>{
 const a=fixture(),b=fixture();catalog.initialize(a);catalog.initialize(b);
 const edits=rows(a);edits[0].icon='🌿';edits[0].name='Plant-based';
 edits[1].iconImage='data:image/png;base64,iVBORw0KGgo=';catalog.apply(a,edits);
 const restored=JSON.parse(JSON.stringify(a));catalog.initialize(restored);
 assert.equal(restored.tagCatalog[0].icon,'🌿');assert.equal(restored.tagCatalog[0].name,'Plant-based');
 assert.equal(restored.tagCatalog[1].iconImage,edits[1].iconImage);assert.equal(b.tagCatalog[0].icon,'');
 const clear=rows(restored);clear[0].icon='';clear[1].iconImage='';catalog.apply(restored,clear);catalog.initialize(restored);
 assert.equal(restored.tagCatalog[0].icon,'');assert.equal(restored.tagCatalog[1].iconImage,'');
});
test('invalid custom icons are rejected without mutating data',()=>{
 const a=fixture();catalog.initialize(a);const before=structuredClone(a);
 for(const iconImage of ['data:image/svg+xml;base64,abc','https://example.com/icon.png','data:image/png;base64,'+'a'.repeat(400000)]){
  const edits=rows(a);edits[0].iconImage=iconImage;assert.throws(()=>catalog.apply(a,edits));
 }
 assert.deepEqual(a,before);
});

test('legacy menus retain selections and custom labels in independent catalogs',()=>{
 const a=fixture(),b=fixture();catalog.initialize(a);catalog.initialize(b);
 assert.equal(a.tagCatalog.find(t=>t.name==='With baguette').kind,'serving');
 assert.ok(a.tagCatalog.some(t=>t.name==='House special'));
 assert.deepEqual(a.categories[0].items[0].tags,['Vegetarian','With baguette','House special']);
 a.tagCatalog[0].name='Changed';assert.equal(b.tagCatalog[0].name,'Vegetarian');
});
test('renaming updates all assigned dishes only within selected restaurant',()=>{
 const a=fixture(),b=fixture();catalog.initialize(a);const before=structuredClone(b);
 const edits=rows(a);edits.find(t=>t.name==='Vegetarian').name='Plant-based';catalog.apply(a,edits);
 assert.ok(a.categories[0].items.every(i=>i.tags.includes('Plant-based')));
 assert.deepEqual(b,before);
});
test('remove and reclassify options without losing unrelated dish details',()=>{
 const a=fixture();catalog.initialize(a);
 const edits=rows(a).filter(t=>t.name!=='Vegetarian');edits.find(t=>t.name==='House special').kind='serving';catalog.apply(a,edits);
 assert.deepEqual(a.categories[0].items[0].tags,['With baguette','House special']);
 assert.equal(a.tagCatalog.find(t=>t.name==='House special').kind,'serving');
});
test('intentional empty lists stay empty after reload',()=>{
 const a=fixture();catalog.initialize(a);catalog.apply(a,[]);catalog.initialize(a);
 assert.deepEqual(a.tagCatalog,[]);assert.deepEqual(a.categories[0].items[0].tags,[]);
});
test('duplicate or blank names are rejected without changing the menu',()=>{
 const a=fixture();catalog.initialize(a);const before=structuredClone(a);
 assert.throws(()=>catalog.apply(a,[{name:'Hot',kind:'label'},{name:' hot ',kind:'serving'}]));
 assert.throws(()=>catalog.apply(a,[{name:' ',kind:'label'}]));assert.deepEqual(a,before);
});
test('custom item labels become reusable restaurant options',()=>{
 const a=fixture();catalog.initialize(a);
 assert.deepEqual(catalog.addCustom(a,['vegetarian','Chef choice']),['Vegetarian','Chef choice']);
 assert.equal(a.tagCatalog.filter(t=>t.name==='Chef choice').length,1);
});
test('simultaneous renames preserve correct assignment and copied menus are independent',()=>{
 const a=fixture();catalog.initialize(a);const copy=structuredClone(a),edits=rows(copy);
 edits.find(t=>t.original==='Vegetarian').name='With baguette';
 edits.find(t=>t.original==='With baguette').name='Vegetarian';catalog.apply(copy,edits);
 assert.deepEqual(copy.categories[0].items[1].tags,['With baguette']);
 assert.deepEqual(a.categories[0].items[1].tags,['Vegetarian']);
});
