#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-iaocr}"
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
APP_USER="${APP_USER:-$USER}"
APP_GROUP="${APP_GROUP:-$USER}"
APP_ENV_FILE="${APP_ENV_FILE:-/etc/iaocr/iaocr.env}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [[ ! -d "$APP_DIR" ]]; then
  echo "[ERROR] APP_DIR does not exist: $APP_DIR"
  exit 1
fi

sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=IaOCR FastAPI Service
After=network-online.target ollama.service
Wants=network-online.target
Requires=ollama.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_ENV_FILE
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
TimeoutStopSec=30
KillSignal=SIGINT
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo "[OK] Created service file: $SERVICE_FILE"
echo "[INFO] Start service with: sudo systemctl start $SERVICE_NAME"
