#!/bin/sh
# Install from a checkout or an extracted source archive.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.11+ is required. Install Python and its venv support first." >&2
    exit 1
fi
exec python3 "$ROOT/tools/install_linux.py" "$@"
