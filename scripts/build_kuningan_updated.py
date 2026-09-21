"""Create a reference-faithful Kuningan proof from the authenticated saved snapshot.

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
parser.add_argument('--source',type=Path,default=ROOT/'Kuningan Lunch & Dinner 20260606A.pdf')
parser.add_argument('--icons',type=Path,default=ROOT/'dist/menu-icons.js')
parser.add_argument('--font-regular',type=Path,default=Path('C:/Windows/Fonts/calibri.ttf'))
parser.add_argument('--font-bold',type=Path,default=Path('C:/Windows/Fonts/calibrib.ttf'))
args=parser.parse_args()
DATA=json.loads(args.snapshot.read_text(encoding='utf-8'))
assert 'kuningan' in DATA['name'].lower(), 'This renderer is for KOI Kuningan only.'
SOURCE=args.source
OUT=args.output
OUT.parent.mkdir(parents=True,exist_ok=True)
DATE_LABEL=args.date.strftime('%d %B %Y')
source=fitz.open(SOURCE)
assert len(source)==1 and abs(source[0].rect.width-502.32)<.1 and abs(source[0].rect.height-355.2)<.1, "Source dimensions differ; adapt artwork coordinates."
source[0].add_redact_annot(source[0].rect,fill=False)
source[0].apply_redactions(images=0,graphics=0,text=0)
W,H=source[0].rect.width*3,source[0].rect.height*3
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
 page.show_pdf_page(fitz.Rect(dest),source,0,clip=fitz.Rect([v/3 for v in clip]))

def icon(name,x,y,size=22):
 tag=tags.get(name)
 if not tag:return
 encoded=tag.get('iconImage') or presets.get(tag.get('icon'),{}).get('image')
 if encoded:
  raw=base64.b64decode(encoded.split(',',1)[1])
  page.insert_image(fitz.Rect(x,y,x+size,y+size),stream=raw)
 elif tag.get('icon'):
  raise ValueError('An icon needs printable artwork: '+name)

heading_boxes={
 'Small Bites':(0,0,145,29),'Asian':(0,0,75,29),
 'Soups':(204,232,281,261),'Appetizers':(184,381,312,408),
 'Salads':(194,571,280,599),'Sandwiches':(168,703,309,733),
 'Burger':(187,810,274,837),'Pastas':(548,231,632,260),
 'Noodles & Rice':(500,475,669,503),'Poultry':(535,630,625,656),
 'Seafood':(889,232,988,262),'Beef':(903,484,959,512),
 'Grill':(902,694,962,725),'Lamb':(1234,230,1297,261),
 'Poke Bowl':(1213,304,1336,332),'Sauce':(1242,465,1317,497),
 'Side Dishes':(1212,578,1344,610),'Kids':(1252,807,1306,838),
 'Monthly Specials':(640,813,866,844),
}

glyphs={}
for word,key in [('LAMB','Lamb'),('PASTAS','Pastas'),('SANDWICHES','Sandwiches')]:
 drawings=sorted([d for d in source[0].get_drawings() if fitz.Rect(heading_boxes[key]).contains(d['rect']*3)],key=lambda d:d['rect'].x0)
 assert len(drawings)==len(word),(word,len(drawings))
 for letter,drawing in zip(word,drawings):glyphs.setdefault(letter,drawing)

def original_lettering(label,x,y,width):
 # Assemble the actual reference outlines for new category names.
 height=26
 widths=[8 if letter==' ' else glyphs[letter]['rect'].width*height/glyphs[letter]['rect'].height for letter in label]
 xx=x+(width-sum(widths)-1.6*(len(label)-1))/2
 for letter,ww in zip(label,widths):
  if letter!=' ':
   d=glyphs[letter];r=d['rect'];scale=height/r.height
   def pt(p):return fitz.Point(xx+(p.x-r.x0)*scale,y+2+(p.y-r.y0)*scale)
   shape=page.new_shape()
   for command in d['items']:
    if command[0]=='l':shape.draw_line(pt(command[1]),pt(command[2]))
    elif command[0]=='c':shape.draw_bezier(*(pt(p) for p in command[1:]))
    elif command[0]=='re':shape.draw_rect(fitz.Rect(pt(command[1].tl),pt(command[1].br)))
    else:raise ValueError(command[0])
   shape.finish(color=None,fill=d['fill'],even_odd=d['even_odd'],closePath=d['closePath'])
   shape.commit()
  xx+=ww+1.6

def heading(name,x,y,width):
 box=heading_boxes[name];bw=box[2]-box[0];bh=box[3]-box[1]
 # Preserve the source outlined glyph artwork at its original relative scale.
 left=x+(width-bw)/2

 if name in ('Small Bites','Asian'):
  original_lettering(name.upper(),x,y,width)
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
 return h

def draw_category(name,x,y,width):
 cat=categories[name];y=heading(name,x,y,width)
 visible=[i for i in cat['items'] if i['available']]
 for n,i in enumerate(visible):
  opts=[] if n+1<len(visible) and i['options'] and i['options']==visible[n+1]['options'] else None
  y=draw_item(i,x,y,width,shared_options=opts)
 return y

# Original vector branding, rather than a screenshot of old menu content.
assert DATA['menuTitle'].lower()=='lunch & dinner'
vector((559,0,965,173),(559,0,965,173))
# Existing no-pork symbol alongside the saved, approved statement.
vector((691,177,713,198),(691,177,713,198))
text(716,191,DATA['dietaryNote'].upper(),11)
legend_left=['With jasmine rice','Takes more than 15 mins','Vegetarian','Spicy','New menu','Choice of white or red rice']
legend_right=['With baby potatoes','With mashed potato','With French or Belgian fries','With mixed salad','With baguette']
assert set(tags)==set(legend_left+legend_right),'Legend changed: reflow required.'
for x,names in [(1053,legend_left),(1247,legend_right)]:
 for n,name in enumerate(names):
  y=59+n*21;icon(name,x,y,25);text(x+34,y+18,name,10.5)
page.draw_line((44,208),(1457,208),color=RED,width=.65)
page.draw_line((44,212),(1457,212),color=RED,width=1.05)

# Balance whole categories in their saved reading order.
import itertools
regular=[c['name'] for c in DATA['categories'] if not c['name'].startswith('Monthly Specials') and c['name']!='Wine of the Month' and any(i['available'] for i in c['items'])]
widths=[319,330,312,332]; bottoms=[1005,748,748,1005]
height_cache={(n,w):category_height(categories[n],w) for n in regular for w in widths}
choices=[]
for a,b,c in itertools.combinations(range(1,len(regular)),3):
 groups=[regular[:a],regular[a:b],regular[b:c],regular[c:]]
 heights=[sum(height_cache[n,w] for n in group)+6*(len(group)-1) for group,w in zip(groups,widths)]
 remaining=[bottom-233-height for bottom,height in zip(bottoms,heights)]
 if min(remaining)>=0:choices.append((sum((v/max(1,len(g)-1))**2 for v,g in zip(remaining,groups)),groups,remaining))
assert choices,'Content needs a continuation page; cannot fit without reducing readability.'
_,groups,remaining=min(choices)
print('Balanced columns:',groups)
columns=list(zip([78,424,778,1120],widths,groups,bottoms))
for x,width,names,bottom in columns:
 heights=[category_height(categories[n],width) for n in names]
 gap=(bottom-233-sum(heights))/(len(names)-1)
 if gap<0:raise ValueError(f'Column overflow for {names}: gap={gap:.2f}')
 y=233
 for name in names:
  y=draw_category(name,x,y,width)+gap
 print('Column',names,'ends',round(y-gap,1),'gap',round(gap,1))

# Reference central specials panel.
sx,sy,sw,sh=409,760,693,268
page.draw_rect(fitz.Rect(sx,sy,sx+sw,sy+sh),color=RED,width=2)
box=heading_boxes['Monthly Specials'];bw=box[2]-box[0]
vector(box,(sx+(sw-bw)/2,sy+5,sx+(sw+bw)/2,sy+36))
page.draw_line((sx,sy+42),(sx+sw,sy+42),color=RED,width=.9)

def special_group(name,title,x,y,width):
 if not any(i['available'] for i in categories[name]['items']):return y
 text(x,y+17,title.upper(),21,'bold',RED);y+=22
 for item in categories[name]['items']:
  if not item['available']:continue
  if name=='Wine of the Month':
   text(x,y+11.5,item['name'],11.5);right(x+width,y+11.5,'Bottle '+str(item['price']),11.5)
   text(x,y+23,item['description'],9)
   options=' | '.join(o['name']+' '+str(o['price']) for o in item['options'])
   right(x+width,y+25,options,10.5)
   audit.append({'id':item['id'],'name':item['name'],'price':item['price'],'x':x,'y':y});y+=30
  else:y=draw_item(item,x,y,width,11.5)
 return y+3

y=sy+51
for name,title in [('Monthly Specials · Salad','Salad'),('Monthly Specials · Pasta','Pasta'),('Monthly Specials · Main','Main')]:
 y=special_group(name,title,435,y,285)
assert y<1028,y
y=sy+51
for name,title in [('Monthly Specials · Pizza','Pizza'),('Monthly Specials · Dessert','Dessert'),('Wine of the Month','Wine of the Month')]:
 y=special_group(name,title,751,y,323)
assert y<1028,y
text(77,1037,'KOI Kuningan | Lunch & Dinner | '+DATE_LABEL,9)
center(W/2,1053,DATA['footer'],9)

expected=[i for c in DATA['categories'] for i in c['items'] if i['available']]
assert len(audit)==len(expected),(len(audit),len(expected))
assert set(i['id'] for i in audit)==set(i['id'] for i in expected)
assert all(next(i['price'] for i in expected if i['id']==a['id'])==a['price'] for a in audit)
for x,y,x2,y2,name in regions:
 assert 0<=x<x2<W and 0<=y<y2<H,name
# Keep exactly the original physical page dimensions, with embedded scalable content.
final=fitz.open();p=final.new_page(width=W/3,height=H/3)
p.show_pdf_page(p.rect,doc,0)
final.set_metadata({'title':'KOI Kuningan - Lunch & Dinner','author':'KOI','subject':'Menu proof from current saved menu data, '+DATE_LABEL})
final.subset_fonts()
final.save(OUT,garbage=4,deflate=True)
OUT.with_suffix('.audit.json').write_text(json.dumps({'items':audit,'count':len(audit),'pagePoints':[W/3,H/3],'unresolved':[i['name']+': '+i['notes'] for i in expected if i.get('notes')]},ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',OUT,'with',len(audit),'verified item-price pairs.')
