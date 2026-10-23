"""设置窗口。"""

from gi.repository import GLib, Gtk

from ..config import DEFAULTS
from ..desktop import autostart_enabled, set_autostart
from ..hotkey import GLOBAL_KEYS, PANEL_KEYS, hotkey_label
from ..i18n import LANGUAGES, _
from .hotkey_dialog import HotkeyDialog
from .widgets import FloatingWindow


class SettingsWindow(FloatingWindow):
    """所有可调项；改动即时保存到 config.json 并生效。"""

    def __init__(self, app):
        super().__init__(_("设置"))
        self.app = app
        self.connect("destroy", lambda *_: setattr(app, "settings_win", None))

        self.grid = Gtk.Grid(column_spacing=16, row_spacing=8)
        self.body.pack_start(self.grid, True, True, 0)
        self.row = 0

        self._section(_("语言"), first=True)
        self._row(_("语言"), self._language_combo())

        self._section(_("快捷键"))
        self.key_labels = {}
        for key in ("hotkey", "hotkey_trash"):
            self._hotkey_row(key, _(GLOBAL_KEYS[key]) + _("（全局）"), global_key=True)
        for key in ("key_pin", "key_delete", "key_trash"):
            self._hotkey_row(key, _(PANEL_KEYS[key]) + _("（面板内）"), global_key=False)
        fixed = Gtk.Label(xalign=0)
        fixed.set_markup('<span size="small">' + GLib.markup_escape_text(
            _("固定不可改：Enter 粘贴 / 恢复 · Esc 关闭 · ↑↓ 选择 · 直接打字即搜索")) + '</span>')
        fixed.get_style_context().add_class("dim-label")
        self.grid.attach(fixed, 0, self.row, 3, 1)
        self.row += 1

        self._section(_("行为"))
        self._row(_("选中后自动粘贴到原窗口"), self._switch("auto_paste"))
        self._row(_("开机自动启动"), self._switch(None, autostart_enabled(), self._set_autostart))
        self._row(_("显示托盘图标"), self._switch("show_tray"))

        self._section(_("容量"))
        self._row(_("历史条数上限"), self._spin("max_items", 20, 5000, 10))
        self._row(_("回收站条数上限"), self._spin("max_trash", 0, 1000, 10))

        self._section(_("外观"))
        self._row(_("面板宽度（px）"), self._spin("panel_width", 320, 1000, 10))
        self._row(_("列表最大高度（px）"), self._spin("list_max_height", 200, 1600, 20))
        self._row(_("缩略图最大高度（px）"), self._spin("thumb_height", 60, 400, 10))
        self._row(_("多行文本预览行数"), self._spin("preview_lines", 1, 20, 1))

        self.status = Gtk.Label(xalign=0)
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(48)
        self.status.get_style_context().add_class("dim-label")
        self.status.set_margin_top(10)
        self.grid.attach(self.status, 0, self.row, 3, 1)
        self.row += 1

        footer = Gtk.Box(spacing=6)
        footer.set_margin_top(6)
        reset = Gtk.Button(label=_("全部恢复默认"))
        reset.connect("clicked", self._reset_all)
        close = Gtk.Button(label=_("关闭"))
        close.connect("clicked", lambda _b: self.destroy())
        footer.pack_start(reset, False, False, 0)
        footer.pack_end(close, False, False, 0)
        self.grid.attach(footer, 0, self.row, 3, 1)
        self.show_all()

    # ---- 布局辅助
    def _section(self, title, first=False):
        label = Gtk.Label(xalign=0)
        label.set_markup(f"<b>{GLib.markup_escape_text(title)}</b>")
        if not first:
            label.set_margin_top(10)
        self.grid.attach(label, 0, self.row, 3, 1)
        self.row += 1

    def _row(self, text, widget, extra=None):
        label = Gtk.Label(label=text, xalign=0)
        label.set_hexpand(True)
        self.grid.attach(label, 0, self.row, 1, 1)
        widget.set_halign(Gtk.Align.END)
        widget.set_valign(Gtk.Align.CENTER)
        self.grid.attach(widget, 1, self.row, 1, 1)
        if extra is not None:
            extra.set_halign(Gtk.Align.END)
            self.grid.attach(extra, 2, self.row, 1, 1)
        self.row += 1

    def _switch(self, key, active=None, on_change=None):
        sw = Gtk.Switch()
        sw.set_active(self.app.cfg[key] if key else bool(active))
        if key:
            sw.connect("notify::active", lambda w, _p: self._set(key, w.get_active()))
        else:
            sw.connect("notify::active", lambda w, _p: on_change(w.get_active()))
        return sw

    def _language_combo(self):
        combo = Gtk.ComboBoxText()
        for code in LANGUAGES:
            combo.append(code, {"auto": _("跟随系统"), "zh": "中文", "en": "English"}[code])
        combo.set_active_id(self.app.cfg["language"])
        combo.connect("changed", lambda w: self._change_language(w.get_active_id()))
        return combo

    def _change_language(self, code):
        if code and code != self.app.cfg["language"]:
            self.app.update_setting("language", code)
            self.destroy()
            self.app.open_settings()  # 整个窗口按新语言重建

    def _spin(self, key, lo, hi, step):
        spin = Gtk.SpinButton.new_with_range(lo, hi, step)
        spin.set_value(self.app.cfg[key])
        spin.connect("value-changed", lambda w: self._set(key, int(w.get_value())))
        return spin

    # ---- 动作
    def _set(self, key, value):
        self.app.update_setting(key, value)
        self.status.set_text(_("已保存"))

    def _set_autostart(self, enabled):
        set_autostart(enabled)
        self.status.set_text(_("已开启开机自启") if enabled else _("已关闭开机自启"))

    def _hotkey_row(self, key, title, global_key):
        value = Gtk.Label(xalign=0)
        self.key_labels[key] = value
        btns = Gtk.Box(spacing=4)
        actions = [(_("修改…"), lambda _b, k=key: self._change_key(k))]
        if DEFAULTS[key]:
            actions.append((_("恢复默认"), lambda _b, k=key: self._apply_key(k, DEFAULTS[k])))
        if global_key:
            actions.append((_("解除"), lambda _b, k=key: self._remove_key(k)))
        for text, cb in actions:
            b = Gtk.Button(label=text)
            b.connect("clicked", cb)
            btns.pack_start(b, False, False, 0)
        self._row(title, value, btns)
        self._refresh_key(key)

    def _refresh_key(self, key):
        self.key_labels[key].set_markup(f"<b>{GLib.markup_escape_text(hotkey_label(self.app.cfg[key]))}</b>")

    def _change_key(self, key):
        title = _(GLOBAL_KEYS.get(key) or PANEL_KEYS[key])
        HotkeyDialog(title, hotkey_label(self.app.cfg[key]),
                     lambda binding, k=key: self._apply_key(k, binding),
                     lambda binding, k=key: self.app.validate_key(k, binding), parent=self)

    def _apply_key(self, key, binding):
        if key in GLOBAL_KEYS:
            ok, msg = self.app.set_hotkey(binding, key)
        else:
            level, msg = self.app.validate_key(key, binding)
            ok = level != "error"
            if ok:
                self.app.update_setting(key, binding)
                msg = _("「{title}」已设为 {label}").format(title=_(PANEL_KEYS[key]), label=hotkey_label(binding))
        self._refresh_key(key)
        self.status.set_text(msg)
        return ok, msg

    def _remove_key(self, key):
        ok, msg = self.app.remove_hotkey(key)
        self._refresh_key(key)
        self.status.set_text(msg)

    def _reset_all(self, _b):
        for key, value in DEFAULTS.items():
            if key not in GLOBAL_KEYS:
                self.app.update_setting(key, value)
        set_autostart(True)
        for key in GLOBAL_KEYS:
            if DEFAULTS[key]:
                self.app.set_hotkey(DEFAULTS[key], key)
            elif self.app.cfg[key]:
                self.app.remove_hotkey(key)
        self.destroy()
        self.app.open_settings()
        self.app.settings_win.status.set_text(_("已全部恢复默认"))
