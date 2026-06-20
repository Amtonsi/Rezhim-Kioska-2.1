# -*- mode: python ; coding: utf-8 -*-
import os


project_root = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
entrypoint = os.path.join(project_root, "v2", "modern", "launcher_main.py")
package_root = os.path.join(project_root, "v2", "modern")
contracts = os.path.join(project_root, "v2", "contracts")

block_cipher = None

a = Analysis(
    [entrypoint],
    pathex=[package_root],
    binaries=[],
    datas=[(contracts, "contracts")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["kiosk_v2_legacy"],
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
    name='RezhimKioska-V2-Modern',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
