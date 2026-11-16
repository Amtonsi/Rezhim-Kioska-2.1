# -*- mode: python ; coding: utf-8 -*-
import os


project_root = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
entrypoint = os.path.join(project_root, "v2", "modern", "restore_main.py")
package_root = os.path.join(project_root, "v2", "modern")

block_cipher = None

a = Analysis(
    [entrypoint],
    pathex=[package_root],
    binaries=[],
    datas=[(os.path.join(project_root, "v2", "contracts", "kiosk-config-v2.schema.json"), "contracts")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "kiosk_v2_legacy"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Restore-V2-Modern',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
)
