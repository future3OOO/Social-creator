#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

rsync -avz --delete \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='.env' \
  --exclude='.git/' \
  --exclude='.pytest_cache/' \
  "$SCRIPT_DIR/" \
  "codex@hetzner-chch:/home/codex/listing-creator/"

echo "Deployed. Run on server:"
echo "  ssh hetzner-chch 'cd /home/codex/listing-creator && source venv/bin/activate && python main.py'"
