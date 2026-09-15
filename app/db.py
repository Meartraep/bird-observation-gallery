# -*- coding: utf-8 -*-
"""
SQLite 数据访问层。

分类数据(taxon)由 tools/build_database.py 从 eBird xlsx 一次性导入，
运行期只读；照片数据(photo)为应用业务数据，支持增删改备注。
"""

import sqlite3
import time
from contextlib import contextmanager

from . import config


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def database_exists() -> bool:
    return config.DB_PATH.exists()


def ensure_schema() -> None:
    """启动时做轻量迁移：旧库补列、新建缺失的表。"""
    with connect() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(photo)")}
        if "sort_order" not in cols:
            conn.execute(
                "ALTER TABLE photo "
                "ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
            )
        if "file_hash" not in cols:
            conn.execute(
                "ALTER TABLE photo ADD COLUMN file_hash TEXT"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS search_history (
                term    TEXT PRIMARY KEY,
                used_at INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # 兼容早期秒级 TEXT 结构的旧表：重建为毫秒整数（历史记录非关键数据，可重建）
        info = conn.execute("PRAGMA table_info(search_history)").fetchall()
        if any(r[1] == "used_at" and "INT" not in str(r[2]).upper()
               for r in info):
            conn.execute("DROP TABLE search_history")
            conn.execute(
                """
                CREATE TABLE search_history (
                    term    TEXT PRIMARY KEY,
                    used_at INTEGER NOT NULL DEFAULT 0
                )
                """
            )


# ---------------------------------------------------------------------------
# 分类数据
# ---------------------------------------------------------------------------
def iter_taxonomy():
    """
    按 eBird 官方顺序(taxon_order)遍历全部分类单元。
    行字段: species_code, category, name_zh, name_en, sci_name,
            order_name, family_sci, family_en
    """
    sql = """
        SELECT species_code, category, name_zh, name_en, sci_name,
               order_name, family_sci, family_en
        FROM taxon
        ORDER BY taxon_order
    """
    with connect() as conn:
        for row in conn.execute(sql):
            yield dict(row)


def get_taxon(species_code: str):
    sql = "SELECT * FROM taxon WHERE species_code = ?"
    with connect() as conn:
        row = conn.execute(sql, (species_code,)).fetchone()
        return dict(row) if row else None


def search_taxa(term: str, limit: int = 30):
    """
    中文学名 / 英文名 / 拉丁学名 / eBird 代码 / 四字母码模糊搜索。
    排序优先级: eBird 代码精确命中 > 名称前缀匹配 > 包含匹配。
    括号做全半角归一化 + 去除空格匹配：
    eBird 中文名用半角括号 () 且常带空格，用户输入全角括号（）或不带空格也能命中；
    英文名/学名去空格后多词输入（如 "common kingfisher"）也可命中。
    """
    term = term.strip().replace("（", "(").replace("）", ")")
    # 去空格要与 SQL 中对列的处理保持一致（半角 + 全角都去），
    # 否则中文输入法打出的全角空格会导致匹配不到
    term_nospace = term.replace(" ", "").replace("　", "")
    like = f"%{term_nospace}%"
    prefix = f"{term_nospace}%"
    sql = """
        SELECT species_code, category, name_zh, name_en, sci_name,
               order_name, family_sci, family_en, four_letter_code,
               CASE
                   WHEN species_code = :exact OR four_letter_code = :exact THEN 0
                   WHEN REPLACE(REPLACE(name_zh, ' ', ''), '　', '') LIKE :prefix
                     OR REPLACE(name_en, ' ', '') LIKE :prefix
                     OR REPLACE(sci_name, ' ', '') LIKE :prefix THEN 1
                   ELSE 2
               END AS match_rank
        FROM taxon
        WHERE REPLACE(REPLACE(name_zh, ' ', ''), '　', '') LIKE :like
           OR REPLACE(name_en, ' ', '') LIKE :like
           OR REPLACE(sci_name, ' ', '') LIKE :like
           OR species_code LIKE :like
           OR four_letter_code LIKE :like
        ORDER BY match_rank, taxon_order
        LIMIT :limit
    """
    with connect() as conn:
        rows = conn.execute(
            sql,
            {"like": like, "prefix": prefix, "exact": term.strip(),
             "limit": limit},
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 照片数据
# ---------------------------------------------------------------------------
def list_photos(species_code: str):
    """相册列表：新图(sort_order=0)默认排最前；用户上移/下移后按 sort_order 升序。"""
    sql = """
        SELECT id, species_code, file_path, thumb_path, note, created_at, sort_order
        FROM photo
        WHERE species_code = ?
        ORDER BY sort_order, id DESC
    """
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, (species_code,))]


def move_photo(photo_id: int, direction: int) -> bool:
    """
    调整某张照片的顺序。direction: -1 上移（向列表头），+1 下移（向列表尾）。
    交换后对该鸟种全部照片重新编号 sort_order=0,1,2...，保证唯一、顺序稳定。
    返回是否真的发生了移动（在边界时返回 False）。
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT species_code FROM photo WHERE id = ?", (photo_id,)
        ).fetchone()
        if row is None:
            return False
        ordered = [
            r["id"]
            for r in conn.execute(
                """SELECT id FROM photo WHERE species_code = ?
                   ORDER BY sort_order, id DESC""",
                (row["species_code"],),
            )
        ]
        idx = ordered.index(photo_id)
        other = idx + direction
        if other < 0 or other >= len(ordered):
            return False
        ordered[idx], ordered[other] = ordered[other], ordered[idx]
        for i, pid in enumerate(ordered):
            conn.execute(
                "UPDATE photo SET sort_order = ? WHERE id = ?", (i, pid)
            )
        return True


def add_photo(species_code: str, file_path: str, thumb_path: str,
              file_hash: str = None) -> int:
    sql = """
        INSERT INTO photo(species_code, file_path, thumb_path, file_hash)
        VALUES (?, ?, ?, ?)
    """
    with connect() as conn:
        cur = conn.execute(
            sql, (species_code, file_path, thumb_path, file_hash)
        )
        return cur.lastrowid


def get_photo_hashes(species_code: str) -> set:
    """该鸟种相册中已有照片的哈希集合（重复图片检测用）。"""
    with connect() as conn:
        rows = conn.execute(
            """SELECT file_hash FROM photo
               WHERE species_code = ? AND file_hash IS NOT NULL""",
            (species_code,),
        ).fetchall()
        return {r["file_hash"] for r in rows}


def get_photo(photo_id: int):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM photo WHERE id = ?", (photo_id,)
        ).fetchone()
        return dict(row) if row else None


def update_note(photo_id: int, note: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE photo SET note = ? WHERE id = ?", (note, photo_id))


def delete_photo(photo_id: int):
    """删除数据库记录，返回被删照片的(原图相对路径, 缩略图相对路径)供清理文件。"""
    with connect() as conn:
        row = conn.execute(
            "SELECT file_path, thumb_path FROM photo WHERE id = ?", (photo_id,)
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM photo WHERE id = ?", (photo_id,))
        return row["file_path"], row["thumb_path"]


def photo_count() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM photo").fetchone()[0]


def photo_species_codes() -> set:
    """返回所有已收录照片的鸟种 species_code 集合（成就清单用）。"""
    with connect() as conn:
        rows = conn.execute("SELECT DISTINCT species_code FROM photo").fetchall()
        return {r["species_code"] for r in rows}


# ---------------------------------------------------------------------------
# 搜索历史
# ---------------------------------------------------------------------------
def add_search_history(term: str) -> None:
    """记录一条搜索词；已存在则刷新使用时间（自然去重）。
    用毫秒时间戳，避免同一秒内多次搜索时排序不稳定。"""
    term = term.strip()
    if not term:
        return
    used_ms = int(time.time() * 1000)
    with connect() as conn:
        conn.execute(
            """INSERT INTO search_history(term, used_at) VALUES (?, ?)
               ON CONFLICT(term) DO UPDATE SET used_at = excluded.used_at""",
            (term, used_ms),
        )


def list_search_history(limit: int = 20):
    """按最近使用时间倒序返回搜索词列表。"""
    with connect() as conn:
        rows = conn.execute(
            "SELECT term FROM search_history "
            "ORDER BY used_at DESC, term LIMIT ?",
            (limit,),
        ).fetchall()
        return [r["term"] for r in rows]


def clear_search_history() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM search_history")


def taxon_count() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM taxon").fetchone()[0]
