# Stage 1: docx -> ordered blocks with run-level formatting
import json, re, sys, html
from lxml import etree
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
V='urn:schemas-microsoft-com:vml'
ns={'w':W,'r':R,'a':A,'wp':WP,'v':V}
base=sys.argv[1]
doc=etree.parse(base+'/word/document.xml')
rels=etree.parse(base+'/word/_rels/document.xml.rels')
relmap={e.get('Id'):(e.get('Target'),e.get('TargetMode')) for e in rels.getroot()}
def q(t): return '{%s}%s'%(W,t)
def rprops(r):
    rp=r.find(q('rPr')); d={}
    if rp is None: return d
    c=rp.find(q('color'))
    if c is not None: d['color']=c.get(q('val'))
    u=rp.find(q('u'))
    if u is not None and u.get(q('val')) not in (None,'none'): d['u']=1
    if u is not None and u.get(q('val')) is None: d['u']=1
    va=rp.find(q('vertAlign'))
    if va is not None and va.get(q('val')) in ('superscript','subscript'): d['va']=va.get(q('val'))[:3]
    b=rp.find(q('b'))
    if b is not None and b.get(q('val')) not in ('0','false'): d['b']=1
    h=rp.find(q('highlight'))
    if h is not None and h.get(q('val')) not in ('none',None): d['mark']=1
    s=rp.find(q('shd'))
    if s is not None and (s.get(q('fill')) or 'auto').upper() not in ('AUTO','FFFFFF'): d['mark']=1
    em=rp.find(q('em'))
    if em is not None and em.get(q('val')) not in ('none',None): d['em']=1
    return d
def run_items(r, link=None):
    out=[]; p=rprops(r)
    if link: p=dict(p,link=link)
    for ch in r:
        tag=etree.QName(ch).localname
        if tag=='t': out.append(dict(p,t=ch.text or ''))
        elif tag=='tab': out.append(dict(p,t='\t'))
        elif tag in ('br','cr'): out.append({'br':1})
        elif tag=='sym': 
            out.append(dict(p,t=chr(int(ch.get(q('char')),16)) if ch.get(q('char')) else ''))
        elif tag in ('drawing','pict','object'):
            for bl in ch.iter('{%s}blip'%A):
                rid=bl.get('{%s}embed'%R)
                if rid in relmap: 
                    ext=ch.find('.//{%s}extent'%WP)
                    w=int(ext.get('cx'))/914400*96 if ext is not None else None
                    out.append({'img':relmap[rid][0].split('/')[-1],'w':round(w) if w else None})
            for im in ch.iter('{%s}imagedata'%V):
                rid=im.get('{%s}id'%R)
                if rid in relmap: out.append({'img':relmap[rid][0].split('/')[-1],'w':None})
    return out
def para_runs(p):
    runs=[]
    for ch in p:
        tag=etree.QName(ch).localname
        if tag=='r': runs+=run_items(ch)
        elif tag=='hyperlink':
            rid=ch.get('{%s}id'%R); link=relmap.get(rid,(None,))[0]
            for r in ch.findall(q('r')): runs+=run_items(r,link)
        elif tag in ('ins','smartTag','customXml','sdt'):
            for r in ch.iter(q('r')): runs+=run_items(r)
    # merge adjacent runs with identical props
    m=[]
    for x in runs:
        if m and 't' in x and 't' in m[-1] and {k:v for k,v in x.items() if k!='t'}=={k:v for k,v in m[-1].items() if k!='t'}:
            m[-1]['t']+=x['t']
        else: m.append(dict(x))
    return m
def para_style(p):
    ps=p.find(q('pPr'))
    if ps is None: return ''
    s=ps.find(q('pStyle'))
    return s.get(q('val')) if s is not None else ''
blocks=[]
body=doc.getroot().find(q('body'))
for el in body:
    tag=etree.QName(el).localname
    if tag=='p':
        runs=para_runs(el)
        blocks.append({'k':'p','style':para_style(el),'runs':runs,'text':''.join(r.get('t','') for r in runs)})
    elif tag=='tbl':
        rows=[]
        for tr in el.findall(q('tr')):
            cells=[]
            for tc in tr.findall(q('tc')):
                pr=tc.find(q('tcPr')); span=1; vm=None
                if pr is not None:
                    g=pr.find(q('gridSpan')); span=int(g.get(q('val'))) if g is not None else 1
                    v=pr.find(q('vMerge')); vm=(v.get(q('val')) or 'continue') if v is not None else None
                paras=[para_runs(p) for p in tc.findall(q('p'))]
                cells.append({'span':span,'vm':vm,'paras':paras})
            rows.append(cells)
        blocks.append({'k':'tbl','rows':rows,'text':' | '.join(''.join(r.get('t','') for p in c['paras'] for r in p) for row in rows for c in row)})
json.dump(blocks,open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False,indent=0)
print(len(blocks),'blocks')
