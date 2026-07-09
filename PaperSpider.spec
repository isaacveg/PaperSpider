# -*- mode: python ; coding: utf-8 -*-
import sys

# Platform-appropriate icon: .icns on macOS, .ico on Windows.
_icon = 'assets/icon.icns' if sys.platform == 'darwin' else 'assets/icon.ico'


a = Analysis(
    ['paper_spider/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name='PaperSpider',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=_icon,
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
    name='PaperSpider',
)
# The .app bundle is a macOS-only concept; on Windows we ship the
# COLLECT directory (dist/PaperSpider/) directly.
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='PaperSpider.app',
        icon=_icon,
        bundle_identifier=None,
    )
