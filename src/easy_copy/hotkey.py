"""组合键的解析、校验、显示名与按键匹配（纯逻辑，不碰系统）。"""

from gi.repository import Gdk, Gtk

HOTKEY_MOD_MASK = (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK
                   | Gdk.ModifierType.SUPER_MASK | Gdk.ModifierType.META_MASK | Gdk.ModifierType.HYPER_MASK)


def hotkey_acceptable(keyval, mods):
    """全局快捷键必须带 Ctrl / Alt / Super 之一；F1–F35 这类功能键可以单独用。"""
    return bool(mods & HOTKEY_MOD_MASK) or Gdk.KEY_F1 <= keyval <= Gdk.KEY_F35


def normalize_hotkey(text):
    """接受 '<Super>v' 或 'Super+V' / 'Ctrl+Alt+V' 两种写法，返回 GTK 标准写法；
    无法识别或没有修饰键（打字就会触发）返回 None。"""
    text = (text or "").strip()
    if not text:
        return None
    if "<" not in text:
        names = {"super": "<Super>", "win": "<Super>", "meta": "<Meta>", "ctrl": "<Control>",
                 "control": "<Control>", "alt": "<Alt>", "shift": "<Shift>", "hyper": "<Hyper>"}
        parts = [x.strip() for x in text.replace("-", "+").split("+") if x.strip()]
        if not parts:
            return None
        mods = ""
        for part in parts[:-1]:
            if part.lower() not in names:
                return None
            mods += names[part.lower()]
        key = parts[-1]
        text = mods + (key.lower() if len(key) == 1 else key)
    keyval, mods = Gtk.accelerator_parse(text)
    if keyval == 0 or not hotkey_acceptable(keyval, mods):
        return None
    # Cinnamon 的绑定解析认 <Control>，不认 GTK 新写法 <Primary>
    return Gtk.accelerator_name(keyval, mods).replace("<Primary>", "<Control>")


def hotkey_label(binding):
    if not binding:
        return "未设置"
    keyval, mods = Gtk.accelerator_parse(binding)
    return Gtk.accelerator_get_label(keyval, mods) if keyval else binding


def panel_key_acceptable(keyval, mods):
    """面板内快捷键不能和打字冲突：带 Ctrl/Alt/Super，或 Shift + 非打印键（如 Shift+Delete），或功能键。"""
    if Gdk.KEY_F1 <= keyval <= Gdk.KEY_F35 or mods & HOTKEY_MOD_MASK:
        return True
    return bool(mods & Gdk.ModifierType.SHIFT_MASK) and keyval >= 0xFF00


def key_matches(event, binding):
    """按键事件是否等于配置里的组合键。"""
    if not binding:
        return False
    keyval, mods = Gtk.accelerator_parse(binding)
    if keyval == 0:
        return False
    state = event.state & Gtk.accelerator_get_default_mod_mask()
    return Gdk.keyval_to_lower(event.keyval) == Gdk.keyval_to_lower(keyval) and state == mods


GLOBAL_KEYS = {"hotkey": "呼出面板", "hotkey_trash": "呼出回收站"}
GLOBAL_COMMANDS = {"hotkey": "toggle", "hotkey_trash": "trash"}
GLOBAL_NAMES = {"hotkey": "easy-copy", "hotkey_trash": "easy-copy-trash"}
PANEL_KEYS = {"key_pin": "置顶 / 取消置顶", "key_delete": "删除", "key_trash": "切换回收站"}
FIXED_KEYS = {"Return": "粘贴 / 恢复", "KP_Enter": "粘贴 / 恢复", "Escape": "关闭",
              "Up": "选择", "Down": "选择", "Page_Up": "翻页", "Page_Down": "翻页"}


def same_binding(a, b):
    return Gtk.accelerator_parse(a) == Gtk.accelerator_parse(b)
