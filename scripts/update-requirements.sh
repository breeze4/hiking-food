#!/usr/bin/env bash
# Regenerate the backend requirements lockfiles from the .in sources.
#
# Default (no args): preserve already-pinned versions, applying only the
# changes made in requirements*.in (add/remove/repin a package). This is what
# you run after editing a .in file.
#
# Upgrade a dependency: pass uv flags through, e.g.
#   scripts/update-requirements.sh --upgrade                # bump everything
#   scripts/update-requirements.sh --upgrade-package anyio  # bump just anyio
#
# The gate (scripts/check-requirements-lock.sh) verifies the committed lock
# matches a default (preference-preserving) regenerate, so it only fails on a
# real inconsistency with the .in files, never on a new upstream release.
set -euo pipefail

cd "$(dirname "$0")/.."

args=("$@")

uv pip compile \
  --quiet \
  --universal \
  --generate-hashes \
  --no-header \
  --output-file backend/requirements.txt \
  ${args[@]+"${args[@]}"} \
  backend/requirements.in

uv pip compile \
  --quiet \
  --universal \
  --generate-hashes \
  --no-header \
  --output-file backend/requirements-dev.txt \
  ${args[@]+"${args[@]}"} \
  backend/requirements-dev.in

echo "Regenerated backend/requirements.txt and backend/requirements-dev.txt"
