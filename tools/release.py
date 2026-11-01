#!/usr/bin/env python3
"""生成 latest.json（程序内“检查更新”读取它）。

发布新版的步骤：
1. 在 拾萃.html 里把 PROGRAM_VERSION 改大：小功能改后两位（如 2.7.0 → 2.8.0 或 2.7.1），重大更新才改第一位（如 3.0.0）。
2. 在 更新记录.md 顶部写上 “## v2.8.0” 和本次更新内容。
3. 运行 python3 tools/release.py，提交 拾萃.html、更新记录.md、latest.json，合并到 main 分支即发布。

版本号兼容：v2.6.0 以前的程序当时编号为 3.1.0–3.6.0，它们的更新程序读 latest.json 的 version
并核对下载文件里第一个 const PROGRAM_VERSION='…'。所以 latest.json 的 version 和 拾萃.html 里
“兼容旧版更新：const PROGRAM_VERSION='…'”注释都写旧编号（第一位数字加 1，如 2.7.0 → 3.7.0），
真正的版本号写在 release 字段。本脚本会自动改好那行注释。

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


LEGACY = re.compile(r"(兼容旧版更新：const PROGRAM_VERSION=')([\d.]+)(')")


def legacy_of(ver):
    major, _, rest = ver.partition('.')
    return str(int(major) + 1) + ('.' + rest if rest else '')


def fix_legacy(check):
    """把 拾萃.html 里给旧版更新程序看的版本号改成和 PROGRAM_VERSION 对应的旧编号。"""
    text = HTML.read_text(encoding='utf-8')
    m = re.search(r"^const PROGRAM_VERSION='([\d.]+)'", text, re.M)
    if not m:
        sys.exit('拾萃.html 里找不到 PROGRAM_VERSION')
    old = LEGACY.search(text)
    if not old or old.start() > m.start():
        sys.exit('拾萃.html 里 PROGRAM_VERSION 前面缺少“兼容旧版更新：const PROGRAM_VERSION=\'…\'”注释')
    want = legacy_of(m.group(1))
    if old.group(2) != want:
        if check:
            sys.exit('拾萃.html 里兼容旧版的版本号应为 %s。请运行 python3 tools/release.py 后提交。' % want)
        HTML.write_text(LEGACY.sub(lambda x: x.group(1) + want + x.group(3), text, count=1), encoding='utf-8')
        print('已把兼容旧版的版本号改为 %s' % want)


def build():
    data = HTML.read_bytes()
    m = re.search(r"^const PROGRAM_VERSION='([\d.]+)'", data.decode('utf-8'), re.M)
    if not m:
        sys.exit('拾萃.html 里找不到 PROGRAM_VERSION')
    ver = m.group(1)
    notes = NOTES.read_text(encoding='utf-8')
    sec = re.search(r'^## v' + re.escape(ver) + r'\s*\n(.*?)(?=^## |\Z)', notes, re.S | re.M)
    if not sec:
        sys.exit('更新记录.md 里没有 “## v%s” 这一节，请先写上本次更新内容' % ver)
    return {
        'format': 'shicui-latest',
        'version': legacy_of(ver),
        'release': ver,
        'file': '拾萃.html',
        'size': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'notes': sec.group(1).strip(),
    }


def main():
    fix_legacy('--check' in sys.argv)
    info = build()
    old = json.loads(LATEST.read_text(encoding='utf-8')) if LATEST.exists() else {}
    if '--check' in sys.argv:
        keys = ('version', 'release', 'size', 'sha256', 'notes')
        bad = [k for k in keys if old.get(k) != info[k]]
        if bad:
            sys.exit('latest.json 和 拾萃.html / 更新记录.md 不一致（%s）。请运行 python3 tools/release.py 后提交。' % '、'.join(bad))
        print('latest.json 正确：v%s' % info['release'])
        return
    same = old.get('release') == info['release'] and old.get('sha256') == info['sha256']
    info['date'] = old.get('date') if same and old.get('date') else datetime.date.today().isoformat()
    out = {k: info[k] for k in ('format', 'version', 'release', 'date', 'file', 'size', 'sha256', 'notes')}
    LATEST.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('已写入 latest.json：v%s（给旧版程序看的编号 %s）  sha256 %s' % (info['release'], info['version'], info['sha256'][:12]))


if __name__ == '__main__':
    main()
