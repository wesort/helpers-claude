---
name: security-audit
description: Run a read-only, no-sudo audit of a server or public site for misconfiguration rather than out-of-date software. On a server it checks inside (SSH settings, listening ports, app debug mode, files in web roots, stray nginx sites, Statamic CP and 2FA) and outside (whether .env, .git, logs or listings are served over HTTP). Given URLs instead, it runs only the outside checks, from anywhere. Root-only checks are handed to the user as a short read-only script to run as root (for example as a Laravel Forge recipe). Use this when the user wants to check a server or site for poor configuration, leaks or hardening gaps, or asks "is this box locked down", "is anything exposed", "security check <site>". For EOL versions and CVEs use /server-audit instead.
allowed-tools: Read, Glob, Grep, Bash(cat /etc/os-release), Bash(hostname -I), Bash(ss -tln), Bash(ss -uln), Bash(ls *), Bash(grep *), Bash(ssh-keygen -lf *), Bash(php */artisan about*), Bash(php */artisan --version), Bash(curl -sS --max-time 10 *), Bash(wc *)
---

# Security configuration audit

Audit for **misconfiguration**: things that are set up in a way that leaks data or widens the attack surface. Out-of-date software, EOL dates and CVEs are `/server-audit`'s job; do not repeat them here. The mailer / password-reset check also lives in `/server-audit`; refer to it rather than redoing it.

The baseline is a server provisioned by Laravel Forge (or similar) running small marketing sites: Laravel, Statamic and static sites behind nginx. Forge's defaults are the expected state, so report **drift from them**.

## Arguments

`$ARGUMENTS`

- **Empty:** server mode. Run on the server itself. Inside checks, then outside checks against every site this server's nginx serves.
- **One or more URLs:** outside mode. Run the outside checks (section C) only, against those URLs. Works from any machine, including for sites hosted elsewhere (Netlify, shared hosting). Skip sections A, B and D.

## Hard rules

- **READ-ONLY.** Change nothing: no installs, no config edits, no restarts, no writes outside an explicitly requested report file.
- **NO SUDO.** Never run sudo or prompt for a password. Root-only checks go in the root script (section D) for the user to run themselves.
- **NEVER PRINT SECRETS.** Do not read or `stat` `.env` files at all; use `php artisan about` for environment and debug state, and the root script for their permissions. Never print HTTP response bodies: pipe them to `grep -c` and report the match count only. SSH keys as fingerprints only (`ssh-keygen -lf`), never full key lines. User files (for example Statamic `users/*.yaml`) hold password hashes and 2FA secrets: read key names only, never values.
- **GET and HEAD only, fixed paths only.** Every outside request is one of the paths listed in section C, with `--max-time 10`. No crawling, no fuzzing, no POST, no login attempts. This must look like a few page views, not a scan.
- **Timebox it.** A quick read, not a forensic audit. If something is slow or ambiguous, note it and move on.

## A. Server, inside (server mode only)

1. **Context.** `cat /etc/os-release`, `hostname -I` (public addresses, for the catch-all check in C).
2. **SSH as configured.** Grep `/etc/ssh/sshd_config` and `/etc/ssh/sshd_config.d/*.conf` for `PermitRootLogin`, `PasswordAuthentication`, `KbdInteractiveAuthentication`, `PubkeyAuthentication`, `Port`. Drop-ins are included first and the first value wins, so a drop-in beats the main file. Watch for a cloud-init drop-in (for example `50-cloud-init.conf`) setting `PasswordAuthentication yes`; it is often readable only by root, so a permission error there is expected. The effective values come from the root script; mark these "as configured, confirm with root script".
   - Forge itself logs in as root with its own key, so root login **by key** is expected. Flag root login by password, and password authentication generally.
3. **Keys for this user.** `ssh-keygen -lf ~/.ssh/authorized_keys`: list fingerprints and comments, and ask the user to confirm each one is known. Other users' and root's keys come from the root script.
4. **Listening ports.** `ss -tln` (and `ss -uln`). Anything bound to `0.0.0.0`, `[::]` or a public address other than 22, 80 and 443 is a finding: especially databases (3306, 5432), Redis (6379), Memcached (11211), search engines (7700, 9200) and dev servers (5173, 3000, 8000). Process owners and firewall state come from the root script, so until then say "listening publicly, firewall unconfirmed". Redis and Memcached on `0.0.0.0` have appeared on every Forge server audited so far, so if the firewall denies them, record a baseline note rather than a finding.
5. **Sites from nginx.** Read `/etc/nginx/sites-enabled/*` and record each `server_name`, `root`, and any `autoindex on`, following each `include`: newer Forge sites keep their rules in `/etc/nginx/forge-conf/<site-id>/site.conf`. For each site also check:
   - the dotfile deny rule Forge adds (`location ~ /\.(?!well-known).*` with `deny all`) is present, inline or in an include; missing means `.env` and `.git` may be served if they sit in the web root
   - the `root` directory exists (missing means an orphaned config)
   Configs only in `sites-available` are not served: mention them, but they are not a finding.
6. **Leftovers.** Compare site directories in the web user's home (for example `/home/forge/*`) with the nginx configs: directories with no config may be stale copies of old sites, often holding a `.env`, or deliberate (backups, working clones), so list them and ask, and rate them only once the user says they are stale. Note whether a catch-all / default server exists and what it does (Forge's closes the connection with 444).

## B. Per site, inside (server mode only)

For each site from A5, terse. Say which directories you inspected and which you skipped and why. The app directory is the nginx `root` without its trailing `/public`; on zero-downtime sites that is `<site>/current`.

7. **Environment and debug.** Run artisan by absolute path, with no `cd`. On Laravel 9.21 and later (check with `php <app>/artisan --version`): `php <app>/artisan about --only=environment`. Flag `Debug Mode` enabled or `Environment` not `production` on a live hostname. Note whether config is cached, since cached config is what runs. Older Laravel apps lack `about`: mark ⚪ unknown (still without reading `.env`) and add it to the caveats. Statamic 2 and static sites: n/a.
8. **Web root contents.** Glob the nginx `root` (depth 3, skip `node_modules` and `vendor`) for files that should not be public: `*.sql`, `*.sql.gz`, `*.zip`, `*.tar*`, `*.bak`, `*.log`, `.env*`, `.git/`, `phpinfo.php`, `info.php`, `adminer*.php`, `composer.json`, `package.json`. Static sites often have the repo root as the web root, so this matters most there. Zips in an assets folder may be intentional downloads: list them and let the user judge. A `.git/` in the web root of a site deployed from git is fine if the deny rule is present and C12 returns 403.
9. **`.env` permissions.** From the root script, which follows symlinks: zero-downtime releases link `.env` to a shared file, and a symlink's own mode is always 777. Mode `664` means any local account can read the file, not just its owner. Where one site user owns everything, record a baseline note rather than a finding; where several site users share the box, it is 🟡.
10. **Statamic control panel.** From `config/statamic/cp.php`: whether the CP is enabled and its route. A reachable CP on a site nobody edits is surface for no benefit.
11. **Statamic 2FA (Statamic 6 only).** Report `two_factor_enforced_roles` from `config/statamic/users.php`: `*`, `super_users` or a list of roles must use 2FA, and a missing key means the default `[]`, so nobody must. For flat-file users, count users and how many have confirmed 2FA by grepping key names only (`grep -l '^two_factor_confirmed_at:' users/*.yaml`). Earlier versions: n/a. If users are not flat files, say "unknown" rather than guess. 2FA off outside production is expected. Where production does not enforce it for all users, include the fix below with the finding.

## C. Outside (both modes)

For each hostname (server mode: every `server_name` from A5 over https, dropping any leading dot and skipping `_`; outside mode: the URLs given). Report status codes and match counts only, never bodies. Do not follow redirects: a host that answers 301 for every path just redirects, so note it and probe its target instead. A 401 means the site is behind basic auth, so report those paths as "behind auth, not probed" rather than clean.

12. **Leaks.** GET each path and grep the body for a signature, reporting the count:
    - `/.env`: lines matching `^[A-Z][A-Z0-9_]*=` (3 or more on a non-HTML response is a leak)
    - `/.git/HEAD`: `^ref: refs/`; `/.git/config`: `\[core\]`
    - `/storage/logs/laravel.log` and `/laravel.log`: `\.(ERROR|WARNING|INFO):`
    - `/composer.lock`, `/package.json`: status only (version disclosure, low)
    A 200 alone is not a leak: some sites answer 200 with an HTML page for every path. The signature match is the test.
13. **Directory listing.** GET `/assets/`, `/uploads/`, `/storage/`, `/img/`: grep for `Index of /`.
14. **Statamic CP.** GET `/cp/auth/login` (or the route from B10): reachable or not. Record it; the verdict combines it with B10, B11 and `/server-audit`'s mailer finding.
15. **Catch-all (server mode).** `curl` each public IP from A1 with no matching Host header: it should not serve a real site. Curl's "Empty reply" (52, Forge's 444) and a TLS "unrecognized name" error (35) both mean it refused, which is a pass.
16. **Basic auth on non-production PHP sites.** GET `/` and report the status and whether basic auth answered (`grep -ci '^www-authenticate: basic'` on the response headers). Server mode: each Laravel or Statamic site whose Environment from B7 is not `production`, or whose hostname starts `dev.`, `staging.`, `test.` or `uat.` where B7 is unknown. Outside mode: those hostnames only, since the environment cannot be seen from outside. An app's own login page does not count. Static sites: n/a.

## D. Root script (server mode only)

Some checks need root. Do not run them. Print this script exactly, ask the user to run it as root (for example as a Laravel Forge recipe with user `root`), and to paste the output back: the Forge CLI has no recipe commands, so you cannot fetch it yourself. Explain that it is read-only and prints no secrets: fingerprints, settings and port owners only. When the output arrives, complete the pending verdicts; until then mark them ⏳ pending root.

```bash
#!/bin/bash
# security-audit root checks. Read-only. Prints no secrets.
echo "== sshd effective"
sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|port|authenticationmethods|allowusers|allowgroups) '
echo "== ufw"
ufw status verbose
echo "== listening, with process"
ss -tlnp
echo "== authorized keys (fingerprints only)"
for f in /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys; do
  [ -f "$f" ] || continue
  echo "-- $f"
  ssh-keygen -lf "$f" 2>&1
done
echo "== users with a login shell"
awk -F: '$7 !~ /(nologin|false)$/ {print $1, $7}' /etc/passwd
echo "== sudoers drop-ins"
ls -l /etc/sudoers.d/
echo "== .env and auth.json permissions (following symlinks, never contents)"
for f in /home/*/*/.env /home/*/*/current/.env /home/*/*/auth.json /home/*/*/current/auth.json; do
  [ -e "$f" ] && stat -L -c '%a %U:%G %n' "$f"
done
```

## Severity

- 🔴 **Act now:** `.env`, `.git` or a log served over HTTP; a database dump, `phpinfo` or Adminer in a web root; debug mode on a live site; SSH password authentication effective; firewall inactive; a database, Redis or Memcached reachable publicly.
- 🟡 **Fix soon:** an SSH key nobody recognises; a service listening publicly but firewalled; directory listing; dotfile deny rule missing; Statamic CP reachable with 2FA not enforced; site directories the user confirms are stale; enabled configs whose root is missing; `APP_ENV` not `production` on a live hostname; a non-production PHP site without basic auth; catch-all serving a site.
- 🟢 **Fine:** checked and matches the baseline.
- ⏳ **Pending root:** waiting on section D output.
- ⚪ **Unknown:** could not be determined; say why.

## Output

Tight and scannable. Lead with what matters.

1. **Verdict** (2 to 3 sentences): overall posture and the single most urgent thing.
2. **🔴 Act now**, most urgent first. If empty, say so plainly.
3. **Server table** (server mode): `Check | Finding | Status`.
4. **Per-site table**: `Site | Leaks | Debug/env | Basic auth | Web root files | Listing | CP / 2FA`.
5. **⏳ Pending root**: what the root script will settle, and the script itself if not yet run.
6. **Caveats**: what could not be checked and why. Requests from the server to its own hostnames may bypass a cloud firewall and a CDN, so outside results from the box are indicative; re-run in outside mode from another machine to confirm a borderline finding.

Just flag. No remediation steps unless asked, other than the 2FA fix below; the user decides what to do.

## Fix: enforce Statamic 2FA

Enforce 2FA for all users on production. Add this to `config/statamic/users.php`:

```php
/*
|--------------------------------------------------------------------------
| Two-Factor Authentication
|--------------------------------------------------------------------------
|
| Production only. User files move between branches in git, and their 2FA
| secrets can only be decrypted with the APP_KEY that encrypted them, so
| it stays off elsewhere. Dev sites sit behind basic auth instead.
|
*/

'two_factor_enabled' => env('APP_ENV') === 'production',

/*
|--------------------------------------------------------------------------
| Enforce Two-Factor Authentication
|--------------------------------------------------------------------------
|
| Every user must set up two-factor authentication.
|
*/

'two_factor_enforced_roles' => ['*'],
```

Users are sent to setup at their next login, so warn them first. Where user files are cloned into each release (zero-downtime deploys), back up any setup to git before the next deploy, or it is lost. Merge the config into dev branches before or with any user file holding a 2FA secret, or logins there can fail.
