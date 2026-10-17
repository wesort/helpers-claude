#!/bin/bash
# Back up content edited in the control panel on production to GitHub.
# Runs daily from the Laravel schedule (routes/console.php), and by hand before each deploy.
# Stages an allowlist of everywhere the CP writes, mirroring config/statamic/git.php.
# Never `git add .`: on zero-downtime, storage/ is a symlink to shared storage, so git
# would stage the tracked storage/**/.gitignore skeleton as deleted.
# [BOT] in the message tells the deploy script to skip this push.
set -e
git add -A -- content users resources public
if git diff --cached --quiet; then
  echo "Nothing to back up"
  exit 0
fi
git commit -m "[BOT] Automatic backup via cronjob"
git push
