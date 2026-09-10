#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x backend/venv/bin/python ]]; then
  python3 -m venv backend/venv
fi

backend/venv/bin/pip install --quiet --require-hashes -r backend/requirements-dev.txt
backend/venv/bin/python -m pytest backend/tests

(cd frontend && pnpm install --frozen-lockfile && pnpm test --maxWorkers=1 && pnpm lint && pnpm build)
