Audit this Statamic project and its server for how far they are from our upgrade target, what's in the way, and which route gets there. READ-ONLY: this pass produces a picture and a decision, never a change. Budget about 3 minutes — thorough enough to be trusted, not a forensic audit. If something is slow or ambiguous, note it and move on.

**If you run short on time, drop checks from the bottom up:** the S6 landmine sweep goes first, then the skeleton and licence checks. Never drop PHP version, the Composer blocker hunt, or the route call — those decide everything.

## The target (as of July 2026)

Laravel 13 @latest + Statamic 6 @latest, with everything underneath them current too — PHP, Composer packages, Node, npm packages. Ideally PHP 8.5.

The dependency chain that decides everything else:
- Statamic 6 → Laravel 12–13, PHP 8.3–8.5
- Laravel 13 → PHP 8.3–8.5
- So: **PHP 8.3 is a hard floor. Below it, the target is unreachable until PHP moves — treat that as a blocker, not a drift.** PHP 8.5 is fully supported by both and is the aim.

**Where the work actually sits.** Statamic's own 5→6 guide says the upgrade takes minutes for sites already on Laravel 12+. So on a site that's behind, the cost is almost entirely the *Laravel* move (and the PHP move under it), not the Statamic one. Say which of those two this site is, because it changes the size of the job by an order of magnitude.

Frame every gap against this target, not just "a newer version exists."

## Hard rules

- **READ-ONLY.** Install, update, remove or modify nothing: no `composer install/update/require`, no `npm install/ci/update`, no `apt` changes, no edits to composer.json, package.json or lockfiles, no writing files. Allowed because they don't mutate: `composer outdated`, `composer show`, `composer audit`, `composer why-not`, `composer check-platform-reqs`, `npm outdated`, `git log`/`git status`, `grep`. **`composer update --dry-run` is not allowed** — it writes nothing, but it's one typo away from the single genuinely costly mistake on a live box, so it's off the table by policy, not by physics. If unsure whether a command changes state, skip it and say so.
- **NO SUDO.** If a check needs elevation, skip it and record "requires sudo — skipped". Never prompt for a password. This keeps the pass safe to run on a live client box.
- **NEVER PRINT SECRETS.** You may read `.env` to find versions or the mailer, but never echo `APP_KEY`, passwords, tokens, DB or SMTP credentials, licence keys, or API keys — not even partially, not even in passing. Report presence ("licence key set"), never the value. The same applies to `auth.json`, which holds Statamic marketplace credentials: report that it exists, never its contents.
- **DON'T INVENT DATES.** Use the reference tables below for support/EOL status. For anything not in them, say "unknown" — a confidently wrong EOL date sends someone chasing the wrong risk. "Unknown" beats a guess.
- **NEVER USE A BARE STATUS DOT.** Every marker carries its word: `🟢 supported`, `🟡 security-only`, `🔴 EOL`, `⚪ unknown`. The dot is for scanning; the word is the meaning. A dot alone is unreadable to anyone with colour vision deficiency and impossible to grep.
- **Prefer reading lockfiles and version files** over invoking tools that might fetch or install. Never run bare `npx <pkg>`.

## First: where are you looking?

One line, up front: can you see the live server, or only the repo on this machine? Running versions live on the box; the repo shows only what's intended, and the two diverge. If repo-only, label every version "declared, not confirmed on server" and list what would need server access (OS release, PHP-FPM version, actual deployed Node).

Also establish, briefly:
- **What's managing this box** — Laravel Forge, Ploi, plain nginx + a deploy script, something else. Look for `/home/forge`, `.forge`, `/etc/nginx/forge-conf`, or a deploy script. It decides how a PHP or OS move actually happens, and whether "rebuild elsewhere" is cheap.
- **Which copy is this** — production, staging or a temporary test vhost. These estates routinely have two or three copies of the same site on different hosts (e.g. a `dev.` or test-domain clone). Auditing a stale staging copy and reporting it as the client's site is the expensive mistake here.
- **What's actually deployed** — `git log -1 --format='%h %ci %s'` and `git status --porcelain` (read-only). A repo well ahead of the deployed ref, or uncommitted changes on the box, changes what "the site" even means.

If you're sitting above several site directories rather than inside one, enumerate each and report per-site, kept terse. Say which you inspected and which you skipped and why (no composer.lock → not a deployed app).

## Checks

**Server**
- Ubuntu release + LTS status (`/etc/os-release`), kernel (`uname -r`).
- Support status from the table. Note that Ubuntu backports security fixes, so a package whose upstream branch is EOL may still be patched — say so rather than raising a false alarm.
- **Then the route question. The default is: upgrade in place.** A rebuild drags a long tail behind it — DNS, TLS, cron, deploy keys, backup scripts, `.env` reconstruction, shared paths, then decommissioning the old box — and that tail is paid per server, not per upgrade. Assume in place unless one specific fact forces otherwise.
- **The one trigger that opens the question: Ubuntu on ESM or older** (20.04, 18.04, 16.04). The ondrej PHP repo publishes only for Ubuntu LTS releases still in standard support and explicitly excludes ESM releases — so on those boxes there's no supported route to PHP 8.3+, and the choice becomes `do-release-upgrade` (two LTS hops, on a live client site) or rebuild. On 22.04, 24.04 or 26.04, this question doesn't arise: state "in place" and move on.
- If you do call for a rebuild, say which fact forced it. "The OS is old" isn't enough — name the thing that can't be fixed in place. Once a rebuild is forced, stop investigating the in-place PHP path; it isn't available, and the audit's budget is better spent on the app.
- **One sequencing note, on 22.04 only.** In place is right for this upgrade, but 22.04's standard support ends 1 Apr 2027, so the OS move is due within the year regardless. Flag it so the two moves get sequenced deliberately — PHP now and OS later, or both together — rather than the box being touched twice by accident.

**PHP**
- CLI version (`php -v`) and FPM if reachable — flag if they differ, since the site runs on FPM.
- List all installed versions (`ls /etc/php/`), not just the active one. **This is the cheapest good news in the audit:** if 8.3+ is already installed alongside the active version, the PHP move is a pool switch and a test, not a project.
- **State plainly: is it 8.3+ (the target floor)? Is it 8.5 (the aim)?** This is the single most decisive fact in the audit. Report support status and target-readiness separately — they diverge (PHP 8.2 is `🟡 security-only` and still blocks the target).
- If PHP needs to move, check what supplies it: distro packages or the ondrej/php repo. **Verified 22 July 2026:** ondrej publishes co-installable PHP branches for Ubuntu LTS releases in standard support (22.04, 24.04, 26.04) and explicitly *not* for ESM releases. Distro defaults are 8.1 on 22.04, 8.3 on 24.04, 8.5 on 26.04 — so on 22.04 and 24.04 the target PHP comes from ondrej, not from apt's default.
- **Say plainly how hard the PHP move actually is**, because it's usually much less than it looks: versions are co-installable, so the new PHP goes on beside the old one rather than replacing it, and FPM pools are per site — you can move one site to 8.5 and leave its neighbours on the box untouched, then roll back by pointing the pool at the old version. Note if this box hosts other sites, since that's the thing that makes an in-place move feel risky and this is the answer to it.

**Composer + packages**
- `composer --version` (1.x is EOL — flag loudly; below 2.9 also means none of the advisory blocking below applies yet).
- `statamic/cms` and `laravel/framework`: installed version vs target. Use `composer show <pkg>` or the lockfile; `php please --version` also gives Statamic.
- `composer outdated --direct` — counts, then the notable ones. Separate safe-within-major from major/breaking.
- **Check composer.json constraints, not just the lockfile** — a constraint ceiling (`^11.0`) blocks a newer release that otherwise exists. Name any you find.
- **The PHP ceiling hiding in the lockfile.** Locked packages carry their own `php` platform constraints, and an old one with an upper bound (`<8.4`, `<8.5`) will refuse to install on the target PHP even though nothing in composer.json says so. This has bitten us. Cheap check: `grep -o '"php": "[^"]*"' composer.lock | sort -u` and report any constraint with an upper bound below 8.5, with the package that declares it if you can find it quickly.
- **`composer audit`.** Read-only, and more predictive than it looks: since Composer 2.9, versions with known advisories are blocked during resolution by default, so an advisory in the current set means a future `composer update` will *fail*, not warn. Report the count and whether anything sits on the upgrade path.
- **The blocker hunt.** `composer why-not laravel/framework 13` and `composer why-not statamic/cms 6` answer this directly — run both and report what they name. Third-party Statamic addons are the usual culprit. These are what hold the target up.
- **Don't cry wolf on known immovables.** Observed on a completed Laravel 13.21 + Statamic 6.26 upgrade (July 2026): `guzzlehttp/guzzle` stays on 7 because both laravel/framework and statamic/cms pin it, and PHPUnit stays on 12 per Laravel 13's own guidance. Report these as expected, not as blockers. *This list is a snapshot and will age — treat it as a prior, and if the evidence in front of you disagrees, say so.*
- **The stepping-stone trap.** Laravel 11 is EOL with unpatched advisories, so Composer's advisory blocking will refuse to resolve to it. A site on Laravel 10 goes 10 → 12 → 13, skipping 11 entirely. Note the route if the site is below 12.

**Node + npm**
- `node -v`, `npm -v`, support status from the table.
- **First decide whether Node matters here:** are assets built on the server, or built in CI/locally and deployed pre-compiled? Check for a build step and committed compiled output. If pre-compiled, say so — the server's Node is then largely irrelevant and shouldn't drive urgency.
- `npm outdated` — counts, then notable ones.
- **Tailwind major version.** Statamic 6 moves to Tailwind v4; if this project is on v3 that's a real migration cost, not a version bump. Flag it.
- **Custom Vue in the control panel.** Statamic 6 moves the CP to Vue 3 + Inertia 2. Quick check for custom CP components or addons on Vue 2 — this cost never shows up in a version table.

**Laravel skeleton state (quick)**
Is this on the pre-11 skeleton (`app/Http/Kernel.php`, `app/Console/Kernel.php`, a fat `app/Providers/`) or the slim one (`bootstrap/app.php`)? The slim migration is separate work from the version bump, it's the usual route via Laravel Shift, and on a Statamic site it needs the `config/` directory reconciling afterwards. One line: which skeleton, and whether `config/` looks like current Laravel + Statamic conventions or has drifted.

**Statamic edition & licence (quick)**
- Pro or Solo/Core (`config/statamic/editions.php` or `STATAMIC_PRO_ENABLED`), and whether a licence key is present in `.env` — **presence only, never the value**.
- If the plan involves validating on a temporary hostname, note that Statamic's licence domain check treats obviously-dev hostnames (`dev.`, `test.`, `staging.`, `.test`, `.local`) as non-public, but an arbitrary test domain is treated as public and will nag in the CP. Worth a line if a temp vhost is likely; don't investigate further.

**Statamic 5 → 6 landmine sweep (bounded — one pass, hits only)**
These are cost signals, not blockers. Count them, name them, fix nothing. Cap the output; if a pattern has many hits, say "many" and move on. From Statamic's own 5→6 guide, the ones worth cheap detection:
- **Timezone** — `config/app.php` `timezone` not `UTC` *and* the site uses dated collections or date fields. In v6 dates convert to UTC at runtime, so displayed dates can shift. Highest-impact item here and invisible in any version table.
- **Carbon** — `nesbot/carbon` major in the lockfile; v6 requires Carbon 3. Note anything pinning Carbon 2.
- **Search config** — `'searchables' => 'all'` in `config/statamic/search.php`. Deliberately not auto-migrated, so it's guaranteed manual work.
- **`statamic` cache driver** in `config/cache.php` (removed in v6).
- **Users in the database** — `config/statamic/users.php` repository set to `eloquent` rather than file. If so, v6 adds 2FA/passkey migrations to run.
- **Templates/JS greps:** `moment` (removed), `relate` tag, `{{ session:` / `{{ cookie:` / `{{ nav:` / `{{ redirect:` wildcard form, `urlencode`, `where('status'`, `type: section` fieldtypes, custom Glide manipulators, Algolia.

**Email (quick check, early exit)**
Email is rarely configured on these servers, so this is a confirm-the-expected check, not an investigation. Read `MAIL_MAILER` (or legacy `MAIL_DRIVER`) from `.env` — value only, no credentials.
- `log`, `array`, unset or empty → inert. One line: "email not configured." **Stop there, no further discovery.**
- A real transport (`smtp`, `mailgun`, `ses`, `postmark`, `resend`) → unexpected. Note the transport type and that live credentials are present in `.env` (never the values). Still don't go deeper in this pass — just flag it.
- No `.env` in the directory → fall back to `config/mail.php` default and say it's the config default, not confirmed runtime.

## Reference: a site that's already there (July 2026)

Useful as a sanity anchor for "what does done look like" — versions observed on a completed upgrade, not a spec:
PHP 8.5.8 · Composer 2.10 · Node 22 · Laravel 13.21 · Statamic 6.26 · Vite 8.1 · laravel-vite-plugin 3.1 · Tailwind 4.3 · Alpine 3.15.
Note Node 22 there: current managed-host provisioning still lands on 22, which is `🟡 maintenance LTS`. Don't raise urgency on a Node 22 box that isn't even building assets.

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

## Then: the blockers

For each area, state whether reaching the target is **routine**, **needs care**, or **blocked** — and why. Look for the cross-cutting ones specifically:
- PHP below 8.3 → blocks the whole target, regardless of its support status.
- Ubuntu on ESM or older, so ondrej won't supply PHP 8.3+ — the only case where the OS itself blocks the target rather than merely being old. On a supported LTS, an outdated PHP is a task, not a blocker.
- A direct package or Statamic addon with no L13/S6-compatible release (`composer why-not` names these).
- A locked package with a PHP upper bound below the target PHP.
- An existing advisory in the current dependency set that will stop `composer update` resolving at all.
- Tailwind v3 → v4, or custom Vue 2 CP components — cost that a version table hides.
- A composer.json constraint acting as the real ceiling.
- Pre-slim Laravel skeleton — not a blocker, but separate work with its own route.

## Output

Reply inline only — no report file, no changes proposed.
1. **One-line verdict:** how far is this project from Laravel 13 + Statamic 6, and what's the single biggest thing in the way?
2. **Route & size:** in place (the default) or, exceptionally, rebuild and migrate — and if rebuild, the specific fact that forces it. Then a rough size (small / medium / large) and where the work sits: the Laravel move, the PHP move, or genuinely just the Statamic bump.
3. **Table:** Component | Running (or declared) | Target | Gap | Support status | Target verdict
   - Support status uses the labelled markers: `🟢 supported`, `🟡 security-only`, `🔴 EOL`, `⚪ unknown`.
   - Target verdict is plain words: `routine`, `needs care`, `blocked`. Never a dot.
   - These two columns will disagree — that's the point. Something can be `🟡 security-only` and still `blocked`.
4. **Blockers** — the section above, in prose. This is the part that matters most: not "you're N behind" but "here's what stands in the way and roughly what it'd take."
5. **Hidden costs** — landmine sweep hits, skeleton state, Tailwind/Vue. Counted, not fixed.
6. **Email:** one line.
7. **Couldn't confirm:** what was skipped (sudo, no server access) and what's unknown.

Keep it scannable. Show reasoning where a verdict isn't obvious, name assumptions as assumptions, and flag ambiguity rather than guessing.
