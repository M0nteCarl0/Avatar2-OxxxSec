#!/usr/bin/env bash
# Quick launcher for post 08: Custom MMIO Peripheral Modeling with AvatarPeripheral
# Usage: ./run.sh   (extra arguments are forwarded to example.py)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON_BIN="python3"
for candidate in "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/.venv/Scripts/python.exe"; do
    if [ -x "${candidate}" ]; then
        PYTHON_BIN="${candidate}"
        break
    fi
done

cd "${SCRIPT_DIR}"
exec "${PYTHON_BIN}" example.py "$@"
