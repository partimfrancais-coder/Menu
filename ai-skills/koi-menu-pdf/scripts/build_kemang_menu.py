"""Create a reference-faithful Kemang proof from the authenticated saved snapshot.

The source PDF contributes only vector branding and outlined heading artwork.
All dish text, prices, options and icon assignments come from the saved menu.
"""
import base64
import argparse
from datetime import date
import json
from pathlib import Path
import fitz

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
parser.add_argument('--date',type=date.fromisoformat,default=date.today())
parser.add_argument('--source',type=Path,default=Path('Kemang Lunch & Dinner 20260605A.pdf'))
parser.add_argument('--icons',type=Path,default=Path('dist/menu-icons.js'))
parser.add_argument('--font-regular',type=Path,default=Path('C:/Windows/Fonts/calibri.ttf'))
parser.add_argument('--font-bold',type=Path,default=Path('C:/Windows/Fonts/calibrib.ttf'))
args=parser.parse_args()
DATA=json.loads(args.snapshot.read_text(encoding='utf-8'))
assert 'kemang' in DATA['name'].lower(), 'This renderer is for KOI Kemang only.'
SOURCE=args.source
OUT=args.output
OUT.parent.mkdir(parents=True,exist_ok=True)
DATE_LABEL=args.date.strftime('%d %B %Y')
source=fitz.open(SOURCE)
assert len(source)==1 and abs(source[0].rect.width-892.92)<.1 and abs(source[0].rect.height-631.44)<.1, "Source dimensions differ; adapt artwork coordinates."
source[0].add_redact_annot(source[0].rect,fill=False)
source[0].apply_redactions(images=0,graphics=0,text=0)
W,H=source[0].rect.width*1.8,source[0].rect.height*1.8
doc=fitz.open();page=doc.new_page(width=W,height=H)
FONTS={
 'regular':fitz.Font(fontfile=str(args.font_regular)),
 'bold':fitz.Font(fontfile=str(args.font_bold)),
}
for key,name in [('regular',args.font_regular),('bold',args.font_bold)]:
 page.insert_font(fontname=key,fontfile=str(name))
RED=(.90,.045,.085);BLACK=(0,0,0)
categories={c['name']:c for c in DATA['categories']}
presets=json.loads(args.icons.read_text(encoding='utf-8').split('globalThis.MenuIconSet=',1)[1].rstrip(';\n'))
tags={t['name']:t for t in DATA['tagCatalog']}
audit=[]
regions=[]

def measure(text,size,font='regular'):
 return FONTS[font].text_length(text,fontsize=size)

def text(x,y,value,size=12,font='regular',color=BLACK):
 page.insert_text((x,y),value,fontname=font,fontsize=size,color=color)

def right(x,y,value,size=12): text(x-measure(value,size),y,value,size)
def center(x,y,value,size=12,font='regular',color=BLACK): text(x-measure(value,size,font)/2,y,value,size,font,color)

def vector(clip,dest):
 page.show_pdf_page(fitz.Rect(dest),source,0,clip=fitz.Rect([v/1.8 for v in clip]))

def icon(name,x,y,size=22):
 tag=tags.get(name)
 if not tag:return
 encoded=tag.get('iconImage') or presets.get(tag.get('icon'),{}).get('image')
 if encoded:
  raw=base64.b64decode(encoded.split(',',1)[1])
  page.insert_image(fitz.Rect(x,y,x+size,y+size),stream=raw)
 elif tag.get('icon'):
  raise ValueError('An icon needs printable artwork: '+name)

heading_boxes={'Appetizers': (211.09, 391.16, 336.36, 417.65), 'Soups': (229.15, 242.37, 305.58, 272.16), 'Salads': (224.03, 584.7, 313.83, 612.59), 'Sandwiches': (185.38, 726.05, 331.07, 754.88), 'Burger': (210.08, 841.88, 298.11, 871.65), 'Pastas': (587.01, 241.37, 669.76, 270.51), 'Noodles & Rice': (530.87, 505.17, 715.39, 532.0), 'Poultry': (580.59, 659.14, 676.02, 686.11), 'Seafood': (934.08, 242.07, 1034.5, 271.85), 'Beef': (954.19, 504.08, 1008.52, 529.74), 'Grill': (951.67, 735.31, 1011.22, 765.09), 'Pizza': (1299.62, 244.19, 1366.22, 270.36), 'Lamb': (1310.65, 375.32, 1372.13, 404.57), 'Poke Bowl': (1271.36, 447.88, 1398.19, 474.05), 'Sauce': (1303.67, 611.19, 1378.99, 640.97), 'Side Dishes': (1271.71, 730.06, 1404.86, 758.9), 'Kids': (1312.58, 953.71, 1364.45, 983.94), 'Monthly Specials': (679.86, 855.77, 884.46, 882.02)}

def divider_index(cat):
 visible=[i for i in cat['items'] if i['available']]
 cuisines=[i.get('cuisine','') for i in visible]
 transitions=[n for n in range(1,len(cuisines)) if cuisines[n]!=cuisines[n-1]]
 return transitions[0] if set(cuisines)=={'European','Asian'} and len(transitions)==1 else None

# Rebuild BURGER from individual source outlines with consistent tracking.
source_drawings=source[0].get_drawings()
burger_letters=sorted([d for d in source_drawings if fitz.Rect(heading_boxes['Burger']).contains(d['rect']*1.8)],key=lambda d:d['rect'].x0)
beef_letters=sorted([d for d in source_drawings if fitz.Rect(heading_boxes['Beef']).contains(d['rect']*1.8)],key=lambda d:d['rect'].x0)
assert len(burger_letters)==6 and len(beef_letters)==4
burger_letters[0]=beef_letters[0]
BURGER_HEIGHT=27.5
BURGER_GAP=2.0
burger_widths=[d['rect'].width*BURGER_HEIGHT/d['rect'].height for d in burger_letters]

def burger_lettering(left,y):
 for d,letter_width in zip(burger_letters,burger_widths):
  r=d['rect'];scale=BURGER_HEIGHT/r.height
  def pt(p):return fitz.Point(left+(p.x-r.x0)*scale,y+1+(p.y-r.y0)*scale)
  shape=page.new_shape()
  for command in d['items']:
   if command[0]=='l':shape.draw_line(pt(command[1]),pt(command[2]))
   elif command[0]=='c':shape.draw_bezier(*(pt(p) for p in command[1:]))
   elif command[0]=='re':shape.draw_rect(fitz.Rect(pt(command[1].tl),pt(command[1].br)))
   else:raise ValueError(command[0])
  shape.finish(color=None,fill=d['fill'],even_odd=d['even_odd'],closePath=d['closePath']);shape.commit()
  left+=letter_width+BURGER_GAP

def heading(name,x,y,width):
 box=heading_boxes[name];bw=box[2]-box[0];bh=box[3]-box[1]
 if name=='Burger':bw=sum(burger_widths)+5*BURGER_GAP
 # Preserve the source outlined glyph artwork at its original relative scale.
 left=x+(width-bw)/2

 if name=='Burger':
  burger_lettering(left,y)
 else:vector(box,(left,y,left+bw,y+bh))
 page.draw_line((x,y+bh+3),(x+width,y+bh+3),color=RED,width=.7)
 if name in ('Burger','Grill'):
  icon('With French or Belgian fries',left+bw-1,y+5,22)
  icon('With mixed salad',left+bw+17,y+5,22)
 return y+bh+8

def wrap_runs(runs,width):
 lines=[];line=[];used=0
 for value,size,font in runs:
  words=value.split()
  for word in words:
   prefix=' ' if line else ''
   token=prefix+word;tw=measure(token,size,font)
   if used+tw>width and line:
    lines.append(line);line=[];used=0;token=word;tw=measure(token,size,font)
   if tw>width:raise ValueError('Unbreakable text exceeds column: '+word)
   line.append((token,size,font));used+=tw
 if line:lines.append(line)
 return lines

def draw_runs(lines,x,y):
 # Coordinates use the original menu at 3x native PDF size.
 cursor=y
 for line in lines:
  size=max(run[1] for run in line);baseline=cursor+size
  xx=x
  for value,fs,font in line:
   text(xx,baseline,value,fs,font);xx+=measure(value,fs,font)
  cursor+=size+2.3
 return cursor

LEADING={'Vegetarian','Spicy','New menu','Takes more than 15 mins','Choice of white or red rice'}

def item_layout(item,width,size=12):
 leader=next((tag for tag in item['tags'] if tag in LEADING),None)
 trailing=[tag for tag in item['tags'] if tag!=leader]
 price_space=max(28,measure(str(item['price']),size)+10)
 available=width-price_space-(16*len(trailing))
 name=item['name'];description=item['description']
 runs=[(name,size,'regular')]
 if description:runs.append((description,8.8,'regular'))
 lines=wrap_runs(runs,available)
 return lines,trailing,price_space

def draw_item(item,x,y,width,size=12,shared_options=None):
 start=y;lines,trailing,price_space=item_layout(item,width,size)
 leaders=[tag for tag in item['tags'] if tag in LEADING][:1]
 for j,tag in enumerate(leaders):icon(tag,x-23-17*(len(leaders)-1-j),y-4,22)
 y=draw_runs(lines,x,y)
 last=lines[-1];last_size=max(run[1] for run in last)
 last_y=y-(last_size+2.3)
 tx=x+sum(measure(v,fs,f) for v,fs,f in last)+1
 for tag in trailing:icon(tag,tx,last_y-4,22);tx+=17
 right(x+width,start+size,str(item['price']),size)
 audit.append({'id':item['id'],'name':item['name'],'price':item['price'],'x':x,'y':start})
 opts=item['options'] if shared_options is None else shared_options
 for option in opts:
  option_lines=wrap_runs([(option['name'],10.2,'regular')],width-42)
  option_y=y;y=draw_runs(option_lines,x+12,y)
  right(x+width,option_y+10.2,('+' if option['kind']=='Add-on' else '')+str(option['price']),10.2)
 y+=.7
 regions.append((x,start,x+width,y,item['name']))
 return y

def category_height(cat,width):
 h=heading_boxes[cat['name']][3]-heading_boxes[cat['name']][1]+8
 visible=[i for i in cat['items'] if i['available']]
 for n,i in enumerate(visible):
  lines,_,_=item_layout(i,width)
  h+=sum(max(r[1] for r in line)+2.3 for line in lines)+.7
  # Adjacent dishes may share the same add-on row, as in the reference.
  opts=[] if n+1<len(visible) and i['options'] and i['options']==visible[n+1]['options'] else i['options']
  for o in opts:h+=sum(max(r[1] for r in line)+2.3 for line in wrap_runs([(o['name'],10.2,'regular')],width-42))
 return h+(8 if divider_index(cat) is not None else 0)

def draw_category(name,x,y,width):
 cat=categories[name];y=heading(name,x,y,width)
 visible=[i for i in cat['items'] if i['available']]
 for n,i in enumerate(visible):
  if n==divider_index(cat):
   page.draw_line((x,y+3),(x+width,y+3),color=BLACK,width=.6);y+=8
  opts=[] if n+1<len(visible) and i['options'] and i['options']==visible[n+1]['options'] else None
  y=draw_item(i,x,y,width,shared_options=opts)
 return y

# Kemang artwork clips measured against its own source at 1.8x native size.
assert DATA['menuTitle'].lower()=='lunch & dinner'
vector((557,8,988,176),(557,8,988,176))
vector((695,187,716,209),(695,187,716,209))
text(720,204,DATA['dietaryNote'].upper(),13)
legend_left=['With jasmine rice','Takes more than 15 mins','Vegetarian','Spicy','New menu','Choice of white or red rice']
legend_right=['With baby potatoes','With mashed potato','With French or Belgian fries','With mixed salad','With baguette']
extra=[n for n in tags if n not in legend_left+legend_right]
legend_right+=extra
for x,names in [(1118,legend_left),(1313,legend_right)]:
 for n,name in enumerate(names):
  y=68+n*22;icon(name,x,y,25);text(x+34,y+18,name,10.5)
page.draw_line((71,219),(1524,219),color=RED,width=.65)
page.draw_line((71,224),(1524,224),color=RED,width=1.05)

# Preserve current order and Kemang's reference column grouping.
regular=[c['name'] for c in DATA['categories'] if not c['name'].startswith('Monthly Specials') and c['name']!='Wine of the Month' and any(i['available'] for i in c['items'])]
import itertools
widths=[323,332,326,330];bottoms=[1047,807,807,1047]
heights={(name,w):category_height(categories[name],w) for name in regular for w in widths}
CATEGORY_GAP=14.0
choices=[]
for a,b,c in itertools.combinations(range(1,len(regular)),3):
 groups=[regular[:a],regular[a:b],regular[b:c],regular[c:]]
 remaining=[bottom-243-sum(heights[n,w] for n in group)-CATEGORY_GAP*(len(group)-1) for group,w,bottom in zip(groups,widths,bottoms)]
 if min(remaining)>=0:choices.append((sum(r*r for r in remaining),groups))
assert choices,'Current menu requires more room; adapt the layout.'
_,groups=min(choices)
print('Current saved category order:',groups)
columns=list(zip([103,460,817,1173],widths,groups,bottoms))
column_ends=[]
for x,width,names,bottom in columns:
 heights=[category_height(categories[n],width) for n in names]
 gap=CATEGORY_GAP
 if sum(heights)+gap*(len(names)-1)>bottom-243:raise ValueError(f'Column overflow for {names}')
 y=243
 for name in names:
  y=draw_category(name,x,y,width)+gap
 column_ends.append(y-gap)
 print('Column',names,'ends',round(y-gap,1),'gap',round(gap,1))

# Reference central specials panel.
sx,sy,sw=440,max(column_ends[1:3])+CATEGORY_GAP,710
box=heading_boxes['Monthly Specials'];bw=box[2]-box[0]
vector(box,(sx+(sw-bw)/2,sy+5,sx+(sw+bw)/2,sy+36))
page.draw_line((sx,sy+42),(sx+sw,sy+42),color=RED,width=.9)

def special_group(name,title,x,y,width):
 if not any(i['available'] for i in categories[name]['items']):return y
 text(x,y+17,title.upper(),21,'bold',RED);y+=22
 visible=[i for i in categories[name]['items'] if i['available']]
 for n,item in enumerate(visible):
  if n==divider_index(categories[name]):
   page.draw_line((x,y+3),(x+width,y+3),color=BLACK,width=.6);y+=8
  if name=='Wine of the Month':
   text(x,y+11.5,item['name'],11.5);right(x+width,y+11.5,'Bottle '+str(item['price']),11.5)
   text(x,y+23,item['description'],9)
   options=' | '.join(o['name']+' '+str(o['price']) for o in item['options'])
   right(x+width,y+25,options,10.5)
   audit.append({'id':item['id'],'name':item['name'],'price':item['price'],'x':x,'y':y});y+=30
  else:y=draw_item(item,x,y,width,11.5)
 return y+3

special_columns=[
 [('Monthly Specials Appetizers','Appetizers'),('Monthly Specials · Salads','Salad'),('Monthly Specials · Mains','Main')],
 [('Monthly Specials · Dessert','Dessert'),('Wine of the Month','Wine of the Month')]
]
special_ends=[]
for x,group in zip([468,797],special_columns):
 y=sy+48
 for name,title in group:y=special_group(name,title,x,y,325)
 special_ends.append(y)
special_bottom=max(special_ends)+10
assert special_bottom<1084,'Specials panel would overlap the footer'
page.draw_rect(fitz.Rect(sx,sy,sx+sw,special_bottom),color=RED,width=2)
print('Specials top',round(sy,1),'bottom',round(special_bottom,1),'gap',CATEGORY_GAP)
text(55,1100,'KOI Kemang | Lunch & Dinner | '+DATE_LABEL,8)
center(W/2,1112,DATA['footer'],10)

expected=[i for c in DATA['categories'] for i in c['items'] if i['available']]
assert len(audit)==len(expected),(len(audit),len(expected))
assert set(i['id'] for i in audit)==set(i['id'] for i in expected)
assert all(next(i['price'] for i in expected if i['id']==a['id'])==a['price'] for a in audit)
for x,y,x2,y2,name in regions:
 assert 0<=x<x2<W and 0<=y<y2<H,name
# Keep exactly the original physical page dimensions, with embedded scalable content.
final=fitz.open();p=final.new_page(width=W/1.8,height=H/1.8)
p.show_pdf_page(p.rect,doc,0)
final.set_metadata({'title':'KOI Kemang - Lunch & Dinner','author':'KOI','subject':'Menu proof from current saved menu data, '+DATE_LABEL})
final.subset_fonts()
final.save(OUT,garbage=4,deflate=True)
OUT.with_suffix('.audit.json').write_text(json.dumps({'items':audit,'count':len(audit),'pagePoints':[W/1.8,H/1.8],'dividers':[c['name'] for c in DATA['categories'] if divider_index(c) is not None],'unresolved':[i['name']+': '+i['notes'] for i in expected if i.get('notes')]},ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',OUT,'with',len(audit),'verified item-price pairs.')
