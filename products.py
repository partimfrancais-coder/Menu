"""Shared products; restaurant items are placements with materialized export fields."""
import copy
import uuid

FIELDS = ('name','productCode','description','price','tags','options','notes','image','reviewed','cuisine')

def synchronize(data):
    if 'products' not in data: return data
    if not isinstance(data['products'],list): raise ValueError('Invalid product catalog.')
    products={}
    codes=set()
    for product in data['products']:
        if not isinstance(product,dict) or not isinstance(product.get('id'),str) or not product['id'] or product['id'] in products: raise ValueError('Product identifiers must be unique.')
        if product.get('cuisine','') not in ('','European','Asian'): raise ValueError('Cuisine must be European or Asian.')
        code=product.get('productCode','')
        if not isinstance(code,str): raise ValueError('Invalid product code.')
        if code.strip() and code.strip().casefold() in codes: raise ValueError('Product codes must be unique in Products.')
        if code.strip(): codes.add(code.strip().casefold())
        products[product['id']]=product
    for r in data['restaurants']:
        for c in r['categories']:
            for item in c['items']:
                product=products.get(item.get('productId'))
                if product is None: raise ValueError('Choose an existing product from Products before adding it to a restaurant.')
                for key in FIELDS: item[key]=copy.deepcopy(product.get(key,'' if key in ('productCode','cuisine') else None))
        # Shared label definitions keep every restaurant preview/export self-contained.
        r['tagCatalog']=copy.deepcopy(data.get('productTags',[]))
    return synchronize_categories(data)

def migrate(data):
    if 'products' in data: return data
    data=copy.deepcopy(data)
    products={}; tags={}
    restaurants=sorted(data['restaurants'],key=lambda r: 0 if r['name']=='KOI Kuningan' else 1 if r['name']=='KOI Kemang' else 2)
    for r in restaurants:
        for tag in r.get('tagCatalog',[]): tags.setdefault(tag['name'],copy.deepcopy(tag))
        for cat in r['categories']:
            for item in cat['items']:
                code=item.get('productCode','').strip()
                key='code:'+code.casefold() if code else 'item:'+item['id']
                if key not in products:
                    p={k:copy.deepcopy(item.get(k,'' if k in ('productCode','cuisine') else None)) for k in FIELDS}
                    p.update(id=str(uuid.uuid5(uuid.NAMESPACE_URL,'menu-studio:'+key)),available=True)
                    products[key]=p
                item['productId']=products[key]['id']
                for tag in item['tags']: tags.setdefault(tag,{'name':tag,'kind':'label','icon':''})
    data['products']=list(products.values()); data['productTags']=list(tags.values())
    return synchronize(data)

def prepare_save(data,current):
    if 'productCategories' in current and 'productCategories' not in data:
        raise ValueError('Reload this window or use a backup containing shared product categories.')
    if 'products' in current and 'products' not in data:
        raise ValueError('This backup or window predates the shared product catalog. Reload and use a current backup.')
    return synchronize(data)

def category_key(name):
    return ' '.join(name.casefold().replace('&',' and ').split())

def synchronize_categories(data):
    if 'productCategories' not in data: return data
    categories=data['productCategories']
    if not isinstance(categories,list): raise ValueError('Invalid product categories.')
    by_id={};names=set()
    for cat in categories:
        if not isinstance(cat,dict) or not isinstance(cat.get('id'),str) or not cat['id'] or cat['id'] in by_id: raise ValueError('Category identifiers must be unique.')
        name=cat.get('name')
        if not isinstance(name,str) or not name.strip() or len(name)>200: raise ValueError('Enter a category name of 1–200 characters.')
        key=category_key(name)
        if key in names: raise ValueError('Category names must be unique.')
        names.add(key);by_id[cat['id']]=cat
    products={p['id']:p for p in data['products']}
    for p in products.values():
        if p.get('categoryId') not in by_id: raise ValueError('Every product must belong to one existing category.')
    for r in data['restaurants']:
        groups={};ordered=[];placements=[]
        for cat in r['categories']:
            placements.extend(cat['items'])
            cid=cat.get('catalogCategoryId')
            if cid not in by_id:
                # Legacy per-restaurant exports can still identify a known category by name.
                cid=next((c['id'] for c in categories if category_key(c['name'])==category_key(cat['name'])),None)
            if cid in by_id and cid not in groups:
                cat['catalogCategoryId']=cid;cat['name']=by_id[cid]['name'];cat['items']=[]
                groups[cid]=cat;ordered.append(cat)
        for item in placements:
            cid=products[item['productId']]['categoryId']
            if cid not in groups:
                cat={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'menu-category:'+r['id']+':'+cid)),'catalogCategoryId':cid,'name':by_id[cid]['name'],'notes':'','items':[]}
                groups[cid]=cat
                # Insert missing categories relative to the catalog, retain existing restaurant ordering.
                rank=next(n for n,c in enumerate(categories) if c['id']==cid)
                position=next((n for n,c in enumerate(ordered) if next(k for k,v in enumerate(categories) if v['id']==c['catalogCategoryId'])>rank),len(ordered))
                ordered.insert(position,cat)
            groups[cid]['items'].append(item)
        r['categories']=ordered
    return data

def migrate_categories(data):
    if 'productCategories' in data: return data
    data=copy.deepcopy(data);categories={};assignments={}
    restaurants=sorted(data['restaurants'],key=lambda r:0 if r['name']=='KOI Kuningan' else 1 if r['name']=='KOI Kemang' else 2)
    for r in restaurants:
        for cat in r['categories']:
            key=category_key(cat['name'])
            master=categories.setdefault(key,{'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'product-category:'+key)),'name':cat['name']})
            cat['catalogCategoryId']=master['id']
            for item in cat['items']:assignments.setdefault(item['productId'],master['id'])
    for p in data['products']:
        if p['id'] not in assignments:
            master=categories.setdefault('uncategorized',{'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'product-category:uncategorized')),'name':'Uncategorized'})
            assignments[p['id']]=master['id']
        p['categoryId']=assignments[p['id']]
    used=set(assignments.values())
    # Combined/obsolete headings with no assigned products no longer belong to the uniform taxonomy.
    data['productCategories']=[c for c in categories.values() if c['id'] in used]
    return synchronize_categories(data)


def migrate_cuisines(data):
    data=copy.deepcopy(data)
    for product in data['products']: product.setdefault('cuisine','')
    return synchronize(data)
