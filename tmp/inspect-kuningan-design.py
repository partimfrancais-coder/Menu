exec(open('tmp/investigate-kuningan.py').read())
rid=rest['id'] if rest['name']=='KOI Kuningan' else next(r['id'] for r in data['restaurants'] if r['name']=='KOI Kuningan')
design=json.loads(get('/api/ai/restaurants/'+rid+'/design-skill'))
(folder/'design.json').write_text(json.dumps(design),encoding='utf-8')
print('Active design',design.get('activeVersion'))
for doc in design['documents']:
 for line in doc['content'].splitlines():
  if any(w in line.lower() for w in ['wine','elix','cabernet','snapshot','restaurant.json']):print(doc['name']+': '+line)
print('PROMPT WINE LINES')
for line in design.get('designPrompt','').splitlines():
 if any(w in line.lower() for w in ['wine','elix','cabernet']):print(line)
