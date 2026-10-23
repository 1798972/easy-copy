"""路径、默认配置与配置文件读写。"""

import json
from pathlib import Path

from gi.repository import GLib

APP_ID = "io.github._1798972.EasyCopy"
DATA_DIR = Path(GLib.get_user_data_dir()) / "easy-copy"
IMG_DIR = DATA_DIR / "images"
HISTORY_FILE = DATA_DIR / "history.json"
TRASH_FILE = DATA_DIR / "trash.json"
CONFIG_FILE = Path(GLib.get_user_config_dir()) / "easy-copy" / "config.json"

DEFAULTS = {                 # 都能在「设置」窗口里改，存 CONFIG_FILE
    "hotkey": "<Super>v",            # 全局：呼出面板
    "hotkey_trash": "",              # 全局：直接呼出回收站（默认不设）
    "key_pin": "<Control>p",         # 面板内：置顶 / 取消置顶
    "key_delete": "<Shift>Delete",   # 面板内：删除（回收站里为彻底删除）
    "key_trash": "<Control>t",       # 面板内：切换回收站
    "auto_paste": True,      # 选中后自动粘贴到之前的窗口
    "show_tray": True,       # 显示托盘图标
    "max_items": 200,        # 历史条数上限（文本 + 图片）
    "max_trash": 50,         # 回收站条数上限，超出丢弃最早删除的
    "panel_width": 440,      # 面板宽度
    "list_max_height": 640,  # 列表区最大高度（条目少时面板随内容收缩）
    "thumb_height": 120,     # 图片卡片缩略图最大高度
    "preview_lines": 5,      # 多行文本在卡片里最多显示几行（保留原始换行与缩进）
}
MAX_TEXT_BYTES = 1_000_000  # 超过 1MB 的文本不记录


def load_config():
    """读配置并和默认值合并；类型不对的项忽略（bool 不能当 int）。"""
    cfg = dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    for key, default in DEFAULTS.items():
        value = data.get(key, default)
        ok = isinstance(value, bool) if isinstance(default, bool) else \
            (isinstance(value, type(default)) and not isinstance(value, bool))
        if ok:
            cfg[key] = value
    return cfg


def save_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {k: cfg[k] for k in DEFAULTS}
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
