#!/bin/bash
# Build script for Blossom LASIGE AppImage
# Usage: bash build_appimage.sh
set -e

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# VENV_PREFIX  = the active virtualenv (has site-packages with all our deps)
# BASE_PREFIX  = the real CPython install (has stdlib + interpreter binary)
VENV_PREFIX=$(python3 -c "import sys; print(sys.prefix)")
BASE_PREFIX=$(python3 -c "import sys; print(sys.base_prefix)")
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APPDIR="$PROJECT_DIR/AppDir"
DIST_DIR="$PROJECT_DIR/dist"
APPIMAGE_NAME="Blossom_LASIGE-x86_64.AppImage"
APPIMAGETOOL="$PROJECT_DIR/appimagetool-x86_64.AppImage"

echo "======================================="
echo " Blossom LASIGE AppImage Builder"
echo "======================================="
echo " Base Python   : $BASE_PREFIX"
echo " Virtualenv    : $VENV_PREFIX"
echo " Python version: $PYTHON_VERSION"
echo " Project dir   : $PROJECT_DIR"
echo "======================================="
echo ""

# ---------------------------------------------------------------------------
# 1. Clean and create AppDir
# ---------------------------------------------------------------------------
echo "[1/6] Preparing AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/python"
mkdir -p "$APPDIR/usr/src"
mkdir -p "$DIST_DIR"

# ---------------------------------------------------------------------------
# 2. Copy Python environment
#    Step 1: base CPython (stdlib + interpreter binary)
#    Step 2: virtualenv site-packages on top (our installed packages)
# ---------------------------------------------------------------------------
echo "[2/6] Copying Python environment (may take a while)..."

echo "  [2a] Copying base CPython from $BASE_PREFIX ..."
# Exclude 'envs/' — pyenv stores virtualenvs inside the base prefix;
# we handle site-packages separately in step [2b].
rsync -a --delete           \
    --exclude='__pycache__/'\
    --exclude='*.pyc'       \
    --exclude='*.pyo'       \
    --exclude='test/'       \
    --exclude='tests/'      \
    --exclude='ensurepip/'  \
    --exclude='pip/'        \
    --exclude='setuptools/' \
    --exclude='wheel/'      \
    --exclude='envs/'       \
    --exclude='tensorflow/' \
    --exclude='tensorflow_core/' \
    --exclude='tensorflow_estimator/' \
    --exclude='tensorboard/' \
    "$BASE_PREFIX/" "$APPDIR/usr/python/"

echo "  [2b] Overlaying virtualenv site-packages from $VENV_PREFIX ..."
# Keep __pycache__ here — large packages (mediapipe, tensorflow) need
# pre-compiled .pyc to avoid circular import issues during slow first import.
# Exclude tensorflow entirely: mediapipe only uses it for doc decorators
# (optional_dependencies.py catches ModuleNotFoundError already).
rsync -a                    \
    --exclude='test/'       \
    --exclude='tests/'      \
    --exclude='pip/'        \
    --exclude='setuptools/' \
    --exclude='wheel/'      \
    --exclude='tensorflow/' \
    --exclude='tensorflow_core/' \
    --exclude='tensorflow_estimator/' \
    --exclude='tensorboard/' \
    "$VENV_PREFIX/lib/python${PYTHON_VERSION}/site-packages/" \
    "$APPDIR/usr/python/lib/python${PYTHON_VERSION}/site-packages/"

# Patch mediapipe's optional_dependencies.py:
# The existing 'except ModuleNotFoundError' doesn't catch TensorFlow's
# circular ImportError. Widen it to catch both.
OPTIONAL_DEPS="$APPDIR/usr/python/lib/python${PYTHON_VERSION}/site-packages/mediapipe/tasks/python/core/optional_dependencies.py"
if [ -f "$OPTIONAL_DEPS" ]; then
    sed -i 's/except ModuleNotFoundError:/except (ModuleNotFoundError, ImportError):/' "$OPTIONAL_DEPS"
    echo "  Patched mediapipe/tasks/python/core/optional_dependencies.py"
fi

# ---------------------------------------------------------------------------
# 3. Copy application source code
# ---------------------------------------------------------------------------
echo "[3/6] Copying source code..."
cp "$PROJECT_DIR/start.py" "$APPDIR/usr/src/"

for dir in src mimetic blossom_public dancer; do
    rsync -a --delete               \
        --exclude='__pycache__/'    \
        --exclude='*.pyc'           \
        --exclude='output/'         \
        --exclude='build/'          \
        --exclude='dist/'           \
        "$PROJECT_DIR/$dir/" "$APPDIR/usr/src/$dir/"
done

# ---------------------------------------------------------------------------
# 4. AppImage metadata (AppRun + desktop entry + icon)
# ---------------------------------------------------------------------------
echo "[4/6] Preparing AppImage metadata..."

cp "$PROJECT_DIR/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

cp "$PROJECT_DIR/blossom.desktop" "$APPDIR/blossom.desktop"

# Icon — use existing file or generate a plain coloured square as fallback
if [ -f "$PROJECT_DIR/src/blossom.png" ]; then
    cp "$PROJECT_DIR/src/blossom.png" "$APPDIR/blossom.png"
elif command -v convert &>/dev/null; then
    convert -size 256x256 xc:'#3a7ebf' \
        -fill white -font DejaVu-Sans-Bold -pointsize 32 \
        -gravity center -annotate 0 "Blossom\nLASIGE" \
        "$PROJECT_DIR/src/blossom.png"
    cp "$PROJECT_DIR/src/blossom.png" "$APPDIR/blossom.png"
else
    # Minimal valid 1×1 PNG generated by Python (no external tool required)
    python3 - <<'PYEOF'
import struct, zlib, sys

def make_png(width, height, r, g, b):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_row = b"\x00" + bytes([r, g, b] * width)
    raw = raw_row * height
    idat = zlib.compress(raw)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat)
            + chunk(b"IEND", b""))

with open(sys.argv[1], "wb") as f:
    f.write(make_png(256, 256, 58, 126, 191))
PYEOF
    python3 - "$PROJECT_DIR/blossom.png" <<'PYEOF'
import struct, zlib, sys

def make_png(width, height, r, g, b):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_row = b"\x00" + bytes([r, g, b] * width)
    raw = raw_row * height
    idat = zlib.compress(raw)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat)
            + chunk(b"IEND", b""))

with open(sys.argv[1], "wb") as f:
    f.write(make_png(256, 256, 58, 126, 191))
PYEOF
    cp "$PROJECT_DIR/blossom.png" "$APPDIR/blossom.png"
fi

# ---------------------------------------------------------------------------
# 5. Download appimagetool if needed
# ---------------------------------------------------------------------------
echo "[5/6] Checking appimagetool..."
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "  Downloading appimagetool..."
    wget -q --show-progress \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
        -O "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
else
    echo "  appimagetool already present."
fi

# ---------------------------------------------------------------------------
# 6. Build the AppImage
# ---------------------------------------------------------------------------
echo "[6/6] Building AppImage..."
ARCH=x86_64 "$APPIMAGETOOL" --appimage-extract-and-run --comp gzip "$APPDIR" "$DIST_DIR/$APPIMAGE_NAME"

echo ""
echo "======================================="
echo " Done!"
echo " Output: dist/$APPIMAGE_NAME"
echo "======================================="
