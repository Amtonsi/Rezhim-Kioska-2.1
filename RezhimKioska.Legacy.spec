# -*- mode: python -*-

import os


block_cipher = None
project_root = os.path.abspath(os.path.dirname(SPEC))

a = Analysis(
    [os.path.join(project_root, "legacy_main.py")],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, "config", "kiosk.legacy.json"), "config"),
    ],
    hiddenimports=["Tkinter", "tkFileDialog", "tkMessageBox"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="RezhimKioska-Legacy",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
