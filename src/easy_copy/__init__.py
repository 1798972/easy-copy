"""easy-copy：极简剪贴板历史（Linux / X11），对标 Windows 的 Win+V。"""

import json
import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("GdkPixbuf", "2.0")

__version__ = "0.1.0"


def _apply_language_env():
    """界面语言被手动指定为 zh / en 时，让 GTK 自己的翻译（快捷键名等）也跟着走。
    必须在导入 Gtk 之前设置，所以放在包初始化里，只读一次配置文件。"""
    from gi.repository import GLib  # GLib 不触发 GTK 初始化

    path = os.path.join(GLib.get_user_config_dir(), "easy-copy", "config.json")
    try:
        with open(path, encoding="utf-8") as f:
            lang = json.load(f).get("language")
    except (OSError, ValueError, AttributeError):
        return
    if lang in ("zh", "en"):
        os.environ["LANGUAGE"] = "zh_CN" if lang == "zh" else "en_US"


_apply_language_env()
