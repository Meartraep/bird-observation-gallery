# -*- coding: utf-8 -*-
"""
生成 PyInstaller 用的 Windows 版本资源文件（VSVersionInfo 文本）。

为什么需要：Windows「属性 → 详细信息」里的产品名称 / 版本号来自 exe 的版本
资源，而 PyInstaller 默认不写（实测冻结后的 exe 里 VersionInfo 全空）。
代码签名（SignPath）的 artifact configuration 还会强制校验这些元数据每次
构建都固定，所以必须显式写入。

版本号唯一来源仍是 app/__init__.py 的 __version__，本模块只做派生：
  - FileVersion / FILEVERSION 用 x.y.z.0 形式（与 bird_album.iss 的
    VersionInfoVersion={#MyAppVersion}.0 保持一致）；
  - ProductVersion 用 x.y.z 形式（与 AppVersion / MyAppVersion 一致）。
"""

import sys
from pathlib import Path

APP_NAME = "鸟类相册"
APP_PUBLISHER = "BirdAlbum"
APP_LICENSE = "GPL-3.0"
APP_DESCRIPTION = "鸟类相册 —— 离线本地鸟类相册（基于 eBird 分类体系）"
APP_EXE_NAME = "鸟类相册.exe"

# StringTable 的键：0812 = 简体中文，04B0 = 1200(UTF-16)。与 VarFileInfo 的
# Translation 必须一致，否则 Windows 只显示「文件说明」等默认键。
_LANG_ID = 0x0804
_CODEPAGE = 1200
_LANG_KEY = f"{_LANG_ID:04X}{_CODEPAGE:04X}"


def version_parts(version: str) -> tuple:
    """"0.1.0" -> (0, 1, 0, 0)；非数字段按 0 处理，长度不足补 0。"""
    parts = []
    for chunk in version.split(".")[:4]:
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple((parts + [0, 0, 0, 0])[:4])


def build_version_info_text(version: str) -> str:
    """返回 VSVersionInfo 文本。PyInstaller 用 eval 解析，结构不能改。"""
    v4 = version_parts(version)
    file_version = "{}.{}.{}.{}".format(*v4)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={v4},
    prodvers={v4},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          "{_LANG_KEY}",
          [
            StringStruct("CompanyName", "{APP_PUBLISHER}"),
            StringStruct("FileDescription", "{APP_DESCRIPTION}"),
            StringStruct("FileVersion", "{file_version}"),
            StringStruct("InternalName", "BirdAlbum"),
            StringStruct("LegalCopyright", "{APP_LICENSE}"),
            StringStruct("OriginalFilename", "{APP_EXE_NAME}"),
            StringStruct("ProductName", "{APP_NAME}"),
            StringStruct("ProductVersion", "{version}"),
          ],
        )
      ]
    ),
    VarFileInfo([VarStruct("Translation", [{_LANG_ID}, {_CODEPAGE}])]),
  ],
)
"""


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    """命令行入口：写入 build/version_info.txt（PyInstaller 的 spec 也会直接调
    build_version_info_text，不依赖这个文件，所以 --clean 清空 build 也不影响）。"""
    sys.path.insert(0, str(_project_root()))
    from app import __version__  # 版本号唯一源头

    out = _project_root() / "build" / "version_info.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_version_info_text(__version__), encoding="utf-8")
    print(f"已写入 {out}（版本 {__version__}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
