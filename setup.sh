#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "缺少 python3。请先安装 Python 3.12 或更高版本。"
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit("需要 Python 3.12 或更高版本")
PY

if ! command -v pnpm >/dev/null 2>&1; then
  echo "缺少 pnpm。请先安装 Node.js/pnpm，本脚本不会自动安装系统软件。"
  exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv .venv --python python3
  else
    python3 -m venv .venv
  fi
fi

if command -v uv >/dev/null 2>&1; then
  uv pip install --python .venv/bin/python -r backend/requirements-dev.txt
else
  .venv/bin/python -m pip install -r backend/requirements-dev.txt
fi

pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build

echo "安装完成。"
if command -v autossh >/dev/null 2>&1; then
  echo "autossh: $(command -v autossh)"
else
  echo "警告：未找到 autossh。使用前执行 brew install autossh。"
fi
echo "启动：./run.sh"

