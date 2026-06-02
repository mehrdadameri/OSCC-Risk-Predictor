#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  exec python3 install.py "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python install.py "$@"
fi

echo "Python 3.10+ was not found. Install Python, then rerun this installer." >&2
exit 1
