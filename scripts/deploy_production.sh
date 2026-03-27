#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_ENV_FILE="${APP_ENV_FILE:-/etc/iaocr/iaocr.env}"
SERVICE_NAME="${SERVICE_NAME:-iaocr}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"

if [[ ! -f "$APP_ENV_FILE" ]]; then
  echo "[ERROR] Environment file not found: $APP_ENV_FILE"
  echo "Create it first (example: .env.production.example)"
  exit 1
fi

cd "$APP_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if ! sudo -n true 2>/dev/null; then
  echo "[ERROR] This script needs passwordless sudo for systemctl"
  echo "Grant sudo NOPASSWD for deploy user or run manually with sudo"
  exit 1
fi

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

sleep 3

if ! curl -fsS "$HEALTH_URL" >/dev/null; then
  echo "[ERROR] Health check failed: $HEALTH_URL"
  sudo systemctl status "$SERVICE_NAME" --no-pager || true
  exit 1
fi

echo "[OK] Deployment completed. Service $SERVICE_NAME is healthy."
