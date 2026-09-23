---
name: statamic-upgrade-readiness
description: Read-only audit of a Statamic project and its server against the upgrade target (Laravel 13 + Statamic 6, PHP 8.3+ floor, 8.5 ideal) — PHP and OS status, Composer blockers, S6 landmines, licence and hygiene checks — ending in a route decision (upgrade in place vs rebuild). No installs, no sudo, never prints secrets.
allowed-tools: Read, Glob, Grep, Bash(php -v*), Bash(ls *), Bash(uname *), Bash(cat /etc/os-release), Bash(composer outdated*), Bash(composer show*), Bash(composer audit*), Bash(composer why-not*), Bash(composer check-platform-reqs*), Bash(npm outdated*), Bash(node -v), Bash(git log*), Bash(git status*), Bash(git branch*), Bash(git check-ignore*)
---

# Statamic upgrade readiness

Audit this Statamic project and its server for how far they are from our upgrade target, what's in the way, and which route gets there. READ-ONLY: this pass produces a picture and a decision, never a change. Budget about 3 minutes — thorough enough to be trusted, not a forensic audit. If something is slow or ambiguous, note it and move on.

**If you run short on time, drop checks from the bottom up:** hygiene goes first, then the S6 landmine sweep, then the skeleton and licence checks. Never drop PHP version, the Composer blocker hunt, or the route call — those decide everything.

## The target

Laravel 13 @latest + Statamic 6 @latest, with everything underneath them current too — PHP, Composer packages, Node, npm packages. Ideally PHP 8.5.

The dependency chain that decides everything else:
- Statamic 6 → Laravel 12–13, PHP 8.3–8.5
- Laravel 13 → PHP 8.3–8.5
- So: **PHP 8.3 is a hard floor. Below it, the target is unreachable until PHP moves — treat that as a blocker, not a drift.** PHP 8.5 is fully supported by both and is the aim.

**Where the work actually sits.** Statamic's own 5→6 guide says the upgrade takes minutes for sites already on Laravel 12+. So on a site that's behind, the cost is almost entirely the *Laravel* move (and the PHP move under it), not the Statamic one. Say which of those two this site is, because it changes the size of the job by an order of magnitude.

Frame every gap against this target, not just "a newer version exists."

## Hard rules

- **READ-ONLY.** Install, update, remove or modify nothing: no `composer install/update/require`, no `npm install/ci/update`, no `apt` changes, no edits to composer.json, package.json or lockfiles, no writing files. Allowed because they don't mutate: `composer outdated`, `composer show`, `composer audit`, `composer why-not`, `composer check-platform-reqs`, `npm outdated`, `git log`/`git status`/`git check-ignore`, `grep`. **`composer update --dry-run` is not allowed** — it writes nothing, but it's one typo away from the single genuinely costly mistake on a live box, so it's off the table by policy, not by physics. If unsure whether a command changes state, skip it and say so.
- **NO SUDO.** If a check needs elevation, skip it and record "requires sudo — skipped". Never prompt for a password. This keeps the pass safe to run on a live client box.
- **NEVER PRINT SECRETS — AND USE AN ALLOWLIST, NOT A REDACTION FILTER.** You may read `.env` to find versions, config values and the mailer, but **never run a broad grep or `cat` over `.env` and try to filter the output afterwards** — filters miss things and the value lands in the transcript permanently. Instead, name the exact keys you want:
  - Safe: `grep -E '^(APP_ENV|APP_URL|APP_DEBUG|SESSION_LIFETIME|SESSION_DRIVER|CACHE_STORE|MAIL_MAILER|STATAMIC_PRO_ENABLED|STATAMIC_STATIC_CACHING_STRATEGY)=' .env`
  - For anything sensitive, test for presence and print only a verdict: `grep -qE '^STATAMIC_LICENSE_KEY=.+' .env && echo "licence key set" || echo "not set"`
  - Never echo `APP_KEY`, passwords, tokens, DB or SMTP credentials, licence keys, or API keys — not even partially, not even in passing. The same applies to `auth.json`: report that it exists, never its contents.
  - *This rule is written this firmly because v1 of this prompt leaked a licence key through a `sed` redaction that didn't match.*
- **DON'T INVENT DATES.** Use the reference tables below for support/EOL status. For anything not in them, say "unknown" — a confidently wrong EOL date sends someone chasing the wrong risk. "Unknown" beats a guess.
- **NEVER USE A BARE STATUS DOT.** Every marker carries its word: `🟢 supported`, `🟡 security-only`, `🔴 EOL`, `⚪ unknown`. The dot is for scanning; the word is the meaning. A dot alone is unreadable to anyone with colour vision deficiency and impossible to grep.
- **Prefer reading lockfiles and version files** over invoking tools that might fetch or install. Never run bare `npx <pkg>`.

## First: where are you looking?

One line, up front: can you see the live server, or only the repo on this machine? Running versions live on the box; the repo shows only what's intended, and the two diverge. If repo-only, label every version "declared, not confirmed on server" and list what would need server access (OS release, PHP-FPM version, actual deployed Node).

Also establish, briefly:

- **What's managing this box** — Laravel Forge, Ploi, plain nginx + a deploy script, something else. Look for `/home/forge`, `.forge`, `/etc/nginx/forge-conf`, or a deploy script. It decides how a PHP or OS move actually happens, and whether "rebuild elsewhere" is cheap.
- **Which copy is this, and what else is on the box.** `ls` the parent directory and **enumerate every sibling site**. These estates routinely have two or three copies of the same site on different hosts, plus unrelated sites. Read `APP_ENV` and `APP_URL` to determine role. **State prominently, near the top of the output, which single directory you inspected and which you did not** — auditing a stale dev copy and reporting it as the client's production site is the expensive mistake here. If a production sibling exists and you were pointed at a non-production copy, say so plainly and offer to run the same pass against it.
- **What's actually deployed** — `git log -1 --format='%h %ci %s'`, `git branch --show-current` and `git status --porcelain` (read-only). A repo well ahead of the deployed ref, or uncommitted changes on the box, changes what "the site" even means.

If you're sitting above several site directories rather than inside one, enumerate each and report per-site, kept terse. Say which you inspected and which you skipped and why (no composer.lock → not a deployed app).

## Checks

### Server

- Ubuntu release + LTS status (`/etc/os-release`), kernel (`uname -r`).
- Support status from the table. Note that Ubuntu backports security fixes, so a package whose upstream branch is EOL may still be patched — say so rather than raising a false alarm.
- **Then the route question. The default is: upgrade in place.** A rebuild drags a long tail behind it — DNS, TLS, cron, deploy keys, backup scripts, `.env` reconstruction, shared paths, then decommissioning the old box — and that tail is paid per server, not per upgrade. Assume in place unless one specific fact forces otherwise.
- **The one trigger that opens the question: Ubuntu on ESM or older** (20.04, 18.04, 16.04). The ondrej PHP repo publishes only for Ubuntu LTS releases still in standard support and explicitly excludes ESM releases — so on those boxes there's no supported route to PHP 8.3+, and the choice becomes `do-release-upgrade` (two LTS hops, on a live client site) or rebuild. On 22.04, 24.04 or 26.04, this question doesn't arise: state "in place" and move on.
- If you do call for a rebuild, say which fact forced it. "The OS is old" isn't enough — name the thing that can't be fixed in place. Once a rebuild is forced, stop investigating the in-place PHP path; it isn't available, and the audit's budget is better spent on the app.
- **Distinguish a rebuild forced by the upgrade from a new site created for other reasons.** A move to zero-downtime deployment, or splitting a site off a shared box, also produces "a new site on the VPS" — that is a deployment-architecture decision that may coincide with the upgrade, not a rebuild the upgrade forced. Don't let one get reported as the other.
- **One sequencing note, on 22.04 only.** In place is right for this upgrade, but 22.04's standard support ends 1 Apr 2027, so the OS move is due within the year regardless. Flag it so the two moves get sequenced deliberately — PHP now and OS later, or both together — rather than the box being touched twice by accident.

### PHP

- CLI version (`php -v`) and FPM if reachable — flag if they differ, since the site runs on FPM.
- List all installed versions (`ls /etc/php/`), not just the active one. **This is the cheapest good news in the audit:** if 8.3+ is already installed alongside the active version, the PHP move is a pool switch and a test, not a project.
- **State plainly: is it 8.3+ (the target floor)? Is it 8.5 (the aim)?** This is the single most decisive fact in the audit. Report support status and target-readiness separately — they diverge (PHP 8.2 is `🟡 security-only` and still blocks the target).
- If PHP needs to move, check what supplies it: distro packages or the ondrej/php repo. **Verified 22 July 2026:** ondrej publishes co-installable PHP branches for Ubuntu LTS releases in standard support (22.04, 24.04, 26.04) and explicitly *not* for ESM releases. Distro defaults are 8.1 on 22.04, 8.3 on 24.04, 8.5 on 26.04 — so on 22.04 and 24.04 the target PHP comes from ondrej, not from apt's default.
- **Say plainly how hard the PHP move actually is**, because it's usually much less than it looks: versions are co-installable, so the new PHP goes on beside the old one rather than replacing it, and FPM pools *can* be per site — you can move one site to 8.5 and leave its neighbours on the box untouched, then roll back by pointing the pool at the old version. **But check first whether they are:** on a default Forge box every site shares the single `www` pool (`ls /etc/php/*/fpm/pool.d/`), so moving one site independently means splitting the pool first — a server change with its own rollback story. Note if this box hosts other sites, since that's the thing that makes an in-place move feel risky and this is the answer to it.
- **PHP 8.5 is the aim, not a requirement.** Laravel 13 needs only `^8.3`. A site already on 8.3/8.4 can reach the target with **no server change at all** — peascod did (8.4, 8.5 deferred). Say so when it applies: it keeps root access and rollback out of the upgrade.
- **OPcache timestamps.** `grep -h validate_timestamps /etc/php/*/fpm/php.ini /etc/php/*/fpm/conf.d/* 2>/dev/null`. If `0` on FPM (while CLI is `On`), FPM serves stale bytecode after any in-place code change, and **CLI checks give false positives**. Record it — it decides how the upgrade must be verified (reload PHP, then test over HTTP) and makes any in-place `refresh.sh` actively dangerous.

### Composer + packages

- `composer --version` (1.x is EOL — flag loudly; below 2.9 also means none of the advisory blocking below applies yet).
- `statamic/cms` and `laravel/framework`: installed version vs target. Use `composer show <pkg>` or the lockfile; `php please --version` also gives Statamic.
- `composer outdated --direct` — counts, then the notable ones. Separate safe-within-major from major/breaking.
- **Check composer.json constraints, not just the lockfile** — a constraint ceiling (`^11.0`) blocks a newer release that otherwise exists. Name any you find. Expect the root constraints to be the top result of the blocker hunt below; that's normal.
- **The PHP ceiling hiding in the lockfile.** Locked packages carry their own `php` platform constraints, and an old one with an upper bound (`<8.4`, `<8.5`) will refuse to install on the target PHP even though nothing in composer.json says so. This has bitten us. Cheap check: `grep -o '"php": "[^"]*"' composer.lock | sort -u` and report any constraint with an upper bound below 8.5, with the package that declares it if you can find it quickly. **If there is no such ceiling, say so explicitly** — it's a real piece of good news and worth recording so it isn't re-investigated later.
- **`composer audit`.** Read-only, and more predictive than it looks: since Composer 2.9, versions with known advisories are blocked during resolution by default, so an advisory in the current set means a future `composer update` will *fail*, not warn. Use `composer audit --format=summary` for the count (the full output is long), then the full output only if you need the detail.
  - **Then ask a second question the count doesn't answer: is there a security patch available within the current minor line?** Check the advisories' "affected versions" against the installed version. A site on 5.73.23 where the fix landed in 5.73.24 is one patch short of clearing a CVE — that's an action available *today*, independent of the upgrade window, and it's the highest value-per-effort finding in the whole audit. Report it separately from the upgrade path.
  - **But check the patch is actually installable — the advisory squeeze.** Composer 2.10 refuses to *select* any version affected by an advisory. Find the newest release of `statamic/cms` that still permits the current Laravel major, and check whether *that release itself* carries advisories (`composer show statamic/cms --all` lists versions; the advisories' affected ranges say whether it's clean). On peascod the last Laravel 11-compatible Statamic 5 (5.73.24) had seven advisories, every clean 5.x needed Laravel 12.40+, so **no patch was available without the framework move** — the upgrade *was* the security work. Say which shape this site has; it decides whether "patch now, upgrade later" exists at all. Never suggest `policy.advisories.block: false` as the way round it.
- **The blocker hunt.** `composer why-not laravel/framework 13` and `composer why-not statamic/cms 6` answer this directly — run both and report what they name. Third-party Statamic addons are the usual culprit. These are what hold the target up.
- **Don't cry wolf on known immovables.** Report these as expected, not as blockers:
  - **The root package itself** (`statamic/statamic dev-main requires laravel/framework (^11)`) will head the `why-not` output. That's just the `composer.json` constraint you'd edit as step one — it is not a blocker, and reporting it as one is noise.
  - `guzzlehttp/guzzle` stays on 7 because both laravel/framework and statamic/cms pin it.
  - PHPUnit stays on 12 per Laravel 13's own guidance.
  - `laravel/tinker ^2.x` → `^3.0` and `php ^8.2` → `^8.3` are constraint edits, not blockers.
  - Statamic 6's transitive requirements (`league/glide ^3`, `symfony/lock ^7`, `symfony/var-exporter ^7`, `ueberdosis/tiptap-php ^2`) resolve automatically — list them as consequences, not obstacles.

  *This list is a snapshot and will age — treat it as a prior, and if the evidence in front of you disagrees, say so.*
- **Dev dependencies the upgrade guide doesn't list.** `barryvdh/laravel-debugbar ^3.x` has no Laravel 13 support (needs `^4.4`) and was the only thing blocking peascod's L13 resolve. Name any dev tool that shows up in `why-not`.
- **`laravel/helpers` is load-bearing if anything calls `str_slug`, `array_get`, `array_first` etc.** — grep `app/` and `routes/`. It looks vestigial and Shift may drop it (fatal), and on Laravel 13 `symfony/polyfill-php85` silently overrides `array_first`/`array_last` with a different signature. Count the calls; each is a `Str::`/`Arr::` swap.
- **Addon bindings in `AppServiceProvider`.** `grep -nE 'bind|extend|singleton' app/Providers/AppServiceProvider.php` and note any that name an addon class. A binding required by an addon's old major can be fatal on its new one — peascod bound `Tiptap\Editor` to a bard-mutator v2 class that v3 no longer ships, and every Bard page 500'd. Count, don't investigate.
- **The stepping-stone trap.** Laravel 11 is EOL with unpatched advisories, so Composer's advisory blocking will refuse to resolve to it. A site on Laravel 10 goes 10 → 12 → 13, skipping 11 entirely. Note the route if the site is below 12. **Any Laravel 12 stop must be ≥ 12.40** — Statamic 6 requires it.
- **Addon compatibility is not settled by `composer why-not` alone.** If an addon hooks a subsystem that changed majors underneath it (e.g. a Bard addon over `tiptap-php` 1.x → 2.x), Composer's silence means the constraints allow it, not that it works. Flag such addons for a post-upgrade smoke test.

### Node + npm

- `node -v`, `npm -v`, support status from the table.
- **First decide whether Node matters here, and make it an explicit check, not an impression:** run `git check-ignore public/build` (or the project's build output path) and look for committed compiled output with `git ls-files public/build`.
  - **Gitignored and present on disk → assets are built on the server.** Node is load-bearing: it gates Vite and Tailwind majors, and it must move before or alongside the front-end work. Say so.
  - **Committed / built in CI → the server's Node is largely irrelevant** and shouldn't drive urgency.
  - **Even when assets are built on the server, Node 22.12+ is sufficient for the target front end.** Vite 8 and `laravel-vite-plugin` 3 declare `engines: ^20.19.0 || >=22.12.0`; peascod built them on Node 22.21 with no Node move. Node 24 is a preference (22 is maintenance LTS until 30 Apr 2027), not a blocker — report Node below 20.19 as blocking the front-end step, and 22.12+ as `routine`. Check the actual `engines` field in `node_modules/vite/package.json` if present rather than trusting this line forever.
- `npm outdated` — counts, then notable ones. **Treat its output as unreliable:** in practice it has reported a wrong "latest" and omitted a direct dependency that was two majors behind. Cross-check against the real sources:
  - **`package.json` constraint ceilings** — the npm equivalent of the composer.json check, and the one v1 of this prompt was missing. A `"tailwindcss": "^3.4.3"` is a ceiling in exactly the way `"laravel/framework": "^11"` is. Name any you find.
  - **Resolved versions from `package-lock.json`** for what's actually installed.
- **Vite / laravel-vite-plugin majors.** Target is Vite 8 + plugin 3 (+ Tailwind 4.3). From Vite 7 / plugin 2 this was a constraint bump with an unchanged manifest on peascod — `routine`. Note any leftover `@vitejs/plugin-vue2` import in `vite.config.js` (dead once CP Vue is gone).
- **Tailwind major version.** Statamic 6 moves to Tailwind v4; if this project is on v3 that's a real migration cost, not a version bump. On a site with no other hidden costs this is often the single largest manual item — size it accordingly.
- **Custom Vue in the control panel.** Statamic 6 moves the CP to Vue 3 + Inertia 2. Check `resources/js/cp.js` and any components directory. **Distinguish real components from the commented-out boilerplate Statamic ships** — the stock `cp.js` is entirely commented example code, and reading it as custom Vue would invent a cost that isn't there. If it's all boilerplate, say so: it removes a cost the version table implies.

### Laravel skeleton state (quick)

Is this on the pre-11 skeleton (`app/Http/Kernel.php`, `app/Console/Kernel.php`, a fat `app/Providers/`) or the slim one (`bootstrap/app.php`)? The slim migration is separate work from the version bump, it's the usual route via Laravel Shift, and on a Statamic site it needs the `config/` directory reconciling afterwards. One line: which skeleton, and whether `config/` looks like current Laravel + Statamic conventions or has drifted.

**Then make the Shift call, because it changes the cost and the risk:**
- **Slim skeleton + small app** → recommend doing the Laravel steps **by hand, no Shift.** Measure it: `find app routes bootstrap -name '*.php' -not -path 'bootstrap/cache/*' | xargs wc -l | tail -1`. Under a few hundred lines, Laravel's own guides put 11→12 at ~5 minutes and 12→13 at ~10, and hand-editing removes the estate's dominant upgrade failure (below) rather than mitigating it. Peascod: ~250 lines, `config/` untouched across three framework steps.
- **Pre-slim** → Shift is right for the flatten, **and** the plan needs a line-by-line `config/` diff after every Shift run.
- **Either way, list the config defaults Shift is known to streamline away**, since they fail silently: `config/app.php` `name` and `timezone` defaults where `.env` sets no `APP_NAME` / `APP_TIMEZONE` (check presence with `grep -cE '^APP_(NAME|TIMEZONE)=' .env`), the `config/statamic/users.php` auth driver (CP login), `config/filesystems.php` `default`/`public`/`links`/cloud disks, all of `config/statamic/*`, and the `please` binary.

### Statamic edition & licence (quick)

- Pro or Solo/Core (`config/statamic/editions.php` or `STATAMIC_PRO_ENABLED`), and whether a licence key is present in `.env` — **presence only, never the value; use the `grep -q ... && echo` form from the hard rules**.
- If the plan involves validating on a temporary hostname, note that Statamic's licence domain check treats obviously-dev hostnames (`dev.`, `test.`, `staging.`, `.test`, `.local`) as non-public, but an arbitrary test domain is treated as public and will nag in the CP. Worth a line if a temp vhost is likely; don't investigate further.
- If Pro is enabled but no `auth.json` exists in the project or `~/.composer/`, note it — it's worth understanding how the Pro packages authenticate before the first `composer update` on a new site.

### Statamic 5 → 6 landmine sweep (bounded — one pass, hits only)

These are cost signals, not blockers. Count them, name them, fix nothing. Cap the output; if a pattern has many hits, say "many" and move on. **Report the clean results too** — a landmine list where most items came back clear is itself the finding, and recording it stops the next session re-checking. From Statamic's own 5→6 guide:

- **Timezone** — `config/app.php` `timezone` not `UTC` *and* the site has **dated collections (`date: true`), `type: date` fields, or dated entry filenames**. In v6 dates convert to UTC at runtime; the real bite (tom-hammick, statamic/cms#14122) is date-only entries gaining a `-0000` filename suffix on save during BST, which autobackup then commits as renames twice a year. Highest-impact item when the preconditions hold. **`date_behavior:` without `date: true` is inert — a false positive peascod's first audit fell for.** If it applies, tom-hammick's 28-line `App\Entries\Entry::hasTime()` override is the fix.
- **Carbon** — `nesbot/carbon` major in the lockfile; v6 requires Carbon 3. Note anything pinning Carbon 2.
- **Search config** — `'searchables' => 'all'` in `config/statamic/search.php`. Deliberately not auto-migrated, so it's guaranteed manual work.
- **`statamic` cache driver** in `config/cache.php` (removed in v6). **Grep for the driver, not the word** — a bare `grep statamic config/cache.php` false-positives on static-cache *paths* like `storage_path('statamic/static-urls-cache')`. Look for a `'statamic'` store key or `'driver' => 'statamic'`.
- **Users in the database** — `config/statamic/users.php` repository set to `eloquent` rather than file. If so, v6 adds 2FA/passkey migrations to run.
- **CP icon names.** v6 replaced the icon set; a stale `icon:` renders as a blank with no error and a sweep of `app/` for icon APIs misses it entirely. A pre-upgrade `vendor/` only holds the v5 icon set, so the audit can't resolve them yet: count the distinct `icon:` values in `resources/fieldsets` and `resources/blueprints` (`grep -rhoE '^\s*icon: [a-z0-9._-]+' resources/ | sort -u | wc -l`), and put a post-bump check against `vendor/statamic/cms/resources/svg/icons` into the plan. Replicator/Bard set *groups* carry icons one level above the sets, and fieldtype icons gained a `fieldtype-` prefix.
- **Globals** — `content/globals/*.yaml` with a `data:` key will be migrated to per-site dirs during `composer update`. Not a cost, but the plan must include `php please stache:clear` straight after, or every global silently resolves empty.
- **Templates/JS greps:** `moment` (removed), `relate` tag, `{{ session:` / `{{ cookie:` / `{{ nav:` / `{{ redirect:` wildcard form, `urlencode`, `where('status'`, `type: section` fieldtypes, custom Glide manipulators, Algolia.
- For any hit, check whether the feature is actually *in use* before sizing it — a stale Algolia config block in a site that doesn't use Algolia is a deletion, not a migration.

### Config hygiene (quick, drop first if short on time)

Cheap checks that consistently surface real problems adjacent to the upgrade:

- **Session lifetime and driver.** `SESSION_LIFETIME` and `SESSION_DRIVER` from `.env`. With the `file` driver, a very long lifetime accumulates files indefinitely. If it looks long, quantify it: `ls storage/framework/sessions | wc -l` and `du -sh storage/framework/sessions`. A count in the tens of thousands is worth reporting.
- **Session GC.** `grep -n lottery config/session.php`. `[2, 100]` with a large session dir is the 2026-09-04 outage shape (in-request GC walking 1.4 M files past nginx's 60 s timeout). Note it; don't redesign it.
- **Static caching.** `STATAMIC_STATIC_CACHING_STRATEGY` and `STATAMIC_BACKGROUND_RECACHE` (allowlist grep), plus `grep -n ignore_query_strings config/statamic/static_caching.php` — `half` caches 200s *and* 404s forever, so `false` leaves bot query strings growing the cache unbounded. `APP_DEBUG=true` or `LOG_LEVEL=debug` in production is a finding.
- **Backup & deploy scripts.** Read `autobackup.sh` if present: flag `git add .`, a `:!storage` pathspec (exits 1 under `set -e` on an ignored path), `optimize:clear` (outage contributor), a hard-coded webhook URL (credential — report presence only). Flag a `refresh.sh` on a zero-downtime site. `git check-ignore -q storage auth.json public/build` and `git status --porcelain` from inside `current/` — anything spurious means the backup cron is committing deploy artefacts.
- **Sitemap.** `grep -n sitemap routes/web.php` and the sitemap template: canonical should be `/sitemap.xml` with `/sitemap` 301ing to it, and `<loc>` should use `{{ permalink }}` (peascod's used a non-existent `config:app:app_url` key, so every `<loc>` was relative). One `curl -s https://<site>/sitemap.xml | grep -c '<loc>/'` settles it — non-zero means relative URLs.
- **nginx headers and asset caching** (read-only HTTP from the box is fine). Compare `curl -sI` on a page, a hashed asset under `/build/` or `/vendor/statamic/cp/build/`, and a 404: all three should carry `X-Frame-Options`, and the hashed asset should have a long `Cache-Control`. Missing on assets = `add_header` in a location block dropping inherited headers; missing on the 404 = no `always`. Both were in the template the estate copies. Without asset caching the v6 CP (558 code-split files) will feel slow and get blamed on Statamic.
- **TLS renewal.** `ls /etc/cron.d/ | grep letsencrypt` and compare against the site's domains; `ls -la ~/.letsencrypt-renew/*.out` should show weekly timestamps. Forge once issued a peascod cert without a renewal cron and it silently expired. One line.
- **Storage footprint.** `du -sh storage/*` sorted, plus `df -h /`. One line. Distinguishes hygiene from emergency.
- **Env template drift.** If the project keeps env templates (e.g. `docs/*.env`), check whether a bad value appears in the templates as well as the live `.env` — a wrong setting in the template will be reintroduced on the next site build, so the fix has two homes.

### Email (quick check, early exit)

Email is rarely configured on these servers, so this is a confirm-the-expected check, not an investigation. Read `MAIL_MAILER` (or legacy `MAIL_DRIVER`) from `.env` — value only, no credentials.

- `log`, `array`, unset or empty → inert. One line: "email not configured." **Stop there, no further discovery.**
- A real transport (`smtp`, `mailgun`, `ses`, `postmark`, `resend`) → unexpected. Note the transport type and that live credentials are present in `.env` (never the values). Still don't go deeper in this pass — just flag it.
- No `.env` in the directory → fall back to `config/mail.php` default and say it's the config default, not confirmed runtime.

## Estate conventions

Standing facts about how we run these sites. Apply them when sizing work and when recommending a route; flag anything on this site that contradicts them.

- **Hosting** is Laravel Forge on DigitalOcean droplets. Multiple sites commonly share a box.
- **Deployment** is Forge zero-downtime (`current -> releases/…`, shared `.env`, `storage`, `auth.json`, `public/robots.txt`), with Quick Deploy. Where a site is still on the older model, expect a `refresh.sh`-style script doing maintenance mode + install + build + cache warm; that becomes redundant under zero-downtime, and is dangerous where FPM has `validate_timestamps=0`. The estate deploy script (peascod `docs/forge-deploy.md`, adapted from tom-hammick) is: `[BOT]` commit guard → `cp:lock` → `$CREATE_RELEASE()` → `composer install --no-dev` → `npm ci && npm run build` → `artisan optimize` → `storage:link` → `stache:refresh` → `search:update --all` → `$ACTIVATE_RELEASE()` → `cp:unlock` → `cache:clear` → `static:clear` → `static:warm`. Keep scripts consistent across sites rather than adding per-site guards. It needs **`wesort/statamic-cp-lock`** installed (vcs repo entry) — note if absent.
- **Content vs deploys.** `content/` is per-release and Statamic git integration is off, so a CP edit between the last backup and a deploy is lost. Note whether this site has the same exposure; don't redesign it in the audit.
- **Backups** run from a Forge scheduled `autobackup.sh`, **run from `~/<site>/current`**, committing `[BOT] Automatic backup via cronjob` to GitHub. House convention (lcva-v2 `228c0a3`, peascod `42533dd`): **stage an allowlist, `git add -A -- content users resources public`**, mirroring `config/statamic/git.php`. *Not* `git add .`, and *not* `git add -A -- ':!storage'` — naming an ignored path exits 1 and `set -e` aborts before the commit (tested). No `optimize:clear`, no `artisan optimize`, no `static:warm --queue` on a sync queue, no webhook URL in the file. Author read from `STATAMIC_GIT_USER_NAME`/`_EMAIL` (defaults `wesort`); author/committer split is **still an open estate decision** — don't report a site as "wrong" on it.
- **`.gitignore`** must ignore `/storage` and `auth.json` (plus `/public/build`, `/public/robots.txt`), with no `storage/**/.gitignore` skeleton tracked — otherwise the backup cron commits Forge symlinks.
- **Session lifetime** is `SESSION_LIFETIME=10080` (7 days), `SESSION_DRIVER=file`. *(v2 said 43200; 30 days was rejected on 2026-09-05 after measuring ~8,300 bot sessions/day → ~250 k files and a 25 s concurrent GC scan vs nginx's 60 s timeout. 7 days settles ~58 k files.)* Anything above 7 days is a finding; near a year is an incident waiting to happen. Fix `docs/*.env` too.
- **Static caching** in production is the `half` strategy with `STATAMIC_BACKGROUND_RECACHE=true` and `ignore_query_strings => true`. Development runs no static caching.
- **`STATAMIC_STACHE_WATCHER`** is `true` on development, `false` in production. `APP_DEBUG=false` on both; `LOG_LEVEL=warning` in production.
- **Redis and queues are not assumed.** Peascod runs `QUEUE_CONNECTION=sync`, `CACHE_STORE=file`, Redis installed but deliberately inactive; tom-hammick uses a Redis queue. Report which this site is — it changes the deploy script (`$RESTART_QUEUES()`, `static:warm --queue`) — and don't recommend Redis.
- **Email** is intentionally unconfigured on these boxes.
- **nginx** carries the security headers with `always`, repeated inside the hashed-asset `location` (`^/(build|vendor/statamic/cp/build)/` → `expires 1y`, `public, immutable`), other static files `expires 1y` with no `add_header`, and `application/json` in `gzip_types`. Applied through the Forge UI per site, verified with `sudo nginx -t` — not edited on disk.
- **Sitemap** is served at `/sitemap.xml` with `/sitemap` 301ing to it, `<loc>{{ permalink }}</loc>`, hidden entries excluded.
- **`APP_KEY` / licence key in `docs/*.env`** is accepted practice on private repos (peascod, confirmed with the client). Record presence as known; don't re-raise it as a finding unless repo access has widened.
- **Documentation** lives in `docs/`. Ask for the intended reference/structure before rewriting it rather than inventing one. The transferable upgrade write-up is peascod's `docs/upgrade-playbook.md`.
- **Laravel Shift** is the accepted route for the pre-slim skeleton flatten and Tailwind 3→4. **On a slim skeleton with a small app, do the Laravel steps by hand** (see skeleton check). Route order: housekeeping → Laravel 12 (≥12.40) → **Statamic 6 on the Laravel 12 bridge** → Laravel 13 → front end isolated → cutover.
- **Don't adopt Laravel 13 skeleton defaults wholesale:** `session.serialization => json` logs everyone out; `cache.serializable_classes => false` likely breaks the Stache. Flag if a Shift has already applied them.

*Keep this section updated as conventions change — it's the part of this prompt with the shortest shelf life.*

## Then: the blockers

For each area, state whether reaching the target is **routine**, **needs care**, or **blocked** — and why. Look for the cross-cutting ones specifically:

- PHP below 8.3 → blocks the whole target, regardless of its support status.
- Ubuntu on ESM or older, so ondrej won't supply PHP 8.3+ — the only case where the OS itself blocks the target rather than merely being old. On a supported LTS, an outdated PHP is a task, not a blocker.
- A direct package or Statamic addon with no L13/S6-compatible release (`composer why-not` names these — discounting the root package).
- A locked package with a PHP upper bound below the target PHP.
- An existing advisory in the current dependency set that will stop `composer update` resolving at all.
- Tailwind v3 → v4, or custom Vue 2 CP components — cost that a version table hides.
- A composer.json or package.json constraint acting as the real ceiling.
- Pre-slim Laravel skeleton — not a blocker, but separate work with its own route.
- **An addon with no stable S6 release — check what it actually does on this site's config before calling it a blocker.** Peascod's `duncanmcclean/static-cache-manager` (archived, alpha-only on v6) only acts on `full` caching; the site ran `half`, so it was inert and was simply removed.

**Also report the costs that turned out to be absent.** A slim skeleton small enough to skip Shift, no custom CP Vue, Carbon already on 3, no lockfile PHP ceiling, PHP already ≥ 8.3 (no server change), Node already ≥ 22.12, an inert addon that can simply be dropped — each is a cost the version table implies and the evidence rules out. These change the size estimate as much as the blockers do, and stating them stops the next person re-investigating.

## Output

Default to replying inline only — no report file, no changes proposed. **If the requester asks for a written record, write it to `docs/` following the conventions above.**

1. **One-line verdict:** how far is this project from Laravel 13 + Statamic 6, and what's the single biggest thing in the way? If nothing actually blocks, say that plainly and name the largest *cost* instead.
2. **Scope, stated prominently:** which directory you inspected, which sibling sites exist on the box and were not inspected, and each one's role. Put this near the top, not in a footnote.
3. **Route & size:** in place (the default) or, exceptionally, rebuild and migrate — and if rebuild, the specific fact that forces it. Distinguish a forced rebuild from a new site created for deployment reasons. Then a rough size (small / medium / large) and where the work sits: the Laravel move, the PHP move, the front-end move, or genuinely just the Statamic bump.
4. **Table:** Component | Running (or declared) | Target | Gap | Support status | Target verdict
   - Support status uses the labelled markers: `🟢 supported`, `🟡 security-only`, `🔴 EOL`, `⚪ unknown`.
   - Target verdict is plain words: `routine`, `needs care`, `blocked`. Never a dot.
   - These two columns will disagree — that's the point. Something can be `🟡 security-only` and still `blocked`.
5. **Blockers** — in prose. This is the part that matters most: not "you're N behind" but "here's what stands in the way and roughly what it'd take." Include the costs ruled out, not just the ones found.
6. **Available now** — anything actionable today, independent of the upgrade window. A security patch within the current minor line is the common case — **but only if it survives the advisory squeeze; say explicitly if it doesn't**. Config hygiene (session lifetime, `APP_DEBUG`, nginx headers, sitemap, backup script) is the other.
7. **Hidden costs** — landmine sweep hits, skeleton state and the Shift call, Tailwind/Vue, addon bindings, `laravel/helpers` calls, icon count. Counted, not fixed. Record the clean results too.
7a. **Traps to put in the plan** — one line each, only those that apply: reload PHP before trusting any HTTP check (`validate_timestamps=0`); `stache:clear` after the globals migration; don't verify URL-dependent behaviour via tinker `app()->handle()` (the `Cascade` singleton keeps `/`); first zero-downtime deploy across a major can leave a route cache with no `statamic.cp.*` routes → `php artisan optimize:clear`; comment out `cp:lock` on the first deploy if the live release lacks the addon.
8. **Email:** one line.
9. **Couldn't confirm:** what was skipped (sudo, no server access, sibling sites) and what's unknown.

Keep it scannable. Show reasoning where a verdict isn't obvious, name assumptions as assumptions, and flag ambiguity rather than guessing.

## Reference: a site that's already there (July 2026)

Useful as a sanity anchor for "what does done look like" — versions observed on a completed upgrade, not a spec:

PHP 8.5.8 · Composer 2.10 · Node 22 · Laravel 13.21 · Statamic 6.26 · Vite 8.1 · laravel-vite-plugin 3.1 · Tailwind 4.3 · Alpine 3.15.

Second anchor — **peascod.studio, 5 Sep 2026**, from Laravel 11.46.1 + Statamic 5.67.0 in one day, no Shift, assets built on the server:

PHP 8.4.14 · Composer 2.10.3 · Node 22.21 · Laravel 13.30.1 · Statamic 6.31.0 · Vite 8.2.2 · laravel-vite-plugin 3.2.0 · Tailwind 4.3 · bard-mutator 3.0.5 · cp-lock 1.1.0. `composer audit` 78 → 0, `npm audit` 3 → 0.

Note Node 22 on both: `🟡 maintenance LTS`, and **sufficient even where assets are built on the server** (Vite 8 needs `>=22.12.0`). Node 24 is the preference when a Node move is happening anyway, not a reason to schedule one. Likewise PHP 8.4 reaches the target; 8.5 is the aim.

## Reference: support & EOL (verified 22 July 2026)

Treat as authoritative for this pass; no network lookups needed. If today's date is materially later than the above, say the table may have moved on.

Markers: `🟢 supported` = in full support · `🟡 security-only` = security fixes only, or full support ends within ~12 months · `🔴 EOL` = no security fixes (or paid ESM only) · `⚪ unknown` = not verified, say so rather than guess. Always write the word with the dot.

**Laravel** (18mo bug fixes, 24mo security)

| Ver | Released | Bug fixes end | Security ends | PHP | Status |
|---|---|---|---|---|---|
| 13 | 17 Mar 2026 | 30 Sep 2027 | 17 Mar 2028 | 8.3–8.5 | 🟢 supported — **TARGET** |
| 12 | 24 Feb 2025 | 16 Aug 2026 | 24 Feb 2027 | 8.2–8.5 | 🟡 security-only from Aug 2026 |
| 11 | 12 Mar 2024 | 3 Sep 2025 | 12 Mar 2026 | 8.2–8.4 | 🔴 EOL — **skip, don't step through** |
| 10 | 14 Feb 2023 | 6 Aug 2024 | 4 Feb 2025 | 8.1–8.3 | 🔴 EOL |
| 9 | 8 Feb 2022 | 8 Aug 2023 | 6 Feb 2024 | 8.0–8.2 | 🔴 EOL |
| 8 | 8 Sep 2020 | 26 Jul 2022 | 24 Jan 2023 | 7.3–8.1 | 🔴 EOL |
| 7 | 3 Mar 2020 | 6 Oct 2020 | 3 Mar 2021 | 7.2–8.0 | 🔴 EOL |
| 6 LTS | 3 Sep 2019 | 25 Jan 2022 | 6 Sep 2022 | 7.2–8.0 | 🔴 EOL |
| 5.8 | 26 Feb 2019 | 26 Aug 2019 | 26 Feb 2020 | 7.1–7.3 | 🔴 EOL |
| 5.5 LTS | 30 Aug 2017 | 30 Aug 2019 | 30 Aug 2020 | 7.0–7.1 | 🔴 EOL |
| 5.0–5.4 | 2015–2017 | — | all long past | 5.5–7.1 | 🔴 EOL |

**Statamic** (≥12mo bug fixes, ≥18mo security)

| Ver | Released | Bug fixes end | Security ends | Laravel | PHP | Status |
|---|---|---|---|---|---|---|
| 6 | 28 Jan 2026 | 31 Mar 2027 | 31 Dec 2027 | 12–13 | 8.3–8.5 | 🟢 supported — **TARGET** |
| 5 | 9 May 2024 | 31 Mar 2026 | **31 Dec 2026** | 10–12 | 8.2–8.4 | 🟡 security-only — deadline |
| 4 | 9 May 2023 | 31 May 2024 | 30 Sep 2024 | 9–10 | 8.0–8.3 | 🔴 EOL |
| 3.4 | 27 Jan 2023 | 31 Jan 2023 | 31 Jul 2024 | 8–9 | 7.4–8.1 | 🔴 EOL |
| 3.3 | 14 Mar 2022 | 31 Mar 2023 | 30 Sep 2023 | 8–9 | 7.4–8.1 | 🔴 EOL |
| ≤3.2, v2 | 2015–2021 | not tracked by endoflife.date | | | | ⚪ unknown, but long 🔴 EOL |

**Note the deadline: Statamic 5 loses security support 31 Dec 2026.** If this site is on 5, that's the clock the plan runs against.

**PHP** — two columns, because support status and target-readiness diverge

| Ver | Released | Active support ends | Security ends | Support status | vs L13 floor (8.3) |
|---|---|---|---|---|---|
| 8.5 | 20 Nov 2025 | 31 Dec 2027 | 31 Dec 2029 | 🟢 supported | **the aim** |
| 8.4 | 21 Nov 2024 | 31 Dec 2026 | 31 Dec 2028 | 🟢 supported | OK |
| 8.3 | 23 Nov 2023 | 31 Dec 2025 | 31 Dec 2027 | 🟡 security-only | at floor — OK |
| 8.2 | 8 Dec 2022 | 31 Dec 2024 | 31 Dec 2026 | 🟡 security-only | **below floor — blocked** |
| 8.1 | 25 Nov 2021 | 25 Nov 2023 | 31 Dec 2025 | 🔴 EOL | **below floor — blocked** |
| 8.0 | 26 Nov 2020 | 26 Nov 2022 | 26 Nov 2023 | 🔴 EOL | **below floor — blocked** |
| 7.4 | 28 Nov 2019 | 28 Nov 2021 | 28 Nov 2022 | 🔴 EOL | **below floor — blocked** |
| 7.3 | 6 Dec 2018 | 6 Dec 2020 | 6 Dec 2021 | 🔴 EOL | **below floor — blocked** |
| 7.2 | 30 Nov 2017 | 30 Nov 2019 | 30 Nov 2020 | 🔴 EOL | **below floor — blocked** |
| 7.1 | 1 Dec 2016 | 1 Dec 2018 | 1 Dec 2019 | 🔴 EOL | **below floor — blocked** |
| 7.0 | 3 Dec 2015 | 4 Jan 2018 | 10 Jan 2019 | 🔴 EOL | **below floor — blocked** |
| 5.6 | 28 Aug 2014 | 19 Jan 2017 | 31 Dec 2018 | 🔴 EOL | **below floor — blocked** |

**Ubuntu** (LTS: 5yr standard, +5yr ESM via Pro)

| Release | Released | Standard support ends | ESM ends | Status |
|---|---|---|---|---|
| 26.04 LTS Resolute | 23 Apr 2026 | 30 Apr 2031 | 30 Apr 2036 | 🟢 supported |
| 25.10 | 9 Oct 2025 | 1 Jul 2026 | — | 🔴 EOL |
| 25.04 | 17 Apr 2025 | 17 Jan 2026 | — | 🔴 EOL |
| 24.10 | 10 Oct 2024 | 10 Jul 2025 | — | 🔴 EOL |
| 24.04 LTS Noble | 25 Apr 2024 | 31 May 2029 | 31 May 2036 | 🟢 supported |
| 23.10 / 23.04 | 2023 | Jul 2024 / Jan 2024 | — | 🔴 EOL |
| 22.10 | 20 Oct 2022 | 20 Jul 2023 | — | 🔴 EOL |
| 22.04 LTS Jammy | 21 Apr 2022 | **1 Apr 2027** | 9 Apr 2032 | 🟡 supported, ends in ~8mo |
| 21.10 / 21.04 | 2021 | Jul 2022 / Jan 2022 | — | 🔴 EOL |
| 20.10 | 22 Oct 2020 | 22 Jul 2021 | — | 🔴 EOL |
| 20.04 LTS Focal | 23 Apr 2020 | 31 May 2025 | 2 Apr 2030 | 🔴 EOL unless Ubuntu Pro |
| 19.10 / 19.04 | 2019 | Jul 2020 / Jan 2020 | — | 🔴 EOL |
| 18.10 | 18 Oct 2018 | 18 Jul 2019 | — | 🔴 EOL |
| 18.04 LTS Bionic | 26 Apr 2018 | 31 May 2023 | 1 Apr 2028 | 🔴 EOL unless Ubuntu Pro |
| 17.10 / 17.04 / 16.10 | 2016–17 | all 2017–18 | — | 🔴 EOL |
| 16.04 LTS Xenial | 21 Apr 2016 | 2 Apr 2021 | 2 Apr 2026 (ended) | 🔴 EOL — ESM also expired |
| 15.10 / 15.04 | 2015 | Jul 2016 / Feb 2016 | — | 🔴 EOL |
| 14.04 LTS Trusty | 17 Apr 2014 | 2 Apr 2019 | 2 Apr 2024 (ended) | 🔴 EOL — ESM also expired |

**Node.js** (even majors → LTS; production should run Active or Maintenance LTS)

| Ver | Released | Active support ends | Security ends | Status |
|---|---|---|---|---|
| 26 LTS | 5 May 2026 | 27 Oct 2027 | 30 Apr 2029 | 🟢 supported |
| 25 | 15 Oct 2025 | 1 Apr 2026 | 1 Jun 2026 | 🔴 EOL |
| 24 LTS | 6 May 2025 | 20 Oct 2026 | 30 Apr 2028 | 🟢 supported |
| 23 | 16 Oct 2024 | 1 Apr 2025 | 1 Jun 2025 | 🔴 EOL |
| 22 LTS | 24 Apr 2024 | 21 Oct 2025 | 30 Apr 2027 | 🟡 maintenance LTS |
| 21 | 17 Oct 2023 | 1 Apr 2024 | 1 Jun 2024 | 🔴 EOL |
| 20 LTS | 18 Apr 2023 | 22 Oct 2024 | 30 Apr 2026 | 🔴 EOL |
| 19 | 18 Oct 2022 | 1 Apr 2023 | 1 Jun 2023 | 🔴 EOL |
| 18 LTS | 19 Apr 2022 | 18 Oct 2023 | 30 Apr 2025 | 🔴 EOL |
| 16 LTS | 20 Apr 2021 | 18 Oct 2022 | 11 Sep 2023 | 🔴 EOL |
| 14 LTS | 21 Apr 2020 | 19 Oct 2021 | 30 Apr 2023 | 🔴 EOL |
| 12 LTS | 23 Apr 2019 | 20 Oct 2020 | 30 Apr 2022 | 🔴 EOL |
| 10 LTS | 24 Apr 2018 | 19 May 2020 | 30 Apr 2021 | 🔴 EOL |
| 8 LTS | 30 May 2017 | 1 Jan 2019 | 31 Dec 2019 | 🔴 EOL |
| 6 LTS | 26 Apr 2016 | 30 Apr 2018 | 30 Apr 2019 | 🔴 EOL |
| 4 LTS | 9 Sep 2015 | 1 Apr 2017 | 30 Apr 2018 | 🔴 EOL |

**npm** — no published EOL calendar; it ships bundled with Node. Judge it by the Node it came with rather than inventing a support date; report as `⚪ unknown` on its own. Flag npm only if the Node underneath it is 🔴 EOL.

**Composer** — 1.x is 🔴 EOL, flag it. 2.x is current; 2.9 introduced advisory blocking during resolution and 2.10 added malware blocking that applies even to `composer install` from an existing lockfile. *Not verified against endoflife.date in this pass* — report the installed version and mark it `⚪ unknown` rather than asserting a date.

---

## What changed in v2

Each change traces to something the v1 run got wrong, nearly missed, or spent effort re-deriving.

**Corrections to rules**

1. **Secret handling rewritten from redaction to allowlist.** v1 said "never print secrets"; the run then leaked a licence key through a `sed` filter that didn't match the line. v2 bans broad greps over `.env` outright and gives the exact safe forms.

**New checks**

2. **Security patch within the current minor line.** v1 asked for the advisory count but not whether a fix was available *without* the upgrade. The site was one patch short of clearing two CVEs — the highest value-per-effort finding available, and v1 wouldn't have asked for it.
3. **`package.json` constraint ceilings.** v1 checked `composer.json` constraints but had no npm equivalent, so a `^3.4.3` Tailwind ceiling would go unnamed.
4. **`npm outdated` marked unreliable.** In the run it reported a wrong "latest" for Vite and omitted `laravel-vite-plugin` entirely despite it being two majors behind.
5. **Config hygiene section** (sessions, storage footprint, env template drift). Not in v1. Surfaced 16,976 session files at 68 MB from a 365-day lifetime — and the bad value was in the env *templates* too, so it would have been rebuilt into the next site.
6. **`auth.json` absent while Pro is enabled** — worth flagging before a first `composer update` on a new site.

**Sharpened to prevent specific errors**

7. **Root package excluded from the blocker hunt.** `composer why-not` heads its output with the project's own `composer.json` constraint. v1's "don't cry wolf" list didn't cover it, inviting it to be reported as a blocker.
8. **Node relevance made an explicit command** (`git check-ignore public/build`), and the reference anchor's Node 22 caveat narrowed — it only holds when the server *isn't* building assets, which is the opposite of the case found.
9. **Cache driver grep corrected.** A bare `grep statamic config/cache.php` false-positives on `storage_path('statamic/static-urls-cache')`. It did.
10. **Stock `cp.js` boilerplate called out.** Statamic ships a fully commented-out example; reading it as custom Vue would invent a migration cost that doesn't exist.
11. **Addon compatibility caveat.** `composer why-not` silence means constraints allow it, not that it works — relevant where an addon sits over a subsystem that changed majors.
12. **Rebuild vs. new-site-for-other-reasons** separated, so a zero-downtime migration doesn't get reported as an upgrade-forced rebuild.
13. **Scope reporting promoted** to its own numbered output section near the top, with sibling enumeration required. v1 buried it and the run was against a dev copy.

**New output**

14. **"Available now" section** — actions independent of the upgrade window.
15. **Report costs ruled out, not just costs found.** Slim skeleton, no CP Vue, Carbon already 3, no lockfile PHP ceiling — four absent costs that moved the estimate as much as any blocker, and recording them stops re-investigation.
16. **Record clean landmine results**, for the same reason.
17. **Verdict wording** — allow for "nothing blocks", which was the actual answer and didn't fit v1's framing.
18. **Deliverable made configurable** — inline by default, `docs/` on request.

**New section**

19. **Estate conventions** — standing facts (Forge/DO, zero-downtime, `autobackup.sh` staging and authorship, session lifetime, static caching, stache watcher, email, docs, Laravel Shift) so they inform sizing on every site instead of being re-established each time.

---

## What changed in v3

From the peascod.studio upgrade (4–16 Sep 2026): the first site taken all the way through after a v2 audit. Each item is something v2 got wrong, or that cost time and wasn't asked.

**Corrections**

1. **Session lifetime convention 43200 → 10080.** 30 days was measured and rejected in favour of 7.
2. **Autobackup staging `':!storage'` → allowlist.** The `:!storage` form exits 1 under `set -e` on an already-ignored path — tested.
3. **"FPM pools are per site" qualified.** Default Forge boxes share the `www` pool, so a per-site PHP move means splitting it first.
4. **Node 24 on build boxes downgraded from target to preference.** Vite 8 / plugin 3 accept `>=22.12.0`; peascod built on 22.21.
5. **The "patch within the current minor" check now tests installability.** v2's highest value-per-effort finding turned out to be uninstallable: Composer 2.10 refuses advisory-affected versions, and every Laravel 11-compatible Statamic 5 had advisories.
6. **Timezone landmine tightened.** `date_behavior` without `date: true` was a false positive in the peascod audit.
7. **Shift is no longer the default Laravel route.** On a small slim-skeleton app, by hand removes the config-dropping failure mode entirely.

**New checks**

8. The Shift call with a line count, and the silent config defaults Shift drops (`app.name`, `timezone`, auth driver, disks, `please`).
9. `laravel/helpers` usage and the `polyfill-php85` `array_first` collision; addon bindings in `AppServiceProvider` (the one real breakage on peascod); `laravel-debugbar` blocking L13; Laravel 12 stop must be ≥ 12.40.
10. OPcache `validate_timestamps` on FPM — decides how verification must be done.
11. CP icon names (silent blanks; missed by an `app/` sweep) and the globals `stache:clear` requirement.
12. Config hygiene: session lottery, static-caching env + `ignore_query_strings`, `APP_DEBUG`/`LOG_LEVEL`, `autobackup.sh` / `refresh.sh` / `.gitignore` contents, sitemap canonical URL and absolute `<loc>`, nginx headers + asset caching on page/asset/404, Let's Encrypt renewal cron.
13. Inert addons: check what a "blocking" addon does on this site's config before sizing it.

**New output**

14. **7a. Traps to put in the plan** — stale bytecode, globals stache, tinker `Cascade`, first-deploy route cache, `cp:lock` on first deploy.
15. Second reference anchor (peascod) showing a no-server-change upgrade on PHP 8.4 / Node 22.

**Estate conventions expanded** — zero-downtime deploy script order, content-vs-deploy exposure, `.gitignore`, Redis/queue as a per-site fact rather than an assumption, nginx, sitemap, `APP_KEY`-in-templates acceptance, skeleton defaults not to adopt, route order.
