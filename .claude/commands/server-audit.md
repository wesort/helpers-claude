---
name: stack-health-audit
description: Run a fast, read-only, no-sudo audit of a server's stack for security exposure from end-of-life and outdated software and known CVEs — OS, kernel, PHP, Laravel, Statamic, Node, nginx, Redis, Composer, Vite, per-site composer/npm advisories, and whether email (a password-reset / account-takeover vector) is configured on any site. Use this whenever the user wants to check a server or site's health, EOL exposure, patch/version currency, or security posture; asks things like "is this box up to date", "what's out of date / unsupported", "check versions on <server>", "audit this server", or is triaging which Forge servers need attention — even without the word "audit". Read-only and sudo-free, so safe on production. Built to run via Claude Code on the server itself, but the instructions also stand alone if pasted as a prompt.
---

# Stack health & EOL audit

You are auditing THIS server for security exposure from end-of-life / outdated software and known CVEs. Produce a fast, high-level, **read-only** report. The point is a quick read on where security risk sits — not a deep audit, and never a change. It is safe to run on production because it touches nothing.

Runs best via Claude Code on the server itself; the instructions also stand alone if pasted as a prompt.

## Hard rules — do not break these

- **READ-ONLY.** Install, update, remove, or modify nothing: no package installs, no `composer install/update/require`, no `npm install/ci/update/fix`, no `apt`/`dpkg` changes, no writing or editing files (unless the user explicitly asks for a report file).
- **NO SUDO.** If a check needs elevated privileges, skip it and record "requires sudo — skipped". Never prompt for a password. Sudo-free is the whole point — it keeps this safe to hand to anyone and safe to run on a live box.
- **Prefer reading lockfiles / version files** over invoking tools that might fetch or install. Never run bare `npx <pkg>` — it can silently download. Read versions from `node_modules` or lockfiles instead.
- **Network is allowed only for read-only lookups:** `composer audit`, `npm audit`, and endoflife.date. If the network is blocked, degrade gracefully and say which lookups you couldn't do.
- **NEVER print secrets.** You may read `.env` / config to find versions, the mailer, or a DB host — but never echo `APP_KEY`, passwords, tokens, DB credentials, SMTP credentials, or API keys anywhere in the output. Report presence ("credentials set"), never the value.
- **Timebox it.** Quick scan, not a forensic audit. If something's slow or ambiguous, note it and move on.

## Authoritative EOL dates

Verify EOL / support dates against the endoflife.date API rather than memory, e.g. `curl -s https://endoflife.date/api/php.json`. Useful products: `ubuntu`, `debian`, `php`, `laravel`, `nodejs`, `nginx`, `mariadb`, `mysql`, `redis`. For anything not covered there (e.g. **Statamic**), use your own knowledge and clearly mark those dates "unverified — check vendor". If you can't reach the network, mark all dates "from memory — verify". Do not invent a date — "unknown" beats a confident wrong one, because a wrong date here sends someone chasing the wrong risk.

## What to check

### A. Runtime layer (run from anywhere)

1. **OS** — distro + version + its EOL (`cat /etc/os-release`, `lsb_release -a`).
2. **Kernel** — `uname -r`. Pending reboot? Check `/var/run/reboot-required` and list `/var/run/reboot-required.pkgs` if present. A running kernel older than the newest installed one means patched kernels are sitting unloaded, waiting on a reboot.
3. **PHP** — list ALL installed versions (`ls /etc/php/ 2>/dev/null`, `update-alternatives --list php 2>/dev/null`) and the active CLI (`php -v`). Flag any installed PHP version that is EOL, even if it isn't the active one — an idle EOL FPM pool is still an exposed binary.
4. **Web server** — `nginx -v` and/or `apache2 -v` + EOL.
5. **Database** — client version (`mysql --version` / `mariadb --version`). Server version only if obtainable WITHOUT sudo and WITHOUT printing credentials; otherwise mark unknown. + EOL for whichever engine is present.
6. **Redis** — `redis-server --version` or `redis-cli --version` + EOL.
7. **Node** — `node -v` + EOL. **npm** — `npm -v`.
8. **Composer** — `composer --version` (flag if 1.x — that's EOL).
9. **Best-effort OS updates** — `apt list --upgradable 2>/dev/null` — summarise counts, and note this may be STALE (refreshing the cache needs sudo). Do NOT run `apt update`.

Remember the softening effect of a distro: Ubuntu/Debian backport security fixes, so a package whose *upstream* branch is EOL may still be patched. Say so, rather than raising a false alarm on a distro-managed package.

### B. Per site

Detect Laravel / Statamic sites. If you're running inside one project directory, audit that one. If you're a level above several site dirs (e.g. `/home/forge`), enumerate each and report per-site, kept terse. State clearly which directories you inspected, and which you skipped and why (e.g. no `composer.lock` → not a deployed Laravel/Statamic app).

For each site:

10. **Laravel** — installed `laravel/framework` version (`composer.lock` or `composer show laravel/framework`) + `php artisan --version` + support status from endoflife.date/laravel (distinguish bugfix-ended vs security-ended vs EOL — security-ended is the line that matters).
11. **Statamic** — `statamic/cms` version + support status (mark unverified — check vendor).
12. **Vite** — version from `node_modules/vite/package.json` or the lockfile / `package.json` (don't invoke it). Flag very old majors as unmaintained.
13. **`composer audit`** — count of advisories by severity + the affected packages. This is the key CVE check for PHP deps, and often higher-signal than raw version age: a *supported* framework can still be carrying a vulnerable dependency.
14. **`npm audit`** — best-effort (needs a lockfile; `node_modules` may be absent on a build-in-CI deploy). Counts by severity. If it can't run, say why.
15. **Optional: `composer outdated --direct`** — one-line summary of how far behind direct deps are, unless something's egregious.

16. **Email / password-reset vector** — determine whether outbound email is actually configured on the site. This matters because password-reset and email-verification flows are a routine account-takeover vector, and a live mailer also means real SMTP/API credentials are sitting in `.env`. Read only the mailer *type* and the *presence* of credentials — never echo `MAIL_PASSWORD`, tokens, or SMTP secrets.
    - Runtime truth is `.env`: read `MAIL_MAILER` (or legacy `MAIL_DRIVER`), and note whether `MAIL_HOST` / credentials or a provider key (`MAILGUN_SECRET`, `POSTMARK_TOKEN`, `RESEND_KEY`, SES `AWS_*`) are *present*.
    - If `.env` isn't in that directory, fall back to `config/mail.php`'s default and say the value is the config default, not confirmed runtime.
    - Classify each site:
      - **Not configured / inert** — `MAIL_MAILER` is `log`, `array`, or unset/empty → reset and verification emails cannot be delivered, so that delivery vector is effectively closed. This is the expected state for most of these Statamic sites; confirming it is the goal.
      - **Configured** — a real transport (`smtp`, `mailgun`, `ses`, `postmark`, `resend`) with host/credentials present → reset emails send. Flag it — especially on a site where email wasn't expected — and note that live credentials live in `.env`.
      - **Local MTA** — `sendmail` → relies on a local mail server; note it and mark deliverability unknown from here.
    - The real exposure is configured email **and** a reachable login (Statamic CP or front-end auth). Don't crawl routes to prove reachability in a quick scan — just flag the configured-email sites and note the CP-login caveat.

## Output

Tight and scannable — lead with what matters, not boilerplate. Status markers throughout: 🟢 supported · 🟡 security-only / EOL <~6mo · 🔴 EOL · ⚪ unknown.

1. **Verdict** (2–3 sentences) — overall exposure and the single most urgent thing.
2. **Runtime table** — `Component | Installed | Latest/Supported | Status | EOL date | Notes`.
3. **Per-site table(s)** — `Site | Laravel | Statamic | Vite | composer audit | npm audit`, audit columns showing severity counts.
4. **Email / password-reset vector** — one line per site: *Not configured / Configured / Local MTA*, with the mailer type. Call out any site where email is configured unexpectedly.
5. **🔴 Act now** — anything EOL, any high/critical CVE, an unexpectedly-live mailer, or a pending-reboot kernel; most urgent first. If empty, say so plainly.
6. **Caveats** — which lookups were skipped (sudo/network), and which dates are unverified.

Just flag — don't write detailed remediation. The user decides what to do.
