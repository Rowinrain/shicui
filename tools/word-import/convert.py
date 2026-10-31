# Stage 2: items -> qbank-import JSON (+ review checklist data)
import json, re, sys, base64, html as H, copy
sys.path.insert(0, sys.argv[4])
from mapping import Q, NOTES, EXTRA_TAGS

blocks = json.load(open(sys.argv[1], encoding='utf-8'))
items = json.load(open(sys.argv[2], encoding='utf-8'))
MEDIA = sys.argv[3]
RED, BLUE = 'C00000', '0070C0'
SLOT_TOKEN = ''
SLOT = '<span class="ans-slot"></span>'
BOOKNAME = {'1': '必修1', '2': '必修2', '3': '选必1', '4': '选必2', '5': '选必3', 'Z': '综合题'}

# ---------- 去重编号 ----------
seen = {}
for it in items:
    if it['id'] in seen:
        it['id'] += 'b'
    seen[it['id']] = 1

def img_html(name):
    ext = name.rsplit('.', 1)[-1].lower()
    mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else 'image/' + ext
    data = base64.b64encode(open(f'{MEDIA}/{name}', 'rb').read()).decode()
    return f'<img src="data:{mime};base64,{data}">'

URL = re.compile(r'(https?://[^\s<>"，。；）]+)')
def text_html(t):
    t = H.escape(t, quote=False)
    return URL.sub(lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', t)

def runs_html(runs, mode):
    """mode: q (题目: 彩色下划线=挖空), note (红=加粗), ana (解析)"""
    out = []; i = 0
    while i < len(runs):
        r = runs[i]
        if 'img' in r: out.append(img_html(r['img'])); i += 1; continue
        if 'br' in r: out.append('<br>'); i += 1; continue
        col = r.get('color')
        if mode == 'q' and r.get('u') and col in (RED, BLUE):
            # 合并相邻的挖空 run
            grp = []; miss = False
            while i < len(runs) and 't' in runs[i] and runs[i].get('u') and runs[i].get('color') in (RED, BLUE):
                grp.append(runs[i]); miss |= runs[i].get('color') == BLUE; i += 1
            inner = ''.join(fmt_run(g, 'plain') for g in grp).strip()
            out.append(f'<u class="blank{" miss" if miss else ""}">{inner}</u>')
            continue
        out.append(fmt_run(r, mode)); i += 1
    return ''.join(out)

def fmt_run(r, mode):
    t = r.get('t', '')
    if not t: return ''
    if SLOT_TOKEN in t:
        a, b = t.split(SLOT_TOKEN, 1)
        return fmt_run(dict(r, t=a), mode) + SLOT + fmt_run(dict(r, t=b), mode)
    h = text_html(t)
    if r.get('va') == 'sup': h = f'<sup>{h}</sup>'
    if r.get('va') == 'sub': h = f'<sub>{h}</sub>'
    if mode != 'plain':
        if r.get('u'): h = f'<u>{h}</u>'
        if r.get('b') or (mode == 'note' and r.get('color') == RED): h = f'<b>{h}</b>'
        if r.get('mark'): h = f'<mark>{h}</mark>'
        if r.get('em'): h = f'<span class="em-dot">{h}</span>'
    return h

def tbl_html(b, mode):
    rows = b['rows']; out = ['<table><tbody>']
    # rowspan
    ncol = max(sum(c['span'] for c in row) for row in rows)
    grid = []
    for row in rows:
        cols = []; ci = 0
        for c in row:
            cols.append((ci, c)); ci += c['span']
        grid.append(cols)
    span = {}
    for ri, cols in enumerate(grid):
        for ci, c in cols:
            if c['vm'] == 'restart':
                n = 1
                for rj in range(ri + 1, len(grid)):
                    nxt = [x for x in grid[rj] if x[0] == ci]
                    if nxt and nxt[0][1]['vm'] == 'continue': n += 1
                    else: break
                span[(ri, ci)] = n
    for ri, cols in enumerate(grid):
        out.append('<tr>')
        for ci, c in cols:
            if c['vm'] == 'continue': continue
            attrs = (f' colspan="{c["span"]}"' if c['span'] > 1 else '') + (f' rowspan="{span[(ri, ci)]}"' if span.get((ri, ci), 1) > 1 else '')
            inner = '<br>'.join(runs_html(p, mode) for p in c['paras'] if p)
            out.append(f'<td{attrs}>{inner}</td>')
        out.append('</tr>')
    out.append('</tbody></table>')
    return ''.join(out)

def block_html(b, mode):
    if b['k'] == 'tbl': return tbl_html(b, mode)
    h = runs_html(b['runs'], mode)
    return f'<div>{h}</div>' if h.strip() else ''

# ---------- run 级别的文本裁剪 ----------
def ptext(runs): return ''.join(r.get('t', '') for r in runs)
def strip_prefix(runs, n):
    runs = copy.deepcopy(runs); out = []
    for r in runs:
        if n > 0 and 't' in r:
            k = min(n, len(r['t'])); r['t'] = r['t'][k:]; n -= k
            if not r['t']: continue
        out.append(r)
    return out
def replace_span(runs, start, end, token=''):
    """把纯文本区间 [start,end) 替换为 token（放在 start 所在 run）"""
    runs = copy.deepcopy(runs); pos = 0; placed = False; out = []
    for r in runs:
        if 't' not in r: out.append(r); continue
        t = r['t']; a, b = pos, pos + len(t); pos = b
        if b <= start or a >= end: out.append(r); continue
        keep_l = t[:max(0, start - a)]; keep_r = t[max(0, end - a):] if end < b else ''
        nt = keep_l + ('' if placed else token) + keep_r; placed = True
        if nt: out.append(dict(r, t=nt))
    return out
def lstrip_runs(runs):
    s = ptext(runs); n = len(s) - len(s.lstrip(' 　\t'))
    return strip_prefix(runs, n) if n else runs

SRC_RE = re.compile(r'^（([^（）]*)）')
def parse_source(raw):
    raw = raw.strip()
    multi = '多选' in raw
    s = re.sub(r'[，,·、]?\s*多选\s*[，,·、]?', '', raw).strip()
    m = re.match(r'^(\d{4})([ABC]\d{1,2})?(.*?)(T\d+(?:[A-D]|-\d+)?)?(改)?$', s)
    if not m: return dict(source=s, qno='', adapted=False, grade='高三', multi=multi, raw=raw)
    year, code, name, qno, adapted = m.groups()
    name = name.strip()
    grade = '高二' if '高二' in name else '高一' if '高一' in name else '高三'
    if grade == '高三' and '高三' not in name:
        name = re.sub(r'((?:\d+月)?(?:期初|期末|联考|调研|模拟|段考))', r'高三\1', name, count=1)
    return dict(source=year + name, qno=qno or '', adapted=bool(adapted), grade=grade, multi=multi, raw=raw)
def is_source(raw): return bool(re.search(r'\d{4}', raw)) or raw.strip() == '多选'

def take_sources(runs):
    """去掉段首的（来源）（多选）等，返回 (runs, srcinfo)"""
    info = None; multi = False
    while True:
        t = ptext(runs); m = SRC_RE.match(t.lstrip())
        if not m or not is_source(m.group(1)): break
        lead = len(t) - len(t.lstrip())
        if m.group(1).strip() == '多选': multi = True
        else: info = parse_source(m.group(1))
        runs = strip_prefix(runs, lead + m.end())
    if info is None: info = dict(source='', qno='', adapted=False, grade='高三', multi=False, raw='')
    info['multi'] = info['multi'] or multi
    return lstrip_runs(runs), info

JUDGE_RE = re.compile(r'[（(]\s*([✓✔√×])\s*[）)]\s*$')
OPT_RE = re.compile(r'^\s*([A-H])\s*[．.、]\s*')
KEY_RE = re.compile(r'[（(][\s　]*([A-H]{1,8})[\s　]*[）)][\s　。]*$')

def split_ana(paras):
    """paras: list of block indices. 返回 (body, analysis, extra)"""
    body, ana, ext = [], [], []; cur = body
    for bi in paras:
        b = blocks[bi]; t = b['text'].strip()
        if b['k'] == 'p' and t.startswith('解析：'):
            cur = ana; ana.append(('p', strip_prefix(b['runs'], len(b['text']) - len(b['text'].lstrip()) + 3))); continue
        if b['k'] == 'p' and t.startswith('补充：'):
            cur = ext; ext.append(('p', strip_prefix(b['runs'], len(b['text']) - len(b['text'].lstrip()) + 3))); continue
        if b['k'] == 'p' and t.startswith('【拓展】'):
            cur = ext; ext.append(('p', [dict(r, b=1) if 't' in r else r for r in b['runs']])); continue
        cur.append(('p', b['runs']) if b['k'] == 'p' else ('t', b))
    return body, ana, ext

def seq_html(seq, mode):
    out = []
    for kind, x in seq:
        if kind == 't': out.append(tbl_html(x, mode))
        else:
            h = runs_html(x, mode)
            if h.strip(): out.append(f'<div>{h}</div>')
    return ''.join(out)

def color_of(runs):
    cs = {r.get('color') for r in runs if 't' in r and r['t'].strip()}
    return 'r' if RED in cs else 'b' if BLUE in cs else ''

questions, notes, report = [], [], []

def add_q(q, it, extra_review=None):
    m = Q.get(q['_id'])
    if not m: report.append(('nomap', q['_id'])); return
    sec, tags, borrow = m
    q['section'] = sec
    q['tags'] = tags + [{'section': b.split('|')[0], 'name': b.split('|')[1]} for b in borrow]
    q['tagsPending'] = True
    q['levelUnset'] = True
    missed = bool(q.get('wrong')) or any(j.get('miss') for j in q.get('judges', [])) or 'blank miss' in (q.get('stem', '') + ''.join(s['stem'] for s in q.get('subs', []))) or q.get('missed')
    q['level'] = '较难' if missed else '适中'
    rv = []
    doc_chap = f"{BOOKNAME[it['book']]} 第{it['chap']}章" if it['book'] != 'Z' else '综合题'
    if not sec.startswith('专题'):
        b, c = sec.split('-')[0], sec.split('-')[1]
        if it['book'] == 'Z' or b != it['book'] or int(c) != it['chap']:
            rv.append(f'原文档放在「{doc_chap}」，按考查内容归到这一节')
    if extra_review: rv.append(extra_review)
    if rv: q['review'] = '；'.join(rv)
    q['_doc'] = f"{doc_chap} 第{it['n']}题"
    questions.append(q)

def build_choice(it, paras, src, first_runs):
    body, ana, ext = split_ana(paras)
    stem_seq = [('p', first_runs)]; opts = []; reds = set(); blues = set()
    for kind, x in body:
        if kind == 'p' and OPT_RE.match(ptext(x)) and ptext(x).strip():
            m = OPT_RE.match(ptext(x)); L = m.group(1)
            c = color_of(x)
            if c == 'r': reds.add(L)
            if c == 'b': blues.add(L)
            opts.append((L, strip_prefix(x, m.end())))
        elif not opts: stem_seq.append((kind, x))
        else: stem_seq.append((kind, x))  # 选项之后的图（少见）
    # 答案：在题干文字段落里找（X）
    key = ''
    for idx, (kind, x) in enumerate(stem_seq):
        if kind != 'p': continue
        t = ptext(x); m = KEY_RE.search(t)
        if m:
            key = m.group(1); stem_seq[idx] = ('p', replace_span(x, m.start(), m.end(), SLOT_TOKEN)); break
    letters = [L for L, _ in opts]
    q = dict(_id=it['id'], type='多选题' if (len(key) > 1 or src['multi']) else '单选题',
             stem=seq_html(stem_seq, 'q'), options=[runs_html(r, 'q') for _, r in opts],
             key=key, wrong=''.join(sorted(blues)), analysis=seq_html(ana, 'ana'), extra=seq_html(ext, 'ana'),
             source=src['source'], qno=src['qno'], adapted=src['adapted'], grade=src['grade'])
    rv = None
    if letters != list('ABCDEFGH'[:len(letters)]): rv = f'原题只摘录了选项 {"、".join(letters)}'
    if key and reds and not (reds <= set(key) and set(key) - reds <= blues):
        report.append(('mismatch', it['id'], key, ''.join(sorted(reds)), ''.join(sorted(blues))))
        rv = (rv + '；' if rv else '') + f'原文颜色和括号答案不一致：括号答案为 {key}，红色标在 {"".join(sorted(reds))} 上。已按 {key} 为答案、{"".join(sorted(reds - set(key)))} 为曾误选，请确认'
        q['wrong'] = ''.join(sorted((reds - set(key)) | (blues - set(key))))
    if not key: report.append(('nokey', it['id']))
    return q, rv

def build_judges(it, paras, src, first_runs):
    body, ana, ext = split_ana(paras)
    seq = [('p', first_runs)] + body
    lead, judges = [], []
    for kind, x in seq:
        if kind == 'p' and JUDGE_RE.search(ptext(x)):
            t = ptext(x); m = JUDGE_RE.search(t)
            k = '✓' if m.group(1) in '✓✔√' else '×'
            r = replace_span(x, m.start(), m.end(), SLOT_TOKEN)
            om = OPT_RE.match(ptext(r))
            if om: r = strip_prefix(r, om.end())
            judges.append(dict(text=runs_html(r, 'q'), key=k, miss=False))
        elif kind == 'p' and not ptext(x).strip() and not any('img' in z for z in x): continue
        else:
            (lead if not judges else ana).append((kind, x))
    return dict(_id=it['id'], type='判断题', stem=seq_html(lead, 'q'), judges=judges,
                analysis=seq_html(ana, 'ana'), extra=seq_html(ext, 'ana'),
                source=src['source'], qno=src['qno'], adapted=src['adapted'], grade=src['grade'])

def build_fill(it, paras, src, first_runs):
    body, ana, ext = split_ana(paras)
    return dict(_id=it['id'], type='填空题', stem=seq_html([('p', first_runs)] + body, 'q'),
                analysis=seq_html(ana, 'ana'), extra=seq_html(ext, 'ana'),
                source=src['source'], qno=src['qno'], adapted=src['adapted'], grade=src['grade'])

def build_answer(it, paras, src, first_runs):
    body, ana, ext = split_ana(paras)
    stem, subs = [('p', first_runs)], []
    for kind, x in body:
        t = ptext(x) if kind == 'p' else ''
        m = re.match(r'^\s*[（(](\d)[）)]', t)
        if m: subs.append([('p', strip_prefix(x, m.end()))])
        elif subs: subs[-1].append((kind, x))
        else: stem.append((kind, x))
    return dict(_id=it['id'], type='解答题', stem=seq_html(stem, 'q'),
                subs=[dict(stem=seq_html(s, 'q'), answer='', analysis='', score=1) for s in subs],
                analysis=seq_html(ana, 'ana'), extra=seq_html(ext, 'ana'),
                source=src['source'], qno=src['qno'], adapted=src['adapted'], grade=src['grade'])

ANSWER_TYPE = {'2-1-2b', '2-5-6'}
for it in items:
    bl = it['blocks']; first = blocks[bl[0]]
    m = re.match(r'^\s*\d+、', first['text'])
    first_runs = strip_prefix(first['runs'], m.end())
    rest = bl[1:]
    alltext = ''.join(blocks[b]['text'] for b in bl)
    content = re.sub(r'^\s*\d+、', '', alltext)
    if not re.sub(r'[A-D][．.、]|\s', '', content): report.append(('empty', it['id'])); continue
    iid = it['id']
    # ----- 笔记 -----
    if iid in NOTES:
        title = ptext(first_runs).strip().rstrip('：:').strip()
        seq = []
        if not title:  # 标题在第二段
            title = blocks[rest[0]]['text'].strip().rstrip('：:'); rest = rest[1:]
        tail = []
        tl = ptext(first_runs).strip()
        # 首段 = 标题；首段里冒号之后若还有内容（如“基因重组的4种情况：（1）…”）则放进正文
        mm = re.match(r'^([^：:]{1,30})[：:](.+)$', tl)
        if mm: title = mm.group(1).strip(); tail = [('p', strip_prefix(first_runs, len(ptext(first_runs)) - len(ptext(first_runs).lstrip()) + len(mm.group(1)) + 1))]
        imgs_in_first = [r for r in first_runs if 'img' in r]
        if imgs_in_first: tail.insert(0, ('p', imgs_in_first))
        for bi in rest:
            b = blocks[bi]
            if b['k'] == 'tbl': seq.append(('t', b)); continue
            t = b['text'].strip()
            if t.startswith('>'):
                seq.append(('p', [{'t': t.lstrip('> ').strip(), 'b': 1}])); continue
            seq.append(('p', b['runs']))
        body = re.sub(r'^<div>(?:<br>)+', '<div>', seq_html(tail + seq, 'note'))
        notes.append(dict(section=NOTES[iid], title=title, body=body, _id=iid))
        continue
    # ----- 特例 -----
    if iid == '1-5-1':
        stem = runs_html(first_runs, 'q'); ans = runs_html(blocks[rest[0]]['runs'], 'plain')
        parts = ans.split('；')
        segs = stem.split('______')
        h = segs[0] + ''.join(f'<u class="blank">{parts[i].strip()}</u>' + segs[i + 1] for i in range(len(segs) - 1))
        add_q(dict(_id=iid, type='填空题', stem=f'<div>{h}</div>', grade='高三', source=''), it, '原文“______”和下方答案已合并为挖空')
        continue
    if iid in ('1-5-6', '3-3-5'):  # 一个编号下两道不同来源的题
        body, ana, ext = split_ana(rest)
        second = [x for k, x in body if k == 'p' and SRC_RE.match(ptext(x).strip())][0]
        r1, s1 = take_sources(first_runs); r2, s2 = take_sources(second)
        for suf, (r, s) in zip('ab', [(r1, s1), (r2, s2)]):
            sub_it = dict(it, id=iid + suf)
            if iid == '1-5-6':
                q = dict(_id=iid + suf, type='填空题', stem=f'<div>{runs_html(r, "q")}</div>', source=s['source'], qno=s['qno'], adapted=s['adapted'], grade=s['grade'])
            else:
                t = ptext(r); m = JUDGE_RE.search(t)
                k = '✓' if m.group(1) in '✓✔√' else '×'
                q = dict(_id=iid + suf, type='判断题', stem='', judges=[dict(text=runs_html(replace_span(r, m.start(), m.end(), SLOT_TOKEN), 'q'), key=k, miss=False)],
                         analysis=seq_html(ana, 'ana'), source=s['source'], qno=s['qno'], adapted=s['adapted'], grade=s['grade'])
            add_q(q, sub_it, '原文同一编号下有两道不同来源的题，已拆成两道')
        continue
    if iid == '4-2-1':
        r, s = take_sources(first_runs)
        lead = ptext(r); m = KEY_RE.search(lead); r = replace_span(r, m.start(), m.end(), '')
        body, ana, ext = split_ana(rest); js = []
        for k2, x in body:
            om = OPT_RE.match(ptext(x)); c = color_of(x)
            js.append(dict(text=runs_html(strip_prefix(x, om.end()), 'q') + SLOT, key='✓' if c == 'r' else '×', miss=(c == 'b')))
        add_q(dict(_id=iid, type='判断题', stem=f'<div>{runs_html(r, "q").replace("下列叙述正确的是", "判断下列叙述：")}</div>', judges=js, analysis=seq_html(ana, 'ana'),
                   source=s['source'], qno=s['qno'], adapted=s['adapted'], grade=s['grade']), it, '原题只摘录了 A、D 两个选项，已改为“一题多判”：①为原 A（曾误选），②为原 D')
        continue
    if iid == '3-2-3':
        r, s = take_sources(first_runs); t = ptext(r)
        i = t.index('AB'); j = t.index('（填字母）') + len('（填字母）')
        r = replace_span(r, i, j, SLOT_TOKEN)
        r = [dict(x, u=None, color=None) if 't' in x else x for x in r]
        r = [{k: v for k, v in x.items() if v is not None} for x in r]
        q, rv = build_choice(it, rest, dict(s, multi=True), r)
        q['key'] = 'AB'; q['missed'] = True; q['type'] = '多选题'
        report[:] = [x for x in report if not (x[0] == 'nokey' and x[1] == iid)]
        add_q(q, it, '原题为“填字母”，已改为多选题；整题标记为曾做错')
        continue
    if iid == 'Z-0-2':
        r, s = take_sources(first_runs); t = ptext(r); m = KEY_RE.search(t)
        r = replace_span(r, m.start(), m.end(), SLOT_TOKEN)
        body, ana, ext = split_ana(rest)
        add_q(dict(_id=iid, type='单选题', stem=seq_html([('p', r)] + body, 'q'), options=['', '', '', ''], key=m.group(1),
                   analysis=seq_html(ana, 'ana'), source=s['source'], qno=s['qno'], adapted=s['adapted'], grade=s['grade']), it, '选项内容在表格中，选项处只保留了字母')
        continue
    # ----- 一般情况 -----
    runs, src = take_sources(first_runs)
    texts = [blocks[b]['text'] for b in rest]
    has_opts = sum(1 for t in texts if OPT_RE.match(t) and t.strip()) >= 2
    has_judge = bool(JUDGE_RE.search(ptext(runs))) or any(JUDGE_RE.search(t) for t in texts)
    has_blank = any(r.get('u') and r.get('color') in (RED, BLUE) for b in bl if blocks[b]['k'] == 'p' for r in blocks[b]['runs'])
    if iid in ANSWER_TYPE: q = build_answer(it, rest, src, runs); rv = None
    elif has_judge: q = build_judges(it, rest, src, runs); rv = None
    elif has_opts: q, rv = build_choice(it, rest, src, runs)
    elif has_blank: q = build_fill(it, rest, src, runs); rv = None
    else: report.append(('unknown', iid, alltext[:60])); continue
    if iid == '2-1-2': rv = '与本节下一题（2026镇江高三期初 T21）第(1)问内容相同'
    if src['source'].startswith('2016'): rv = (rv + '；' if rv else '') + '来源年份写的是 2016，可能是 2026，请确认'
    add_q(q, it, rv)

# 额外 tag
extra_tags = [{'section': s, 'name': n} for s, ns in EXTRA_TAGS.items() for n in ns]
out = dict(format='qbank-import', topics=['实验专题'], questions=[{k: v for k, v in q.items() if not k.startswith('_')} for q in questions],
           notes=[{k: v for k, v in n.items() if not k.startswith('_')} for n in notes], extraTags=extra_tags)
json.dump(out, open(sys.argv[5], 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(dict(questions=questions, notes=notes, report=report), open(sys.argv[6], 'w', encoding='utf-8'), ensure_ascii=False)
print(len(questions), 'questions', len(notes), 'notes')
from collections import Counter
print(Counter(q['type'] for q in questions))
for r in report: print('REPORT', r)
