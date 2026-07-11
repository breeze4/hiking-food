#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

prod_tmp="$(mktemp)"
dev_tmp="$(mktemp)"
trap 'rm -f "$prod_tmp" "$dev_tmp"' EXIT

uv pip compile \
  --quiet \
  --universal \
  --generate-hashes \
  --no-header \
  --output-file "$prod_tmp" \
  backend/requirements.in

if ! cmp -s backend/requirements.txt "$prod_tmp"; then
  diff -u backend/requirements.txt "$prod_tmp" || true
  echo "backend/requirements.txt is stale; regenerate it from requirements.in" >&2
  exit 1
fi

uv pip compile \
  --quiet \
  --universal \
  --generate-hashes \
  --no-header \
  --output-file "$dev_tmp" \
  backend/requirements-dev.in

if ! cmp -s backend/requirements-dev.txt "$dev_tmp"; then
  diff -u backend/requirements-dev.txt "$dev_tmp" || true
  echo "backend/requirements-dev.txt is stale; regenerate it from requirements-dev.in" >&2
  exit 1
fi
