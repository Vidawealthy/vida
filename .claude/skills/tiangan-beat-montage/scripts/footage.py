#!/usr/bin/env python3
"""Find and fetch watermark-free stock footage (Mixkit, Coverr).

  python3 footage.py search WORK_DIR mixkit flowers,cherry-blossom,lotus [--pages 2]
  python3 footage.py search WORK_DIR coverr "flower field,peony"
  python3 footage.py sheets WORK_DIR [--include "flower,blossom"] [--exclude "tree,forest"]  # numbered contact sheets
  python3 footage.py get WORK_DIR CLIPS_DIR k12440 k48889 c17 ...        # k = Mixkit id, c = Coverr index

The catalog lives in WORK_DIR/catalog.json, thumbnails in WORK_DIR/thumbs, sheets in WORK_DIR/sheets.
Look at every sheet yourself; names lie (a clip called "spring blossom" can be 80% tree trunk).
"""
import argparse, concurrent.futures as cf, json, os, re, subprocess, time
from PIL import Image, ImageDraw

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
PEOPLE = r'\b(woman|women|man|men|girl|boy|couple|people|person|city|car|office|kid|child|dog|cat|laptop|phone|street|' \
         r'traffic|beach|sea|ocean|wedding|food|cooking|dance|dancer|model|young|guy|lady|tourist|selfie|crowd|abstract|' \
         r'animation|3d|background|loop|particles|cartoon|shop|store|market|restaurant|kitchen|premium|user ai)\b'

def curl(url, out=None, t=30):
    args = ['curl', '-sfL', '-m', str(t), '-A', UA, url] + (['-o', out] if out else [])
    r = subprocess.run(args, capture_output=True, text=out is None)
    return r.stdout if out is None else r.returncode == 0

def page_html(url, tries=4):
    """Fetch a listing page. A 429/403 or Cloudflare challenge is a block, not an empty result:
    wait and retry instead of moving on (that bug once returned 0 results for 20 keywords)."""
    for k in range(tries):
        r = subprocess.run(['curl', '-sL', '-m', '30', '-A', UA, '-w', '\n%{http_code}', url], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        if code == '200' and 'Just a moment' not in body[:600]:
            return body
        wait = 60 * (k + 1)
        print(f'  blocked ({code}) on {url}, waiting {wait}s', flush=True); time.sleep(wait)
    print(f'  giving up on {url}'); return ''

def load(work):
    p = os.path.join(work, 'catalog.json')
    return json.load(open(p)) if os.path.exists(p) else {}

def save(work, cat):
    json.dump(cat, open(os.path.join(work, 'catalog.json'), 'w'), ensure_ascii=False, indent=0)

def search(a):
    os.makedirs(a.work, exist_ok=True); cat = load(a.work)
    if a.site == 'mixkit':
        for kw in a.terms.split(','):
            for p in range(1, a.pages + 1):
                h = page_html(f'https://mixkit.co/free-stock-video/{kw}/' + (f'?page={p}' if p > 1 else ''))
                n = 0
                for slug, i in re.findall(r'href="/free-stock-video/([a-z0-9-]+)-(\d+)/"', h):
                    k = 'k' + i
                    if k not in cat:
                        cat[k] = dict(site='mixkit', id=i, name=slug, term=kw,
                                      thumb=f'https://assets.mixkit.co/videos/{i}/{i}-thumb-720-0.jpg',
                                      page=f'https://mixkit.co/free-stock-video/{slug}-{i}/'); n += 1
                print(kw, 'page', p, 'new', n, flush=True); save(a.work, cat); time.sleep(6)
                if n == 0: break
    else:
        base = sum(1 for v in cat.values() if v['site'] == 'coverr')
        for q in a.terms.split(','):
            h = page_html('https://coverr.co/s?q=' + q.replace(' ', '%20'))
            n = 0
            for s in dict.fromkeys(re.findall(r'https://cdn\.coverr\.co/videos/([^/"]+)/', h)):
                if any(v.get('slug') == s for v in cat.values()): continue
                k = f'c{base}'; base += 1; n += 1
                cat[k] = dict(site='coverr', slug=s, name=s, term=q, thumb=f'https://cdn.coverr.co/videos/{s}/thumbnail?width=385',
                              page=f'https://coverr.co/videos/{s}')
            print(q, 'new', n, flush=True); save(a.work, cat); time.sleep(2)
    print('catalog size', len(cat))

def sheets(a):
    cat = load(a.work); td = os.path.join(a.work, 'thumbs'); sd = os.path.join(a.work, 'sheets')
    os.makedirs(td, exist_ok=True); os.makedirs(sd, exist_ok=True)
    bad = re.compile(PEOPLE + (r'|\b(' + '|'.join(a.exclude.split(',')) + r')\b' if a.exclude else ''))
    keys = [k for k, v in cat.items() if not bad.search(v['name'].replace('-', ' '))]
    if a.include:  # keep only names with one of these words (prefix match, e.g. "flower" hits "flowers")
        inc = re.compile(r'\b(' + '|'.join(a.include.split(',')) + r')')
        keys = [k for k in keys if inc.search(cat[k]['name'].replace('-', ' '))]
    def dl(k):
        p = os.path.join(td, k + '.jpg')
        return k if os.path.exists(p) or curl(cat[k]['thumb'], p, 20) else None
    with cf.ThreadPoolExecutor(8) as ex: keys = [k for k in ex.map(dl, keys) if k]
    W, H, C, R = 192, 108, 10, 7
    for s in range(0, len(keys), C * R):
        im = Image.new('RGB', (W * C, H * R)); dr = ImageDraw.Draw(im)
        for j, k in enumerate(keys[s:s + C * R]):
            try: t = Image.open(os.path.join(td, k + '.jpg')).convert('RGB').resize((W, H))
            except Exception: continue
            x, y = (j % C) * W, (j // C) * H; im.paste(t, (x, y))
            dr.rectangle([x, y, x + 50, y + 14], fill='black'); dr.text((x + 2, y + 1), k, fill='yellow')
        p = os.path.join(sd, f'sheet_{s // (C * R):02d}.jpg'); im.save(p, quality=82); print(p)
    print(len(keys), 'candidates after filtering')

def get(a):
    cat = load(a.work); os.makedirs(a.clips, exist_ok=True)
    def one(k):
        v = cat[k]; out = os.path.join(a.clips, k + '.mp4')
        if os.path.exists(out): return f'{k} cached'
        if v['site'] == 'mixkit':
            if v.get('direct'):  # newer items live under active_storage/.../<id>-video-<q>.mp4
                if not re.search(r'-(360|720|1080|2160)\.mp4$', v['direct']):  # opaque blob link
                    return f'{k} direct' if curl(v['direct'], out, 300) else f'{k} FAILED'
                for q in ('2160', '1080', '720'):
                    u = re.sub(r'-(360|720|1080|2160)\.mp4$', f'-{q}.mp4', v['direct'])
                    if curl(u, out, 300): return f'{k} {q}p'
            if not v.get('id'): return f'{k} FAILED'
            for q in ('2160', '1080', '720'):
                if curl(f'https://assets.mixkit.co/videos/{v["id"]}/{v["id"]}-{q}.mp4', out, 300): return f'{k} {q}p'
        elif curl(f'https://cdn.coverr.co/videos/{v["slug"]}/1080p.mp4', out, 300): return f'{k} 1080p'
        return f'{k} FAILED'
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(one, a.keys): print(r)

ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='cmd', required=True)
s = sp.add_parser('search'); s.add_argument('work'); s.add_argument('site', choices=['mixkit', 'coverr']); s.add_argument('terms'); s.add_argument('--pages', type=int, default=2)
s = sp.add_parser('sheets'); s.add_argument('work'); s.add_argument('--exclude', default=''); s.add_argument('--include', default='')
s = sp.add_parser('get'); s.add_argument('work'); s.add_argument('clips'); s.add_argument('keys', nargs='+')
a = ap.parse_args(); dict(search=search, sheets=sheets, get=get)[a.cmd](a)
