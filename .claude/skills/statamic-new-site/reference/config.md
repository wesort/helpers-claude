# Config changes

Applied on top of the files the latest skeleton generates. Find the matching key in each file; don't paste whole files over the generated ones.

## `config/statamic/system.php`

```php
'display_timezone' => 'Europe/London',
```

## `config/statamic/cp.php`

```php
'default_timezone' => env('STATAMIC_CP_DEFAULT_TIMEZONE', 'Europe/London'),
```

App and server stay on UTC (`config/app.php` `timezone`). Every date-only field in a blueprint gets `format: Y-m-d`.

## `resources/sites.yaml`

```yaml
default:
  name: '{{ config:app:name }}'
  url: /
  locale: en_GB
```

## `config/session.php`

```php
'lifetime' => (int) env('SESSION_LIFETIME', 10080), // 7 days
'serialization' => 'json',
```

## `config/cache.php`

```php
'serializable_classes' => false,
```

## `config/statamic/git.php`

Add below the existing keys, for the dev panel and the head comment. `git -C` makes it work wherever artisan runs from.

```php
'repo_url' => env('GIT_REPO_URL', null),
'commit_hash' => exec('git -C '.escapeshellarg(base_path()).' rev-parse --short HEAD'),
'commit_datetime' => exec('git -C '.escapeshellarg(base_path()).' log -1 --format=%cd --date=format:"%d %b %Y %H:%M"'),
'commit_datetime_relative' => exec('git -C '.escapeshellarg(base_path()).' log -1 --format=%ar --date=relative'),
'commit_author' => exec('git -C '.escapeshellarg(base_path()).' log -1 --format=%an'),
'commit_message' => exec('git -C '.escapeshellarg(base_path()).' log -1 --format=%s'),
```

Keep `paths` in step with the allowlist in `autobackup.sh`.

## `config/logging.php`

```php
'stack' => [
    'driver' => 'stack',
    // Adds the slack channel (Discord with /slack on the webhook URL) only when its webhook URL is set
    'channels' => array_values(array_unique(array_merge(
        explode(',', (string) env('LOG_STACK', 'single')),
        env('LOG_SLACK_WEBHOOK_URL') ? ['slack'] : [],
    ))),
    'ignore_exceptions' => false,
],

'slack' => [
    'driver' => 'slack',
    'url' => env('LOG_SLACK_WEBHOOK_URL'),
    'username' => env('LOG_SLACK_USERNAME', parse_url((string) env('APP_URL'), PHP_URL_HOST) ?: 'Laravel Log'),
    'emoji' => env('LOG_SLACK_EMOJI', ':boom:'),
    'level' => env('LOG_SLACK_LEVEL', 'error'),
    'replace_placeholders' => true,
],
```

## Block set icons

Statamic 6 changed its icon set. Check every set's `icon` exists in the installed version's set (an unknown icon shows blank in the CP).

## `.env` templates

Commit `docs/dev.env` and `docs/prod.env` with every key and **no secrets**: placeholders or empty values only. Notable values:

```sh
APP_ENV=dev                    # production on prod
APP_LOCALE=en_GB
APP_URL=https://DEV_DOMAIN
APP_DEBUG=true                 # false on prod
GIT_REPO_URL=https://github.com/REPO

STATAMIC_LICENSE_KEY=
STATAMIC_PRO_ENABLED=true
STATAMIC_STACHE_WATCHER=true   # false on prod
STATAMIC_STATIC_CACHING_STRATEGY=null   # half on prod, if used
STATAMIC_GIT_ENABLED=false

DEV_PANEL_ENABLED=true

SESSION_DRIVER=file
SESSION_LIFETIME=10080

LOG_STACK=single
LOG_SLACK_WEBHOOK_URL=
LOG_SLACK_LEVEL=error

QUEUE_CONNECTION=sync
```

Plus the assets disk's keys (D4), all empty in the template.
