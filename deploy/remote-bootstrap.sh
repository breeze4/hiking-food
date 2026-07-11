#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

test -f "$HOME/.config/hiking-food/mcp.env"

if [[ ! -x backend/venv/bin/python ]]; then
  python3 -m venv backend/venv
fi

backend/venv/bin/pip install --quiet --upgrade pip
backend/venv/bin/pip install --quiet -r backend/requirements.txt

(
  cd backend
  venv/bin/python run_migrations.py
  venv/bin/python seed.py
  venv/bin/python verify_database.py
)

mkdir -p ~/.config/systemd/user
cp deploy/hiking-food.service ~/.config/systemd/user/
systemctl --user daemon-reload
