# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置（onedir 模式，供 Inno Setup 安装器使用）。

构建：pyinstaller BirdAlbum.spec --noconfirm
产物：dist/鸟类相册/鸟类相册.exe
注意：不含任何数据库种子文件（eBird 数据合规），首次运行由用户导入。
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("PIL")
hiddenimports += collect_submodules("openpyxl")

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=[],
    # 注意：eBird 分类表及其演绎产物不允许分发，不打包任何数据库种子文件。
    # 首次运行由用户从官方地址自行下载并导入。
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="鸟类相册",
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="鸟类相册",
)
