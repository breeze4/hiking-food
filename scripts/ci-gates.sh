#!/bin/sh
# Every check that hiking-food must pass. The check workflow runs
# `bash scripts/ci-gates.sh all` inside the shared BeeBaby CI image, and
# `sh scripts/ci-local.sh all` runs the same command in the same image on your
# machine. scripts/stamp-ci.py stamps this file only when the repository has
# none, so add the project's own checks to gate_project.
#
# Usage: bash scripts/ci-gates.sh [workflows|project|all]
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

usage() {
  printf '%s\n' "Usage: bash scripts/ci-gates.sh [workflows|project|all]" >&2
}

# Woodpecker gives ghcr_token to plugin steps only. The check reads every
# workflow file, the main-only publish and deploy workflows too, so a pull
# request fails before main does.
gate_workflows() {
  python3 "$root/scripts/check-ghcr-token.py" "$root"
}

gate_project() {
  if [ ! -x "$root/backend/venv/bin/python" ]; then
    python3 -m venv "$root/backend/venv"
  fi
  "$root/backend/venv/bin/pip" install --quiet --require-hashes \
    -r "$root/backend/requirements-dev.txt"
  "$root/backend/venv/bin/python" -m pytest "$root/backend/tests"

  (
    cd "$root/frontend"
    pnpm install --frozen-lockfile
    pnpm test --maxWorkers=1
    pnpm lint
    pnpm build
  )
}

target="${1:-all}"

case "$target" in
  workflows) gate_workflows ;;
  project) gate_project ;;
  all)
    gate_workflows
    gate_project
    ;;
  *)
    usage
    exit 2
    ;;
esac
