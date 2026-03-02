#!/bin/bash
# Build script for Blossom LASIGE Research
# Usage: bash build.sh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION=$(git -C "$PROJECT_DIR" describe --tags --abbrev=0 2>/dev/null || echo "dev")
OUTPUT="Blossom_LASIGE_Research-${VERSION}-x86_64"

echo "======================================="
echo " Blossom LASIGE Research — PyInstaller"
echo " Version : $VERSION"
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

# Rename output to include version
mv "$PROJECT_DIR/dist/Blossom_LASIGE_Research" "$PROJECT_DIR/dist/$OUTPUT"

echo ""
echo "======================================="
echo " Done!"
echo " Output: dist/$OUTPUT"
echo "======================================="
