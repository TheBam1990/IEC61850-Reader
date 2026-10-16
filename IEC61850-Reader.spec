# -*- mode: python ; coding: utf-8 -*-
a = Analysis(["app.py"], pathex=[], binaries=[("build/Release/iec61850-bridge.exe", ".")], datas=[], hiddenimports=[], hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="IEC61850-Reader", debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, disable_windowed_traceback=False)
