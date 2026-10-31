#!/usr/bin/env bash
# ==============================================================================
# Avatar2 OxxxSec - Automated Virtual Environment Setup (Linux / macOS / WSL)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"

echo "================================================================="
echo "  🚀 Avatar2 Master Playbook - Environment Setup (Bash)  "
echo "================================================================="

if [ ! -f "${PYTHON_BIN}" ]; then
    echo "[*] Creating virtual environment in .venv..."
    python3 -m venv "${VENV_DIR}"
else
    echo "[+] Virtual environment already exists."
fi

echo "[*] Upgrading pip, setuptools, and wheel..."
"${PYTHON_BIN}" -m pip install --upgrade pip "setuptools<70" wheel

echo "[*] Installing dependencies..."
"${PYTHON_BIN}" -m pip install -r "${SCRIPT_DIR}/requirements.txt"

echo "[*] Running verification suite..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/verify_all.py"

echo ""
echo "[+] Setup completed successfully!"
echo "[*] Activate via: source .venv/bin/activate"
