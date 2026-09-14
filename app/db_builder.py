# -*- coding: utf-8 -*-
"""
eBird xlsx 分类表 -> SQLite 转换核心（CLI 与 UI 共用）。

tools/build_database.py 是本模块的命令行入口；
app/update_dialog.py 通过 update_database() 在 UI 中更新数据库。
更新时会保留用户业务数据（photo、search_history）。
"""

import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

from . import config

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
SHEET_NAME = "full_sparse"
BATCH_SIZE = 1000

# xlsx 中需要提取的列名 -> 程序内部字段
COLUMN_MAP = {
    "taxon_order": "taxon_order",
    "category": "category",
    "species_code": "species_code",
    "primary_com_name": "name_en",
    "Chinese, Simple": "name_zh",
    "sci_name": "sci_name",
    "order1": "order_name",
    "family": "family_raw",
    "species_group": "group_name",
    "report_as": "report_as",
    "four_letter_code": "four_letter_code",
    "extinct": "extinct",
    "extinct_year": "extinct_year",
}

# family 列形如 "Struthionidae (Ostriches)"，拆成拉丁科名 + 英文科名
FAMILY_RE = re.compile(r"^\s*(.+?)\s*[（(](.+?)[）)]\s*$")

# ---------------------------------------------------------------------------
# SQL 表结构
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- 鸟类分类单元（种 / 亚种 issf / 杂交 / slash / spuh 等，对应左侧树的叶子）
CREATE TABLE taxon (
    species_code     TEXT PRIMARY KEY,          -- eBird 物种代码，如 ostric2
    taxon_order      INTEGER NOT NULL,          -- eBird 全局分类序号（排序用）
    category         TEXT NOT NULL,             -- species/issf/hybrid/slash/spuh/form/domestic/intergrade
    name_en          TEXT NOT NULL,             -- 英文通用名
    name_zh          TEXT,                      -- 简体中文名（无官方中译时为 NULL，界面回退英文名）
    sci_name         TEXT NOT NULL,             -- 拉丁学名
    order_name       TEXT,                      -- 目（拉丁），如 Struthioniformes，树第 1 级
    family_sci       TEXT,                      -- 科（拉丁），如 Struthionidae，树第 2 级
    family_en        TEXT,                      -- 科（英文），如 Ostriches
    group_name       TEXT,                      -- eBird 鸟类群组（非分类层级，备用）
    report_as        TEXT,                      -- 该分类单元上报时归属的 species_code
    four_letter_code TEXT,                      -- 四字母简码
    extinct          INTEGER NOT NULL DEFAULT 0,-- 是否灭绝 0/1
    extinct_year     INTEGER                    -- 灭绝年份
);

CREATE INDEX idx_taxon_order        ON taxon(taxon_order);
CREATE INDEX idx_taxon_hierarchy    ON taxon(order_name, family_sci, taxon_order);
CREATE INDEX idx_taxon_name_zh      ON taxon(name_zh);

-- 数据库元信息（数据版本、构建时间等）
CREATE TABLE app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- 照片表（应用业务数据：原图、缩略图、备注、顺序、哈希）
CREATE TABLE photo (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    species_code TEXT NOT NULL REFERENCES taxon(species_code),
    file_path    TEXT NOT NULL,                 -- 原图（应用托管目录内的相对路径）
    thumb_path   TEXT,                          -- 缩略图路径
    note         TEXT NOT NULL DEFAULT '',      -- 照片下方的说明备注
    created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    sort_order   INTEGER NOT NULL DEFAULT 0,    -- 用户自定义排序
    file_hash    TEXT                           -- 图片 SHA-256（重复检测）
);

CREATE INDEX idx_photo_species ON photo(species_code, created_at);

-- 搜索历史
CREATE TABLE IF NOT EXISTS search_history (
    term    TEXT PRIMARY KEY,
    used_at INTEGER NOT NULL DEFAULT 0
);
"""


# ---------------------------------------------------------------------------
# 单元格清洗
# ---------------------------------------------------------------------------
def clean(value):
    """None / 空白串 -> None，其余去首尾空白。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_int(value):
    text = clean(value)
    if text is None:
        return None
    return int(float(text))


def split_family(raw):
    """'Struthionidae (Ostriches)' -> ('Struthionidae', 'Ostriches')。"""
    if not raw:
        return None, None
    m = FAMILY_RE.match(raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return raw.strip(), None


# ---------------------------------------------------------------------------
# 校验与读取
# ---------------------------------------------------------------------------
def validate_xlsx(xlsx_path: Path):
    """
    校验文件是否为可用的 eBird 分类表。
    返回 (ok: bool, message: str)。ok=False 时 message 为可展示给用户的失败原因。
    """
    xlsx_path = Path(xlsx_path)
    if not xlsx_path.exists():
        return False, f"文件不存在：{xlsx_path}"
    if xlsx_path.suffix.lower() != ".xlsx":
        return False, f"不是 Excel 文件（.xlsx）：{xlsx_path.name}"
    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    except Exception:
        return False, "文件无法打开或已损坏，不是有效的 Excel 文件。"
    try:
        if SHEET_NAME not in wb.sheetnames:
            return False, (
                f"不是有效的 eBird 分类表：缺少工作表「{SHEET_NAME}」。"
            )
        ws = wb[SHEET_NAME]
        header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        missing = [c for c in COLUMN_MAP if c not in header]
        if missing:
            return False, (
                "不是有效的 eBird 分类表：缺少必需列 "
                + "、".join(missing[:5]) + "。"
            )
        return True, "ok"
    finally:
        wb.close()


def extract_rows(xlsx_path: Path, progress_cb=None):
    """
    流式读取 xlsx，逐行产出裁剪后的字典记录。
    progress_cb(done: int, total: int) 在每批后回调（total 为估算值）。
    """
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb[SHEET_NAME]
        total_est = max(ws.max_row - 1, 1) if ws.max_row else 1
        row_iter = ws.iter_rows(values_only=True)
        header = next(row_iter)
        col_index = {}
        missing = []
        for xlsx_col, field in COLUMN_MAP.items():
            try:
                col_index[field] = header.index(xlsx_col)
            except ValueError:
                missing.append(xlsx_col)
        if missing:
            raise RuntimeError(
                f"工作表 {SHEET_NAME} 缺少必需列: {missing}"
            )

        seen_codes = set()
        done = 0
        for line_no, row in enumerate(row_iter, start=2):
            get = lambda f: row[col_index[f]]  # noqa: E731

            code = clean(get("species_code"))
            name_en = clean(get("name_en"))
            sci_name = clean(get("sci_name"))
            if not code or not name_en or not sci_name:
                continue
            if code in seen_codes:
                raise RuntimeError(f"第 {line_no} 行 species_code 重复: {code}")
            seen_codes.add(code)

            family_sci, family_en = split_family(clean(get("family_raw")))
            yield {
                "species_code": code,
                "taxon_order": parse_int(get("taxon_order")),
                "category": clean(get("category")) or "unknown",
                "name_en": name_en,
                "name_zh": clean(get("name_zh")),
                "sci_name": sci_name,
                "order_name": clean(get("order_name")),
                "family_sci": family_sci,
                "family_en": family_en,
                "group_name": clean(get("group_name")),
                "report_as": clean(get("report_as")),
                "four_letter_code": clean(get("four_letter_code")),
                "extinct": parse_int(get("extinct")) or 0,
                "extinct_year": parse_int(get("extinct_year")),
            }
            done += 1
            if progress_cb and done % 1000 == 0:
                progress_cb(done, total_est)
    finally:
        wb.close()


# ---------------------------------------------------------------------------
# 构建数据库
# ---------------------------------------------------------------------------
def build_database(xlsx_path: Path, db_path: Path, progress_cb=None) -> None:
    """从 xlsx 全新建库（含全部表结构）。db_path 存在时直接覆盖。"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        insert_sql = """
            INSERT INTO taxon (
                species_code, taxon_order, category, name_en, name_zh, sci_name,
                order_name, family_sci, family_en, group_name, report_as,
                four_letter_code, extinct, extinct_year
            ) VALUES (
                :species_code, :taxon_order, :category, :name_en, :name_zh, :sci_name,
                :order_name, :family_sci, :family_en, :group_name, :report_as,
                :four_letter_code, :extinct, :extinct_year
            )
        """
        batch = []
        total = 0
        for record in extract_rows(xlsx_path, progress_cb):
            batch.append(record)
            total += 1
            if len(batch) >= BATCH_SIZE:
                conn.executemany(insert_sql, batch)
                conn.commit()
                batch = []
        if batch:
            conn.executemany(insert_sql, batch)
            conn.commit()

        meta = {
            "source_file": Path(xlsx_path).name,
            "source_sheet": SHEET_NAME,
            "authority_code": "EBIRD",
            "built_at_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            ),
            "taxon_count": str(total),
        }
        conn.executemany(
            "INSERT INTO app_meta(key, value) VALUES (?, ?)", meta.items()
        )
        conn.commit()
    except Exception:
        conn.close()
        db_path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()


def update_database(xlsx_path: Path, progress_cb=None) -> dict:
    """
    用新的 eBird xlsx 更新正式数据库：
      1. 构建临时库 birds_new.db
      2. 迁移旧库的业务数据（photo、search_history）
      3. 备份旧库 -> 原子替换 -> 清理备份
    返回统计信息 dict：{taxon_count, photo_count, history_count}。
    校验失败或转换失败抛 ValueError / RuntimeError（message 可展示给用户）。
    """
    xlsx_path = Path(xlsx_path)
    ok, msg = validate_xlsx(xlsx_path)
    if not ok:
        raise ValueError(msg)

    old_db = config.DB_PATH
    new_db = old_db.with_name("birds_new.db")
    backup = old_db.with_name("birds.db.bak")

    build_database(xlsx_path, new_db, progress_cb)

    # 迁移旧库业务数据（照片、搜索历史），保留用户数据
    stats = {"taxon_count": 0, "photo_count": 0, "history_count": 0}
    if old_db.exists():
        conn = sqlite3.connect(new_db)
        try:
            conn.execute("ATTACH ? AS old", (str(old_db),))
            # 旧库照片列可能比新库少（历史版本），取交集列迁移
            old_photo_cols = {
                r[1] for r in conn.execute("PRAGMA old.table_info(photo)")
            }
            photo_cols = [
                c for c in (
                    "species_code", "file_path", "thumb_path", "note",
                    "created_at", "sort_order", "file_hash",
                ) if c in old_photo_cols
            ]
            if photo_cols:
                cols_sql = ", ".join(photo_cols)
                conn.execute(
                    f"INSERT INTO photo({cols_sql}) "
                    f"SELECT {cols_sql} FROM old.photo"
                )
            # 搜索历史（旧库可能无此表）
            old_tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM old.sqlite_master WHERE type='table'"
                )
            }
            if "search_history" in old_tables:
                conn.execute(
                    "INSERT INTO search_history(term, used_at) "
                    "SELECT term, used_at FROM old.search_history"
                )
            conn.commit()
        finally:
            conn.close()

    # 统计（注意：with sqlite3.connect 不关闭连接，需显式 close）
    conn = sqlite3.connect(new_db)
    try:
        stats["taxon_count"] = conn.execute(
            "SELECT COUNT(*) FROM taxon"
        ).fetchone()[0]
        stats["photo_count"] = conn.execute(
            "SELECT COUNT(*) FROM photo"
        ).fetchone()[0]
        stats["history_count"] = conn.execute(
            "SELECT COUNT(*) FROM search_history"
        ).fetchone()[0]
    finally:
        conn.close()

    # 原子替换：备份 -> 替换 -> 删除备份
    if old_db.exists():
        shutil.copy2(old_db, backup)
    os.replace(new_db, old_db)
    backup.unlink(missing_ok=True)
    return stats


# ---------------------------------------------------------------------------
# 校验（构建后自检）
# ---------------------------------------------------------------------------
def verify(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        assert ok == "ok", f"integrity_check = {ok}"
        total = conn.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
        n_order = conn.execute(
            "SELECT COUNT(DISTINCT order_name) FROM taxon"
        ).fetchone()[0]
        n_family = conn.execute(
            "SELECT COUNT(DISTINCT family_sci) FROM taxon"
        ).fetchone()[0]
        print(f"校验: taxon={total} 行, 目={n_order}, 科={n_family}")
    finally:
        conn.close()
