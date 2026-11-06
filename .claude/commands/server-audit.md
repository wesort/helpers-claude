---
name: server-audit
description: Run a fast, read-only, no-sudo audit of a server's stack for security exposure from end-of-life and outdated software and known CVEs — OS, kernel, PHP, Laravel, Statamic, Node, nginx, Redis, Composer, Vite, per-site composer/npm advisories, and whether email (a password-reset / account-takeover vector) is configured on any site. Use this whenever the user wants to check a server or site's health, EOL exposure, patch/version currency, or security posture; asks things like "is this box up to date", "what's out of date / unsupported", "check versions on <server>", "audit this server", or is triaging which Forge servers need attention — even without the word "audit". Read-only and sudo-free, so safe on production. Built to run via Claude Code on the server itself; given another server's name or IP it hands the on-box checks to the user as short read-only scripts. The instructions also stand alone if pasted as a prompt.
allowed-tools: Read, Glob, Grep, Bash(hostname), Bash(hostname -I), Bash(forge server:list), Bash(forge server:current), Bash(forge server:switch *), Bash(forge site:list), Bash(apt-cache policy *), Bash(apt-get -s upgrade), Bash(dpkg-query *), Bash(systemctl is-enabled *), Bash(systemctl is-active *), Bash(cat /etc/os-release), Bash(lsb_release -a), Bash(uname -r), Bash(ls /etc/php/*), Bash(update-alternatives --list php*), Bash(php -v), Bash(php artisan --version), Bash(composer --version), Bash(composer show *), Bash(composer outdated *), Bash(composer audit*), Bash(node -v), Bash(npm -v), Bash(npm audit*), Bash(nginx -v), Bash(apache2 -v), Bash(mysql --version), Bash(mariadb --version), Bash(redis-server --version), Bash(redis-cli --version), Bash(apt list --upgradable*), Bash(curl -s https://endoflife.date/api/*)
---

# Stack health & EOL audit

You are auditing THIS server for security exposure from end-of-life / outdated software and known CVEs. Produce a fast, high-level, **read-only** report. The point is a quick read on where security risk sits — not a deep audit, and never a change. It is safe to run on production because it touches nothing.

Runs best via Claude Code on the server itself; the instructions also stand alone if pasted as a prompt.

## Arguments

`$ARGUMENTS`

- **Empty, or this machine's name or IP:** audit this server directly, following the checks below.
- **Another server's name or IP** (compare with `hostname` and `hostname -I`): remote mode. Look up EOL dates from here, and hand the on-box checks to the user as the two scripts in [Remote mode](#remote-mode).

## Hard rules — do not break these

- **READ-ONLY.** Install, update, remove, or modify nothing: no package installs, no `composer install/update/require`, no `npm install/ci/update/fix`, no `apt`/`dpkg` changes, no writing or editing files (unless the user explicitly asks for a report file).
- **NO SUDO.** If a check needs elevated privileges, skip it and record "requires sudo — skipped". Never prompt for a password. Sudo-free is the whole point — it keeps this safe to hand to anyone and safe to run on a live box.
- **Prefer reading lockfiles / version files** over invoking tools that might fetch or install. Never run bare `npx <pkg>` — it can silently download. Read versions from `node_modules` or lockfiles instead.
- **Network is allowed only for read-only lookups:** `composer audit`, `npm audit`, and endoflife.date. If the network is blocked, degrade gracefully and say which lookups you couldn't do.
- **NEVER print secrets.** You may read `.env` / config to find versions, the mailer, or a DB host — but never echo `APP_KEY`, passwords, tokens, DB credentials, SMTP credentials, or API keys anywhere in the output. Report presence ("credentials set"), never the value.
- **No remote shells.** In remote mode, never SSH or run commands on the other server, including through the Forge CLI. The user runs the scripts and pastes the output back.
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

9a. **Auto-update coverage.** Whether this server can keep itself patched, per component:
    - unattended-upgrades enabled and active (`systemctl is-enabled` / `is-active unattended-upgrades`), and its origins (`Allowed-Origins` and `Origins-Pattern` in `/etc/apt/apt.conf.d/*unattended-upgrades*`). The Ubuntu default is `-security` only.
    - where each key package's *installed* version comes from (`apt-cache policy <pkg>`: the source listed under the `***` line), for nginx, every `php*-fpm`, nodejs, redis-server and any database server. A package from a third-party repo (sury, setup-php, nginx.org, nodesource, redis.io) is outside the default origins, so it only updates when someone updates it by hand.
    - a package whose installed version **no configured repo offers** (only `/var/lib/dpkg/status` under `***`) is stranded: its source has been removed or disabled, so it will never update. 🔴 if its upstream branch is EOL, 🟡 otherwise.
    - what `apt-get -s upgrade` holds back ("kept back"). Held-back packages need new dependencies, so neither unattended-upgrades nor a plain `apt-get upgrade` will ever install them. Held-back kernel meta-packages (`linux-image-virtual`, `linux-virtual`) mean new kernels are not being installed. 🟡.

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
2a. **Auto-update coverage** — `Component | Installed from | Covered by unattended-upgrades | Held back`, then a line for any stranded package.
3. **Per-site table(s)** — `Site | Laravel | Statamic | Vite | composer audit | npm audit`, audit columns showing severity counts.
4. **Email / password-reset vector** — one line per site: *Not configured / Configured / Local MTA*, with the mailer type. Call out any site where email is configured unexpectedly.
5. **🔴 Act now** — anything EOL, any high/critical CVE, an unexpectedly-live mailer, or a pending-reboot kernel; most urgent first. If empty, say so plainly.
6. **Caveats** — which lookups were skipped (sudo/network), and which dates are unverified. In remote mode, say which script each fact came from and how it was run.

Just flag — don't write detailed remediation. The user decides what to do.

## Remote mode

When the server named is not this machine:

1. **Hostnames and sites.** If the Forge CLI is available: `forge server:current`, `forge server:switch <name>` if needed (say which org and server it is now on), then `forge site:list`.
2. **EOL dates.** Look them up from here as usual.
3. **On-box checks.** Give the user the two scripts below, following [Handing scripts to the user](#handing-scripts-to-the-user). Both run as the site user (`forge`), not root: run as root, composer and npm would leave root-owned cache files, and `$HOME` would point at `/root`. They are read-only; their only network calls are `composer audit` and `npm audit`, each capped at 60 seconds. Part 2 reads each site's `.env` but prints only the mailer name and which mail keys are set or empty, never a value.
4. **When the output arrives,** build the report from it. Mail: a site with no `MAIL_MAILER` in `.env` uses the config default printed under it.

**Part 1: runtime and auto-updates**

```bash
#!/bin/bash
# server-audit part 1: runtime and auto-updates. Read-only. Prints no secrets.
echo "== os"; . /etc/os-release; echo "$PRETTY_NAME"; hostname
echo "== kernel running, then installed"; uname -r; ls /boot/vmlinuz-* | sed 's#.*vmlinuz-##'
echo "== reboot"
if [ -f /var/run/reboot-required ]; then cat /var/run/reboot-required.pkgs; else echo "not required"; fi
echo "== php"; ls /etc/php; php -v | head -1
echo "== versions"
for c in nginx mysql mariadb psql redis-server node npm composer; do
  v=--version; [ "$c" = nginx ] && v=-v
  if command -v "$c" >/dev/null; then echo "$c: $($c $v 2>&1 | head -1)"; else echo "$c: not installed"; fi
done
echo "== unattended-upgrades (enabled, active, origins)"
systemctl is-enabled unattended-upgrades; systemctl is-active unattended-upgrades
grep -hvE '^\s*//' /etc/apt/apt.conf.d/*unattended-upgrades* \
  | perl -0ne 'print "$1\n" while /(?:Allowed-Origins|Origins-Pattern)\s*\{(.*?)\};/sg' | grep -oE '"[^"]+"'
echo "== where each package's installed version comes from"
for p in nginx $(dpkg-query -W -f='${Package}\n' 'php*-fpm' 2>/dev/null) nodejs redis-server mysql-server mariadb-server; do
  dpkg -s "$p" >/dev/null 2>&1 || continue
  src=$(apt-cache policy "$p" | awk '/\*\*\*/ {f=1; next} f && $2 ~ /^http/ {print $2, $3; exit} f && $2 !~ /^\// {exit}')
  echo "$p $(dpkg-query -W -f='${Version}' "$p") <- ${src:-no repo offers it}"
done
echo "== held back by apt-get upgrade"
apt-get -s upgrade 2>/dev/null | sed -n '/kept back:/,/^[^ ]/p' | sed '1d;$d'
echo "== upgradable: $(apt list --upgradable 2>/dev/null | grep -c upgradable), security: $(apt list --upgradable 2>/dev/null | grep -c -- -security)"
echo "== end"
```

**Part 2: per site**

```bash
#!/bin/bash
# server-audit part 2: per site. Read-only. Prints no secrets (mail: names only).
for d in "$HOME"/*/; do
  app=${d%/}; [ -L "$app/current" ] && app="$app/current"
  [ -f "$app/composer.lock" ] || { echo "== skip $app (no composer.lock)"; continue; }
  echo "== site $app"; cd "$app" || continue
  grep -A1 -E '"name": "(laravel/framework|statamic/cms)"' composer.lock \
    | grep -oE '"(name|version)": "[^"]+"' | cut -d'"' -f4 | paste -d' ' - -
  grep -m1 '"version"' node_modules/vite/package.json 2>/dev/null | sed 's/^ */vite /' \
    || echo "vite: no node_modules"
  echo "-- composer audit"
  timeout 60 composer audit --locked --no-interaction 2>&1 \
    | grep -E 'advisor|abandoned|^\| (Package|Severity|CVE) ' || echo "could not run"
  echo "-- npm audit"
  if [ -f package-lock.json ]; then
    timeout 60 npm audit --package-lock-only 2>&1 | grep -iE 'vulnerabilit' || echo "could not run"
  else echo "no package-lock.json"; fi
  echo "-- mail (names only)"
  grep -E '^MAIL_(MAILER|DRIVER)=' .env 2>/dev/null || echo "MAIL_MAILER not in .env"
  grep -oE "env\('MAIL_MAILER', '[a-z]+'\)" config/mail.php
  grep -E '^(MAIL_[A-Z_]+|MAILGUN_SECRET|POSTMARK_TOKEN|RESEND_KEY|AWS_ACCESS_KEY_ID)=' .env 2>/dev/null \
    | sed -E 's/=(null|""|)$/ (empty)/; s/=.*/ (set)/'
done
echo "== end"
```

## Handing scripts to the user

Scripts for another server (or for root) are run by the user, never by Claude. Ask once per audit which way they want to run them, then give every script in that form:

- **Forge recipe.** Print the script as it stands and say which user the recipe runs as (the site user, usually `forge`, or `root`). A recipe that still shows as running after a couple of minutes has usually died part-way: ask the user to look at the newest `~/.forge/provision-*.output` on the server (and `ps -u forge` for a live process). If it died, re-run that part over SSH.
- **Over SSH.** Print the script wrapped in `bash <<'EOF' 2>&1` and `EOF`, so it runs in its own shell and an `exit` cannot close the session. For a root script, wrap it in `sudo bash <<'EOF' 2>&1` instead (sudo asks for the password once). Terminals can mangle a long paste: syntax errors or garbled lines in the output mean nothing after them ran, so give the rest again in smaller pieces.

Keep every handover script short (about 30 lines at most) and split longer work into parts that each end with `== end`, so a part that stops early is obvious.
