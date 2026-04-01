#!/usr/bin/env bash
# One-time setup on beebaby. Run from the dev machine:
#   ssh beebaby 'bash -s' < deploy/setup.sh
set -euo pipefail

APP_DIR=~/dev/hiking-food

echo "==> Creating app directory"
mkdir -p "$APP_DIR"

echo "==> Creating Python venv"
python3 -m venv "$APP_DIR/backend/venv"

echo "==> Enabling lingering (so user services start on boot)"
loginctl enable-linger "$(whoami)" 2>/dev/null || echo "Warning: could not enable linger. Service may not auto-start on boot."

echo "==> Setup complete. Run deploy.sh from your dev machine to sync code and start the service."
