---
name: static-site-archive
description: Turn a site into a static copy hosted on Netlify, then retire the server it ran on. Covers sites that are already static, Statamic v1, v2 and v3+, and other server-rendered CMS sites (crawled with wget). Use when archiving, freezing or retiring a site, moving a static site to Netlify, or when a wget mirror won't deploy on Netlify or has broken srcset images or '?' filenames. Walks the user through every decision that needs their input.
---

# Site → static copy on Netlify

**End state:** a static copy of the site in one folder of the site's own git repo, deployed by Netlify on every push, served on the agreed domain (with `noindex` if it's an archive), and the old server-side site deleted.

**Why bother:** an end-of-life CMS on an end-of-life server is a standing risk to everything else on that server. A static copy has nothing to exploit and nothing to patch.

Placeholders used below: `DOMAIN` (the domain the site is served on), `SITE` (the Netlify site name), `MIRROR` (the folder holding the static copy, `archive/` by default), `BRANCH` (the branch Netlify deploys).

## How to run this

Work through the phases in order. Each one ends in something checkable; don't start the next until it passes.

**Ask, don't assume.** The steps marked **ASK** need the user's decision. Use `AskUserQuestion`, batch related questions (up to four at a time), and put your recommendation first. Ask at the point the question becomes answerable, not all up front: most need the survey's findings. Record every answer in `ARCHIVE.md` as you go (phase 7), so the decisions survive the session.

**Things only the user can do.** Say exactly what to click or type, then wait and verify the result yourself:

- creating the Netlify site and connecting the repo;
- adding the custom domain in Netlify;
- changing DNS at the registrar;
- adding web-server rules that need root;
- deleting the old site from the server or hosting panel.

**Hard rules**

- **Never print secrets.** Read `.env`, user files and config only for named keys (`grep -E '^(APP_ENV|APP_URL)=' .env`). Report that credentials or password hashes exist, never their values.
- **No sudo.** If something needs root, tell the user what to add and where.
- **Check who you'll commit as.** On a shared server, `git config user.name` / `user.email` may be someone else's (a client's, a previous developer's). Show them and **ASK** before the first commit; amending authorship after a push means a force-push.
- **Confirm before anything irreversible or public:** committing changes that were already sitting uncommitted on the server, pushing, editing CMS settings or content on a live site, deleting generated files, and anything in the list above.
- **Revert every temporary CMS change** after the crawl, and check the live site afterwards. Keep a running list of them.
- **Nothing identifying goes into this skill.** Site-specific findings belong in the site repo's `ARCHIVE.md`.

## Decisions to collect

| # | Decision | When | Default to recommend |
|---|---|---|---|
| D1 | Archive (frozen, `noindex`) or a live site just changing host (indexable)? | Phase 0 | — |
| D2 | Which domain will the static copy live on, and what happens to the main domain? It can change late (see Phase 5). | Phase 0 | An archive subdomain, e.g. `v2.example.com` |
| D3 | Which repo and branch does Netlify deploy? Folder name for the mirror? Tag the last CMS commit? | Phase 0 | The site's existing repo and current branch; `archive/`; an annotated tag on the commit before the archive |
| D4 | Commit the uncommitted changes found on the server? | Phase 1 | Show the diff, then ask |
| D5 | Hidden pages and drafts: include or leave out, per item? | Phase 1 | Include hidden, ask about each draft |
| D6 | Redirects, short links and vanity URLs: keep all? | Phase 1 | Keep all, including external and dead ones |
| D7 | Analytics and third-party scripts: keep, remove, or self-host, per script? | Phase 3 | Remove dead services; ask about the rest |
| D8 | Forms, search, login, comments, and embedded third-party forms (iframes): remove or replace (e.g. with a mailto link)? | Phase 3 | Remove; an embedded form keeps submitting to the real service |
| D9 | README wording: what the site was, where its successor lives, credits | Phase 7 | Ask for the text |
| D10 | When to delete the old site | Phase 6 | After verification; the user may want it as a dev environment for a few days |
| D11 | If the static copy ends up on a different hostname: redirect the old one or retire it? | Phase 5 | Redirect (a Netlify domain alias) |
| D12 | `robots.txt` for an archive: none, or disallow-all? | Phase 3 | None, so crawlers can see `noindex` |

## Scripts

In `scripts/`, Python 3.6+ with no dependencies. Copy them into the site repo as `archive-tools/`, alongside the crawl's `urls.txt` and `crawl.sh`, so the repo is self-contained.

- **`fix_mirror.py MIRROR [--dry-run] [--noindex] [--old-domain DOMAIN]`**
  1. Rebuilds `srcset`s that wget mangled. The original width descriptors can't be recovered, so each candidate gets its image's real pixel width. Warns if a rebuilt `srcset` has only one candidate.
  2. Renames files with `?` or `#` in the name, drops commas from file and folder names, and rewrites the references.
  3. With `--noindex`, leaves each page with exactly one `noindex,nofollow` robots tag.
  4. Lists what still needs a human: analytics, forms, `<img>` tags whose `src` is a page, HTML comments naming the environment or a commit, external script and iframe hosts.
- **`linkcheck.py MIRROR`**: checks that every local `href`/`src`/`srcset`/`url()` resolves (a clean URL `/about` counts if `about.html` exists, as Netlify serves it). Exits 1 on a missing target or a `?`/`#` filename.
- **`verify_deploy.py MIRROR DEPLOY_URL [--live LIVE_URL] [--indexable]`**: checks the deployed site.
  - every file returns 200, and non-HTML files are byte-identical;
  - every page has the `X-Robots-Tag` header and one noindex meta tag (skipped with `--indexable`);
  - every `srcset` candidate loads and its descriptor equals the image's real width;
  - with `--live`, page text matches the original site, and no image has lost the extra sizes its live `srcset` has;
  - CMS internals and unknown URLs return 404;
  - it reports any HTML Netlify injects.

  Exits 1 on failure. **Run `--live` before the DNS swap**: afterwards the domain no longer reaches the original.

## 0. Identify the site and agree the plan

1. **What kind of site is it?** Look in the site's directory:

   | Found | Type | Route |
   |---|---|---|
   | Only HTML/CSS/JS/assets; no `.php`, no `composer.json` | Already static | Phase 2A |
   | A static-site generator (`package.json` build script, `_config.yml`, `config.toml`…) | Generated static | Phase 2A, using the build output |
   | `_app/` and `_content/` | Statamic v1 | Phase 2B |
   | `statamic/` and `site/` (version in `statamic/core/Statamic.php`) | Statamic v2 | Phase 2B |
   | `statamic/cms` in `composer.json` | Statamic v3+ | Phase 2B with the Statamic v3+ notes. The `statamic/ssg` addon is the alternative, but means adding a Composer dependency to the live site |
   | Any other server-rendered site | Other CMS | Phase 2B; find the equivalents of the Statamic notes yourself |

   A "static" site can still depend on the server: grep for `.php`, server-side includes (`<!--#include`), `.htaccess` rules, and rewrite or redirect rules in the web-server config. Anything found either becomes a Netlify redirect or header, or makes it a Phase 2B crawl.

2. **ASK D1–D3.** If the site already runs on the domain the static copy will use, going live is only a DNS change.

3. **Is the site still being served?** A crawl needs it working. `dig +noall +answer DOMAIN` (note the TTL; suggest lowering it ahead of the swap if it's long) and `curl -sI https://DOMAIN/`.

## 1. Survey before touching anything

Report findings to the user as a short list before changing anything.

1. **Are internal files publicly readable right now?** Curl a few paths that should never be served and report only the status code:

   ```
   curl -s -o /dev/null -w '%{http_code}\n' https://DOMAIN/.env
   ```

   Try the CMS's user files, settings and logs too (Statamic v2: `site/users/<name>.yaml`, `site/settings/…`, `local/storage/logs/`; v1: `_config/users/`). Some web-server configs serve the whole repo root and block only dotfiles, which exposes user files containing password hashes.
   - If anything is exposed, tell the user at once. The proper fix is a web-server rule returning 404 for those paths, which usually needs root or the hosting panel.
   - The stopgap without root is to move the files out of the web root into a private folder (mode 700), leaving the deletion uncommitted. **ASK** first. Changing file permissions doesn't help when the web server runs as the same user.

2. **Uncommitted changes and auto-commits.**
   - `git status --short`. **ASK D4** before committing anything that was already there; show the diff.
   - `crontab -l`. A backup script running `git add .` on a schedule will silently commit, or revert, your work. **ASK** before disabling it.
   - `git rev-parse --abbrev-ref HEAD`: Netlify must deploy this branch (D3).
   - `git fetch && git status -sb`: the branch should match its remote before you tag it.
   - If D3 says tag: `git tag -a NAME -m "…" HEAD` now, before any archive commit, and push it with the first push.

3. **`.gitignore`.** Check the mirror folder isn't ignored: `git check-ignore -v MIRROR/x.html`. A rule like `static/` matches a folder of that name at any depth, and some CMSs write their page cache to `static/`, which is why `archive/` is the default.

4. **What a crawl won't find** (Phase 2B only). Don't trust the sitemap: sitemap templates usually filter out hidden items. Build the seed list from the content files themselves, and curl each candidate.
   - **Hidden items** are served but left out of navigation, listings and the sitemap.
   - **Drafts** are not served at all. To include one, publish it for the crawl and unpublish it afterwards.
   - **Taxonomy and listing pages**, pagination, and any route defined only in the routes config.
   - **Anything referenced only from JavaScript, feeds or JSON.** wget follows HTML and CSS only.
   - Statamic v1: `_`-prefixed entries are hidden; `__`-prefixed are drafts.
   - Statamic v2: `_`-prefixed files are drafts; `is_hidden: true` items are served but hidden. List `site/content/{pages,collections,taxonomies}` with each file's `is_hidden`. Entries can carry their own `redirect:` field (`grep -rln '^redirect:' site/content`).
   - Statamic v3+: drafts have `published: false` in the entry's front matter. Ask Statamic for every URL rather than deriving them from filenames, since routes, mounts and trees decide them:

     ```
     php artisan tinker --execute='foreach (Statamic\Facades\Entry::all() as $e) echo ($e->published() ? "P " : "D ").$e->collectionHandle()." ".$e->url()."\n";'
     ```

     Pages that are published but not in navigation (style guides, WIP pages, help pages) are still served: list them for D5. Custom routes and redirects live in `routes/web.php` (`Route::statamic`, `Route::redirect`).

   **ASK D5** with the actual list of hidden items and drafts.

5. **Routes and redirects.** Read the routes config (Statamic v2: `site/settings/routes.yaml`), `.htaccess`, and any redirect rules in the web-server config.
   - **Template routes** (a sitemap, a feed): crawl the ones worth keeping. Give non-HTML routes a file extension in the CMS before crawling (`/sitemap` → `/sitemap.xml`) so the static file gets the right Content-Type.
   - **Redirects and vanity URLs** become `[[redirects]]` in `netlify.toml`. **ASK D6.**
     - Curl every rule on the live site first (`-w '%{http_code} %{redirect_url}'`) and copy what the site actually answers, status code included. Where a path is both a source and a target, the site's precedence matters: Netlify uses the first matching rule, so order them to match.
     - Set `force = true` on each, so a file or folder that happens to exist in the mirror can't shadow the redirect.
     - Generate the rules from the config with a script rather than by hand.
     - Exclude their paths from the crawl, or wget saves the redirect target under the redirect's path.
   - **Protected routes, forms, search and auth:** exclude them.

6. **Environment-conditional output.** Templates often switch on the environment name, so analytics or robots tags gated on `production` may be missing from (or present in) what you crawl. Grep the layouts for the environment variable and check what the site's current environment is. Also look for HTML comments in the layout that print the environment, app URL or latest commit: offer to cut them down in the mirror.

7. **What can't work as static files.** Search, forms, comments, login/register/account pages, anything per-visitor. List them for D8.

8. **Assets on external storage.** If an asset container is on S3, DigitalOcean Spaces or similar, resized images come through the CMS and get crawled, but files the content links to directly (videos, PDFs, originals) stay on the bucket. **ASK** whether the bucket will outlive the archive; if not, copy those files into `MIRROR` and rewrite the links.

## 2A. Already static: collect the files

1. If the repo root is the site, move the public files into `MIRROR/` (`git mv`), so that Netlify publishes only that folder and never the repo's other contents. If a generator builds the site, **ASK** whether Netlify should run the build (set `command` and `publish` accordingly) or whether to commit the built output as a frozen archive.
2. Translate `.htaccess` and web-server rules into `netlify.toml` redirects and headers.
3. Continue at Phase 3. `fix_mirror.py` will mostly find nothing to repair, but its report and `linkcheck.py` are still worth running.

## 2B. Server-rendered: crawl with wget

### Prepare

1. Write the seed URLs to `urls.txt`, one per line, from:
   - the content folders and routes config (Phase 1.4–1.5);
   - the sitemap;
   - any static page cache's filenames, which record every URL visitors actually hit. Filter out bot-probe junk.
2. Make the temporary CMS changes agreed above (publish drafts, add route extensions). List each one for reverting.
3. **Image URLs without file extensions.** If the CMS serves resized images from URLs like `/img/<token>/<name>?w=360&s=<signature>`, the mirror gets files with no extension and a query in the name. Prefer switching the CMS to write real image files for the duration of the crawl.

   **Statamic v2 (Glide):**
   1. Set `image_manipulation_cached: true` in `site/settings/assets.yaml`. URLs become `/img/containers/<container>/<path>/<image.jpg>/<md5>.jpg`.
   2. Clear the caches: `php please clear:stache`, `clear:cache`, `clear:static`. The static page cache holds HTML with the old URLs, and must be empty before the crawl if the web server serves it directly.
   3. **Warm every page once before wget runs:** `curl -s -o /dev/null --max-time 300 -w '%{http_code} %{time_total}s\n' URL`. Images are generated synchronously during the first render, which can take longer than PHP's request timeout on image-heavy pages. Re-request any page that fails.
   4. Crawl.
   5. **Before deleting the generated `img/` folder, copy in the images wget skipped.** wget doesn't follow `<meta>` tags, so social-card images (`og:image`, `twitter:image`) were generated during warming but never fetched. Copy every `content="https://DOMAIN/img/…"` target into `MIRROR/img/`, removing any `/./` in those paths. Then check that every absolute `https://DOMAIN/…` URL in the mirror resolves to a file. The md5 filenames are deterministic, so the steps can be repeated if needed.
   6. **Revert:** restore `assets.yaml`, rename drafts back, **ASK** before `rm -rf img`, clear the caches again, and check the live site renders its original image URLs.

   **Statamic v3+ (Glide):**
   1. Config is often cached (`bootstrap/cache/config.php` exists), so every config edit needs `php artisan config:cache` to take effect, and again after reverting.
   2. Set `'cache' => true` under `image_manipulation` in `config/statamic/assets.php`. URLs become `/img/containers/<container>/<path>/<md5>/<file>` for local containers, or `/img/http/<file>/<md5>/<file>` for assets served by URL (S3, Spaces). **Each size is in its own `<md5>` folder.**
   3. Publish drafts by editing `published:`; the Stache watcher is usually off in production, so run `php please stache:clear && php please stache:warm`, then `php artisan cache:clear` and `php please static:clear`.
   4. Warm every page as above. Image-heavy pages can hit the web server's timeout (a 504 at about 90 s on nginx): the images made so far are kept, so request again until every page returns 200.
   5. Crawl, then copy the social-card images in from `public/img/` and check every absolute URL resolves, as for v2.
   6. **Revert** with `git checkout` on the config and content files, rebuild the config cache and the Stache, and check that drafts 404 again and image URLs are back to their original form. **ASK** before deleting `public/img/`.

   **Re-rendering a page without touching the live site (Statamic v3+).** To recover what a page looked like at crawl time, for instance to repair a mirror, render it inside a throwaway `tinker` process with the config changed in memory only:

   ```php
   config(['statamic.assets.image_manipulation.cache' => true, 'statamic.static_caching.strategy' => null]);
   $res = app(Illuminate\Contracts\Http\Kernel::class)->handle(Illuminate\Http\Request::create('https://DOMAIN/path', 'GET'));
   ```

   - Pass the full URL: Statamic picks the site by host, so a bare path returns 404.
   - Drafts can't be rendered this way; they return 404.
   - `Statamic\Facades\Image::manipulate($url, ['p' => '<preset>', 'fit' => 'max'])` returns the same cached URL as the Glide tag for preset-based images. `crop_focal` crops don't reproduce this way: for those, use the files wget already fetched.

### Crawl

```
wget -e robots=off --mirror --page-requisites --convert-links --adjust-extension \
  --no-if-modified-since -nH -P archive -o wget.log \
  --reject-regex '/(login|register|account|forgot-password|reset-password|users|search)(/|\?|$)' \
  -i urls.txt
```

- Add `--no-check-certificate` only if the server's certificate has already lapsed.
- Add each redirect and vanity path to `--reject-regex`, anchored (`^https?://DOMAIN/(contact|blog)/?(\?.*)?$`) so `/blog` doesn't also reject `/blog/post`.
- Save the exact command as `archive-tools/crawl.sh`: it's too long to reconstruct later.
- Run long crawls in the background. Check with `grep ERROR wget.log`, not `grep 404`, which matches image hashes and transfer speeds.
- Then revert the temporary CMS changes and confirm the live site is as it was.

### What wget does to a mirror (tested on GNU Wget 1.19.4)

- `--convert-links` mangles a `srcset` whose value spans several lines or contains `&amp;`. The result looks like `a.jpg596cba1.jpg 360w../b.jpg… 625../c.jpg 90…`. `fix_mirror.py` repairs it, including when each size sits in its own folder (Statamic v3+ Glide). wget does fetch every candidate. **After any srcset repair, compare a few images' candidate counts with the live page:** the fixer warns about rebuilt srcsets with a single candidate, and `verify_deploy.py --live` fails on them.
- A comma in a filename breaks `srcset`: browsers split candidates on commas. `fix_mirror.py` drops commas from file and folder names and rewrites references.
- A URL with a query keeps the query in the saved filename (`news?page=2.html`, `styles.css?v=123.css`), and references to it are written with `%3F`. Netlify refuses to deploy filenames containing `?` or `#`. `fix_mirror.py` renames them.
- References wget couldn't fetch (a 404, or a rejected path) are left as absolute URLs to the original domain. `--old-domain` lists them.
- Absolute URLs in `<meta>` tags and sitemap `<loc>`s are never converted and their targets never fetched. They're fine if the static copy keeps the same domain, provided the targets exist.
- Files referenced only from feeds, JavaScript or JSON aren't fetched. Find them and copy them in from the server.

## 3. Fix and verify locally

Read the dry-run report first, then apply. Drop `--noindex` if D1 is "indexable".

```
python3 scripts/fix_mirror.py archive --dry-run --noindex --old-domain DOMAIN
python3 scripts/fix_mirror.py archive --noindex --old-domain DOMAIN
python3 scripts/linkcheck.py archive
git add -A archive
```

`linkcheck.py` must exit 0 before moving on. `git add -A` records the renames. Also check:

- `git ls-files archive | wc -l` equals `find archive -type f | wc -l`. An ignore rule can silently drop files.
- No file is over 100 MB (GitHub's limit; it warns above 50 MB). **ASK** what to do with any that are.

Then work through the report:

- **"Repeated width" warnings.** The source image was smaller than the larger size presets, so the CMS produced identical sizes. Harmless: browsers drop the duplicate.
- **Analytics and third-party scripts. ASK D7** with the list from the report's "external script hosts" and "analytics" lines. The analytics check only knows Google's tags, so grep for any others the site used. Universal Analytics (`UA-…`) stopped collecting in 2023 and can always go. Check environment-gated snippets (Phase 1.6).
- **Links to the old domain.**
  - Make CSS and HTML URLs relative, fetching any file wget skipped.
  - Point feed links at the final domain.
  - Scripts hotlinked from another domain the owner controls: download them into the mirror, after checking the page really loads and uses them.
  - Links to redirect paths stay absolute, because the crawl rejected them, and `linkcheck.py` reports them missing. Point each at its final page, so internal links don't depend on redirects. The Netlify redirects still cover links from outside.
- **Extensionless files** (e.g. `feed`): give each a `Content-Type` header in `netlify.toml`, or better, add the extension in the CMS and re-crawl that URL.
- **Forms, search, login. ASK D8**, then remove or replace them. The report lists external iframe hosts: an embedded third-party form (Airtable, Google Forms, Typeform…) still works from the static copy and still submits to the real service.
- **`<img>` whose `src` is a page.** An image field left empty in the CMS can render `<img src="">`, which wget converts to the page's own filename. The report lists them; remove the tag.
- **Absolute URLs that should stay absolute.** `og:url`, `og:image`, `twitter:image` and sitemap `<loc>`s must be absolute: link previews and sitemaps don't resolve relative URLs. Users retiring a server sometimes ask to make *everything* relative; explain that these name the domain, not the server, and once DNS points at Netlify, Netlify serves them. Check every one resolves to a file in `MIRROR`. If the static copy will be served on a different domain from the one crawled, rewrite them to the final domain.
- **404 page.** Fetch the site's own (`curl https://DOMAIN/this-page-does-not-exist`), make every URL in it root-relative (Netlify serves it at any depth, so relative URLs break), match any renamed CSS filename, set the robots tag, and save it as `MIRROR/404.html`.
- **Content the crawl couldn't reach.** Prefer publishing it temporarily and crawling it. Otherwise build each page by hand from an existing page of the same type, and generate its images to match the CMS's sizes. If the CMS strips colour profiles, convert wide-gamut originals to sRGB first: `convert in.jpg -profile sRGB.icc -resize '1200x1000>' -strip -quality 80 out.jpg`.
- **JavaScript features.** `grep -rhoE "<script[^>]*>" archive | sort | uniq -c` shows what's there. Serve locally (`cd archive && python3 -m http.server 8000`) and ask the user to click through anything script-driven: galleries, sliders, video embeds.
- **`robots.txt`. ASK D12.** For an archive, recommend not shipping one that disallows crawling: crawlers must be able to fetch a page to see its `noindex`, so a disallowed page that's already indexed can linger as a bare link. If the user wants disallow-all anyway, ship it and record the trade-off.

## 4. Netlify

`netlify.toml` at the repo root:

```toml
[build]
  base = "archive"      # publish is resolved relative to base
  publish = "."
  command = "echo 'No build step: publishing pre-rendered archive/'"

# Archives only (D1). Remove for an indexable site.
[[headers]]
  for = "/*"
  [headers.values]
    X-Robots-Tag = "noindex, nofollow"

# Extensionless files, e.g. a feed saved as "feed"
# [[headers]]
#   for = "/feed"
#   [headers.values]
#     Content-Type = "application/rss+xml; charset=utf-8"

# One per redirect (301) or vanity URL (302), external targets included
# [[redirects]]
#   from = "/old-page"
#   to = "/new-page"
#   status = 301
#   force = true
```

- **Publish only the mirror folder.** The repo root may hold CMS config and user files with password hashes. If the repo is, or might become, public, tell the user that those files are in its history.
- **Base directory.** `publish` is resolved relative to `base`, and a Base directory set in the Netlify UI counts too: a UI base of `archive` plus `publish = "archive"` makes Netlify look for `archive/archive`. Setting `base` and `publish = "."` in the toml works whatever the UI says.
- **The user creates the site.** Ask them to: commit and push (after confirming), create a Netlify site from the repo, pick `BRANCH`, leave the build settings to the toml, and tell you the `SITE.netlify.app` name. The Netlify CLI is an alternative if a recent Node is available and the user prefers it.
- **Netlify rewrites HTML as it serves it.**
  - Internal links become clean URLs (`about.html#team` → `/about#team`). `/x`, `/x.html` and `/x/` all reach the page.
  - It can inject a comment, meta tags and a script into pages: always on `*.netlify.app`, and on some custom domains. It depends on the request's `Accept` header. It's harmless; if the user wants it gone, it's a site setting on their side.
  - So compare only non-HTML files byte-for-byte, and fetch with browser headers. `verify_deploy.py` does both.

## 5. Verify the deploy, then go live

1. **Before the DNS swap:**

   ```
   python3 archive-tools/verify_deploy.py archive https://SITE.netlify.app --live https://DOMAIN
   ```

   It must exit 0 (add `--indexable` if D1 says so). Every page-text difference should be explainable, e.g. a draft published only for the crawl. A live page returning 500 straight after a cache clear is often transient: re-request it before worrying.
   - Curl every redirect on `SITE.netlify.app` and compare status and target with the rules.
   - Ask the user to click through the deploy and confirm it looks right.
2. **User:** add the custom domain to the Netlify site.
3. **User:** at the DNS provider, point the domain at Netlify. For a subdomain, replace the `A` record with a `CNAME` to `SITE.netlify.app`. For an apex domain, follow Netlify's instructions for that provider. Give them the exact record to enter.
   **If the domain changes** (D2 often does once the user sees the deploy): rewrite the absolute meta and sitemap URLs to the new domain, update README and `ARCHIVE.md`, and **ASK D11** about the old hostname. A redirect is a Netlify domain alias plus a DNS record. Retiring it means deleting its DNS record *no later than* the server goes: a record left pointing at a released IP can end up serving someone else's machine.
4. **Wait for the certificate, then verify on the domain.** Provisioning can fail at first and take up to 24 hours. Meanwhile verify on `SITE.netlify.app`, and don't test the custom domain over plain HTTP.
   - Check the authoritative answer first (`dig DOMAIN @<authoritative-ns>`), then a public resolver (`@1.1.1.1`). Resolvers that cached the old record wait out its TTL, and the machine you're on may be one of them.
   - Until Netlify issues the certificate, HTTPS on the domain fails with a certificate name mismatch. Poll it: `echo | openssl s_client -connect NETLIFY_IP:443 -servername DOMAIN 2>/dev/null | openssl x509 -noout -ext subjectAltName`, with `NETLIFY_IP` from `dig +short SITE.netlify.app @1.1.1.1`.
   - While this machine still resolves the old address, use `curl --resolve DOMAIN:443:NETLIFY_IP`, and run `verify_deploy.py` under a shim that sends the domain to Netlify (SNI and the Host header stay `DOMAIN`):

     ```python
     import socket, sys, runpy
     _gai = socket.getaddrinfo
     socket.getaddrinfo = lambda h, *a, **k: _gai('SITE.netlify.app' if h == 'DOMAIN' else h, *a, **k)
     sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')
     ```

     `python3 shim.py archive-tools/verify_deploy.py archive https://DOMAIN`

   Done when:
   - `dig +short DOMAIN` shows the new record;
   - `curl -sI https://DOMAIN/` shows `server: Netlify` (and `x-robots-tag: noindex, nofollow` for an archive);
   - `verify_deploy.py archive https://DOMAIN` exits 0;
   - the redirects work on the domain.

## 6. Decommission the old site

1. **Check nothing exists only on the server:**
   - `git status --short --ignored`, and `git log origin/BRANCH..BRANCH` is empty;
   - tracked file counts match what's on disk for asset and upload folders (`git ls-files assets | wc -l` vs `find assets -type f | wc -l`);
   - list the *names* of the keys in `.env` and ask whether any credential needs saving elsewhere or revoking;
   - databases, cron jobs, queue workers, scheduled backups and mailboxes tied to the site.
2. **ASK D10.** Until the old site is deleted, the server keeps answering for that hostname to anyone who connects to its IP directly, exposed files included.
   - After the swap, the old site is still reachable from the server itself with `curl --resolve DOMAIN:443:127.0.0.1 https://DOMAIN/`.
   - wget has no `--resolve`. A later re-crawl needs a hosts entry (root), a temporary extra hostname on the old site, or DNS pointed back.
3. **User:** delete the site from the server or hosting panel. Afterwards, confirm the server no longer answers for the hostname.

## 7. Document in the repo

Write these as you go, not at the end.

- **`README.md`**: a short human description. **ASK D9** for the wording: what the site was, where its successor lives, who made it.
- **`ARCHIVE.md`**:
  - a status checklist, including what's still pending and who owns it;
  - every decision (D1–D12) and who made it;
  - the tag on the last CMS commit, if any;
  - the temporary CMS changes and that they were reverted;
  - where the seeds came from, and the crawl command;
  - the fixes and hand edits;
  - the Netlify setup and anything odd about it;
  - the verification results;
  - security findings, without secrets;
  - how to revisit, before and after the old site is deleted;
  - known issues left as they were on the live site.
- **`archive-tools/`**: the scripts, `urls.txt`, `crawl.sh`, and any redirect generator.

If the repo is public, keep security findings and server details out of it: **ASK** where they should go instead.

The mirror is now the source of truth. Future changes are edits to its HTML.

## Final report to the user

Finish with: what's live and where; what was verified and how; every temporary change and that it was reverted; what's still pending and whose move it is; and anything found along the way that they should know about (exposed files, stale credentials, other sites on the server in the same state).
