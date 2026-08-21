#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# This project is a static PHP site. Keep the hook dependency-free, while
# supporting dependency installation automatically if a future change adds
# a Node or Composer manifest.
if [[ -f package-lock.json ]]; then
  npm ci --ignore-scripts --no-audit --no-fund
elif [[ -f package.json ]]; then
  npm install --ignore-scripts --no-audit --no-fund
fi

if [[ -f composer.lock ]]; then
  composer install --no-interaction --no-progress --prefer-dist
fi

test -f index.html