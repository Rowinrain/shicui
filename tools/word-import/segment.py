import json, re, sys
blocks=json.load(open(sys.argv[1],encoding='utf-8'))
BOOKS={'必修一':'1','必修二':'2','选修一':'3','选修二':'4','选修三':'5'}
items=[]; book=None; chap=None; cur=None
def flush():
    global cur
    if cur: items.append(cur)
    cur=None
for i,b in enumerate(blocks):
    t=b['text'].strip()
    if b['k']=='p' and t in BOOKS: flush(); book=BOOKS[t]; chap=None; continue
    m=re.match(r'^第(\d+)章',t)
    if b['k']=='p' and m and len(t)<60: flush(); chap=int(m.group(1)); continue
    if b['k']=='p' and t=='综合题': flush(); book='Z'; chap=0; continue
    m=re.match(r'^(\d+)、',t)
    if b['k']=='p' and m:
        flush(); cur={'id':f'{book}-{chap}-{m.group(1)}','book':book,'chap':chap,'n':int(m.group(1)),'blocks':[i]}; continue
    if cur is not None: cur['blocks'].append(i)
    elif t: print('ORPHAN',i,t[:60],file=sys.stderr)
flush()
json.dump(items,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False)
def fmt(runs,trunc):
    s=''
    for r in runs:
        if 'img' in r: s+=f"[IMG {r['img']}]"; continue
        if 'br' in r: s+='⏎'; continue
        t=r['t']; c=r.get('color','')
        if r.get('va')=='sup': t='^'+t
        if r.get('va')=='sub': t='_'+t
        if r.get('u'): t='‹'+t+'›'
        if c=='C00000': t='{R:'+t+'}'
        elif c=='0070C0': t='{B:'+t+'}'
        elif c=='75BD42': t='{G:'+t+'}'
        s+=t
    return s if len(s)<=trunc else s[:trunc]+'…'
out=[]
for it in items:
    out.append(f"#### {it['id']}")
    for bi in it['blocks']:
        b=blocks[bi]
        if b['k']=='tbl': out.append('  [TABLE '+str(len(b['rows']))+' rows] '+b['text'][:150]); continue
        s=fmt(b['runs'],int(sys.argv[4]))
        if s.strip(): out.append('  '+s)
open(sys.argv[3],'w',encoding='utf-8').write('\n'.join(out))
print(len(items),'items')
