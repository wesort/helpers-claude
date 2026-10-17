---
name: statamic-new-site
description: Build a new Statamic site from scratch on the latest stable everything (Ubuntu LTS, PHP, Node Active LTS, Laravel, Statamic, Tailwind, Alpine, Vite), with an opinionated set of front-end and hosting defaults, deployed with Forge zero-downtime releases. Use when starting a new Statamic site, replacing a starter kit, or rebuilding a site on a fresh server. Walks the user through every decision that needs their input.
---

# New Statamic site

**End state:** a new Statamic site in its own git repo, on the latest stable versions of everything, with the defaults below in place, deploying to production with Forge zero-downtime releases, and with `docs/deploy.md` saying exactly how.

**Why a skill and not a starter repo:** a starter repo is a snapshot. It is a major version behind within a year, and the reasons behind its choices aren't written down. This skill installs whatever is current, then applies each default for the reason it gives. When a default no longer fits the latest release, keep the reason and change the code.

Placeholders used below: `DOMAIN` (the production domain), `DEV_DOMAIN` (the dev site's domain), `REPO` (`owner/name` on GitHub), `SERVER` (the Forge server name), `AUTHOR` (who built the site, for the head comment).

## How to run this

Work through the phases in order. Each ends in something checkable; don't start the next until it passes.

**Ask, don't assume.** The steps marked **ASK** need the user's decision. Use `AskUserQuestion`, batch related questions (up to four at a time), and put your recommendation first. Record every answer in the site's `docs/deploy.md` or README as you go, so the decisions survive the session.

**Things only the user can do.** Say exactly what to click or type, then wait and verify the result yourself:

- creating the server and sites in Forge, and issuing SSL certificates;
- creating the GitHub repo and adding the Forge deploy key;
- creating storage buckets and API keys (DigitalOcean Spaces or similar);
- entering secrets into `.env` (licence key, bucket keys, webhook URLs);
- DNS changes at the registrar;
- pasting the deploy script into Forge and adding shared paths and scheduled jobs.

**Hard rules**

- **Never print secrets.** Read `.env` only for named keys (`grep -E '^(APP_ENV|APP_URL)=' .env`). For secrets, test presence and print a verdict: `grep -qE '^STATAMIC_LICENSE_KEY=.+' .env && echo set || echo "not set"`.
- **No sudo.** If something needs root, tell the user what to run and where.
- **Confirm before anything public or hard to undo:** creating or pushing to a repo, changing a Forge site, deploying.
- **Don't commit or push until the user asks.**
- **Nothing identifying goes into this skill.** Site-specific findings belong in the site's own repo.

## Reference files

`reference/` holds working snippets from a site built this way. **Hold them lightly.** Each one illustrates an intent stated in this file. Adapt them to what the latest Statamic, Laravel and Tailwind ship with: if a snippet fights the new skeleton, follow the intent and rewrite the snippet. Never copy a reference file over a freshly generated file without diffing first.

| File | Intent it serves |
|---|---|
| `css/site.css` | 12-column site grid, base layers, prose |
| `js/site.js` | Alpine with persist, `no-js` to `js`, external links in a new tab |
| `views/layout.antlers.html` | Grid layout, access levels, code injection, dev panel |
| `views/head/*` | Author comment, basics, SEO and robots meta |
| `views/utils/skip_to_content.antlers.html` | Skip link |
| `views/errors/*` | 404 with redirects |
| `views/sitemap_xml.antlers.html` | XML sitemap |
| `views/blocks/*`, `views/helpers/*` | Bard blocks, `<picture>` images |
| `blueprints/`, `fieldsets/` | Settings and redirects globals, access and page meta |
| `routes/web.php`, `routes/console.php` | Sitemap route, schedule with failure alerts |
| `config.md` | Config changes, by file |
| `autobackup.sh` | Content backup from production |
| `robots/` | Dev and prod robots.txt |
| `npmrc` | npm release-age cooldown (install as `.npmrc`) |
| `deploy.md` | Skeleton for the site's `docs/deploy.md`, including the Forge deploy script |
| `refresh.sh` | Only for the manual-pull alternative |

## Decisions to collect

| # | Decision | When | Default to recommend |
|---|---|---|---|
| D1 | Site name, `DOMAIN`, `DEV_DOMAIN`, `REPO`, `AUTHOR` | Phase 0 | `dev.` subdomain for dev |
| D2 | New server or an existing one? | Phase 0 | New server |
| D3 | Deploy method for production | Phase 0 | Forge zero-downtime |
| D4 | Assets: DigitalOcean Spaces (or other S3) or local disk? | Phase 0 | Spaces, plus an `-assets-backup` repo if that is the estate's habit |
| D5 | Statamic Pro? Licence key available? | Phase 0 | Pro (needed for multi-user and Git integration) |
| D6 | Static caching: none, `half` or `full`? | Phase 0 | `half` in production (no nginx change needed) |
| D7 | Search needed? | Phase 0 | Ask |
| D8 | Discord (or Slack) channel for error alerts? | Phase 3 | Yes, if one exists |

## 0. Agree the plan

1. **ASK D1 to D8.**
2. **Find the latest stable versions now.** Don't rely on versions remembered from training or written in this file.
   - PHP: `curl -s https://www.php.net/releases/active.php` (JSON). The highest active branch.
   - Node: `curl -s https://nodejs.org/dist/index.json`. **Active LTS** is the highest major whose `lts` field is not `false`. Not "Current".
   - Ubuntu: the newest LTS that Forge offers when creating a server.
   - Statamic, Laravel, npm packages: whatever `composer create-project` and `npm install` resolve, within the cooldown below.
3. Tell the user the versions you're targeting before Phase 1.

## 1. Server and sites (the user, in Forge)

New sites usually get a fresh VPS, so target the latest of everything. Nothing is held back for an older box.

1. **Server** (D2 = new). Forge > create server: App server, newest Ubuntu LTS, the PHP version from Phase 0. Name it `<site>-prod-<n>`.
2. **Node.** Forge installs a Node version of its own choosing. Check with `node -v` and `npm -v`. If it isn't the Active LTS, give the user the commands to install it (NodeSource or Forge's Node setting, depending on what Forge offers). The cooldown in `.npmrc` needs npm 11.10 or later: `npm install -g npm@latest` if older.
3. **Dev site:** a standard (not zero-downtime) site on `DEV_DOMAIN`, web directory `/public`. This is where the site is built and where day-to-day development happens.
4. **Production site:** a zero-downtime site on `DOMAIN` (D3), web directory `/public`, created later in Phase 6 once the repo exists.
5. **Existing server** (D2): read the real versions (`php -v`, `node -v`, `lsb_release -a`). Say plainly where they fall short of latest stable and what that holds back. Don't quietly target older versions.

**Check:** `php -v`, `node -v`, `npm -v` on the server match Phase 0's targets, or the user has accepted the gap.

## 2. Scaffold

In the dev site's directory (Forge may have created a default `public/index.php`; ask before removing anything):

1. `composer create-project statamic/statamic . --prefer-dist --no-interaction` (or into a temp directory and move it in, if the site directory isn't empty).
2. Tie the dependency resolvers to the server, so neither can pick a version the server can't run:
   - `composer.json`: `"php": "^<server major.minor>"` and `composer config platform.php <server full version>`.
   - `package.json`: `"engines": { "node": ">=<Active LTS major>" }`.
3. `.npmrc` from `reference/npmrc`: `min-release-age=7`. **Why:** a version published in the last 7 days hasn't had time to be caught if it's malicious. "Latest stable" means latest that is at least 7 days old.
4. Front end: Tailwind (the `@tailwindcss/vite` plugin), Alpine and `@alpinejs/persist`, at latest. `vite.config.js` inputs `resources/css/site.css` and `resources/js/site.js`.
5. Leave out `laravel/debugbar` and `concurrently`. **Why:** debugbar has leaked data on misconfigured production sites. `concurrently` only served a `composer dev` script that isn't used, and its pinned `shell-quote` carried an advisory.
6. `.gitignore` adds `/public/vendor` (**why:** `statamic:install` republishes addon assets on every `composer install`), `/public/robots.txt` and `.claude/settings.local.json`.
7. `npm run build`, then load `DEV_DOMAIN`.

**Check:** the default Statamic home page renders, and `php please --version` shows the latest Statamic.

## 3. Defaults

Apply each one, adapting the reference file as needed. Each has a reason; keep the reason even if the code changes.

### Config (`reference/config.md`)

- **Dates.** App and server stay on UTC. Statamic's `display_timezone` and the CP's `default_timezone` are `Europe/London`. Every date-only field gets an explicit `format: Y-m-d`. **Why:** without a format, Statamic 6 treats a date-only field as a moment in time and converts it from the CP's timezone, so a save during BST stores 23:00 the day before (statamic/cms#14122).
- **Locale.** `en_GB` in `resources/sites.yaml` and `APP_LOCALE`.
- **Sessions.** `serialization => 'json'` (**why:** a leaked `APP_KEY` can't then be used for PHP object deserialisation through the session). Lifetime 7 days (**why:** a year-long lifetime on the file driver let hundreds of thousands of session files build up).
- **Cache.** `serializable_classes => false`, as the Laravel 13+ skeleton does. Statamic extends it with its own classes.
- **Commit info.** `config/statamic/git.php` reads the commit hash, date, author and message with `git -C base_path()`. **Why:** a bare `git` runs in the current directory, so `config:cache` run from elsewhere caches empty values. Zero-downtime releases have their own `.git`, so this works there too.
- **Logging.** The `stack` channel adds `slack` only when `LOG_SLACK_WEBHOOK_URL` is set (D8). A Discord webhook works with `/slack` on the end. It has its own `LOG_SLACK_LEVEL` (default `error`) and names the site by its hostname.
- **Assets** (D4). Configure the chosen disk and **remove the one not used**, with any stale `.gitkeep` and ignores.
- **Static caching** (D6). Set the strategy via `STATAMIC_STATIC_CACHING_STRATEGY`, `null` on dev.

### Addons

Both are installed from their GitHub repos via composer `repositories` (`type: vcs`). Check each addon's README for the current version and requirements first.

- **[`wesort/statamic-dev-panel`](https://github.com/wesort/statamic-dev-panel)**: a panel for logged-in users with the commit, access level, breakpoint, design-grid overlay, raw-data toggle, edit link and back-to-top. Publish its config and set `grids.container_class` to the site grid's classes (`grid-site-12 px-site max-w-site mx-auto`) and `breakpoints` to match `@theme`. Add `@source` for `vendor/wesort/statamic-dev-panel/resources/views` in `site.css`. Templates use `{{ dev_panel }}`, `{{ dev_panel:grids }}` and `{{ dev_panel:raw_data }}`.
- **[`wesort/statamic-cp-lock`](https://github.com/wesort/statamic-cp-lock)**: `cp:lock` blocks CP writes while still letting people browse. **Why:** content is in git and each release is cloned fresh. An edit made mid-deploy lands in the old release and is lost at the swap. The lock file lives in shared `storage/`, so it spans the swap.

### Layout and CSS (`reference/css/site.css`, `reference/views/layout.antlers.html`)

- **12-column site grid.** Components `grid-site-12` (12 columns, `gap-4 lg:gap-8`), `px-site` (`px-4 lg:px-8`) and `max-w-site` (the content width), used together as `grid-site-12 px-site max-w-site mx-auto`. Layout regions are `col-span-*` children. **Why:** plain Tailwind grid utilities, easy to reason about and to override per region. A fluid grid with named lines (Statamic Peak's) was tried and dropped.
- `@theme` sets `--color-primary` and `--color-background` and any extra breakpoints. The layout uses those tokens rather than raw colours.
- `<html lang="{{ site:locale }}" dir="ltr" class="no-js ...">`, swapped to `js` by `site.js`.
- **Skip to content** is the first element in `<body>`, targeting `<main id="main">`.

### Head (`reference/views/head/*`)

- **Author comment** with `AUTHOR`, Statamic version, environment, app URL and the commit. Useful when debugging a live site from view-source.
- **Title** with a `*` prefix on dev, so dev and production tabs can't be confused.
- **Robots meta:** `INDEX, FOLLOW` only when `access >= 80` and `APP_ENV` is `production`, otherwise `NOINDEX, NOFOLLOW`.
- Canonical, Open Graph (`og:locale en_GB`, image cropped to 1200 × 628 from `primary_image`) and meta description.

### Access levels (`reference/fieldsets/access.yaml`, `page_meta.yaml`)

| Level | Meaning |
|---|---|
| 1 | Super users |
| 10 | Logged-in authors only |
| 50 | Public, not listed, hidden from robots |
| 80 | Public, not listed |
| 100 | Public (default) |

- The layout serves 10 and below to logged-in users only; anyone else gets a 404 plus the redirects message. **It fails closed:** an entry with no `access` value is treated as restricted. So **every routed blueprint must import `page_meta`** (or `access`), or its pages 404 for visitors.
- Level 1 is treated like 10 by the reference layout. If a site needs genuinely super-only pages, add a check on the user's super flag.
- Listings and navigation should filter to `access:gte="100"` (listed) and the sitemap to `access:gte="80"` (indexable), matching the robots meta.

### Redirects, 404 and sitemap

- **Redirects global** (`reference/blueprints/globals/redirects.yaml`): a 404 message and a grid of rules (internal or external, 301 or 302, or disabled). The 404 template (`reference/views/errors/404.antlers.html`) checks the rules first and redirects on a match. Editors can then fix broken URLs without a deploy.
- **Sitemap:** `/sitemap` → `/sitemap.xml` (301), served by `Route::statamic` with no layout and `text/xml` (`reference/routes/web.php`). Lists entries at `access >= 80`, with `sitemap_priority` from `page_meta`.
- **Robots.txt:** `docs/dev.robots.txt` disallows everything; `docs/prod.robots.txt` allows all and names the sitemap. `public/robots.txt` is gitignored and installed per environment. On zero-downtime it's a shared path (Phase 6).

### Code injection (`reference/blueprints/globals/settings.yaml`)

A settings global with two replicators: code for `<head>`, and code before `</body>` with a `production_only` toggle per item. In the layout, a `production_only` item renders only when `APP_ENV` is `production` and nobody is logged in, so analytics never count dev or editors. Items without the toggle always render.

### Images (`reference/views/helpers/photo_asset.antlers.html`, `photo_srcset.antlers.html`)

- `<picture class="contents">` with a WebP `<source>`, then an `<img>` in the image's own format (PNG stays PNG, the rest JPEG), each with the same widths and `sizes`. **Why:** WebP is far smaller, and the fallback keeps older browsers working. `display: contents` means the `<picture>` adds no box, so layout CSS targets the `<img>` as before.
- One srcset partial, called once per format, sets `width`, `q="80"`, `fit="max"` and `fm` explicitly. **No Glide presets.** **Why:** when a format or fit is also given, Glide drops the preset, so a "360w" image came out at full size and default quality.
- No upscaling: leave out widths larger than the source.
- SVG inline, GIF as is. `alt` always comes from the asset, ending in a full stop.
- `width`, `height` and `loading="lazy"` on every `<img>` (pass `loading="eager"` for the first image above the fold).

### Templates

- **Every `{{ nocache }}` gets `select="@auto"`.** **Why:** without it, each region stores the whole Antlers context, including all config, per URL and forever, even with static caching off.
- **Bard blocks** (`reference/views/blocks/*`): a `blocks` fieldset with text, photo and code sets. Text goes through `widont | smartypants`, so a heading or paragraph never ends on a word alone. [`jacksleight/statamic-bard-mutator`](https://github.com/jacksleight/statamic-bard-mutator) adds anchors to headings, if the site wants linkable headings.
- **Search** (D7): rebuild the index on every deploy (`please search:update --all`), so search matches the deployed content.

### Schedule and alerts (`reference/routes/console.php`)

- One Forge scheduled job on production runs `schedule:run` every minute. Jobs live in `routes/console.php`, not as separate Forge jobs. **Why:** they are versioned, and Statamic's own scheduled jobs (publishing scheduled entries to search and the static cache) need `schedule:run` anyway.
- The content backup (`autobackup.sh`) runs daily at 03:00 UK time, production only, `withoutOverlapping`, output appended to `storage/logs/autobackup.log`. On failure, it logs an error with the last lines of output, which reaches the alerts channel (D8).

### Content backup (`reference/autobackup.sh`)

Content edited in the CP on production is committed and pushed by `autobackup.sh`:

- It stages an **allowlist**: `git add -A -- content users resources public`. **Why:** on zero-downtime, `storage/` in each release is a symlink to shared storage. Git can't descend a symlink, so `git add .` stages the tracked `storage/**/.gitignore` skeleton as deleted and commits it out of the repo.
- It exits cleanly when there's nothing to commit.
- Its commit message contains `[BOT]`, which the deploy script skips, so a backup push never triggers a deploy.
- It never clears or rebuilds caches. **Why:** a nightly `optimize` puts pending `.env` edits live unannounced.

### helpers-claude

Install the full [helpers-claude](https://github.com/wesort/helpers-claude) set, following that repo's README "Install" steps: every command in `.claude/commands/` and every skill in `.claude/skills/`. Skip anything already present and identical. If a file exists and differs, list it and **ASK**. Make sure `.claude/settings.local.json` is gitignored. Record the helpers commit it came from in the hand-off.

**Check, before Phase 4:** `npm run build` succeeds and `php artisan about` is clean.

## 4. Repo

1. **User:** create `REPO` on GitHub (private unless they say otherwise).
2. README: what the site is, the stack and versions, links to `docs/deploy.md`.
3. When the user asks: commit (one commit per default group reads well later), add the remote, push `main`.
4. **User:** in Forge, give the dev site access to the repo, so dev can pull.

## 5. Deploy docs (`reference/deploy.md`)

Write `docs/deploy.md` from the reference skeleton, filled in for this site: method, production and dev, what other branches do, steps, the deploy script, shared paths, content backup, rollback, provisioning.

**Forge zero-downtime deploy script** (the copy in `docs/deploy.md` is the source of truth; the one that runs is pasted into Forge). The sequence, in order:

1. Exit if `$FORGE_DEPLOY_MESSAGE` contains `[BOT]` (a content backup).
2. `$CREATE_RELEASE()`, `cd $FORGE_RELEASE_DIRECTORY`.
3. `$FORGE_COMPOSER install --no-dev --no-interaction --prefer-dist --optimize-autoloader`.
4. `npm ci && npm run build`.
5. `$FORGE_PHP artisan optimize`.
6. `$FORGE_PHP please stache:warm`, then `search:update --all` if D7.
7. `$ACTIVATE_RELEASE()`.
8. Reload PHP-FPM (see the reference; **why:** PHP's realpath cache otherwise serves the old release's paths for a couple of minutes).
9. `$FORGE_PHP please cp:unlock`.
10. Static caching (D6): `static:clear`, then `static:warm`.

The **operator** runs `php please cp:lock` and then `./autobackup.sh` in `current/` before deploying, so no edit is lost. Say so prominently in `docs/deploy.md`.

**D3 = manual pull** instead: use `reference/refresh.sh`. It stops at the first failure, uses an `EXIT` trap rather than `ERR` (it runs under `sh`), reads only `APP_ENV` from `.env`, installs with `--no-dev`, and unlocks the CP at the end.

## 6. Production

**User**, in Forge, with exact instructions from you:

1. Create the zero-downtime site on `DOMAIN` from `REPO`, `main`, keeping 10 releases.
2. Shared paths: `.env` and `storage/` (Forge's defaults), plus `public/robots.txt`.
3. Put `.env` at the site root from `docs/prod.env`, entering the secrets themselves. Copy `docs/prod.robots.txt` to the site root as `robots.txt`.
4. Paste the deploy script. Deploy.
5. Scheduled job: `php<version> /home/forge/DOMAIN/current/artisan schedule:run`, every minute.
6. SSL once DNS points at the server (check with letsdebug.net first).

## 7. Verify

On dev, then production:

- `npm run build` succeeds; no errors in `storage/logs`.
- The home page loads; a missing URL returns 404 with the redirects message; a redirect rule redirects with the right status.
- A page at access 10 returns 404 logged out and renders logged in.
- `/sitemap` → `/sitemap.xml` (301); the XML lists only access 80 and above.
- `/robots.txt` matches the environment; the robots meta says `NOINDEX` on dev.
- The CP loads; saving is blocked after `cp:lock` and works after `cp:unlock`.
- An uploaded test image: the `<source>` URLs return WebP and the fallback URLs PNG or JPEG, at the stated widths.
- The dev panel shows the commit hash, and the design grid lines up with the layout.
- A `production_only` snippet renders on production logged out, and nowhere else.
- `php artisan schedule:list` shows the backup; `./autobackup.sh` with nothing to commit says so and exits 0.

## Final report to the user

What's live and where; the versions installed; every decision (D1 to D8); the helpers-claude commit installed; what was verified and how; and what's still the user's to do.
