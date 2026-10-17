#!/bin/bash
# Stop at the first failed command rather than bringing the site up half-installed
set -e
starttime=$(date +'%T')
START=$(date +%s);
echo '\e[1;32mStart:\e[1;m '$starttime' UTC'
# Get APP_ENV only, so no other .env values reach composer, npm or their scripts
APP_ENV=$(grep -E '^APP_ENV=' .env | cut -d= -f2)


# Put site into maintenace mode with a secret route to get around it
php artisan down --with-secret

# On failure, say so: the site stays in maintenance mode until fixed
# (EXIT rather than ERR, as ERR is bash-only and this is run with sh)
trap 'if [ $? -ne 0 ]; then echo "refresh.sh failed. Site is still in maintenance mode: fix and re-run, or php artisan up"; fi' EXIT

  # List basic application details
  php artisan about

  # Check if in production
  if [ "$APP_ENV" = "production" ]; then
    composer install --no-dev --no-interaction --optimize-autoloader

    npm ci

    npm run build
  fi

  # Clear everything
  php artisan optimize:clear
  php artisan statamic:stache:clear
  # php artisan view:clear
  # php artisan cache:clear
  # php artisan route:clear
  # php artisan config:clear
  # php artisan clear-compiled

  # php artisan statamic:static:clear

  # php artisan queue:restart

  # Check if in production
  if [ "$APP_ENV" = "production" ]; then
    # Cache important stuff (optimize includes config:cache)
    php artisan optimize
    php artisan statamic:stache:warm

    # Rebuild the search index, so it matches the deployed content
    php please search:update --all

    # Generate all asset presets
    # php artisan statamic:assets:generate-presets
  fi

  # Check if in production
  if [ "$APP_ENV" = "dev" ]; then
    echo '\e[1;32mNot running cache commands as APP_ENV not production\e[1;m'
  fi

# Bring site out of maintenace mode
php artisan up

# Unlock the Control Panel if it was locked before the deploy (a no-op if not)
php please cp:unlock

# Elapsed time
midtime=$(date +'%s')
echo $((midtime-START)) | awk '{printf "%02d:%02d\n", int($1/60), int($1%60)}'

# Warm key routes
if [ "$APP_ENV" = "production" ]; then
  # php please static:warm
  # echo 'Warming some common routes ...'
  # curl -# $APP_URL/commissions > /dev/null
    # echo '  Warmed: /commissions'

  # echo 'Done warming common routes.'
  echo 'NB: not warming any routes'
fi

# Output end time
endtime=$(date +'%T')
echo '\e[1;32mEnd time:\e[1;m '$endtime' UTC'
END=$(date +%s);
echo 'Elapsed time (minutes:seconds)'
echo $((END-START)) | awk '{printf "%02d:%02d\n", int($1/60), int($1%60)}'
echo '\e[1;32mDone!\e[1;m'
exit
