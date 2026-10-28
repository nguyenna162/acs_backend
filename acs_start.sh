#!/usr/bin/env bash
# ================================================================
# ACS Backend - AMR Fleet Controller (CNC Prod 2G) Launch Script
# ================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
else
    PYTHON_CMD="python3"
fi

echo "================================================================"
echo "   KHOI DONG HE THONG ACS BACKEND - VDA 5050 v2.1.0"
echo "   Khu vuc: CNC Prod 2G - Dieu khien & Quan ly AMR"
echo "================================================================"

echo "[1/2] Dang kiem tra va ap dung migrations co so du lieu..."
$PYTHON_CMD manage.py migrate --noinput

echo "[2/2] Dang khoi chay he thong bang acs_launch.py..."
exec $PYTHON_CMD acs_launch.py
