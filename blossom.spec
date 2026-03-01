# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect all files for packages with native extensions or data assets
mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")
cv2_datas, cv2_binaries, cv2_hiddenimports = collect_all("cv2")
librosa_datas, librosa_binaries, librosa_hiddenimports = collect_all("librosa")

datas = [
    ("src", "src"),
    ("dancer", "dancer"),
    ("mimetic", "mimetic"),
    ("blossom_public", "blossom_public"),
]
datas += mediapipe_datas
datas += cv2_datas
datas += librosa_datas

binaries = []
binaries += mediapipe_binaries
binaries += cv2_binaries
binaries += librosa_binaries

hiddenimports = [
    "PyQt6.sip",
    "PyQt6.QtCore",
    "PyQt6.QtWidgets",
    "PyQt6.QtGui",
    "PyQt6.QtNetwork",
    "scipy",
    "scipy.signal",
    "scipy.fftpack",
    "numpy",
    "sounddevice",
    "_sounddevice_data",
    "pypot",
    "ikpy",
    "ikpy.chain",
    "ikpy.link",
    "flask",
    "flask_cors",
    "matplotlib",
    "matplotlib.backends.backend_agg",
    "pandas",
    "seaborn",
    "fpdf",
    "sympy",
    "requests",
    "sseclient",
    "configargparse",
    "prettytable",
]
hiddenimports += mediapipe_hiddenimports
hiddenimports += cv2_hiddenimports
hiddenimports += librosa_hiddenimports

a = Analysis(
    ["start.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="blossom",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="blossom",
)
