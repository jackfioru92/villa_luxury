#!/bin/bash
# Importa i calendari dei portali esterni (Booking.com, Airbnb, ...).
# Da cron ogni 15 minuti:
#   */15 * * * * /opt/altesiasuite/app/scripts/sync_calendars.sh
set -euo pipefail

APP_DIR=/opt/altesiasuite/app
VENV=/opt/altesiasuite/venv
LOG_DIR="$APP_DIR/logs"

mkdir -p "$LOG_DIR"
cd "$APP_DIR"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "--- $(date '+%Y-%m-%d %H:%M:%S') ---" >> "$LOG_DIR/calendar-sync.log"
python manage.py sync_calendars >> "$LOG_DIR/calendar-sync.log" 2>&1
