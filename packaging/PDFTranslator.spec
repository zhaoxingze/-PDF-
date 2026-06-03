# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(SPECPATH).parent

OPTIONAL_EXCLUDES = [
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "IPython",
    "dask",
    "jupyter",
    "matplotlib",
    "notebook",
    "numpy",
    "pandas",
    "pytest",
    "scipy",
    "sphinx",
    "sentencepiece",
    "tokenizers",
    "torch",
    "transformers",
    "zmq",
]


a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "fonts" / "NotoSansSC-Regular.ttf"), "fonts"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=OPTIONAL_EXCLUDES,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name="PDFTranslator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
