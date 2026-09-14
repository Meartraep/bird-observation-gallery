# -*- coding: utf-8 -*-
"""
eBird 分类表 (xlsx) -> SQLite 数据库转换程序（命令行入口）。

转换核心逻辑在 app/db_builder.py（与 UI 内"更新数据库"共用）。
数据裁剪说明见 app/db_builder.py 顶部注释。

用法:
  python tools/build_database.py                 # 默认路径转换（覆盖已存在库）
  python tools/build_database.py --xlsx 其他.xlsx --db 其他.db
"""

import argparse
import sys
from pathlib import Path

# 让脚本可直接运行（python tools/build_database.py）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.db_builder import (  # noqa: E402
    build_database,
    verify,
    validate_xlsx,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="eBird xlsx 分类表 -> SQLite 转换程序")
    parser.add_argument("--xlsx", type=Path, default=None, help="eBird xlsx 源文件路径")
    parser.add_argument("--db", type=Path, default=None, help="输出 SQLite 数据库路径")
    parser.add_argument("--force", action="store_true",
                        help="覆盖已存在的数据库（会丢失其内的照片数据）")
    args = parser.parse_args()

    xlsx = args.xlsx or next(
        (p for p in config.BASE_DIR.glob("eBird_Taxonomy_*.xlsx")),
        None,
    )
    db = args.db or config.DB_PATH
    if xlsx is None:
        raise SystemExit("找不到 eBird xlsx 源文件，请用 --xlsx 指定")

    ok, msg = validate_xlsx(xlsx)
    if not ok:
        raise SystemExit(msg)
    if db.exists() and not args.force:
        raise SystemExit(
            f"目标数据库已存在: {db}\n"
            "如确定覆盖请加 --force（注意：会清空其中照片/搜索历史数据；"
            "在程序内请用「更新数据库」按钮以保留数据）"
        )

    print(f"源文件 : {xlsx}")
    print(f"数据库 : {db}\n")
    build_database(xlsx, db)
    verify(db)


if __name__ == "__main__":
    main()
