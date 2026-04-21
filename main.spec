# -*- mode: python ; coding: utf-8 -*-

import os
import pathlib
import re


def _read_app_version():
    main_py = pathlib.Path("main.py").resolve()
    if not main_py.exists():
        raise ValueError("Could not locate main.py while reading app version")
    text = main_py.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        raise ValueError("Could not find __version__ in main.py")
    return m.group(1)


APP_VERSION = os.environ.get("PLOTTER_VERSION", _read_app_version())
DIST_NAME = f"Plotter-{APP_VERSION}"


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('full_config_reference.json', 'Config'),
        ('CHANGELOG.md', '.'),
        ('RELEASE_NOTES.md', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Plotter',
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=DIST_NAME,
)
