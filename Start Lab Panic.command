#!/bin/zsh

set -e
cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/python" ]]; then
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import pygame" >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/python -m pip install -e . --no-deps
elif ! .venv/bin/python -c "import lab_panic" >/dev/null 2>&1; then
  .venv/bin/python -m pip install -e . --no-deps
fi

exec .venv/bin/python -m lab_panic.main
