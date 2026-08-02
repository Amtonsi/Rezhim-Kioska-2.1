# -*- mode: python ; coding: utf-8 -*-
import os


project_root = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
entrypoint = os.path.join(project_root, "v2", "legacy", "configurator_main.py")
package_root = os.path.join(project_root, "v2", "legacy")
contracts = os.path.join(project_root, "v2", "contracts")

block_cipher = None

a = Analysis(
    [entrypoint],
    pathex=[package_root],
    binaries=[],
    datas=[(contracts, "contracts")],
    hiddenimports=["Tkinter", "tkFileDialog", "tkMessageBox"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["kiosk_v2_modern"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='Configurator-V2-Legacy',
    debug=False,
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
    name='Configurator-V2-Legacy',
)
