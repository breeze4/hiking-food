#!/usr/bin/env bash
# Deploy hiking-food to beebaby from dev machine.
# Usage: ./deploy/deploy.sh
set -euo pipefail

HOST=beebaby
APP_DIR=dev/hiking-food
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> Syncing code to $HOST:~/$APP_DIR"
rsync -az --delete \
  --exclude='node_modules' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.db' \
  --exclude='*.pdf' \
  --exclude='dist' \
  --exclude='.git' \
  "$PROJECT_DIR/" "$HOST:$APP_DIR/"

echo "==> Installing Python deps"
ssh "$HOST" "cd ~/$APP_DIR/backend && venv/bin/pip install -q -r requirements.txt"

echo "==> Running migrations"
ssh "$HOST" "cd ~/$APP_DIR/backend && venv/bin/python migrate_add_ratings.py"

echo "==> Seeding database"
ssh "$HOST" "cd ~/$APP_DIR/backend && venv/bin/python seed.py"

echo "==> Building frontend"
ssh "$HOST" "cd ~/$APP_DIR/frontend && npm install --silent && npm run build"

echo "==> Installing user systemd service"
ssh "$HOST" "mkdir -p ~/.config/systemd/user && cp ~/$APP_DIR/deploy/hiking-food.service ~/.config/systemd/user/ && systemctl --user daemon-reload"

echo "==> Restarting service"
ssh "$HOST" "systemctl --user restart hiking-food"

echo "==> Done. Status:"
ssh "$HOST" "systemctl --user status hiking-food --no-pager -l" || true
