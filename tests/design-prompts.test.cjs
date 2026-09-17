const test=require('node:test');const assert=require('node:assert/strict');
const prompts=require('../dist/design-prompts.js');
test('reference-specific briefs preserve restaurant layout differences',()=>{
 const a=prompts.create({name:'KOI Kemang',source:'Kemang Lunch & Dinner 20260605A.pdf'});
 const b=prompts.create({name:'KOI Kuningan',source:'Kuningan Lunch & Dinner 20260606A.pdf'});
 assert.notEqual(a,b);assert.match(a,/892.92 × 631.44/);assert.match(b,/502.32 × 355.20/);
 assert.match(a,/Right column: Pizza, Lamb/);assert.match(b,/Right column: Lamb/);
 for(const p of [a,b]){assert.match(p,/Do not generate a menu now/);assert.match(p,/For extra dishes/);assert.ok(p.length<30000);}
});
test('new restaurant brief does not borrow another restaurant reference',()=>{
 const brief=prompts.create({name:'New restaurant',source:''});assert.match(brief,/New restaurant/);assert.match(brief,/attach it before generation/);assert.doesNotMatch(brief,/Kemang|Kuningan/);
});
