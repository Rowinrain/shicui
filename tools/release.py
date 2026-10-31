#!/usr/bin/env python3
"""生成 latest.json（程序内“检查更新”读取它）。

发布新版的步骤：
1. 在 拾萃.html 里把 PROGRAM_VERSION 改大（如 3.1.0 → 3.2.0）。
2. 在 更新记录.md 顶部写上 “## v3.2.0” 和本次更新内容。
3. 运行 python3 tools/release.py，提交 拾萃.html、更新记录.md、latest.json，合并到 main 分支即发布。

python3 tools/release.py --check 只检查 latest.json 是否和 拾萃.html 一致（GitHub 上的自动检查用它）。
"""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / '拾萃.html'
NOTES = ROOT / '更新记录.md'
LATEST = ROOT / 'latest.json'


def build():
    data = HTML.read_bytes()
    m = re.search(r"const PROGRAM_VERSION='([\d.]+)'", data.decode('utf-8'))
    if not m:
        sys.exit('拾萃.html 里找不到 PROGRAM_VERSION')
    ver = m.group(1)
    notes = NOTES.read_text(encoding='utf-8')
    sec = re.search(r'^## v' + re.escape(ver) + r'\s*\n(.*?)(?=^## |\Z)', notes, re.S | re.M)
    if not sec:
        sys.exit('更新记录.md 里没有 “## v%s” 这一节，请先写上本次更新内容' % ver)
    return {
        'format': 'shicui-latest',
        'version': ver,
        'file': '拾萃.html',
        'size': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'notes': sec.group(1).strip(),
    }


def main():
    info = build()
    old = json.loads(LATEST.read_text(encoding='utf-8')) if LATEST.exists() else {}
    if '--check' in sys.argv:
        keys = ('version', 'size', 'sha256', 'notes')
        bad = [k for k in keys if old.get(k) != info[k]]
        if bad:
            sys.exit('latest.json 和 拾萃.html / 更新记录.md 不一致（%s）。请运行 python3 tools/release.py 后提交。' % '、'.join(bad))
        print('latest.json 正确：v%s' % info['version'])
        return
    same = old.get('version') == info['version'] and old.get('sha256') == info['sha256']
    info['date'] = old.get('date') if same and old.get('date') else datetime.date.today().isoformat()
    out = {k: info[k] for k in ('format', 'version', 'date', 'file', 'size', 'sha256', 'notes')}
    LATEST.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('已写入 latest.json：v%s  sha256 %s' % (info['version'], info['sha256'][:12]))


if __name__ == '__main__':
    main()
