"""Transcribed starting data from the two supplied menu PDFs; never overwrites edits."""
import json, pathlib, copy, uuid
ROOT = pathlib.Path(__file__).resolve().parents[1]
def uid(): return uuid.uuid4().hex
sections = {
'Soups': '''Mushroom Soup|70|with Garlic Bread|Vegetarian
Onion Soup|70|with Cheese Toast Gratined|New menu
Asparagus Soup|70|with Seed Bread
Baby Spinach Soup|95||Vegetarian,With baguette
Tom Yam Seafood|125|Served with Rice or Rice Noodles|Spicy''',
'Appetizers': '''Escargots Gratin|60|with Garlic Butter|With baguette
Cheese Fondue|85||Vegetarian
Homemade Smoked Barramundi Fillet|125|with Herbs Cream Cheese, Rustiquette Bread
Avocado & Goat Cheese|125|with Dry Tomato Toast|Vegetarian
Homemade Duck Pâté|130|with Chutney|With baguette
Smoked Salmon Platter|140|with Baby Spinach
Burrata Cheese|155|with Baby Tomato, spicy Italian Dressing and French Bread''',
'Salads': '''Koi Special Caesar Salad|105|with Truffle & Krupuk|Vegetarian
Gado - Gado|70|Indonesian Salad
Chicken & Avocado Salad|90|with Wasabi Dressing''',
'Sandwiches': '''Home Made Smoked Salmon Bagel|95|with Cream Cheese|New menu
Club Sandwich|115||With French or Belgian fries
Beef Bacon, Egg and Cheese Croissant|125||With French or Belgian fries''',
'Burger': '''Beef Burger|135
Vegetarian Burger with Melted Cheese|140||Vegetarian
Cheese Burger|145
Smoked Beef Brisket Burger|195|with Melted Cheese
KOI Mega Double Cheese Burger|210||New menu''',
'Pastas': '''Potato Gnocchi|95|with Gorgonzola Sauce & Cherry Tomatoes|New menu
Aglio Olio Spaghetti|95||Vegetarian,Spicy
Mac & Cheese|95|with Beef Bacon
Beef Lasagna|115
Tagliatelle Carbonara|125|with Beef Bacon, Parmesan & 62° Egg
Spaghetti Bolognese|125
Smoked Brisket Ravioli|130|with Gravy Sauce
Truffle Ravioli|130|with Brown Butter|Vegetarian
Salmon Ravioli|130|with Light Crustacean Creamy Sauce
Spinach Ravioli|130|with Creamy Parmesan Sauce|Vegetarian
Black ink Seafood Spaghetti|125|with Shrimp and Calamari
Arabica Spaghetti Burrata|190||New menu,Spicy''',
'Noodles & Rice': '''Mie Ayam Kampung|75
Mie Goreng|85
Nasi Goreng (Chicken or Beef or Seafood)|95||Choice of white or red rice
Nasi Goreng (Lamb or Duck)|130||Choice of white or red rice
Fried Rice Sambal Ijo with Beef|95
Pad Thai (Chicken/Sea Food)|105
Nasi Campur|130|with Crispy Chicken, Egg, Chili Tempe & Beef Satay|Choice of white or red rice''',
'Poultry': '''Chicken Shawarma|105|with Tabbouleh & Fresh Pita Bread
Pan-Fried Duck Fillet|150|with Green Pepper Sauce & French Fries|New menu
Roasted Chicken (1/2 Chicken)|155||Takes more than 15 mins,With French or Belgian fries,With mixed salad
Homemade Duck Confit|155|with Green Beans & Beef Bacon
Hainanese Chicken Rice|105|Steamed or Fried
Chicken Betutu|105|with Garlic Rice & Sambal Matah|Spicy
Thai Chicken Green Curry|105||With jasmine rice
Ayam Bakar|105|with Nasi Daun Jeruk
Chicken Kemangi|105||With jasmine rice''',
'Seafood': '''Roasted Dory Fillet topped with “Niçoise”|95|with Eggplant, Red Paprika, Mushrooms, Basil Sauce & Mashed Potatoes|New menu
Smoked Barramundi Fillet|120|steamed on crushed potatoes with leek, cherry tomatoes & asparagus sauce|New menu
Fish & Chips|130|with Tartare Sauce
Dory Fish Fillet & Parmesan Gratin|160|Served with Sautéed Asparagus and Ricotta Ravioli
Barramundi Fillet|210|with Creamy Polenta, Cherry Tomatoes & Arugula
Salmon Fillet|245|with Nori Butter, Sautéed Vegetables & Fennel Creamy Sauce|With mashed potato
Crispy Kalan|65|with Shrimp
Indonesian Dory Fillet “Bumbu Kuning”|95||New menu
Calamari Asiatique|115|Deep Fried Squid Sautéed w/ Chilli Padi & Garlic|With jasmine rice''',
'Beef': '''Gratin Potato|80|with Beef and Cheese|New menu
Beef Tongue “Poulette”|145|carrot, Leek|With baby potatoes
Vegetarian Tartare|150
Beef Piccata|165
Belgian Beef Stew|165||With French or Belgian fries
Beef Tartare|215||With French or Belgian fries,With mixed salad
Vietnamese Steak|135|with Fried Rice
Beef Rendang|140||With jasmine rice
Beef Ribs|155|with Fried Rice
Beef Tongue “Sambal Ijo”|155||Spicy,With jasmine rice
Oxtail Soup|245''',
'Grill': '''Meltique Australian Striploin (200Gr)|220
Tenderloin (220Gr)|240
Wagyu Flank Steak (200Gr)|270
Wagyu Rib Eye Grade 6 (300G 2Pax)|750''',
'Pizza': '''Margherita|75|Tomato Sauce, Basil & Mozarella|Vegetarian
Turkish Beef|105|Beef Kebab, Cherry Tomatoes, Mint & Mozarella
Carbonara|155|Beef Bacon, Egg 62°, Mozarella & Parmesan
Carnivora|170|Tomato Sc, Beef sausage, Brisket, paprika & Mozarella
Burrata and Rucola|195||New menu''',
'Lamb': '''Lamb “Tongseng”|145||With jasmine rice''',
'Poke Bowl': '''Grilled Chicken|85|white & red cabbage, carrot, chayote, radishes, edamame, Nori, & mushrooms dressing|Choice of white or red rice,New menu
Shrimp|85|white & red cabbage, carrot, chayote, radishes, edamame, mushrooms, nori & KOI caesar sauce|Choice of white or red rice,New menu
Smoked Salmon|105|white & red cabbage, carrot, chayote, radishes, edamame, mushrooms, nori & KOI caesar sauce|Choice of white or red rice,New menu''',
'Sauce': '''Tartare, Mushroom|20
Black Pepper, BBQ|20
Béarnaise|45
Gorgonzola Blue Cheese|45''',
'Side Dishes': '''Jasmine Rice|15
Sautéed Green Beans|30
Baby Potato|30
Green Salad with Vinaigrette|49
Spinach à la Crème|49
Garlic Bread|40
French Fries|49
Mashed Potato|49
Homemade Belgian Fries|49
Potato Gratined|49''',
'Kids': '''Roasted Boneless Chicken|75||With French or Belgian fries
Spaghetti Bolognese|65
Beef Sausage|75||With French or Belgian fries''',
'Monthly Specials · Salad': 'Thai Seafood Salad|80',
'Monthly Specials · Pasta': 'Rico… a raviolis|95|with Smoked salmon',
'Monthly Specials · Main': '''Whole Duck Stew|150|with mushroom ravioli
Classic Indonesian Beef Stew “Rawon”|105''',
'Monthly Specials · Pizza': 'Chicken Lahmacun|65|thin Turkish pizza',
'Monthly Specials · Dessert': '''Poppy Seed Lemon Cake|55
Bika Ambon Chocolate Brulee|75''',
'Wine of the Month': 'MOI Primitivo Puglia|590|Italy 2022'
}
categories=[]
for name, lines in sections.items():
    items=[]
    for line in lines.splitlines():
        parts=(line+'|||').split('|')
        items.append(dict(id=uid(), name=parts[0], price=int(parts[1]), description=parts[2], tags=parts[3].split(',') if parts[3] else [], options=[], notes='', image='', available=True, reviewed=False))
    categories.append(dict(id=uid(), name=name, notes='', items=items))
def find(cats, name): return next(i for c in cats for i in c['items'] if i['name']==name)
find(categories,'Koi Special Caesar Salad')['options']=[dict(name='with Chicken or Beef or Beef Snout',price=140,kind='Variant'),dict(name='with Smoked Salmon',price=155,kind='Variant')]
find(categories,'Aglio Olio Spaghetti')['options']=[dict(name='Additional Chicken or Beef bacon or Tuna',price=30,kind='Add-on')]
for n in ['Nasi Goreng (Chicken or Beef or Seafood)','Nasi Goreng (Lamb or Duck)']:
    find(categories,n)['options']=[dict(name='Additional Chicken Satay (2Pcs)',price=25,kind='Add-on')]
find(categories,'MOI Primitivo Puglia').update(options=[dict(name='Glass 12cl',price=105,kind='Variant'),dict(name='Glass 18cl',price=155,kind='Variant')],notes='Bottle price; previous bottle price 690 is crossed out in the source.')
find(categories,'Rico… a raviolis')['notes']='Check spelling against original artwork: one character in the dish name is unclear in both source PDFs.'
next(c for c in categories if c['name']=='Burger')['notes']='Served with French or Belgian fries and mixed salad.'
next(c for c in categories if c['name']=='Grill')['notes']='Served with French or Belgian fries and mixed salad.'
restaurants=[]
for location, filename in [('Kemang','Kemang Lunch & Dinner 20260605A.pdf'),('Kuningan','Kuningan Lunch & Dinner 20260606A.pdf')]:
    cats=copy.deepcopy(categories)
    if location=='Kuningan':
        cats=[c for c in cats if c['name']!='Pizza']
        for c in cats:
            if c['name']=='Beef': c['items']=[i for i in c['items'] if i['name']!='Beef Tongue “Poulette”']
        find(cats,'Mushroom Soup').update(description='with Puff Pastry',tags=['Takes more than 15 mins','Vegetarian'])
        find(cats,'Vegetarian Tartare')['tags']=['With French or Belgian fries']
        find(cats,'Beef Piccata')['tags']=['With French or Belgian fries']
    for c in cats:
        c['id']=uid()
        for item in c['items']: item['id']=uid()
    restaurants.append(dict(id=uid(), name='KOI '+location, location=location, menuTitle='Lunch & Dinner', currency='IDR', priceUnit=1000, serviceCharge=10, tax=10, footer='All prices are listed in Rp. 1.000,- and are subject to a 10% service charge and 10% tax', dietaryNote='No pork, no lard', logo='', source=filename, categories=cats))
target=ROOT/'data'/'menus.json'
if target.exists(): raise SystemExit('Existing menu data retained; seed was not applied.')
target.write_text(json.dumps(dict(version=1,revision=0,restaurants=restaurants),ensure_ascii=False,indent=2),encoding='utf-8')
print([(r['name'],len(r['categories']),sum(len(c['items']) for c in r['categories'])) for r in restaurants])
