"""Gtk.Application 单实例：命令行分发、托盘、快捷键与设置的落地。"""

import os
import sys

from gi.repository import Gdk, Gio, Gtk

from .clipboard import ClipboardWatcher
from .config import APP_ID, load_config, save_config
from .desktop import (conflicts, desktop, launcher_command, launcher_exe, register_hotkey,
                      unregister_hotkey)
from .history import History
from .hotkey import (FIXED_KEYS, GLOBAL_COMMANDS, GLOBAL_KEYS, GLOBAL_NAMES, PANEL_KEYS,
                     hotkey_acceptable, hotkey_label, normalize_hotkey, panel_key_acceptable,
                     same_binding)
from .i18n import _, current as current_language, set_language
from .ui.panel import Panel
from .ui.settings import SettingsWindow
from .ui.style import install_css
from .util import log
from . import __version__

try:
    import gi
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except (ValueError, ImportError):
    AppIndicator = None

USAGE_ZH = """easy-copy：极简剪贴板历史（Linux / X11）。

用法：
  easy-copy            启动常驻进程（开机自启用这个）
  easy-copy toggle     弹出 / 隐藏面板（绑定到快捷键）
  easy-copy trash      直接打开回收站视图
  easy-copy clear      清空历史（进回收站）
  easy-copy hotkey     显示当前快捷键
  easy-copy hotkey 'Ctrl+Alt+V'   改快捷键（也可写 '<Control><Alt>v'）；--remove 解除绑定
  easy-copy settings   打开设置窗口
  easy-copy version    显示版本
  easy-copy quit       退出常驻进程
"""
USAGE_EN = """easy-copy: minimal clipboard history for Linux / X11.

Usage:
  easy-copy            start the daemon (use this for autostart)
  easy-copy toggle     show / hide the panel (bind this to a hotkey)
  easy-copy trash      open the recycle bin view
  easy-copy clear      clear the history (into the recycle bin)
  easy-copy hotkey     show the current hotkey
  easy-copy hotkey 'Ctrl+Alt+V'   change it ('<Control><Alt>v' also works); --remove unbinds
  easy-copy settings   open the settings window
  easy-copy version    print the version
  easy-copy quit       stop the daemon
"""


class EasyCopyApp(Gtk.Application):
    """Gtk.Application 单实例：第二次运行 `easy-copy toggle` 会经 DBus 转发给常驻进程。"""

    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.history = None
        self.watcher = None
        self.panel = None
        self.indicator = None
        self.settings_win = None
        self.cfg = load_config()
        set_language(self.cfg["language"])

    @property
    def hotkey(self):
        return self.cfg["hotkey"]

    def hotkey_label(self):
        return hotkey_label(self.hotkey) if self.hotkey else _("未绑定快捷键")

    def set_hotkey(self, text, which="hotkey"):
        """改全局快捷键：校验写法 → 注册到桌面 → 存配置。返回 (ok, 说明)。"""
        binding = normalize_hotkey(text)
        if binding is None:
            return False, _("无法识别或缺少修饰键：{text}（示例：Ctrl+Alt+V 或 <Control><Alt>v，需带 Ctrl / Alt / Super）").format(text=text)
        level, msg = self.validate_key(which, binding)
        if level == "error":
            return False, msg
        command = f"{launcher_exe()} {GLOBAL_COMMANDS[which]}"
        ok, msg = register_hotkey(binding, command, GLOBAL_NAMES[which])
        if not ok:
            return False, msg
        self.update_setting(which, binding)
        return True, _("「{title}」{msg}").format(title=_(GLOBAL_KEYS[which]), msg=msg)

    def remove_hotkey(self, which="hotkey"):
        ok, msg = unregister_hotkey(GLOBAL_NAMES[which])
        if ok:
            self.update_setting(which, "")
            msg = _("已解除「{title}」的快捷键").format(title=_(GLOBAL_KEYS[which]))
        return ok, msg

    def validate_key(self, which, binding):
        """返回 (级别, 说明)：error 不能用；warn 可用但可能被别的快捷键抢；ok 没问题。"""
        keyval, mods = Gtk.accelerator_parse(binding)
        if keyval == 0:
            return "error", _("无法识别的组合键")
        if which in GLOBAL_KEYS:
            if not hotkey_acceptable(keyval, mods):
                return "error", _("需要配合 Ctrl / Alt / Super 之一（功能键 F1–F12 可单独用）")
            for other, title in GLOBAL_KEYS.items():
                if other != which and self.cfg[other] and same_binding(self.cfg[other], binding):
                    return "error", _("和「{title}」用了同一组合键").format(title=_(title))
            desk = desktop()
            warn = conflicts(binding, desk) if desk else ""
            if warn:
                return "warn", _("{warn}，应用后可能不生效，建议换一个").format(warn=warn)
            return "ok", ""
        if not panel_key_acceptable(keyval, mods):
            return "error", _("面板内快捷键要带 Ctrl / Alt / Super，或 Shift + Delete 这类非打印键，否则和打字冲突")
        for other, title in PANEL_KEYS.items():
            if other != which and same_binding(self.cfg[other], binding):
                return "error", _("和「{title}」用了同一组合键").format(title=_(title))
        name = Gdk.keyval_name(keyval) or ""
        if mods == 0 and name in FIXED_KEYS:
            return "error", _("{label} 固定用于「{what}」").format(label=hotkey_label(binding), what=_(FIXED_KEYS[name]))
        return "ok", ""

    def update_setting(self, key, value):
        """改一项配置：保存并立即生效。"""
        self.cfg[key] = value
        save_config(self.cfg)
        if key == "language":
            set_language(value)
            self._build_tray_menu()
        if key in ("max_items", "max_trash") and self.history is not None:
            self.history.enforce_limits()
        elif key == "show_tray" and self.indicator is not None:
            self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE if value
                                      else AppIndicator.IndicatorStatus.PASSIVE)
        if self.panel is not None and self.panel.get_visible():
            self.panel.rebuild()

    def open_settings(self):
        if self.settings_win is None:
            self.settings_win = SettingsWindow(self)
        self.settings_win.present()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        install_css()
        self.history = History(self.cfg)
        self.panel = Panel(self)
        self.watcher = ClipboardWatcher(self.history, self._on_history_changed)
        self._setup_indicator()
        self.hold()
        log(f"daemon started, {len(self.history.items)} items loaded")

    def do_activate(self):
        pass

    def do_command_line(self, cmdline):
        args = cmdline.get_arguments()[1:]
        cmd = args[0] if args else "daemon"
        if cmd in ("version", "--version", "-V"):
            self._out(cmdline, f"easy-copy {__version__}\n")
            if not cmdline.get_is_remote():
                self.quit()
            return 0
        if cmd == "daemon":
            if cmdline.get_is_remote():
                self._err(cmdline, _("easy-copy 已在运行\n"))
        elif cmd == "toggle":
            self.panel.toggle()
        elif cmd == "show":
            self.panel.popup()
        elif cmd == "trash":
            self.panel.popup(view="trash")
        elif cmd == "clear":
            self.clear_history()
        elif cmd == "settings":
            self.open_settings()
        elif cmd == "hotkey":
            code = self._cmd_hotkey(cmdline, args[1:])
            if not cmdline.get_is_remote():
                self.quit()  # 只是为了改快捷键而启动的，办完就退
            return code
        elif cmd == "quit":
            self.quit()
        else:
            self._err(cmdline, USAGE_EN if current_language() == "en" else USAGE_ZH)
            return 2
        if cmd == "clear" and not cmdline.get_is_remote():
            self.quit()
        return 0

    def _cmd_hotkey(self, cmdline, args):
        if not args:
            self._out(cmdline, _("当前快捷键：{label}（{binding}）\n绑定命令：{command}\n").format(
                label=self.hotkey_label(), binding=self.hotkey, command=launcher_command()))
            return 0
        if args[0] == "--remove":
            results = [self.remove_hotkey(k) for k in GLOBAL_KEYS if self.cfg[k]]
            ok, msg = (all(r[0] for r in results), "\n".join(r[1] for r in results)) if results else (True, _("没有已绑定的全局快捷键"))
        else:
            ok, msg = self.set_hotkey(" ".join(args))
        (self._out if ok else self._err)(cmdline, msg + "\n")
        return 0 if ok else 1

    @staticmethod
    def _out(cmdline, text):
        fn = getattr(cmdline, "print_literal", None)
        if fn is not None:
            fn(text)
        else:
            sys.stdout.write(text)

    @staticmethod
    def _err(cmdline, text):
        fn = getattr(cmdline, "printerr_literal", None)
        if fn is not None:
            fn(text)
        else:
            sys.stderr.write(text)

    def _on_history_changed(self):
        if self.panel.get_visible():
            self.panel.rebuild()

    def clear_history(self):
        self.history.clear()
        self.panel.rebuild()

    def _setup_indicator(self):
        if AppIndicator is None:
            return
        self.indicator = AppIndicator.Indicator.new(
            "easy-copy", "edit-paste-symbolic",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE if self.cfg["show_tray"]
                                  else AppIndicator.IndicatorStatus.PASSIVE)
        self.indicator.set_title("easy-copy")
        self._build_tray_menu()

    def _build_tray_menu(self):
        if self.indicator is None:
            return
        menu = Gtk.Menu()
        entries = (
            (_("打开面板"), lambda _i: self.panel.toggle()),
            (_("回收站"), lambda _i: self.panel.popup(view="trash")),
            (_("设置…"), lambda _i: self.open_settings()),
            (_("清空历史"), lambda _i: self.clear_history()),
            (_("退出"), lambda _i: self.quit()),
        )
        first = None
        for label, cb in entries:
            mi = Gtk.MenuItem(label=label)
            mi.connect("activate", cb)
            menu.append(mi)
            first = first or mi
        menu.show_all()
        self.indicator.set_menu(menu)
        self.indicator.set_secondary_activate_target(first)  # 中键点图标直接打开


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("version", "--version", "-V"):
        print(f"easy-copy {__version__}")  # 不启动任何东西
        return 0
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland" and not os.environ.get("DISPLAY"):
        sys.stderr.write("easy-copy 只支持 X11 会话（Wayland 下拿不到其它程序的剪贴板变化，xdotool 也不工作）。\n"
                         "easy-copy requires an X11 session; please log in with \"Xorg\" / \"X11\" selected.\n")
        return 1
    return EasyCopyApp().run(sys.argv)
