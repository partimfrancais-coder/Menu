import copy, json, re, sys, uuid, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from server import validate
from products import category_key
WORK=ROOT/'tmp/drinks-import'
before=json.loads((WORK/'before.json').read_text(encoding='utf-8'))
data=copy.deepcopy(before)
sources=json.loads((WORK/'transcribed.json').read_text(encoding='utf-8'))
names=['KOI Kuningan Drinks and Cocktail','KOI Rooftop Drinks and Cocktail','KOI Mahakam Drinks and Cocktail']
files=['Kuningan Fingerood Drinks Menu 20260720.pdf','KOI ROOFTOP Menu - Drinks & Cocktails November.pdf','Mahakam Fingerfood Drinks Standart Menu November.pdf']
assert not any(r['name'].casefold() in [n.casefold() for n in names] for r in before['restaurants'])
def key(s):
    s=unicodedata.normalize('NFKD',s.casefold().replace('&',' and '))
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
products={key(p['name']):p for p in data['products']}
assert len(products)==len(data['products']), 'Ambiguous normalized product names'
cats={category_key(c['name']):c for c in data['productCategories']}
aliases={key('Thin Chicken Turkish Pizza'):key('Chicken Lahmacun')}
audit=[];new_products=[];new_cats=[]
for index,(name,entries) in enumerate(zip(names,sources)):
    r=dict(id=str(uuid.uuid4()),name=name,location=['Kuningan','Rooftop','Mahakam'][index],menuTitle='Drinks & Cocktails',currency='IDR',priceUnit=1000,serviceCharge=10,tax=10,footer='All prices are listed in Rp. 1.000,- and are subject to 10% service charge and 10% tax',dietaryNote='' if index==1 else 'No pork, no lard',logo='',source=files[index],designPrompt='',categories=[],tagCatalog=copy.deepcopy(data['productTags']))
    groups={}
    for src in entries:
        k=aliases.get(key(src['name']),key(src['name']))
        p=products.get(k)
        existing=p is not None
        if not p:
            ck=category_key(src['category'])
            if ck not in cats:
                cat=dict(id=str(uuid.uuid4()),name=src['category'])
                cats[ck]=cat;data['productCategories'].append(cat);new_cats.append(cat['name'])
            p=dict(id=str(uuid.uuid4()),name=src['name'],productCode='',categoryId=cats[ck]['id'],price=src['price'],description=src['description'],options=copy.deepcopy(src['options']),tags=[],notes='',image='',available=True,reviewed=False,cuisine='')
            if src['name'] in ['H','Kranken','Gentelman Jack']:
                p['notes']='Name transcribed exactly as printed; verify brand spelling before publication.'
            data['products'].append(p);products[k]=p;new_products.append(p['id'])
        cid=p['categoryId']
        cat=next(c for c in data['productCategories'] if c['id']==cid)
        if cid not in groups:
            notes=''
            if index in (0,2) and cat['name']=='Cocktails':notes='Every Friday & Saturday: buy 1 get 1, from 6 PM until closing.'
            if cat['name']=='Everyday Happy Hour':notes='Every day, 4–8 PM. Bucket of 5 bottles.'
            groups[cid]=dict(id=str(uuid.uuid4()),catalogCategoryId=cid,name=cat['name'],notes=notes,items=[])
            r['categories'].append(groups[cid])
        item=copy.deepcopy(p);item.update(id=str(uuid.uuid4()),productId=p['id'],available=True)
        groups[cid]['items'].append(item)
        differences={field:dict(source=src[field],catalog=p[field]) for field in ['price','options','description'] if src[field]!=p[field]}
        audit.append(dict(restaurant=name,sourceCategory=src['category'],sourceName=src['name'],catalogName=p['name'],catalogCategory=cat['name'],productId=p['id'],reused=existing,differences=differences))
    assert sum(len(c['items']) for c in r['categories'])==len(entries)
    assert len({i['productId'] for c in r['categories'] for i in c['items']})==len(entries)
    data['restaurants'].append(r)
validate(data)
assert data['restaurants'][:len(before['restaurants'])]==before['restaurants'],'Existing restaurants changed'
assert data['products'][:len(before['products'])]==before['products'],'Existing products changed'
assert data['productCategories'][:len(before['productCategories'])]==before['productCategories']
assert data['productTags']==before['productTags']
assert all(r['designPrompt']=='' for r in data['restaurants'][-3:])
summary=dict(restaurants=[dict(name=r['name'],items=sum(len(c['items']) for c in r['categories']),categories=len(r['categories'])) for r in data['restaurants'][-3:]],newProducts=len(new_products),newCategories=new_cats,reusedPlacements=sum(x['reused'] for x in audit),priceDifferences=[a for a in audit if 'price' in a['differences']],reviewNotes=['Spirit prices are preserved in printed order; the PDF does not label serving units.','The Mahakam PDF includes a Thursday Aperitivo promotion explicitly restricted to Kemang and Mega Kuningan; it was not assigned to Mahakam.','Product prices, options, and descriptions are shared across restaurants. Differences are recorded in the audit.'])
(WORK/'proposed.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK/'audit.json').write_text(json.dumps(dict(summary=summary,items=audit),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True,indent=2))
