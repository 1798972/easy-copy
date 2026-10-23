"""所有和桌面环境打交道的部分：启动命令路径、自启动文件、活动窗口与粘贴、
全局快捷键的注册 / 解除 / 冲突检查（Cinnamon、GNOME）。"""

import os
import subprocess
import sys
from pathlib import Path

from gi.repository import Gio, GLib

from .hotkey import hotkey_label, same_binding
from .util import log

AUTOSTART_FILE = Path(GLib.get_user_config_dir()) / "autostart" / "easy-copy.desktop"


def launcher_exe():
    """快捷键 / 自启动要执行的程序，按顺序找：~/.local/bin/easy-copy（install.sh 建的软链）、
    /usr/bin/easy-copy（deb 安装）、仓库里的 bin/easy-copy，最后退回当前启动脚本。"""
    candidates = [
        Path(GLib.get_home_dir()) / ".local" / "bin" / "easy-copy",
        Path("/usr/bin/easy-copy"),
        Path(__file__).resolve().parents[2] / "bin" / "easy-copy",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return os.path.abspath(sys.argv[0])


def autostart_enabled():
    return AUTOSTART_FILE.exists()


def set_autostart(enabled):
    if not enabled:
        try:
            AUTOSTART_FILE.unlink()
        except FileNotFoundError:
            pass
        return
    AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTOSTART_FILE.write_text(
        "[Desktop Entry]\nType=Application\nName=easy-copy\nComment=剪贴板历史\n"
        f"Exec={launcher_exe()}\nIcon=edit-paste\nTerminal=false\nNoDisplay=true\n"
        "X-GNOME-Autostart-enabled=true\n", encoding="utf-8")


TERMINAL_CLASSES = {
    "gnome-terminal", "gnome-terminal-server", "xterm", "kitty", "alacritty",
    "tilix", "terminator", "konsole", "x-terminal-emulator", "xfce4-terminal",
    "mate-terminal", "urxvt", "st", "wezterm", "foot",
}



def run_bg(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as e:
        log(f"run {cmd[0]} failed: {e}")

def active_window_info():
    """返回 (当前活动窗口 id, 是否终端)。"""
    try:
        wid = subprocess.run(["xdotool", "getactivewindow"], capture_output=True,
                             text=True, timeout=1).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None, False
    if not wid:
        return None, False
    is_term = False
    try:
        out = subprocess.run(["xprop", "-id", wid, "WM_CLASS"], capture_output=True,
                             text=True, timeout=1).stdout
        if "=" in out:
            classes = {c.strip().strip('"').lower() for c in out.split("=", 1)[1].split(",")}
            is_term = bool(classes & TERMINAL_CLASSES)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return wid, is_term


def _has_schema(schema):
    src = Gio.SettingsSchemaSource.get_default()
    return src is not None and src.lookup(schema, True) is not None


def desktop():
    """能自动注册快捷键的桌面：cinnamon / gnome；其它返回 None。"""
    d = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "cinnamon" in d and _has_schema("org.cinnamon.desktop.keybindings"):
        return "cinnamon"
    if any(x in d for x in ("gnome", "ubuntu", "unity")) and \
            _has_schema("org.gnome.settings-daemon.plugins.media-keys"):
        return "gnome"
    return None


CINNAMON_SCHEMA = "org.cinnamon.desktop.keybindings"
CINNAMON_KB_SCHEMA = "org.cinnamon.desktop.keybindings.custom-keybinding"
CINNAMON_BASE = "/org/cinnamon/desktop/keybindings/custom-keybindings/"
GNOME_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
GNOME_KB_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
GNOME_BASE = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"


def conflicts(binding, desk):
    """检查系统快捷键和其它自定义快捷键里有没有用了同一组合，返回警告文本。"""
    warns = []
    if desk == "cinnamon":
        schemas = (CINNAMON_SCHEMA + ".wm", CINNAMON_SCHEMA + ".media-keys")
        root = Gio.Settings.new(CINNAMON_SCHEMA)
        customs = [(n, Gio.Settings.new_with_path(CINNAMON_KB_SCHEMA, CINNAMON_BASE + n + "/"))
                   for n in root.get_strv("custom-list") if n != "__dummy__"]
        custom_bindings = [(s.get_string("name"), s.get_strv("binding")) for _n, s in customs]
    else:
        schemas = ("org.gnome.desktop.wm.keybindings", GNOME_SCHEMA)
        root = Gio.Settings.new(GNOME_SCHEMA)
        customs = [Gio.Settings.new_with_path(GNOME_KB_SCHEMA, path)
                   for path in root.get_strv("custom-keybindings")]
        custom_bindings = [(s.get_string("name"), [s.get_string("binding")]) for s in customs]
    for name, bindings in custom_bindings:
        if not name.startswith("easy-copy") and any(same_binding(b, binding) for b in bindings if b):
            warns.append(f"已被自定义快捷键「{name}」占用")
    for schema in schemas:
        if not _has_schema(schema):
            continue
        st = Gio.Settings.new(schema)
        for key in st.props.settings_schema.list_keys():
            v = st.get_value(key)
            if v.get_type_string() == "as" and any(same_binding(b, binding) for b in v.unpack() if b):
                warns.append(f"已被系统快捷键 {key} 占用")
    return "；".join(warns)


def register_hotkey(binding, command, name="easy-copy"):
    """把 command 绑定到 binding（桌面里的条目名为 name），返回 (ok, 说明)。"""
    desk = desktop()
    if desk is None:
        return False, (f"当前桌面「{os.environ.get('XDG_CURRENT_DESKTOP') or '未知'}」不支持自动注册，"
                       f"请在系统的键盘快捷键设置里把命令「{command}」绑定到想要的键")
    warn = conflicts(binding, desk)
    if desk == "cinnamon":
        root = Gio.Settings.new(CINNAMON_SCHEMA)
        names = list(root.get_strv("custom-list"))
        mine = [n for n in names if n != "__dummy__" and
                Gio.Settings.new_with_path(CINNAMON_KB_SCHEMA, CINNAMON_BASE + n + "/").get_string("name") == name]
        if mine:
            target = mine[0]
        else:
            i = 0
            while f"custom{i}" in names:
                i += 1
            target = f"custom{i}"
            names.append(target)
        st = Gio.Settings.new_with_path(CINNAMON_KB_SCHEMA, CINNAMON_BASE + target + "/")
        st.set_string("name", name)
        st.set_string("command", command)
        st.set_strv("binding", [binding])
        root.set_strv("custom-list", names)
    else:
        root = Gio.Settings.new(GNOME_SCHEMA)
        paths = list(root.get_strv("custom-keybindings"))
        path = GNOME_BASE + name + "/"
        st = Gio.Settings.new_with_path(GNOME_KB_SCHEMA, path)
        st.set_string("name", name)
        st.set_string("command", command)
        st.set_string("binding", binding)
        if path not in paths:
            root.set_strv("custom-keybindings", paths + [path])
    Gio.Settings.sync()
    msg = f"快捷键已设为 {hotkey_label(binding)}（{binding}）"
    return True, msg + (f"\n注意：{warn}，可能不生效" if warn else "")


def unregister_hotkey(name="easy-copy"):
    desk = desktop()
    if desk == "cinnamon":
        root = Gio.Settings.new(CINNAMON_SCHEMA)
        names = list(root.get_strv("custom-list"))
        keep = []
        for n in names:
            st = Gio.Settings.new_with_path(CINNAMON_KB_SCHEMA, CINNAMON_BASE + n + "/")
            if n != "__dummy__" and st.get_string("name") == name:
                for key in ("name", "command", "binding"):
                    st.reset(key)
            else:
                keep.append(n)
        root.set_strv("custom-list", keep)
    elif desk == "gnome":
        root = Gio.Settings.new(GNOME_SCHEMA)
        path = GNOME_BASE + name + "/"
        root.set_strv("custom-keybindings", [x for x in root.get_strv("custom-keybindings") if x != path])
        st = Gio.Settings.new_with_path(GNOME_KB_SCHEMA, path)
        for key in ("name", "command", "binding"):
            st.reset(key)
    else:
        return False, "当前桌面不支持自动解除，请在系统快捷键设置里手动删除"
    Gio.Settings.sync()
    return True, "已解除快捷键绑定"


def launcher_command():
    return f"{launcher_exe()} toggle"
