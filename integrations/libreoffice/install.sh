#!/bin/sh
# Install the OXT into the current user's LibreOffice profile.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if ! command -v unopkg >/dev/null 2>&1; then
    echo 'LibreOffice extension manager (unopkg) is required.' >&2
    exit 1
fi
python3 "$ROOT/tools/build_libreoffice.py"
exec unopkg add --force "$ROOT/dist/inlay-writer-0.1.0.oxt"
