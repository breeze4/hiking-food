#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

prod_tmp="$(mktemp)"
dev_tmp="$(mktemp)"
trap 'rm -f "$prod_tmp" "$dev_tmp"' EXIT

# Seed the temp output with the committed lock first. uv treats an existing
# output file as a set of version preferences, so pinned transitive deps are
# kept and only what requirements.in actually changed gets re-resolved. Without
# this seed uv would resolve every dependency to its newest release, so any
# upstream publish (e.g. a new anyio patch) would mark the lock "stale" and
# fail the deploy even though requirements.in never changed. Deliberate
# upgrades still go through `scripts/update-requirements.sh --upgrade`.
cp backend/requirements.txt "$prod_tmp"
uv pip compile \
  --quiet \
  --universal \
  --generate-hashes \
  --no-header \
  --output-file "$prod_tmp" \
  backend/requirements.in

if ! cmp -s backend/requirements.txt "$prod_tmp"; then
  diff -u backend/requirements.txt "$prod_tmp" || true
  echo "backend/requirements.txt is inconsistent with requirements.in; regenerate with scripts/update-requirements.sh" >&2
  exit 1
fi

cp backend/requirements-dev.txt "$dev_tmp"
uv pip compile \
  --quiet \
  --universal \
  --generate-hashes \
  --no-header \
  --output-file "$dev_tmp" \
  backend/requirements-dev.in

if ! cmp -s backend/requirements-dev.txt "$dev_tmp"; then
  diff -u backend/requirements-dev.txt "$dev_tmp" || true
  echo "backend/requirements-dev.txt is inconsistent with requirements-dev.in; regenerate with scripts/update-requirements.sh" >&2
  exit 1
fi
