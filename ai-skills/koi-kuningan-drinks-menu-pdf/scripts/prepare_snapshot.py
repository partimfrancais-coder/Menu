"""Resolve the separate Kuningan drinks restaurant from a current full export."""
import argparse
import copy
import json
from pathlib import Path

RESTAURANT_ID = 'b8ae17c2-f1e0-4169-8a95-40f4b9b39cc9'
RESTAURANT_NAME = 'KOI Kuningan Drinks and Cocktail'
FIELDS = ('name', 'price', 'description', 'options', 'tags', 'cuisine',
          'productCode', 'notes', 'image', 'reviewed')


def index_unique(records, label):
    result = {r['id']: r for r in records}
    if len(result) != len(records):
        raise ValueError('Duplicate ' + label + ' IDs.')
    return result


def prepare(data):
    if not all(k in data for k in ('restaurants', 'products', 'productCategories', 'productTags')):
        raise ValueError('Use a full shared-catalog backup, not a restaurant-only snapshot.')
    restaurants = index_unique(data['restaurants'], 'restaurant')
    if RESTAURANT_ID not in restaurants:
        raise ValueError('The Kuningan Drinks and Cocktail restaurant ID is missing. Verify the target before adapting this helper.')
    restaurant = copy.deepcopy(restaurants[RESTAURANT_ID])
    if restaurant['name'].strip().casefold() != RESTAURANT_NAME.casefold():
        raise ValueError('Restaurant identity changed. Verify the target before adapting this helper.')
    products = index_unique(data['products'], 'product')
    categories = index_unique(data['productCategories'], 'category')
    placements = set()
    for category in restaurant['categories']:
        cid = category['catalogCategoryId']
        if cid not in categories:
            raise ValueError('Unknown shared category. Obtain a fresh saved snapshot.')
        category['name'] = categories[cid]['name']
        for item in category['items']:
            if item['id'] in placements:
                raise ValueError('Duplicate placement ID.')
            placements.add(item['id'])
            product = products.get(item['productId'])
            if product is None or product['categoryId'] != cid:
                raise ValueError('Product/category link drift. Obtain a fresh saved snapshot.')
            for field in FIELDS:
                item[field] = copy.deepcopy(product.get(field, '' if field in ('cuisine', 'productCode') else item.get(field)))
    restaurant['tagCatalog'] = copy.deepcopy(data['productTags'])
    return restaurant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--menus', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.menus.resolve() == args.output.resolve():
        parser.error('Output must differ from input.')
    data = json.loads(args.menus.read_text(encoding='utf-8'))
    result = prepare(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'restaurant': result['name'], 'sourceRevision': data.get('revision'),
                      'visibleItems': sum(i['available'] for c in result['categories'] for i in c['items'])}))


if __name__ == '__main__':
    main()
