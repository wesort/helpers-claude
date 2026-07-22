Audit this Statamic project and its server for how far they are from our upgrade target, and what's in the way. READ-ONLY: this pass produces a picture and a decision, never a change. Budget about 2–3 minutes — thorough enough to be trusted, not a forensic audit. If something is slow or ambiguous, note it and move on.

## The target (as of July 2026)

Laravel 13 @latest + Statamic 6 @latest, with everything underneath them current too — PHP, Composer packages, Node, npm packages. Ideally PHP 8.5.

The dependency chain that decides everything else:
- Statamic 6 → Laravel 12–13, PHP 8.3–8.5
- Laravel 13 → PHP 8.3–8.5
- So: **PHP 8.3 is a hard floor. Below it, the target is unreachable until PHP moves — treat that as a blocker, not a drift.** PHP 8.5 is fully supported by both and is the aim.

Frame every gap against this target, not just "a newer version exists."

## Hard rules

- **READ-ONLY.** Install, update, remove or modify nothing: no `composer install/update/require`, no `npm install/ci/update`, no `apt` changes, no edits to composer.json, package.json or lockfiles, no writing files. `composer outdated`, `composer show`, `npm outdated` are fine — they don't mutate. If unsure whether a command changes state, skip it and say so.
- **NO SUDO.** If a check needs elevation, skip it and record "requires sudo — skipped". Never prompt for a password. This keeps the pass safe to run on a live client box.
- **NEVER PRINT SECRETS.** You may read `.env` to find versions or the mailer, but never echo `APP_KEY`, passwords, tokens, DB or SMTP credentials, or API keys — not even partially, not even in passing. Report presence ("credentials set"), never the value.
- **DON'T INVENT DATES.** Use the reference tables below for support/EOL status. For anything not in them, say "unknown" — a confidently wrong EOL date sends someone chasing the wrong risk. "Unknown" beats a guess.
- **NEVER USE A BARE STATUS DOT.** Every marker carries its word: `🟢 supported`, `🟡 security-only`, `🔴 EOL`, `⚪ unknown`. The dot is for scanning; the word is the meaning. A dot alone is unreadable to anyone with colour vision deficiency and impossible to grep.
- **Prefer reading lockfiles and version files** over invoking tools that might fetch or install. Never run bare `npx <pkg>`.

## First: where are you looking?

One line, up front: can you see the live server, or only the repo on this machine? Running versions live on the box; the repo shows only what's intended, and the two diverge. If repo-only, label every version "declared, not confirmed on server" and list what would need server access (OS release, PHP-FPM version, actual deployed Node).

If you're sitting above several site directories rather than inside one, enumerate each and report per-site, kept terse. Say which you inspected and which you skipped and why (no composer.lock → not a deployed app).

## Checks

**Server**
- Ubuntu release + LTS status (`/etc/os-release`), kernel (`uname -r`).
- Support status from the table. Note that Ubuntu backports security fixes, so a package whose upstream branch is EOL may still be patched — say so rather than raising a false alarm.

**PHP**
- CLI version (`php -v`) and FPM if reachable — flag if they differ, since the site runs on FPM.
- List all installed versions (`ls /etc/php/`), not just the active one.
- **State plainly: is it 8.3+ (the target floor)? Is it 8.5 (the aim)?** This is the single most decisive fact in the audit. Report support status and target-readiness separately — they diverge (PHP 8.2 is `🟡 security-only` and still blocks the target).
- If PHP needs to move, check what supplies it: distro packages or the ondrej/php PPA. *Assumption to verify, not assert:* ondrej typically only publishes for Ubuntu releases still in support, so an EOL Ubuntu may block the PHP upgrade too. Check rather than assume.

**Composer + packages**
- `composer --version` (1.x is EOL — flag loudly).
- `statamic/cms` and `laravel/framework`: installed version vs target. Use `composer show <pkg>` or the lockfile; `php please --version` also gives Statamic.
- `composer outdated --direct` — counts, then the notable ones. Separate safe-within-major from major/breaking.
- **Check composer.json constraints, not just the lockfile** — a constraint ceiling (`^11.0`) blocks a newer release that otherwise exists. Name any you find.
- **The blocker hunt:** which direct packages have no release compatible with Laravel 13 / Statamic 6? Third-party Statamic addons are the usual culprit. Name them; these are what hold the target up.

**Node + npm**
- `node -v`, `npm -v`, support status from the table.
- **First decide whether Node matters here:** are assets built on the server, or built in CI/locally and deployed pre-compiled? Check for a build step and committed compiled output. If pre-compiled, say so — the server's Node is then largely irrelevant and shouldn't drive urgency.
- `npm outdated` — counts, then notable ones.
- **Tailwind major version.** Statamic 6 moves to Tailwind v4; if this project is on v3 that's a real migration cost, not a version bump. Flag it.
- **Custom Vue in the control panel.** Statamic 6 moves the CP to Vue 3 + Inertia 2. Quick check for custom CP components or addons on Vue 2 — this cost never shows up in a version table.

**Email (quick check, early exit)**
Email is rarely configured on these servers, so this is a confirm-the-expected check, not an investigation. Read `MAIL_MAILER` (or legacy `MAIL_DRIVER`) from `.env` — value only, no credentials.
- `log`, `array`, unset or empty → inert. One line: "email not configured." **Stop there, no further discovery.**
- A real transport (`smtp`, `mailgun`, `ses`, `postmark`, `resend`) → unexpected. Note the transport type and that live credentials are present in `.env` (never the values). Still don't go deeper in this pass — just flag it.
- No `.env` in the directory → fall back to `config/mail.php` default and say it's the config default, not confirmed runtime.

## Reference: support & EOL (verified 22 July 2026)

Treat as authoritative for this pass; no network lookups needed. If today's date is materially later than the above, say the table may have moved on.

Markers: `🟢 supported` = in full support · `🟡 security-only` = security fixes only, or full support ends within ~12 months · `🔴 EOL` = no security fixes (or paid ESM only) · `⚪ unknown` = not verified, say so rather than guess. Always write the word with the dot.

**Laravel** (18mo bug fixes, 24mo security)
| Ver | Released | Bug fixes end | Security ends | PHP | Status |
|---|---|---|---|---|---|
| 13 | 17 Mar 2026 | 30 Sep 2027 | 17 Mar 2028 | 8.3–8.5 | 🟢 supported — **TARGET** |
| 12 | 24 Feb 2025 | 16 Aug 2026 | 24 Feb 2027 | 8.2–8.5 | 🟡 security-only from Aug 2026 |
| 11 | 12 Mar 2024 | 3 Sep 2025 | 12 Mar 2026 | 8.2–8.4 | 🔴 EOL |
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

**Composer** — 1.x is 🔴 EOL, flag it. 2.x is current. *Not verified against endoflife.date in this pass* — report the installed version and mark it `⚪ unknown` rather than asserting a date.

## Then: the blockers

For each area, state whether reaching the target is **routine**, **needs care**, or **blocked** — and why. Look for the cross-cutting ones specifically:
- PHP below 8.3 → blocks the whole target, regardless of its support status.
- Ubuntu too old to get a supported PHP (directly or via ondrej).
- A direct package or Statamic addon with no L13/S6-compatible release.
- Tailwind v3 → v4, or custom Vue 2 CP components — cost that a version table hides.
- A composer.json constraint acting as the real ceiling.

## Output

Reply inline only — no report file, no changes proposed.
1. **One-line verdict:** how far is this project from Laravel 13 + Statamic 6, and what's the single biggest thing in the way?
2. **Table:** Component | Running (or declared) | Target | Gap | Support status | Target verdict
   - Support status uses the labelled markers: `🟢 supported`, `🟡 security-only`, `🔴 EOL`, `⚪ unknown`.
   - Target verdict is plain words: `routine`, `needs care`, `blocked`. Never a dot.
   - These two columns will disagree — that's the point. Something can be `🟡 security-only` and still `blocked`.
3. **Blockers** — the section above, in prose. This is the part that matters most: not "you're N behind" but "here's what stands in the way and roughly what it'd take."
4. **Email:** one line.
5. **Couldn't confirm:** what was skipped (sudo, no server access) and what's unknown.

Keep it scannable. Show reasoning where a verdict isn't obvious, name assumptions as assumptions, and flag ambiguity rather than guessing.
