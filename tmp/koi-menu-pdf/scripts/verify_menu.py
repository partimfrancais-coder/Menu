"""Check generated PDF content against the restaurant snapshot and layout audit."""
import argparse
import json
import re
import unicodedata
from pathlib import Path
import fitz

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot', required=True, type=Path)
parser.add_argument('--pdf', required=True, type=Path)
parser.add_argument('--audit', required=True, type=Path)
args = parser.parse_args()
data = json.loads(args.snapshot.read_text(encoding='utf-8'))
audit = json.loads(args.audit.read_text(encoding='utf-8'))
pdf = fitz.open(args.pdf)
pages = [p.get_textpage() for p in pdf]
words = [p.extractWORDS() for p in pages]

def norm(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(value))).replace('\u2010', '-')

content = norm('\n'.join(p.extractText() for p in pages))
items = [i for c in data['categories'] for i in c['items'] if i['available']]
assert len(audit['items']) == len(items), 'Item count mismatch'
assert len({a['id'] for a in audit['items']}) == len(items), 'Duplicate rendered IDs'
assert {a['id'] for a in audit['items']} == {i['id'] for i in items}, 'Item coverage mismatch'
for item in items:
    for field in ('name', 'description'):
        assert norm(item[field]) in content, (item['name'], field)
    a = next(a for a in audit['items'] if a['id'] == item['id'])
    assert a['price'] == item['price'], ('Audit price mismatch', item['name'])
    # Bundled renderer audit coordinates are at three times native page size.
    row = [w[4] for w in words[a.get('page', 0)]
           if a['x']/3-1 <= w[0] and a['y']/3-2 <= w[1] <= a['y']/3+8]
    assert str(item['price']) in row, ('Price missing from row', item['name'])
    for option in item['options']:
        assert norm(option['name']) in content, option
        assert norm(option['price']) in content, option
assert norm(data['footer']) in content, 'Footer mismatch'
print(f'PASS: {len(items)} visible items, names, descriptions, row prices, options and footer; {len(pdf)} page(s). Visual inspection still required.')
