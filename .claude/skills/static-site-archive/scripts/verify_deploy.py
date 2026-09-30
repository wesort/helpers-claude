#!/usr/bin/env python3
"""Check a deployed static mirror against the local copy (and the live CMS site).

    verify_deploy.py MIRROR_DIR DEPLOY_URL [--live LIVE_URL] [--indexable] [--jobs N]

  1. Fetches every file in MIRROR_DIR from DEPLOY_URL. Each must return 200, and
     each non-HTML file must be byte-identical (Netlify rewrites HTML, so HTML is only
     status-checked).
  2. Checks every page's X-Robots-Tag header and robots meta tag for noindex
     (skipped with --indexable, for a site that should stay in search engines).
  3. Checks every srcset candidate on the deployed pages: it must load, and its
     width descriptor must equal the image's real pixel width (JPEG/PNG/GIF/WebP).
  4. With --live, compares each page's visible text with the live CMS page.
  5. Checks that unknown URLs and CMS internals (/site/users/, /index.php, …)
     return 404, and reports any HTML Netlify injects.

Exits 1 on any failure. Python 3.6+, no dependencies.
"""
import argparse
import concurrent.futures as cf
import html
import os
import re
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request

SRCSET_RX = re.compile(r'\ssrcset\s*=\s*(["\'])(.*?)\1', re.I | re.S)
ROBOTS_RX = re.compile(r'<meta[^>]+name=["\']robots["\'][^>]*>', re.I)
INJECT_RX = re.compile(r'hosting-provider|/\.netlify/scripts/|netlify\.new', re.I)
# Netlify varies its HTML by request headers (it injects only for Accept: text/html):
# request as a browser to see what visitors get
BROWSER_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
MUST_404 = ['/this-page-does-not-exist', '/index.php', '/cp', '/login',
            '/site/users/', '/site/settings/routes.yaml', '/.env', '/_config/users/']


def fetch(url, max_bytes=None):
    headers = {'User-Agent': BROWSER_UA, 'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8'}
    if max_bytes:
        headers['Range'] = 'bytes=0-%d' % (max_bytes - 1)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, dict((k.lower(), v) for k, v in r.getheaders()), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict((k.lower(), v) for k, v in e.headers.items()), b''
    except Exception as e:  # network error: report as status 0
        return 0, {'error': str(e)}, b''


def image_width(b):
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>I', b[16:20])[0]
    if b[:6] in (b'GIF87a', b'GIF89a'):
        return struct.unpack('<H', b[6:8])[0]
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
        if b[12:16] == b'VP8X':
            return 1 + int.from_bytes(b[24:27], 'little')
        if b[12:16] == b'VP8L':
            return 1 + (struct.unpack('<I', b[21:25])[0] & 0x3FFF)
        return struct.unpack('<H', b[26:28])[0] & 0x3FFF
    i = 2
    while i < len(b) - 9:  # JPEG: walk markers to the SOF
        if b[i] != 0xFF:
            i += 1
            continue
        marker = b[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            return struct.unpack('>H', b[i + 7:i + 9])[0]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + struct.unpack('>H', b[i + 2:i + 4])[0]
    return None


def visible_text(b):
    h = b.decode('utf-8', 'replace')
    h = re.sub(r'(?is)<(script|style|svg|head)\b.*?</\1>', ' ', h)
    h = html.unescape(re.sub(r'<[^>]+>', ' ', h))
    return ' '.join(h.split())


def page_path(rel):
    """index.html -> /, about/team.html -> /about/team"""
    p = '/' + rel[:-len('.html')]
    return p[:-len('index')] if p.endswith('/index') else p


def main():
    ap = argparse.ArgumentParser(description='Verify a deployed static mirror.')
    ap.add_argument('mirror')
    ap.add_argument('deploy_url')
    ap.add_argument('--live', help='live CMS site to compare page text with')
    ap.add_argument('--indexable', action='store_true', help="the site should be indexed: don't require noindex")
    ap.add_argument('--jobs', type=int, default=16)
    args = ap.parse_args()
    root = os.path.abspath(args.mirror)
    base = args.deploy_url.rstrip('/')
    fails = 0

    files = sorted(os.path.relpath(os.path.join(d, n), root).replace(os.sep, '/')
                   for d, _, names in os.walk(root) for n in names)
    pages = [f for f in files if f.endswith('.html') and f != '404.html']

    # 1. every file
    def check_file(rel):
        status, hdrs, body = fetch(base + '/' + urllib.parse.quote(rel))
        if status != 200:
            return rel, 'status %s' % status
        if not rel.endswith('.html'):
            with open(os.path.join(root, rel), 'rb') as f:
                if f.read() != body:
                    return rel, 'content differs (%d bytes deployed)' % len(body)
        return rel, None

    with cf.ThreadPoolExecutor(args.jobs) as ex:
        bad = [(r, e) for r, e in ex.map(check_file, files) if e]
    print('files: %d fetched, %d problems' % (len(files), len(bad)))
    for r, e in bad[:30]:
        print('  %s: %s' % (r, e))
    fails += len(bad)

    # 2-4. pages
    def check_page(rel):
        path = page_path(rel)
        status, hdrs, body = fetch(base + path)
        live = fetch(args.live.rstrip('/') + path) if args.live else None
        return rel, path, status, hdrs, body, live

    with cf.ThreadPoolExecutor(min(args.jobs, 8)) as ex:
        results = list(ex.map(check_page, pages))

    candidates, injected, text_diffs, robots_bad = {}, 0, [], []
    for rel, path, status, hdrs, body, live in results:
        if status != 200:
            robots_bad.append('%s: status %s' % (path, status))
            continue
        text = body.decode('utf-8', 'replace')
        metas = ROBOTS_RX.findall(text)
        if not args.indexable and ('noindex' not in hdrs.get('x-robots-tag', '').lower() or len(metas) != 1
                                   or 'noindex' not in metas[0].lower()):
            robots_bad.append('%s: header=%r metas=%d' % (path, hdrs.get('x-robots-tag'), len(metas)))
        if INJECT_RX.search(text):
            injected += 1
        for m in SRCSET_RX.finditer(text):
            for part in m.group(2).split(','):
                bits = part.split()
                if len(bits) == 2 and bits[1].endswith('w'):
                    candidates[urllib.parse.urljoin(base + path, bits[0])] = int(bits[1][:-1])
        if live is not None:
            a, b = visible_text(body), visible_text(live[2])
            if a != b:
                i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
                text_diffs.append('%s (live status %s)\n    deployed: …%s…\n    live:     …%s…'
                                  % (path, live[0], a[max(0, i - 50):i + 70], b[max(0, i - 50):i + 70]))

    print('pages: %d checked, %d %s problems' % (len(results), len(robots_bad), 'status' if args.indexable else 'noindex'))
    for r in robots_bad[:20]:
        print('  ' + r)
    fails += len(robots_bad)
    if args.live and all(live[0] == 0 for *_, live in results):
        print('text vs live: SKIPPED, live site unreachable (%s). Compare before the DNS swap.'
              % results[0][5][1].get('error') if results else '')
    elif args.live:
        print('text vs live: %d identical, %d differ (drafts or pages removed from the CMS differ as expected)'
              % (len(results) - len(text_diffs), len(text_diffs)))
        for d in text_diffs[:20]:
            print('  ' + d)

    def check_candidate(item):
        url, w = item
        status, _, body = fetch(url, 65536)
        return url, w, status, image_width(body) if status in (200, 206) else None

    with cf.ThreadPoolExecutor(args.jobs) as ex:
        bad = [c for c in ex.map(check_candidate, candidates.items()) if c[2] not in (200, 206) or c[3] != c[1]]
    print('srcset: %d candidates, %d problems' % (len(candidates), len(bad)))
    for url, w, status, real in bad[:20]:
        print('  status %s, descriptor %dw, real %s: %s' % (status, w, real, url))
    fails += len(bad)

    # 5. 404s
    wrong = []
    for path in MUST_404:
        status, _, _ = fetch(base + path)
        if status != 404:
            wrong.append('%s -> %s' % (path, status))
    print('must-404 URLs: %d checked, %d wrong' % (len(MUST_404), len(wrong)))
    for w in wrong:
        print('  ' + w)
    fails += len(wrong)
    if injected:
        print('note: Netlify injected HTML into %d pages (always on *.netlify.app; on a custom domain it varies by site, check the Netlify site settings)'
              % injected)

    print('OK' if not fails else 'FAILED: %d problems' % fails)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
