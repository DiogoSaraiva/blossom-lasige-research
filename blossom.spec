# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Blossom LASIGE Research
#
# Build with:
#   pip install pyinstaller
#   pyinstaller blossom.spec
#
# Output: dist/Blossom_LASIGE_Research/
#   Blossom_LASIGE_Research   — main GUI executable
#   _internal/                — bundled Python libs + assets
#     mimetic/models/
#     src/blossom.png
#     dancer/musics/

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

COMMON_EXCLUDES = [
    "tkinter",
    "tensorflow",
    "tensorflow_core",
    "tensorflow_estimator",
    "tensorboard",
    "IPython",
    "jupyter",
    "pysqlite2",
    "MySQLdb",
    "psycopg2",
]

a = Analysis(
    ["start.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("mimetic/models/", "mimetic/models/"),
        ("src/blossom.png", "src/"),
        ("dancer/musics/", "dancer/musics/"),
    ],
    hiddenimports=[
        *collect_submodules("src"),
        *collect_submodules("mimetic"),
        *collect_submodules("dancer"),
        "serial.tools.list_ports",
        "PyQt6.QtSvg",
        "PyQt6.QtXml",
        "mediapipe.tasks.python",
        "mediapipe.tasks.python.vision",
        "mediapipe.tasks.python.components.containers",
        "mediapipe.tasks.python.components.processors",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=COMMON_EXCLUDES,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Blossom_LASIGE_Research",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Blossom_LASIGE_Research",
)
