"""Resolve Rooftop placements against a supplied current catalog; no network or writes to source."""
import argparse
import copy
import json
from pathlib import Path


def prepare(data, restaurant_id=None):
    matches = [r for r in data['restaurants'] if
               (r['id'] == restaurant_id if restaurant_id else
                'rooftop' in (r.get('name', '') + ' ' + r.get('location', '')).casefold())]
    if len(matches) != 1:
        raise ValueError('Select exactly one Rooftop restaurant using --restaurant-id.')
    restaurant = copy.deepcopy(matches[0])
    if 'rooftop' not in (restaurant.get('name', '') + ' ' + restaurant.get('location', '')).casefold():
        raise ValueError('This skill only handles Rooftop.')
    products = {p['id']: p for p in data['products']}
    categories = {c['id']: c for c in data['productCategories']}
    if len(products) != len(data['products']):
        raise ValueError('Duplicate product IDs in catalog.')
    for category in restaurant['categories']:
        cid = category['catalogCategoryId']
        category['name'] = categories[cid]['name']
        for item in category['items']:
            product = products[item['productId']]
            if product['categoryId'] != cid:
                raise ValueError('Category drift: obtain a fresh saved snapshot.')
            for field in ('name', 'price', 'description', 'options', 'tags', 'cuisine',
                          'productCode', 'notes', 'image', 'reviewed'):
                if field in product:
                    item[field] = copy.deepcopy(product[field])
    restaurant['tagCatalog'] = copy.deepcopy(data['productTags'])
    return restaurant


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--menus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--restaurant-id')
    args = parser.parse_args()
    if args.menus.resolve() == args.output.resolve():
        parser.error('Output must differ from the input snapshot.')
    data = json.loads(args.menus.read_text(encoding='utf-8'))
    result = prepare(data, args.restaurant_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'restaurant': result['name'], 'sourceRevision': data.get('revision'),
                      'visibleItems': sum(i['available'] for c in result['categories'] for i in c['items'])}))
