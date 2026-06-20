# -*- mode: python ; coding: utf-8 -*-
import os


project_root = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
entrypoint = os.path.join(project_root, "v2", "legacy", "restore_main.py")
package_root = os.path.join(project_root, "v2", "legacy")

block_cipher = None

a = Analysis(
    [entrypoint],
    pathex=[package_root],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["Tkinter", "tkMessageBox", "kiosk_v2_modern"],
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
    name='Restore-V2-Legacy',
    debug=False,
    strip=False,
    upx=True,
    console=True,
)
