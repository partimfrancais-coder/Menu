import json
from pathlib import Path

menus = [[], [], []]
def add(which, cat, name, price, description='', options=None):
    for i in which:
        menus[i].append(dict(category=cat, name=name, price=price, description=description, options=options or []))
def variants(*pairs):
    return [dict(name=n, price=p, kind='Variant') for n,p in pairs]
def rows(which, cat, text):
    for line in text.strip().splitlines():
        name,price=line.rsplit('|',1);add(which,cat,name,float(price))
all3=[0,1,2]
rows(all3,'Finger Food','''Crispy Enoki|45
Cheese & Beef Croquettes|60
Spicy Garlic Chicken Wings|65
Mexican Nachos|105''')
rows([0,1],'Finger Food','''Vietnamese Vegetarian Spring Roll|35
Indian Samosa with Green Chutney|50
Chicken Arayes (Lebanese Sandwich)|60
Homemade Fries with Spicy Aioli|65
Grilled Chicken Wings with Herbs|65
3 Bao Peking Duck (Steamed Sandwich)|65
Crispy Calamari Marinara Sauce|75
Triple Cheese Quesadillas and Guacamole|80''')
rows([0],'Finger Food','''Chicken Gyoza|60
Thin Chicken Turkish Pizza|65
4 Mini Chicken Tacos|95
4 Mini Mexican Wagyu Beef Tacos|115
Cheese and Chicken Quesadilla|115''')
rows([1],'Finger Food','''Spanish Tortilla Spicy Aioli|55
Chicken & Beef Bacon Gyoza|60
Cheese & Seafood Croquette|65
6 Mini Mexican Beef Tacos|115''')
rows([2],'Finger Food','''Indian Samosa with Green Chutney|60
Homemade Fries with Spicy Aioli|60
Platter of Escargots with Garlic Butter|60
Triple Cheese Quesadillas and Guacamole|75''')
rows(all3,'Local Beers','''San Miguel Light|50
Bintang Lemon Radler|50
Bintang Crystal|55
Carlsberg|65''')
rows([0,2],'Local Beers','''Bintang|50
Guinness Extra Stout|55
Koenig|60''')
rows([0],'Local Beers','Heineken|65')
rows([2],'Local Beers','Anker|50')
add([0],'Local Beers','Heineken Draught',65,options=variants(('33cl',65),('55cl',110)))
add([2],'Local Beers','Carlsberg Draught',65,options=variants(('33cl',65),('55cl',110)))
add([1],'Local Beers','Bintang Draught',50,options=variants(('Draught',50),('Pitcher',225)))
rows([1],'Local Beers','Bintang Tower|450')
for n,p,desc in [('Liefmans Fruitesse',95,'Belgium; 3.8%'),('Hoegaarden Blanche',100,'Belgium; 4.9%'),('La Chouffe',170,'Belgium; 8%'),('Duvel Golden Ale',170,'Belgium; 8.5%'),('Maredsous Triple',170,'Belgium; 10%'),('Erdinger Weissbier',135,'Germany; 5.3%'),('Erdinger Dunkel',135,'Germany; 5.3%')]:
    add(all3,'Imported Beers',n,p,desc)
add([0],'Imported Beers','Guinness Micro Draught',120,'Ireland; 4.2%')
add([1,2],'Imported Beers','Corona',100,'Mexico; 4.5%')
for n,p,abv in [('Island of Imagination Whitty White',85,'4.8%'),('Kura Kura Island Ale',90,'5%'),('Small Hazy',95,'4.8%'),('Island of Imagination XPA',135,'7.9%'),('Kura Kura I.P.A',145,'7.1%')]:add(all3,'Bali Craft Beers',n,p,abv)
add([0,2],'Ciders','Somersby Apple Cider',75)
for n in ['Original','Lime','Lychee','Peach','Green Grape']:add(all3,'Korean Soju',n+' Soju',125)
for n in ['Red Wine','White Wine','Sparkling Wine']:
    add([0],'Wine by Glass',n,95,options=variants(('12cl',95),('18cl',135)))
    add([1],'Wine by Glass',n,95)
for n in ['Red Wine','White Wine']:add([2],'Wine by Glass',n,95)
add([0],'Wine by Glass','Niepoort Tawny',95,'9cl')
add([2],'Wine by Glass','Niepoort Tawny',95)
add([1],'Wine by Glass','Svaa Port Wine - Tawny',95)
add([1],'Wine by Glass','Rose Wine',105)
for n in ['Vanilla','Chocolate','Coconut','Strawberry']:add([0,2],'Milkshake',n+' Milkshake',55)
add([0,2],'Milkshake','Salted Caramel Milkshake',70)
for n in ['Banana Honey','Strawberry Banana']:add([0],'Smoothies',n+' Smoothie',55)
rows([0],'Matcha','''Matcha Latte|39
Matcha Milkshake|55''')
for n in ['Lychee Spritzer','Orange The Basil','Pina & Lemongrass']:add([0,2],'Mocktails',n,55)
add([2],'Mocktails','Cucumber Spring',55)
for n in ['Yellow Peach','Unsalted Blue Caramel']:add([2],'Mocktails',n,65)
rows(all3,'Soft','''Pokka Green Tea|20
Coke|25
Sprite|25
Coke Zero|30
Ginger Ale|30
Tonic|30
Soda Water|30
Kratingdaeng|30''')
add(all3,'Water','Mineral Water (50cl)',19)
add(all3,'Water','Sparkling Water (50cl)',25)
add([0],'Water','Aqua Reflection Still (38cl)',35)
add([0],'Water','Aqua Reflection Sparkling (38cl)',39)
for n in ['Dolomia Still','Dolomia Sparkling']:
    add([1],'Water',n,45,options=variants(('33cl',45),('75cl',70)))
    add([2],'Water',n,50,options=variants(('33cl',50),('75cl',75)))
rows([0],'Signature Latte','''Sea Salt Caramel Latte|49
Crème Brûlée Latte|49
Cookie and Cream Latte|49''')
for n in ['Lime','Lemon']:add([0,2],'Juice',n+' Juice',40,'Squeeze or squash')
for n,p in [('Melon',45),('Watermelon',45),('Pineapple',45),('Papaya',45),('Mango',55),('Strawberry',55),('Orange',60),('Carrot',60)]:add([0,2],'Juice',n+' Juice',p)
add([0,2],'Juice','Orange Squash',55)
add([0,2],'Chocolate','Hot or Cold Chocolate',40)
rows(all3,'Tea','''Tea (Iced or Hot)|28
Lemon Tea (Iced or Hot)|30
Lemongrass Tea|40
Peach Sorbet Iced Tea|55
Strawberry Sorbet Iced Tea|55''')
add(all3,'Tea','Flavoured Iced Tea',45,'Lychee, Peach, Strawberry, Green Apple syrups')
add([0],'Tea','Pot of TWG Tea',45,'Black tea: English Breakfast, Earl Grey. Green tea: Sencha, Grand Jasmine, Moroccan Mint, Waterfruit. No theine: Chamomille, Vanilla Bourbon Red Tea. Grand Jasmine, Moroccan Mint, Waterfruit and Vanilla Bourbon Red Tea can be served iced.')
add([2],'Tea','Pot of TWG Tea',45,'Black tea: English Breakfast, Earl Grey. Green tea: Sencha, Grand Jasmine, Moroccan Mint. No theine: Chamomille, Vanilla Bourbon Red Tea. Grand Jasmine, Moroccan Mint and Vanilla Bourbon Red Tea can be served iced.')
add([1],'Tea','Pot of TWG Tea',45,'Black tea: English Breakfast, Earl Grey')
for n,p in [('Espresso',28),('Black Coffee',28),('Macchiato',32),('Piccolo Latte',32),('Cappuccino',42),('Latte',44)]:
    add(all3,'Coffee',n,p)
add([0,2],'Coffee','Mocha',44)
for i in [0,2]:
    for p in menus[i]:
        if p['category']=='Coffee':p['options']=[dict(name=n,price=v,kind='Add-on') for n,v in [('Oat Milk',5),('Caramel Syrup',10),('Hazelnut Syrup',10),('Vanilla Syrup',10),('Espresso Shot',12)]]
rows([0,2],'Healthy Drink','''Papaya & Orange|55
Yakult & Tomato Basil|60
Wheat Grass Orange|65''')
for n,p in [('Bintang',195),('San Miguel Light',195),('Carlsberg',255),('Heineken',255)]:add([0,2],'Everyday Happy Hour',n+' - Bucket of 5 Bottles',p,'Every day, 4–8 PM')
for n,p in [('Anker',195),('Corona',395)]:add([2],'Everyday Happy Hour',n+' - Bucket of 5 Bottles',p,'Every day, 4–8 PM')
cocktails=[('Mojito',120,'White Rum, Fresh Lemon Juice, Simple Syrup, Mint Leaf'),('Dark & Stormy',120,'Spiced Rum, Lime Juice, Fresh Ginger, Brown Sugar'),('Caipiroska',120,'Vodka, Fresh Lime Juice, Simple Syrup'),('Cosmopolitan',125,'Vodka, Triple Sec, Cranberry Juice, Fresh Lime Juice, Simple Syrup'),('Whiskey Sour',125,'Blended Whiskey, Lemon Juice, Egg White'),('Spinning Kiss',125,'Vodka, Strawberry Puree, Pineapple Cordial, Fresh Lemon Juice, Simple Syrup'),('Pinkin Sour',130,'Gold Rum, Guava Juice, Lemon Juice, Passion Fruit Syrup, Egg White'),('Margarita',145,'Tequila, Triple Sec, Lime Juice, Simple Syrup'),('Negroni',155,'Dry Gin, Sweet Vermouth, Campari Bitter, Orange Peel'),('Aperol Spritz',160,'Aperol, Ponte Blanco, Soda Water, Orange Sliced')]
for n,p,d in cocktails:add([1],'Cocktails',n,p,d)
for n,p,d in cocktails:
    if n not in ['Mojito','Cosmopolitan','Margarita']:add([0,2],'Cocktails',n,p,d)
add([0,2],'Cocktails','Caipirinha',120)
def spirits(cat,text):
    for line in text.strip().splitlines():
        names,bottle,glass=line.split('|')
        for name in names.split('/'):
            add([1],cat,name,float(bottle),'Two source prices retained in printed order; serving units are not labelled in the PDF.',variants(('First listed price',float(bottle)),('Second listed price',float(glass))))
spirits('Gin',"""Gordon's/Gordon's Pink|900|85
H|900|85
East Indies|990|90
Bombay Dry|1100|95
Tenjaku Gin|1300|110
Tanqueray|1400|120
Bombay Sapphire|1500|125
Hendrick's|1750|145
Tanqueray 10|2800|235""")
spirits('Rum',"""Captain Morgan White/Captain Morgan Gold|900|85
Bacardi Spice|950|90
Bacardi Light/Bacardi Gold|1200|100
Kranken|2200|180""")
spirits('Vodka',"""Smirnoff|900|85
Skyy|1100|95
Absolut Blue|1300|110
Grey Goose Original|1900|160""")
spirits('Whisky',"""Gilbey's Whisky|690|75
JW Red Label|990|90
Jim Beam|990|90
Jameson|1200|100
Tenjaku Whisky|1500|115
Jack Daniel's|1400|120
JW Black Label|1400|120
Chivas Regal 12 YO|1600|135
Gentelman Jack|1700|140
Glenfiddich 12 YO|2200|185
Umiki|2400|200
Singleton 12 YO|2900|240
Macallan 12 YO - Double Cask|3400|285""")
spirits('Tequila','''Camino Blanca|1200|100
Patron Silver|2900|240''')
Path('tmp/drinks-import/transcribed.json').write_text(json.dumps(menus,ensure_ascii=False,indent=2),encoding='utf-8')
print('Transcribed item counts:',[len(m) for m in menus])
