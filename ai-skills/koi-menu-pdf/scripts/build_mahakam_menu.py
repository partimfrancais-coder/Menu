"""Create a reference-faithful Mahakam proof from the authenticated saved snapshot.

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
parser.add_argument('--source',type=Path,default=Path('MAHAKAM LUNCH DINNER 20260605A.pdf'))
parser.add_argument('--icons',type=Path,default=Path('dist/menu-icons.js'))
parser.add_argument('--font-regular',type=Path,default=Path('C:/Windows/Fonts/calibri.ttf'))
parser.add_argument('--font-bold',type=Path,default=Path('C:/Windows/Fonts/calibrib.ttf'))
args=parser.parse_args()
DATA=json.loads(args.snapshot.read_text(encoding='utf-8'))
assert 'mahakam' in DATA['name'].lower(), 'This renderer is for KOI Mahakam only.'
assert DATA['menuTitle'].casefold()=='lunch & dinner', 'Adapt header artwork for a different menu title.'
SOURCE=args.source
OUT=args.output
OUT.parent.mkdir(parents=True,exist_ok=True)
DATE_LABEL=args.date.strftime('%d %B %Y')
source=fitz.open(SOURCE)
assert len(source)==1 and abs(source[0].rect.width-538.81)<.1 and abs(source[0].rect.height-348.0)<.1, "Source dimensions differ; adapt artwork coordinates."
source[0].add_redact_annot(source[0].rect,fill=False)
source[0].apply_redactions(images=0,graphics=0,text=0)
W,H=source[0].rect.width*3.0,source[0].rect.height*3.0
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
 page.show_pdf_page(fitz.Rect(dest),source,0,clip=fitz.Rect([v/3.0 for v in clip]))

def icon(name,x,y,size=22):
 tag=tags.get(name)
 if not tag:return
 encoded=tag.get('iconImage') or presets.get(tag.get('icon'),{}).get('image')
 if encoded:
  raw=base64.b64decode(encoded.split(',',1)[1])
  page.insert_image(fitz.Rect(x,y,x+size,y+size),stream=raw)
 elif tag.get('icon'):
  raise ValueError('An icon needs printable artwork: '+name)

def divider_index(cat):
 visible=[i for i in cat['items'] if i['available']]
 cuisines=[i.get('cuisine','') for i in visible]
 transitions=[n for n in range(1,len(cuisines)) if cuisines[n]!=cuisines[n-1]]
 return transitions[0] if set(cuisines)=={'European','Asian'} and len(transitions)==1 else None

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

def draw_item(item,x,y,width,size=12,shared_options=None,price_prefix=''):
 start=y;lines,trailing,price_space=item_layout(item,width,size)
 leaders=[tag for tag in item['tags'] if tag in LEADING][:1]
 for j,tag in enumerate(leaders):icon(tag,x-23-17*(len(leaders)-1-j),y-4,22)
 y=draw_runs(lines,x,y)
 last=lines[-1];last_size=max(run[1] for run in last)
 last_y=y-(last_size+2.3)
 tx=x+sum(measure(v,fs,f) for v,fs,f in last)+1
 for tag in trailing:icon(tag,tx,last_y-4,22);tx+=17
 right(x+width,start+size,price_prefix+str(item['price']),size)
 audit.append({'id':item['id'],'name':item['name'],'price':item['price'],'x':x,'y':start,'page':page.number})
 opts=item['options'] if shared_options is None else shared_options
 for option in opts:
  option_lines=wrap_runs([(option['name'],10.2,'regular')],width-42)
  option_y=y;y=draw_runs(option_lines,x+12,y)
  right(x+width,option_y+10.2,('+' if option['kind']=='Add-on' else '')+str(option['price']),10.2)
 y+=.7
 audit[-1]['bottom']=y
 regions.append((x,start,x+width,y,item['name']))
 return y

def category_height(cat,width):
 h=32
 visible=[i for i in cat['items'] if i['available']]
 for n,i in enumerate(visible):
  lines,_,_=item_layout(i,width)
  h+=sum(max(r[1] for r in line)+2.3 for line in lines)+.7
  # Adjacent dishes may share the same add-on row, as in the reference.
  opts=i['options']
  for o in opts:h+=sum(max(r[1] for r in line)+2.3 for line in wrap_runs([(o['name'],10.2,'regular')],width-42))
 return h+(8 if divider_index(cat) is not None else 0)

def draw_category(name,x,y,width):
 cat=categories[name];y=heading(name,x,y,width)
 visible=[i for i in cat['items'] if i['available']]
 for n,i in enumerate(visible):
  if n==divider_index(cat):
   page.draw_line((x,y+3),(x+width,y+3),color=BLACK,width=.6);y+=8
  opts=None
  y=draw_item(i,x,y,width,shared_options=opts)
 return y


# Native Mahakam heading rectangles; only vector glyphs are reused, never dish rows.
ARTWORK={
 'SMALLBITES':(72,82,118,92), 'BEEF':(203,82,221,92),
 'SEAFOOD':(314,82,346,92), 'NOODLES&RICE':(411,82,470,92),
 'SOUPS':(86,162,113,172), 'SALADS':(86,213,115,224),
 'PASTAS':(86,263,114,274), 'GRILL':(201,151,222,161),
 'LAMB':(201,189,221,200), 'SAUCE':(200,213,225,225),
 'POULTRY':(313,157,346,169), 'BURGER&SANDWICH':(287,215,367,226),
 'SIDEDISHES':(418,135,465,147), 'DESSERT':(423,200,458,211),
 'MONTHLY SPECIALS':(234,258,303,269),
}
glyphs={}
source_drawings=source[0].get_drawings()
for label,box in ARTWORK.items():
 letters=sorted([d for d in source_drawings if fitz.Rect(box).contains(d['rect']) and d['rect'].height>6],key=lambda d:d['rect'].x0)
 chars=label.replace(' ','')
 if len(letters)!=len(chars):
  raise ValueError(f'Unexpected Mahakam artwork for {label}: {len(letters)} glyphs, expected {len(chars)}')
 for letter,drawing in zip(chars,letters):glyphs.setdefault(letter,drawing)

def outlined_title(name,x,y,width,height=24):
 name=name.upper()
 def letter_width(ch):
  if ch==' ':return height*.30
  if ch=='Z':return height*.44
  if ch not in glyphs:raise ValueError('Unsupported heading letter: '+ch)
  r=glyphs[ch]['rect'];return r.width*height/r.height
 widths=[letter_width(ch) for ch in name];gap=height*.06
 left=x+(width-sum(widths)-gap*(len(name)-1))/2
 for ch,lw in zip(name,widths):
  if ch=='Z':
   # Narrow outlined Z for APPETIZERS, absent from the original heading alphabet.
   pts=[(0,0),(lw,0),(lw,2),(2,height-2),(lw,height-2),(lw,height),(0,height),(0,height-2),(lw-2,2),(0,2),(0,0)]
   shape=page.new_shape();shape.draw_polyline([fitz.Point(left+a,y+b) for a,b in pts]);shape.finish(color=RED,fill=(1,1,1),width=.55);shape.commit()
  elif ch!=' ':
   d=glyphs[ch];r=d['rect'];scale=height/r.height
   def pt(p):return fitz.Point(left+(p.x-r.x0)*scale,y+(p.y-r.y0)*scale)
   shape=page.new_shape()
   for command in d['items']:
    if command[0]=='l':shape.draw_line(pt(command[1]),pt(command[2]))
    elif command[0]=='c':shape.draw_bezier(*(pt(p) for p in command[1:]))
    elif command[0]=='re':shape.draw_rect(fitz.Rect(pt(command[1].tl),pt(command[1].br)))
    else:raise ValueError('Unsupported heading path: '+command[0])
   shape.finish(color=None,fill=d['fill'],even_odd=d['even_odd'],closePath=d['closePath']);shape.commit()
  left+=lw+gap

def heading(name,x,y,width):
 outlined_title(name,x,y,width)
 page.draw_line((x,y+27),(x+width,y+27),color=RED,width=.7)
 return y+32

CATEGORY_GAP=12
XS=[46*3,160*3,276*3,390*3];CW=102*3;TOP=82*3;BOTTOM=333*3
regular=[c['name'] for c in DATA['categories'] if not c['name'].startswith('Monthly Specials') and c['name']!='Wine of the Month' and any(i['available'] for i in c['items'])]
specials=[c['name'] for c in DATA['categories'] if c['name'] not in regular and any(i['available'] for i in c['items'])]

def group_height(names):
 return sum(category_height(categories[n],CW) for n in names)+max(0,len(names)-1)*CATEGORY_GAP

def special_height(name):
 return category_height(categories[name],CW)-32+22+6

# Specials preserve saved sequence across two columns, including newly added groups.
if specials:
 split=min(range(1,len(specials)+1),key=lambda n:max(sum(special_height(k) for k in specials[:n]),sum(special_height(k) for k in specials[n:])))
 special_groups=[specials[:split],specials[split:]]
 special_height_total=45+max(sum(special_height(n) for n in g) for g in special_groups)+12
else:special_groups=[[],[]];special_height_total=0

def header():
 # Header title and no-pork emblem only; all legend words are rendered from saved tags.
 vector((207*3,42*3,334*3,61*3),(207*3,42*3,334*3,61*3))
 vector((245*3,64*3,252*3,70*3),(245*3,64*3,252*3,70*3))
 text(253*3,69*3,DATA['dietaryNote'],9)
 legend=list(tags)
 for idx,name in enumerate(legend):
  col=idx//6;row=idx%6;x=400*3+col*55*3;y=22*3+row*6.5*3
  icon(name,x,y,18);text(x+24,y+13,name,7.8)
 page.draw_line((30*3,74*3),(509*3,74*3),color=RED,width=.7)
 page.draw_line((30*3,75.5*3),(509*3,75.5*3),color=RED,width=1.0)

def footer():
 text(11*3,342*3,'KOI MAHAKAM | '+args.date.isoformat(),6)
 center(W/2,343*3,DATA['footer'],7)

def new_page():
 global page
 page=doc.new_page(width=W,height=H)
 for key,path in [('regular',args.font_regular),('bold',args.font_bold)]:page.insert_font(fontname=key,fontfile=str(path))
 header()

def draw_regular(names,x):
 y=TOP
 for name in names:
  start=y;y=draw_category(name,x,y,CW)
  if name=='Ice Cream & Sorbet':page.draw_rect(fitz.Rect(x-8,start-4,x+CW+8,y+4),color=RED,width=.8)
  y+=CATEGORY_GAP
 return y-CATEGORY_GAP if names else TOP

def draw_specials(top):
 left=XS[1]-8;right_edge=XS[2]+CW+8
 outlined_title('Monthly Specials',left,top+5,right_edge-left)
 page.draw_line((left,top+34),(right_edge,top+34),color=RED,width=.8)
 ends=[]
 for x,names in zip(XS[1:3],special_groups):
  y=top+43
  for name in names:
   title=name.replace('Monthly Specials','').strip(' ·-') or name
   text(x,y+15,title.upper(),15,'bold',RED);y+=22
   for n,item in enumerate([i for i in categories[name]['items'] if i['available']]):
    if n==divider_index(categories[name]):page.draw_line((x,y+3),(x+CW,y+3),color=BLACK,width=.6);y+=8
    y=draw_item(item,x,y,CW,price_prefix='Bottle ' if name=='Wine of the Month' else '')
   y+=6
  ends.append(y)
 bottom=max(ends)+8
 if bottom>BOTTOM:raise ValueError('Specials exceed page capacity; adjust layout explicitly.')
 page.draw_rect(fitz.Rect(left,top,right_edge,bottom),color=RED,width=1)

import itertools
choices=[]
for cuts in itertools.combinations(range(1,len(regular)),3):
 a,b,c=cuts;groups=[regular[:a],regular[a:b],regular[b:c],regular[c:]]
 ends=[TOP+group_height(g) for g in groups]
 panel_top=max(ends[1:3])+CATEGORY_GAP
 if max(ends)<=BOTTOM and (not specials or panel_top+special_height_total<=BOTTOM):
  choices.append((max(ends+[panel_top+special_height_total if specials else 0]),sum(e*e for e in ends),groups))
header()
if choices:
 groups=min(choices,key=lambda c:c[:2])[2];ends=[draw_regular(g,x) for g,x in zip(groups,XS)]
 if specials:draw_specials(max(ends[1:3])+CATEGORY_GAP)
 footer()
else:
 # Continuation pages retain original type size; never silently drop a category to fit.
 col=0;y=TOP
 for name in regular:
  h=group_height([name])
  if h>BOTTOM-TOP:raise ValueError('Category too tall for a page; split this category explicitly: '+name)
  if y+h>BOTTOM:
   col+=1;y=TOP
   if col==4:footer();new_page();col=0
  y=draw_category(name,XS[col],y,CW)+CATEGORY_GAP
 footer()
 if specials:new_page();draw_specials(TOP);footer()

expected=[i for c in DATA['categories'] for i in c['items'] if i['available']]
assert len(audit)==len(expected) and sorted(i['id'] for i in audit)==sorted(i['id'] for i in expected),'Available-item coverage mismatch'
final=fitz.open()
for n in range(len(doc)):
 p=final.new_page(width=W/3,height=H/3);p.show_pdf_page(p.rect,doc,n)
final.set_metadata({'title':'KOI Mahakam - Lunch & Dinner','author':'KOI','subject':'Current saved menu proof, '+args.date.isoformat()})
final.subset_fonts();final.save(OUT,garbage=4,deflate=True)
# Check extracted text independently of the drawing audit.
import unicodedata
normalize=lambda value:' '.join(unicodedata.normalize('NFKC',value).replace('\u2010','-').split()).casefold()
content=normalize(' '.join(p.get_text() for p in final))
missing=[i['name'] for i in expected if normalize(i['name']) not in content]
assert not missing,'Missing dish names in PDF: '+', '.join(missing)
for item,row in zip(expected,sorted(audit,key=lambda a:next(n for n,i in enumerate(expected) if i['id']==a['id']))):
 p=final[row['page']]
 region=fitz.Rect((row['x']-1)/3,(row['y']-3)/3,(row['x']+CW+2)/3,(row['bottom']+2)/3)
 row_text=normalize(p.get_text(clip=region))
 for value in [item['name'],item.get('description','')]+[o['name'] for o in item.get('options',[])]:
  assert normalize(value) in row_text, 'Missing row content: '+item['name']+' / '+value
 price_region=fitz.Rect((row['x']+CW-55)/3,(row['y']-3)/3,(row['x']+CW+2)/3,(row['bottom']+2)/3)
 price_words=p.get_text(clip=price_region).split()
 for value in [str(item['price'])]+[('+' if o['kind']=='Add-on' else '')+str(o['price']) for o in item.get('options',[])]:
  assert value in price_words, 'Missing row price: '+item['name']+' / '+value
OUT.with_suffix('.audit.json').write_text(json.dumps({'items':audit,'count':len(audit),'pages':len(final),'pagePoints':[W/3,H/3],'dividers':[c['name'] for c in DATA['categories'] if divider_index(c) is not None],'missingNames':missing},ensure_ascii=False,indent=2),encoding='utf-8')
print('Created',OUT,'with',len(expected),'items on',len(final),'page(s).')
