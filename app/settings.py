# -*- coding: utf-8 -*-
"""
应用设置持久化（JSON，存放在 DATA_DIR/settings.json）。

独立于 SQLite：数据库更新/重建时设置不会丢失。
"""

import json

from . import config

# 图片存储方式
STORAGE_COPY = "copy"             # 全量复制：原图复制进程序托管目录
STORAGE_REFERENCE = "reference"   # 引用模式：只存缩略图，原图留在用户目录

_DEFAULTS = {
    "storage_mode": STORAGE_COPY,
    "reference_dir": "",          # 引用模式下原图所在目录（打开原图时定位）
}

_SETTINGS_PATH = config.DATA_DIR / "settings.json"


def load() -> dict:
    """读取设置；文件缺失或损坏时回退默认值。"""
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(_DEFAULTS)
        merged.update({k: v for k, v in data.items() if k in _DEFAULTS})
        return merged
    except (OSError, ValueError):
        return dict(_DEFAULTS)


def save(settings_data: dict) -> None:
    config.ensure_data()
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings_data, f, ensure_ascii=False, indent=2)


def get_storage_mode() -> str:
    return load().get("storage_mode", STORAGE_COPY)


def get_reference_dir() -> str:
    return load().get("reference_dir", "")


def set_storage_mode(mode: str, reference_dir: str = "") -> None:
    data = load()
    data["storage_mode"] = mode
    if mode == STORAGE_REFERENCE:
        data["reference_dir"] = reference_dir
    save(data)
