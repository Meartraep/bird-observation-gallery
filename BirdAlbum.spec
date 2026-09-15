# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置（onedir 模式，供 Inno Setup 安装器使用）。

构建：pyinstaller BirdAlbum.spec --noconfirm
产物：dist/鸟类相册/鸟类相册.exe
注意：不含任何数据库种子文件（eBird 数据合规），首次运行由用户导入。
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# 版本资源：Windows「属性 → 详细信息」里的产品名称 / 版本号来自 exe 的版本资源，
# PyInstaller 默认不写（实测冻结后 VersionInfo 全空）。代码签名（SignPath）的
# artifact configuration 还会强制校验这些元数据，所以必须写入，见项目记忆第 8 节。
# 这里在 spec 里现生成、而不是要求先跑 tools/make_version_info.py：--clean 会清空
# build/，"先生成文件再构建"的顺序很容易踩空。版本号仍只有 app/__init__.py 一处。
# 注：spec 命名空间只注入 SPEC / SPECPATH / DISTPATH（6.22.3 实测没有 WORKPATH），
# 且 --clean 的清空发生在 spec 执行之前，故这里写 build/ 不会被清掉。
sys.path.insert(0, SPECPATH)
from app import __version__
from tools.make_version_info import build_version_info_text

_version_file = Path(SPECPATH) / "build" / "version_info.txt"
_version_file.parent.mkdir(parents=True, exist_ok=True)
_version_file.write_text(build_version_info_text(__version__), encoding="utf-8")

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
    # UPX 压缩过的 exe / DLL 更容易被杀软误报，且与代码签名叠加时风险更高
    upx=False,
    console=False,
    icon="assets/icon.ico",
    version=str(_version_file),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="鸟类相册",
)
