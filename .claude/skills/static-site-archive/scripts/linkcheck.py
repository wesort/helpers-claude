#!/usr/bin/env python3
"""Check that every local reference in a static mirror resolves to a file.

    linkcheck.py MIRROR_DIR [--show N]

Scans href/src/poster/data-src/srcset in HTML, and url() in CSS files, <style>
blocks and style="" attributes. Exits 1 if any reference is missing, or points
at a file whose name contains '?' or '#' (fine locally, but Netlify won't
deploy it). Things only JavaScript or feeds reference aren't checked: test
those by hand.
"""
import argparse
import os
import re
import sys
from collections import defaultdict
from urllib.parse import unquote

ATTR_RX = re.compile(r'\s(?:href|src|poster|data-src)\s*=\s*(["\'])(.*?)\1', re.I | re.S)
SRCSET_RX = re.compile(r'\ssrcset\s*=\s*(["\'])(.*?)\1', re.I | re.S)
CSSURL_RX = re.compile(r'url\(\s*(["\']?)([^"\')]+?)\1\s*\)')
SKIP_RX = re.compile(r'^(?:[a-z][a-z0-9+.-]*:|//|#|\{)', re.I)  # scheme:, //host, #fragment, {template}


def refs(path, text):
    if os.path.splitext(path)[1].lower() in ('.html', '.htm'):
        for m in ATTR_RX.finditer(text):
            yield m.group(2)
        for m in SRCSET_RX.finditer(text):
            for part in m.group(2).split(','):
                bits = part.split()
                if bits:
                    yield bits[0]
    for m in CSSURL_RX.finditer(text):
        yield m.group(2)


def main():
    ap = argparse.ArgumentParser(description='Check local references in a static mirror.')
    ap.add_argument('mirror')
    ap.add_argument('--show', type=int, default=20, help='how many problems to list (default 20)')
    args = ap.parse_args()
    root = os.path.abspath(args.mirror)

    missing, qnamed = defaultdict(set), defaultdict(set)
    checked = files = 0
    for d, _, names in os.walk(root):
        for name in names:
            p = os.path.join(d, name)
            if os.path.splitext(p)[1].lower() not in ('.html', '.htm', '.css'):
                continue
            files += 1
            with open(p, encoding='utf-8', errors='replace') as f:
                text = f.read()
            for ref in refs(p, text):
                ref = ref.strip().replace('&amp;', '&')
                if not ref or SKIP_RX.match(ref):
                    continue
                # a real ?query is ignored by static hosts; a '?' in a filename is written %3F
                path = unquote(ref.split('#', 1)[0].split('?', 1)[0])
                if not path:
                    continue
                checked += 1
                full = os.path.normpath(os.path.join(root if path.startswith('/') else d, path.lstrip('/')))
                if os.path.isdir(full):
                    full = os.path.join(full, 'index.html')
                rel = os.path.relpath(full, root)
                if not os.path.isfile(full):
                    missing[rel].add(os.path.relpath(p, root))
                elif re.search(r'[?#]', rel):
                    qnamed[rel].add(os.path.relpath(p, root))

    print('%d local references checked in %d HTML/CSS files' % (checked, files))
    for label, found in (('missing targets', missing), ('targets with ?/# in the name (Netlify rejects)', qnamed)):
        print('%s: %d' % (label, len(found)))
        for target in sorted(found)[:args.show]:
            pages = sorted(found[target])
            more = ' (+%d more)' % (len(pages) - 1) if len(pages) > 1 else ''
            print('  %s  <- %s%s' % (target, pages[0], more))
    sys.exit(1 if missing or qnamed else 0)


if __name__ == '__main__':
    main()
