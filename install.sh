#!/usr/bin/env bash
# Blossom LASIGE Research installer
# Usage: ./install.sh [--uninstall]
set -euo pipefail

INSTALL_DIR="/opt/BlossomLASIGEResearch"
BIN_LINK="/usr/local/bin/blossom-lasige-research"
DESKTOP_FILE="$HOME/.local/share/applications/blossom-lasige-research.desktop"
ICON_FILE="$HOME/.local/share/icons/blossom-lasige-research.png"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist/Blossom_LASIGE_Research"

# ── Uninstall ──────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" ]]; then
    echo "Uninstalling Blossom LASIGE Research..."
    sudo rm -rf "$INSTALL_DIR"
    sudo rm -f  "$BIN_LINK"
    rm -f "$DESKTOP_FILE" "$ICON_FILE"
    echo "Done. User data in ~/BlossomLASIGEResearch-data (if any) was NOT removed."
    exit 0
fi

# ── Checks ─────────────────────────────────────────────────────────────────
if [ ! -d "$DIST_DIR" ]; then
    echo "ERROR: Build not found at $DIST_DIR"
    echo "Run 'bash build.sh' first."
    exit 1
fi

# ── Install ────────────────────────────────────────────────────────────────
echo "Installing Blossom LASIGE Research to $INSTALL_DIR ..."

sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$DIST_DIR/." "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/Blossom_LASIGE_Research"

# Symlink into PATH
sudo ln -sf "$INSTALL_DIR/Blossom_LASIGE_Research" "$BIN_LINK"
echo "  → symlink: $BIN_LINK"

# Icon
mkdir -p "$(dirname "$ICON_FILE")"
if [ -f "$DIST_DIR/_internal/src/blossom.png" ]; then
    cp "$DIST_DIR/_internal/src/blossom.png" "$ICON_FILE"
fi

# Desktop entry (application menu)
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Blossom LASIGE Research
Comment=Blossom robot research application
Exec=$INSTALL_DIR/Blossom_LASIGE_Research
Icon=$ICON_FILE
Terminal=false
Type=Application
Categories=Science;Education;
StartupWMClass=blossom-lasige-research
EOF
update-desktop-database "$(dirname "$DESKTOP_FILE")" 2>/dev/null || true
echo "  → desktop entry: $DESKTOP_FILE"

# Serial port permissions (needed for USB/robot connection)
if ! id -nG "$USER" | grep -qw dialout; then
    echo ""
    echo "  → WARNING: '$USER' não está no grupo 'dialout'."
    echo "     O robot Blossom usa uma porta USB série (/dev/ttyACM*)."
    echo "     Execute uma vez e depois faça logout/login:"
    echo "       sudo usermod -aG dialout $USER"
fi

echo ""
echo "Installation complete!"
echo "  Run:  blossom-lasige-research"
echo "   or open it from the application menu."
echo ""
echo "To uninstall: bash $INSTALL_DIR/install.sh --uninstall"
