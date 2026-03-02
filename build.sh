#!/bin/bash
# Build script for Blossom LASIGE Research
# Usage: bash build.sh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "======================================="
echo " Blossom LASIGE Research — PyInstaller"
echo "======================================="

# Install PyInstaller if not present
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "[1/2] Installing PyInstaller..."
    pip install pyinstaller
else
    echo "[1/2] PyInstaller already installed."
fi

# Build
echo "[2/2] Building..."
cd "$PROJECT_DIR"
pyinstaller blossom.spec

echo ""
echo "======================================="
echo " Done!"
echo " Output: dist/Blossom_LASIGE_Research/"
echo " To install: bash install.sh"
echo "======================================="
