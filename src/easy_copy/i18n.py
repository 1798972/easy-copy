"""中英文：代码里写中文原文，`_()` 按当前语言查表；没有英文译文时回退中文。
语言由配置项 language 决定：auto（跟随系统）/ zh / en。"""

import os

LANGUAGES = ("auto", "zh", "en")
_current = "zh"


def detect_system_language():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return "zh" if value.lower().startswith("zh") else "en"
    return "en"


def set_language(code):
    global _current
    if code == "auto":
        _current = detect_system_language()
    else:
        _current = "zh" if code == "zh" else "en"


def current():
    return _current


def _(text):
    if _current == "zh":
        return text
    return EN.get(text, text)


EN = {
    # ---- 通用
    "取消": "Cancel", "关闭": "Close", "删除": "Delete", "清空": "Clear", "返回": "Back",
    "设置": "Settings", "设置…": "Settings…", "剪贴板": "Clipboard", "回收站": "Recycle bin",
    "未设置": "Not set", "昨天 %H:%M": "Yesterday %H:%M",
    # ---- 托盘
    "打开面板": "Open panel", "清空历史": "Clear history", "退出": "Quit",
    # ---- 面板
    "清空回收站": "Empty recycle bin", "确定清空回收站？": "Empty the recycle bin?", "搜索…": "Search…",
    "回收站 {n}/{limit} · Enter 恢复 · {k_del} 两次彻底删除 · {k_trash} 返回 · Esc 关闭":
        "Recycle bin {n}/{limit} · Enter restore · {k_del} twice to delete for good · {k_trash} back · Esc close",
    "{n} 条 · Enter 粘贴 · {k_pin} 置顶 · {k_del} 删除 · {k_trash} 回收站 · Esc 关闭":
        "{n} items · Enter paste · {k_pin} pin · {k_del} delete · {k_trash} recycle bin · Esc close",
    "回收站是空的": "Recycle bin is empty",
    "还没有记录\n复制点什么，再按 {hotkey}": "Nothing here yet\nCopy something, then press {hotkey}",
    "没有匹配的内容": "No matches", "（图片文件已丢失）": "(image file missing)",
    "{when} · 图片 {w}×{h}": "{when} · image {w}×{h}",
    "{when} · {chars} 字": "{when} · {chars} chars",
    "{when} · {lines} 行 · {chars} 字": "{when} · {lines} lines · {chars} chars",
    "删除于 {when}": "Deleted {when}", "彻底删除": "Delete permanently", "彻底删除？": "Delete permanently?",
    "恢复到列表（Enter）": "Restore to the list (Enter)", "删除（进回收站）": "Delete (to recycle bin)",
    "取消置顶（{key}）": "Unpin ({key})", "置顶（{key}）": "Pin ({key})",
    # ---- 快捷键名称
    "呼出面板": "Open panel", "呼出回收站": "Open recycle bin", "置顶 / 取消置顶": "Pin / unpin",
    "切换回收站": "Toggle recycle bin", "粘贴 / 恢复": "Paste / restore", "选择": "Select", "翻页": "Page",
    "未绑定快捷键": "No shortcut bound",
    # ---- 快捷键校验与注册
    "无法识别或缺少修饰键：{text}（示例：Ctrl+Alt+V 或 <Control><Alt>v，需带 Ctrl / Alt / Super）":
        "Unrecognized or missing modifier: {text} (e.g. Ctrl+Alt+V or <Control><Alt>v; needs Ctrl / Alt / Super)",
    "已解除「{title}」的快捷键": "Shortcut for “{title}” removed",
    "无法识别的组合键": "Unrecognized key combination",
    "需要配合 Ctrl / Alt / Super 之一（功能键 F1–F12 可单独用）":
        "Needs Ctrl, Alt or Super (function keys F1–F12 may be used alone)",
    "和「{title}」用了同一组合键": "Same combination as “{title}”",
    "{warn}，应用后可能不生效，建议换一个": "{warn}; it may not take effect, better pick another one",
    "面板内快捷键要带 Ctrl / Alt / Super，或 Shift + Delete 这类非打印键，否则和打字冲突":
        "Panel shortcuts need Ctrl / Alt / Super, or Shift plus a non-printing key like Delete, or they clash with typing",
    "{label} 固定用于「{what}」": "{label} is reserved for “{what}”",
    "「{title}」{msg}": "{title}: {msg}",
    "已被自定义快捷键「{name}」占用": "already used by the custom shortcut “{name}”",
    "已被系统快捷键 {key} 占用": "already used by the system shortcut {key}",
    "当前桌面「{desk}」不支持自动注册，请在系统的键盘快捷键设置里把命令「{command}」绑定到想要的键":
        "Desktop “{desk}” is not supported for automatic registration; bind the command “{command}” to a key in your system keyboard settings",
    "快捷键已设为 {label}（{binding}）": "shortcut set to {label} ({binding})",
    "\n注意：{warn}，可能不生效": "\nNote: {warn}; it may not take effect",
    "当前桌面不支持自动解除，请在系统快捷键设置里手动删除":
        "This desktop is not supported for automatic removal; delete it in your system keyboard settings",
    "已解除快捷键绑定": "Shortcut binding removed",
    "easy-copy 已在运行\n": "easy-copy is already running\n",
    "当前快捷键：{label}（{binding}）\n绑定命令：{command}\n": "Current shortcut: {label} ({binding})\nCommand: {command}\n",
    "没有已绑定的全局快捷键": "No global shortcut is bound",
    # ---- 快捷键弹窗
    "设置快捷键：{title}": "Set shortcut: {title}", "按下「{title}」的新组合键": "Press the new combination for “{title}”",
    "当前快捷键": "Current shortcut", "应用": "Apply", "仍然应用": "Apply anyway",
    "点「应用」或回车生效": "Click Apply or press Enter",
    # ---- 设置窗口
    "语言": "Language", "跟随系统": "System default", "中文": "中文", "English": "English",
    "快捷键": "Shortcuts", "（全局）": " (global)", "（面板内）": " (in panel)",
    "固定不可改：Enter 粘贴 / 恢复 · Esc 关闭 · ↑↓ 选择 · 直接打字即搜索":
        "Fixed: Enter paste / restore · Esc close · ↑↓ select · just type to search",
    "行为": "Behavior", "选中后自动粘贴到原窗口": "Auto-paste into the previous window",
    "开机自动启动": "Start at login", "显示托盘图标": "Show tray icon",
    "容量": "Capacity", "历史条数上限": "History limit", "回收站条数上限": "Recycle bin limit",
    "外观": "Appearance", "面板宽度（px）": "Panel width (px)", "列表最大高度（px）": "List max height (px)",
    "缩略图最大高度（px）": "Thumbnail max height (px)", "多行文本预览行数": "Preview lines for multi-line text",
    "全部恢复默认": "Reset all", "已保存": "Saved",
    "已开启开机自启": "Start at login enabled", "已关闭开机自启": "Start at login disabled",
    "修改…": "Change…", "恢复默认": "Default", "解除": "Unbind",
    "「{title}」已设为 {label}": "“{title}” set to {label}", "已全部恢复默认": "All settings reset",
}
