#!/usr/bin/env python3
"""Make a wget mirror deployable on Netlify, then report what still needs a human.

    fix_mirror.py MIRROR_DIR [--dry-run] [--noindex] [--old-domain DOMAIN ...]

1. Rebuild srcset attributes that wget --convert-links mangled (it miscounts
   offsets when a srcset spans several lines or contains &amp;).
2. Rename files whose names contain '?' or '#' (Netlify refuses to deploy them)
   and rewrite the references to them (wget writes those as %3F / %23).
   Also drop commas from file and folder names (a comma splits a srcset
   candidate in two) and rewrite the references.
3. --noindex: leave every page with exactly one
   <meta name="robots" content="noindex,nofollow" />.
4. Report leftovers for a human: .php names, extensionless files, links to the
   old domain, analytics, forms, remaining %3F/%23 references.

Tested on GNU Wget 1.19.4 mirrors. Needs Python 3.6+ and nothing else.
Afterwards run linkcheck.py, then `git add -A` (git records the renames).
"""
import argparse
import os
import re
import struct
from collections import defaultdict
from urllib.parse import unquote

TEXT_EXTS = {'.html', '.htm', '.css', '.js', '.xml', '.json', '.txt', '.svg', '.rss', '.atom'}
HTML_EXTS = {'.html', '.htm'}
ROBOTS_TAG = '<meta name="robots" content="noindex,nofollow" />'
ROBOTS_RX = re.compile(r'([ \t]*)(<meta\s[^>]*\bname\s*=\s*["\']robots["\'][^>]*>)[ \t]*(\r?\n)?', re.I)
HEAD_RX = re.compile(r'<head\b[^>]*>', re.I)
SRCSET_RX = re.compile(r'(\ssrcset\s*=\s*)(["\'])(.*?)\2', re.I | re.S)
DESCRIPTOR_RX = re.compile(r'^\d+(?:\.\d+)?[wx]$')
EXTERNAL_RX = re.compile(r'^(?:[a-z][a-z0-9+.-]*:|//)', re.I)
QNAME_RX = re.compile(r'^(.*?)[?#](.*)$')


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for f in sorted(files):
            yield os.path.join(d, f)


def sniff_ext(path):
    with open(path, 'rb') as f:
        head = f.read(16)
    if head[:3] == b'\xff\xd8\xff':
        return '.jpg'
    if head[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return '.gif'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return '.webp'
    return ''


def load_text(path):
    """Contents of a UTF-8 text file worth editing, else None (binary, image, other encoding)."""
    with open(path, 'rb') as f:
        data = f.read()
    if os.path.splitext(path)[1].lower() not in TEXT_EXTS and (b'\0' in data[:2048] or sniff_ext(path)):
        return None
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        print('  skipped (not UTF-8): %s' % path)
        return None


def image_width(path):
    """Pixel width from the file header (JPEG, PNG, GIF, WebP), or None."""
    with open(path, 'rb') as f:
        data = f.read()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>I', data[16:20])[0]
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return struct.unpack('<H', data[6:8])[0]
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        chunk = data[12:16]
        if chunk == b'VP8 ':
            return struct.unpack('<H', data[26:28])[0] & 0x3FFF
        if chunk == b'VP8L':
            return 1 + (((data[22] & 0x3F) << 8) | data[21])
        if chunk == b'VP8X':
            return 1 + int.from_bytes(data[24:27], 'little')
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker == 0xFF:
                i += 1
            elif marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
            elif 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                return struct.unpack('>H', data[i + 7:i + 9])[0]
            else:
                i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    return None


def width_hint(name):
    """Width named in a resized image's filename: Statamic v1 '-w350-', Glide '?w=350&'."""
    m = re.search(r'(?:^|[-_.?&=])w[-=_]?(\d{2,5})(?=[-_.&]|$)', name)
    return int(m.group(1)) if m else None


def local_path(root, base_dir, ref):
    ref = unquote(ref.replace('&amp;', '&')).split('#', 1)[0]
    base = root if ref.startswith('/') else base_dir
    return os.path.normpath(os.path.join(base, ref.lstrip('/')))


def srcset_ok(value, root, base_dir):
    for part in value.split(','):
        bits = part.split()
        if not bits:
            continue
        if len(bits) > 2 or (len(bits) == 2 and not DESCRIPTOR_RX.match(bits[1])):
            return False
        if not EXTERNAL_RX.match(bits[0]) and not os.path.isfile(local_path(root, base_dir, bits[0])):
            return False
    return True


def rebuild_srcset(value, root, base_dir):
    """Recover the URLs from a mangled srcset. wget writes each converted URL
    correctly but leaves tail characters of the original after it, so each URL
    is the shortest run of text, from a URL start, that names an existing file.
    Descriptors are unrecoverable, so widths come from the filename or the image."""
    s = value.strip()

    def file_end(start):
        m = re.compile(r'\s').search(s, start)
        stop = m.start() if m else len(s)
        for end in range(start + 1, stop + 1):
            if os.path.isfile(local_path(root, base_dir, s[start:end])):
                return end
        return None

    def urls_from(prefix):
        urls, pos = [], 0
        while True:
            start = s.find(prefix, pos)
            if start < 0:
                return urls
            end = file_end(start)
            if end is None:
                pos = start + 1
                continue
            if s[start:end] not in urls:
                urls.append(s[start:end])
            pos = end

    first = file_end(0)
    if first is None:
        return None
    # Every candidate starts with some leading part of the first URL. Usually that's
    # its whole folder ('../assets/img/cache/'), but some caches give each size its
    # own folder (Statamic 3+ Glide: 'img/http/<name>/<md5>/<name>'), so try each
    # folder level from the deepest up and keep whichever finds the most files.
    prefixes = [s[:i + 1] for i in range(first - 1, -1, -1) if s[i] == '/']
    if not prefixes:
        return None
    urls = max((urls_from(p) for p in prefixes), key=len)
    parts = []
    for url in urls:
        width = width_hint(os.path.basename(unquote(url.replace('&amp;', '&')))) \
            or image_width(local_path(root, base_dir, url))
        if not width:
            return None
        parts.append('%s %dw' % (url, width))
    return ', '.join(parts)


def plan_renames(root):
    """New names for files with '?' or '#' in them. A cache-buster query on a file
    that has its own extension is dropped ('Inter.woff2?v=3.19' -> 'Inter.woff2') if
    that's unambiguous; otherwise the query goes into the name, keeping a real
    extension last ('news?page=2.html' -> 'news-page-2.html', Glide
    'img?w=350&s=abc' -> 'img-w-350-s-abc.jpg'). A query on a page is content,
    not a cache-buster, so it always stays in the name."""
    plans = []
    for path in walk(root):
        d, name = os.path.split(path)
        m = QNAME_RX.match(name)
        if not m:
            continue
        base, query = m.groups()
        stem, own = os.path.splitext(base)
        added = ''  # extension wget --adjust-extension appended after the query
        for a in ('.html', '.css'):
            if query.lower().endswith(a):
                query, added = query[:-len(a)], a
                break
        ext = added or own or sniff_ext(path)
        slug = re.sub(r'[^A-Za-z0-9.]+', '-', query).strip('-.') or 'q'
        page = added == '.html' or own.lower() in ('.html', '.htm', '.php')
        stripped = base if own and not page and (not added or added == own.lower()) else None
        plans.append((d, name, stripped, stem + '-' + slug + ext))
    wanted = defaultdict(int)
    for d, _, stripped, _ in plans:
        if stripped:
            wanted[(d, stripped)] += 1
    renames, taken = [], set()
    for d, old, stripped, slugged in plans:
        ok = stripped and wanted[(d, stripped)] == 1 and not os.path.exists(os.path.join(d, stripped))
        new = stripped if ok else slugged
        s, e = os.path.splitext(new)
        n = 1
        while (d, new) in taken or os.path.exists(os.path.join(d, new)):
            n += 1
            new = '%s-%d%s' % (s, n, e)
        taken.add((d, new))
        renames.append((d, old, new))
    return renames


def plan_comma_renames(root):
    """{old name: new name} for every file or folder name containing a comma.
    Browsers split srcset candidates on commas, so such an image never loads
    from a srcset. 'image-may-22,-2026.png' -> 'image-may-22-2026.png'."""
    names = set()
    for d, dirs, files in os.walk(root):
        names.update(n for n in dirs + files if ',' in n)
    return {n: re.sub(r'-{2,}', '-', re.sub(r',\s*', '-', n)) for n in names}


def apply_comma_renames(root, table):
    for d, dirs, files in os.walk(root, topdown=False):
        for n in dirs + files:
            if n in table:
                os.rename(os.path.join(d, n), os.path.join(d, table[n]))


def rewrite_comma_refs(texts, table):
    count = 0
    for old in sorted(table, key=len, reverse=True):
        for form in (old, old.replace(',', '%2C'), old.replace(',', '%2c')):
            for p, t in texts.items():
                if form in t:
                    count += t.count(form)
                    texts[p] = t.replace(form, table[old])
    return count


def rewrite_refs(texts, renames):
    """Point references at the new names. wget writes '?' as %3F, '#' as %23,
    and HTML keeps '&' as &amp;."""
    table, conflicts = {}, set()
    for _, old, new in renames:
        enc = old.replace('?', '%3F').replace('#', '%23')
        for form in {enc, enc.replace('%3F', '%3f'), enc.replace('&', '&amp;')}:
            if table.get(form, new) != new:
                conflicts.add(old)
            table[form] = new
    if not table:
        return 0, conflicts
    alt = '|'.join(re.escape(f) for f in sorted(table, key=len, reverse=True))
    rx = re.compile(r'(?<![A-Za-z0-9_.~%-])(' + alt + r')(?=["\'\s),<>#]|$)')
    count = 0
    for path, text in texts.items():
        new_text, n = rx.subn(lambda m: table[m.group(1)], text)
        if n:
            texts[path] = new_text
            count += n
    return count, conflicts


def set_noindex(text):
    ms = list(ROBOTS_RX.finditer(text))
    if len(ms) == 1 and ms[0].group(2) == ROBOTS_TAG:
        return text
    if not ms:
        h = HEAD_RX.search(text)
        return text[:h.end()] + '\n' + ROBOTS_TAG + text[h.end():] if h else text
    out, last = [], 0
    for i, m in enumerate(ms):  # keep the first tag's position, drop the rest
        out.append(text[last:m.start()])
        if i == 0:
            out.append(m.group(1) + ROBOTS_TAG + (m.group(3) or ''))
        last = m.end()
    out.append(text[last:])
    return ''.join(out)


def files_matching(texts, root, rx):
    return sorted(os.path.relpath(p, root) for p, t in texts.items() if rx.search(t))


def report(root, texts, renames, old_domains):
    renamed_to = {os.path.join(d, new): old for d, old, new in renames}
    final = [p for p in walk(root) if not QNAME_RX.match(os.path.basename(p))] + list(renamed_to)
    print('\nNeeds a human:')
    checks = [
        ('files with .php in the name', sorted(os.path.relpath(p, root) for p in final if '.php' in os.path.basename(p).lower())),
        ('extensionless files (set a Content-Type header in netlify.toml)',
         sorted(os.path.relpath(p, root) for p in final if not os.path.splitext(os.path.basename(p))[1])),
        ('files still containing %3F/%23', files_matching(texts, root, re.compile(r'%3F|%23', re.I))),
        ('files with analytics tags', files_matching(texts, root, re.compile(
            r'googletagmanager\.com|google-analytics\.com|\bgtag\(|\bUA-\d{4,}-\d+|tinylytics\.app|plausible\.io'
            r'|usefathom\.com|simpleanalytics|matomo|clarity\.ms|hotjar\.com|connect\.facebook\.net', re.I))),
        ('files with <img> whose src is a page (an empty image field in the CMS)', files_matching(
            texts, root, re.compile(r'<img\b[^>]*\ssrc\s*=\s*["\'][^"\']*\.html?["\']', re.I))),
        ('files with HTML comments naming the environment, app URL or a commit', files_matching(
            texts, root, re.compile(r'<!--(?:(?!-->).)*?\b(?:environment|app_url|APP_ENV|commit)\b', re.I | re.S))),
        ('files with <form> (forms won\'t work on a static host)', files_matching(texts, root, re.compile(r'<form\b', re.I))),
    ]
    for domain in old_domains:
        rx = re.compile(r'https?://(?:www\.)?' + re.escape(domain) + r'\b', re.I)
        checks.append(('files linking to %s' % domain, files_matching(texts, root, rx)))
    for label, items in checks:
        print('  %-72s %d%s' % (label + ':', len(items), '  e.g. ' + ', '.join(items[:3]) if items else ''))
    hosts = defaultdict(int)
    for t in texts.values():
        for h in re.findall(r'<script[^>]+src=["\'](?:https?:)?//([^/"\']+)', t, re.I):
            hosts[h] += 1
    if hosts:
        print('  external script hosts: ' + ', '.join('%s (%d)' % kv for kv in sorted(hosts.items(), key=lambda kv: -kv[1])))
    frames = defaultdict(int)
    for t in texts.values():
        for h in re.findall(r'<iframe[^>]+src=["\'](?:https?:)?//([^/"\']+)', t, re.I):
            frames[h] += 1
    if frames:
        print('  external iframe hosts (embedded forms keep submitting to the real service): '
              + ', '.join('%s (%d)' % kv for kv in sorted(frames.items(), key=lambda kv: -kv[1])))


def main():
    ap = argparse.ArgumentParser(description='Make a wget mirror deployable on Netlify.')
    ap.add_argument('mirror', help='directory wget wrote (e.g. static/)')
    ap.add_argument('--dry-run', action='store_true', help='report what would change, write nothing')
    ap.add_argument('--noindex', action='store_true', help='make every page noindex,nofollow')
    ap.add_argument('--old-domain', action='append', default=[], help='report absolute links to this domain (repeatable)')
    args = ap.parse_args()
    root = os.path.abspath(args.mirror)

    texts = {}
    for p in walk(root):
        t = load_text(p)
        if t is not None:
            texts[p] = t
    original = dict(texts)

    # 1. srcset first, while files still have their wget names
    rebuilt, failed, dupes, singles = [0], [], [], []
    for p in texts:
        if os.path.splitext(p)[1].lower() not in HTML_EXTS:
            continue
        base_dir = os.path.dirname(p)

        def fix(m):
            if srcset_ok(m.group(3), root, base_dir):
                return m.group(0)
            new = rebuild_srcset(m.group(3), root, base_dir)
            if new is None:
                failed.append(os.path.relpath(p, root))
                return m.group(0)
            rebuilt[0] += 1
            widths = re.findall(r'\s(\d+)w(?=,|$)', new)
            if len(set(widths)) < len(widths):
                dupes.append(os.path.relpath(p, root))
            if len(widths) == 1:
                singles.append(os.path.relpath(p, root))
            return m.group(1) + m.group(2) + new + m.group(2)
        texts[p] = SRCSET_RX.sub(fix, texts[p])
    print('srcset: %d rebuilt, %d left for a human%s' % (
        rebuilt[0], len(failed), ('  e.g. ' + ', '.join(sorted(set(failed))[:3])) if failed else ''))
    if singles:
        print('  WARNING: %d rebuilt srcsets have a single candidate. Compare a few with the live page:'
              ' a srcset that lost its other sizes leaves small, blurry images. e.g. %s' % (
                  len(singles), ', '.join(sorted(set(singles))[:3])))
    if dupes:
        print('  %d rebuilt srcsets repeat a width (same-size images): check e.g. %s' % (
            len(dupes), ', '.join(sorted(set(dupes))[:3])))

    # 2. renames
    renames = plan_renames(root)
    nrefs, conflicts = rewrite_refs(texts, renames)
    print('renamed: %d files with ?/# in the name, %d references rewritten' % (len(renames), nrefs))
    for d, old, new in renames[:8]:
        print('  %s -> %s' % (os.path.relpath(os.path.join(d, old), root), new))
    if len(renames) > 8:
        print('  ... and %d more' % (len(renames) - 8))
    if conflicts:
        print('  WARNING: same name renamed differently in different folders, check refs: %s' % ', '.join(sorted(conflicts)[:5]))

    commas = plan_comma_renames(root)
    ncomma = rewrite_comma_refs(texts, commas)
    print('renamed: %d file/folder names with commas, %d references rewritten' % (len(commas), ncomma))
    for old in sorted(commas)[:5]:
        print('  %s -> %s' % (old, commas[old]))

    # 3. robots
    if args.noindex:
        n = 0
        for p in texts:
            if os.path.splitext(p)[1].lower() in HTML_EXTS:
                new = set_noindex(texts[p])
                n += new != texts[p]
                texts[p] = new
        print('robots: %d pages changed to a single noindex,nofollow tag' % n)

    report(root, texts, renames, args.old_domain)

    if args.dry_run:
        print('\n(dry run: nothing written)')
        return
    changed = 0
    for p, t in texts.items():
        if t != original[p]:
            with open(p, 'w', encoding='utf-8', newline='') as f:
                f.write(t)
            changed += 1
    for d, old, new in renames:
        os.rename(os.path.join(d, old), os.path.join(d, new))
    apply_comma_renames(root, commas)
    print('\nwrote %d files, renamed %d. Next: linkcheck.py %s' % (changed, len(renames) + len(commas), args.mirror))


if __name__ == '__main__':
    main()
