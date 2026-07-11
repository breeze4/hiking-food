#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x backend/venv/bin/python ]]; then
  python3 -m venv backend/venv
fi

backend/venv/bin/pip install --quiet --upgrade pip
backend/venv/bin/pip install --quiet -r backend/requirements-dev.txt
bash scripts/check-requirements-lock.sh
backend/venv/bin/python -m pytest backend/tests

pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
