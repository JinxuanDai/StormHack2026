from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "tools" / "windows_launcher.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Lab Panic",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
