#!/usr/bin/env python3
"""Make a static mirror's HTML readable in view-source and drop what it doesn't need.

    tidy_html.py MIRROR_DIR [--dry-run] [--old-domain DOMAIN ...] [--wordpress]
                 [--drop REGEX ...] [--drop-unless REGEX BODY_REGEX ...]
                 [--inline-list CLASS ...] [--prune]

Run after fix_mirror.py, on a copy if the mirror is being served. Safe to run again.

--old-domain     Point absolute URLs on this domain at local files, where the file
                 exists. wget leaves these in attributes it doesn't convert, such as
                 the data-src and data-srcset of lazy-loaded images.
--wordpress      Remove WordPress's unused head tags and inline CSS (see WP_* below),
                 undo Jetpack Boost's critical CSS, and cut global-styles down to the
                 site's own custom CSS, plus the flex rules on block gallery pages.
--drop           Remove every script, stylesheet link and style block whose attributes
                 or content match REGEX. Base64 data: scripts are decoded first.
--drop-unless    The same, but only on pages whose <body> doesn't match BODY_REGEX.
--inline-list    Keep this <ul>'s items on one line. A line break between inline items
                 shows as a space.
--prune          Delete CSS and JS files nothing references any more.

Always puts tags on their own lines, adding breaks only around block elements and head
tags, never inside scripts, styles or comments. Removing scripts and styles can change
how pages look, so compare them before and after. Needs Python 3.6+ and nothing else.
"""
import argparse
import base64
import os
import re
from urllib.parse import unquote

WP_STYLE_IDS = re.compile(
    r"id=['\"](?:jetpack-sharing-buttons-style-inline-css|wp-emoji-styles-inline-css"
    r"|classic-theme-styles-inline-css|jetpack-boost-critical-css)['\"]")
WP_EMPTY_STYLE = re.compile(r'^\s*(?:img#wpstats\{display:none\})?\s*$')
WP_LINK_RELS = re.compile(r"rel=['\"](?:pingback|EditURI|shortlink|alternate|https://api\.w\.org/)['\"]")
BOOST_SWAP = re.compile(r'media="not all" data-media="all" onload="[^"]*"')
UNUSED_GLOBAL_RULE = re.compile(
    r':root\s*$|\.has-|is-layout-grid|wp-block-columns|wp-block-post-template|wp-block-pullquote')

RAW = re.compile(r'(<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>)', re.S)
CONTAINER = 'html|head|body|div|header|footer|nav|main|article|section|aside|ul|ol|figure|form'
LEAF = 'title|meta|link|li|h[1-6]|p|figcaption|hr'  # the closing tag stays on the text's line
LINE_START = re.compile(r'\s*(</(?:%s)\b[^>]*>|<(?:%s|%s)\b[^>]*>)' % (CONTAINER, CONTAINER, LEAF))
SCRIPT = re.compile(r'<script\b([^>]*)>(.*?)</script>', re.S)
STYLE = re.compile(r'<style\b([^>]*)>(.*?)</style>', re.S)
STYLESHEET = re.compile(r"<link\b[^>]*rel=['\"]stylesheet['\"][^>]*>")


def walk(root):
    for d, dirs, names in os.walk(root):
        dirs.sort()
        for n in sorted(names):
            yield os.path.relpath(os.path.join(d, n), root).replace(os.sep, '/')


def decoded(attrs):
    m = re.search(r'''\bsrc=["']data:text/javascript;base64,([^"']*)''', attrs)
    return base64.b64decode(m.group(1)).decode('utf-8', 'replace') if m else ''


def drop_elements(t, rx):
    """Remove scripts, stylesheet links and style blocks matching rx."""
    t = SCRIPT.sub(lambda m: '' if rx.search(m.group(1)) or rx.search(m.group(2)) or rx.search(decoded(m.group(1))) else m.group(0), t)
    t = STYLE.sub(lambda m: '' if rx.search(m.group(1)) or rx.search(m.group(2)) else m.group(0), t)
    return STYLESHEET.sub(lambda m: '' if rx.search(m.group(0)) else m.group(0), t)


def localise(t, page, root, domain):
    """Absolute URLs on the old domain become relative, if the file is in the mirror."""
    url = r'https?://(?:www\.)?' + re.escape(domain) + r'''(/(?:[^"'\s,<>()]|\([^"'\s,<>()]*\))*)'''

    def fix(m):
        path = unquote(m.group(1)).split('?', 1)[0].split('#', 1)[0].lstrip('/')
        if not path or not os.path.isfile(os.path.join(root, path)):
            return m.group(0)
        target = m.group(1).split('?', 1)[0].split('#', 1)[0].lstrip('/')
        return os.path.relpath(target, os.path.dirname(page) or '.').replace(os.sep, '/')

    return re.sub(url, fix, t)


def trim_global_styles(css, has_block_gallery):
    keep = []
    for rule in re.findall(r'[^{}]+\{[^{}]*\}', re.sub(r'/\*.*?\*/', '', css, flags=re.S)):
        rule = rule.strip()
        selector = rule.split('{', 1)[0]
        if UNUSED_GLOBAL_RULE.search(selector) or ('is-layout-flex' in selector and not has_block_gallery):
            continue
        if rule not in keep:
            keep.append(rule)
    return '\n'.join(keep)


def clean_wordpress(t):
    has_block_gallery = 'wp-block-gallery' in t[t.find('<body'):]

    def style(m):
        if WP_STYLE_IDS.search(m.group(1)) or WP_EMPTY_STYLE.match(m.group(2)):
            return ''
        if 'global-styles-inline-css' in m.group(1):
            return '<style id="site-custom-css">\n%s\n</style>' % trim_global_styles(m.group(2), has_block_gallery)
        return m.group(0)

    t = STYLE.sub(style, t)
    t = re.sub(r"<noscript>\s*<link rel='stylesheet'[^>]*>\s*</noscript>", '', t)
    t = BOOST_SWAP.sub("media='all'", t)
    t = SCRIPT.sub(lambda m: '' if 'jetpack-boost-critical-css' in decoded(m.group(1)) else m.group(0), t)
    t = re.sub(r'<link\b[^>]*>', lambda m: '' if WP_LINK_RELS.search(m.group(0)) else m.group(0), t)
    t = re.sub(r'<meta\s+name="generator"[^>]*>', '', t)
    return re.sub(r'\s*<!-- Page cached by [^>]*-->', '', t)


def add_line_breaks(t, inline_lists):
    # Internet Explorer's conditional comments are dead code, and hide the html tag.
    t = re.sub(r'^(<!DOCTYPE html>)\s*<!--\[if .*?<html\b([^>]*)>\s*<!--<!\[endif\]-->', r'\1\n<html\2>', t, count=1, flags=re.S | re.I)
    out = []
    for i, part in enumerate(RAW.split(t)):
        if i % 2:
            if not part.startswith('<!--'):
                out[-1] = out[-1].rstrip() + '\n'
            out.append(part)
        else:
            out.append(LINE_START.sub(lambda m: '\n' + m.group(1), part))
    t = ''.join(out)
    head_end = t.find('</head>')
    if head_end > 0:
        t = re.sub(r'\s*(<noscript\b|</noscript>)', r'\n\1', t[:head_end]) + t[head_end:]
    t = re.sub(r'[ \t]*\n\s*', '\n', t).strip() + '\n'
    for name in inline_lists:
        t = re.sub(r'<ul\b[^>]*class="[^"]*\b%s\b[^"]*"[^>]*>.*?</ul>' % re.escape(name),
                   lambda m: m.group(0).replace('</li>\n<li', '</li><li'), t, flags=re.S)
    return t


def referenced_assets(root, files):
    """Every local CSS or JS file a page or stylesheet references."""
    used = set()
    todo = [f for f in files if f.endswith(('.html', '.htm'))]
    seen = set(todo)
    while todo:
        rel = todo.pop()
        with open(os.path.join(root, rel), encoding='utf-8', errors='replace') as f:
            text = f.read()
        refs = re.findall(r'''(?:href|src)=["']([^"'?#]+\.(?:css|js))(?:[?#][^"']*)?["']''', text)
        refs += re.findall(r'''@import\s+(?:url\()?["']?([^"')\s;?#]+\.css)''', text)
        for ref in refs:
            if ref.startswith(('http:', 'https:', '//', 'data:')):
                continue
            base = root if ref.startswith('/') else os.path.join(root, os.path.dirname(rel))
            full = os.path.normpath(os.path.join(base, unquote(ref).lstrip('/')))
            target = os.path.relpath(full, root).replace(os.sep, '/')
            used.add(target)
            if target.endswith('.css') and target not in seen and os.path.isfile(full):
                seen.add(target)
                todo.append(target)
    return used


def main():
    ap = argparse.ArgumentParser(description="Tidy a static mirror's HTML.")
    ap.add_argument('mirror')
    ap.add_argument('--dry-run', action='store_true', help='report what would change, write nothing')
    ap.add_argument('--old-domain', action='append', default=[], help='localise URLs on this domain (repeatable)')
    ap.add_argument('--wordpress', action='store_true', help="remove WordPress's unused head tags and inline CSS")
    ap.add_argument('--drop', action='append', default=[], metavar='REGEX', help='remove matching scripts and CSS (repeatable)')
    ap.add_argument('--drop-unless', action='append', nargs=2, default=[], metavar=('REGEX', 'BODY_REGEX'),
                    help="the same, on pages whose <body> doesn't match BODY_REGEX (repeatable)")
    ap.add_argument('--inline-list', action='append', default=[], metavar='CLASS', help="keep this <ul>'s items on one line (repeatable)")
    ap.add_argument('--prune', action='store_true', help='delete CSS and JS nothing references')
    args = ap.parse_args()
    root = os.path.abspath(args.mirror)
    drops = [re.compile(r) for r in args.drop]
    conditional = [(re.compile(a), re.compile(b)) for a, b in args.drop_unless]

    pages = [f for f in walk(root) if f.endswith(('.html', '.htm'))]
    before = after = 0
    for rel in pages:
        path = os.path.join(root, rel)
        with open(path, encoding='utf-8', newline='') as f:
            t = f.read()
        new = t
        for domain in args.old_domain:
            new = localise(new, rel, root, domain)
        if args.wordpress:
            new = clean_wordpress(new)
        for rx in drops:
            new = drop_elements(new, rx)
        body = new[new.find('<body'):]
        for rx, needed in conditional:
            if not needed.search(body):
                new = drop_elements(new, rx)
        new = add_line_breaks(new, args.inline_list)
        before += len(t)
        after += len(new)
        if new != t and not args.dry_run:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(new)

    unused = []
    if args.prune:
        files = list(walk(root))
        used = referenced_assets(root, files)
        unused = [f for f in files if f.endswith(('.css', '.js')) and f not in used]
        if not args.dry_run:
            for f in unused:
                os.remove(os.path.join(root, f))
            for d, _, _ in os.walk(root, topdown=False):
                if d != root and not os.listdir(d):
                    os.rmdir(d)
    print('%d pages tidied, %d KB of HTML removed, %d unused CSS/JS%s' % (
        len(pages), (before - after) // 1024, len(unused), ' (dry run: nothing written)' if args.dry_run else ' deleted'))
    for f in unused:
        print('  unused: ' + f)


if __name__ == '__main__':
    main()
