#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -x .venv/bin/python || ! -f frontend/dist/index.html ]]; then
  ./setup.sh
fi

exec .venv/bin/python app.py

