"""Explicit public projection; never publish workspace records directly."""
import base64
from urllib.parse import quote

def public_menu(data,rid):
    r=next((r for r in data['restaurants'] if r['id']==rid),None)
    if r is None: raise ValueError('Menu not found.')
    result={k:r.get(k,'') for k in ('name','location','menuTitle','currency','priceUnit','serviceCharge','tax','footer','dietaryNote','logo')}
    if r.get('logo'): result['logo']='/api/public/menus/'+quote(rid,safe='')+'/images/logo'
    categories=[];used=set()
    for c in r['categories']:
        items=[]
        for i in c['items']:
            if not i.get('available',False): continue
            item={k:i.get(k,'') for k in ('name','description','price','image','cuisine')}
            if i.get('image'): item['image']='/api/public/menus/'+quote(rid,safe='')+'/images/'+quote(i['id'],safe='')
            item['tags']=list(i.get('tags',[]));used.update(item['tags'])
            item['options']=[{k:o[k] for k in ('name','price','kind')} for o in i.get('options',[])]
            items.append(item)
        if items:categories.append({'name':c['name'],'items':items})
    result['categories']=categories
    result['labels']=[{k:t.get(k,'') for k in ('name','kind','icon','iconImage')} for t in r.get('tagCatalog',[]) if t['name'] in used]
    return result


def public_image(data,rid,iid):
    r=next((r for r in data['restaurants'] if r['id']==rid),None)
    if r is None: raise ValueError('Image not found.')
    if iid=='logo': source=r.get('logo','')
    else: source=next((i.get('image','') for c in r['categories'] for i in c['items'] if i['id']==iid and i.get('available',False)),'')
    prefix,separator,encoded=source.partition(',')
    types={'data:image/png;base64':'image/png','data:image/jpeg;base64':'image/jpeg','data:image/webp;base64':'image/webp'}
    if not separator or prefix not in types: raise ValueError('Image not found.')
    try: raw=base64.b64decode(encoded,validate=True)
    except Exception: raise ValueError('Image not found.')
    return raw,types[prefix]
