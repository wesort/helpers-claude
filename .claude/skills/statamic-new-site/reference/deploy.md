# Deployment

<!-- Skeleton for the site's docs/deploy.md. Fill in every section for this site;
     delete what doesn't apply and say why. -->

## Method

Forge zero-downtime, push to deploy.

## Production

- Site URL: https://DOMAIN
- Deploys from branch: `main`
- Triggered by: push to `main`
- Where it runs: Forge organisation `ORG`, server `SERVER`, zero-downtime site at `~/DOMAIN`, 10 releases kept

## Dev

- Site URL: https://DEV_DOMAIN
- Where it runs: same server, standard (not zero-downtime) site at `~/DEV_DOMAIN`
- Updated by: `git pull`, then `npm run build` if front-end files changed

## Other branches

Pushing any other branch, or opening a PR, does nothing on the servers. Commits whose message contains `[BOT]` (content backups) are skipped by the deploy script.

## Steps

**Before every deploy**, so no edit made in the control panel is lost (content is in git and each release is cloned fresh):

```sh
cd ~/DOMAIN/current
php please cp:lock     # CP stays browsable; saves are blocked until unlock
./autobackup.sh        # commits and pushes CP edits made since the last backup
```

Then push to `main` (or click Deploy in Forge). The deploy script unlocks the CP once the new release is live.

### The deploy script

This copy is the source of truth; the one that runs is in Forge (Site > Deployments > Deploy script). Keep the two in step. The `$CREATE_RELEASE()` and `$ACTIVATE_RELEASE()` macros are expanded by Forge and aren't valid shell, which is why the script lives here rather than in a `.sh` file.

```bash
# Skip the deploy that a content backup push would otherwise trigger
if [[ $FORGE_DEPLOY_MESSAGE =~ "[BOT]" ]]; then
    echo "Automated backup commit. Nothing to deploy."
    exit 0
fi

$CREATE_RELEASE()

cd $FORGE_RELEASE_DIRECTORY

$FORGE_COMPOSER install --no-dev --no-interaction --prefer-dist --optimize-autoloader
npm ci && npm run build

$FORGE_PHP artisan optimize

$FORGE_PHP please stache:warm
$FORGE_PHP please search:update --all    # only if the site uses search

$ACTIVATE_RELEASE()

# No PHP-FPM reload: nginx passes PHP the resolved release path ($realpath_root),
# so each release is compiled fresh by OPcache

$FORGE_PHP please cp:unlock

# Only with static caching
$FORGE_PHP please static:clear
$FORGE_PHP please static:warm
```

### Shared paths

`.env` and `storage/` (Forge's defaults), plus `public/robots.txt`. Forge symlinks each from the site root into every release.

In a release, `git status` reports the tracked `storage/**/.gitignore` files as deleted and `storage` as untracked, because git can't descend the symlink. That is expected. Never `git add .`, `git commit -a`, `git reset --hard` or `git restore storage` in `current/`: they either commit the skeleton out of the repo or replace the symlink with a real directory, cutting the release off from shared storage (and the CP lock with it). To repair: `cd ~/DOMAIN/current && rm -rf storage && ln -s ~/DOMAIN/storage storage`, or deploy.

## Content backups from production

`autobackup.sh` runs daily at 03:00 UK time from the Laravel schedule (`routes/console.php`), production only, and by hand before each deploy. It stages only `content users resources public`, commits as `[BOT] Automatic backup via cronjob` and pushes to `main`. Output goes to `storage/logs/autobackup.log`; a failure is logged as an error, which reaches the alerts channel when `LOG_SLACK_WEBHOOK_URL` is set.

So `main` receives commits from production. Pull before pushing code changes.

## Provisioning a new server and site

- Server: Ubuntu LTS VERSION, PHP VERSION, Node VERSION (Active LTS), npm 11.10+. Global git user on the server for backup commits.
- PHP config: max upload size, max execution time.
- Sites: production zero-downtime on `DOMAIN` (web directory `/public`, repo `REPO`, branch `main`, push to deploy, shared paths above); dev standard site on `DEV_DOMAIN`.
- `.env` at the site root from `docs/prod.env` (dev: `docs/dev.env`). Secrets entered by hand.
- `robots.txt` at the site root from `docs/prod.robots.txt` (dev: `docs/dev.robots.txt` to `public/robots.txt`).
- Deploy script: above.
- nginx changes: none, or list them.
- SSL: Let's Encrypt for every domain and alias, once DNS points at the server.
- Scheduled job: `php<version> /home/forge/DOMAIN/current/artisan schedule:run`, every minute.

## Manual deploy and rollback

- Deploy: the steps above, or Forge > Deploy.
- Roll back: Forge > Deployments > roll back to the previous release. Then revert the bad commit on `main`, so the next deploy doesn't bring it back. Avoid `git reset` on the server: production pushes to `main` every night.

## Notes

- Static caching: STRATEGY.
- Queues: `sync` (none).
- Statamic Git automation: off. Backups are by `autobackup.sh`.
