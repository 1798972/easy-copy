"""按键捕获弹窗。"""

from gi.repository import Gdk, GLib, Gtk

from ..hotkey import hotkey_label
from ..i18n import _
from .widgets import FloatingWindow


class HotkeyDialog(FloatingWindow):
    """按下组合键即捕获；validator(binding) 返回 (级别, 说明)，级别 ok / warn / error。
    warn 时按钮变成「仍然应用」，error 时不能应用。应用后交给 on_apply(binding)。"""

    MODIFIER_KEYS = {
        Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Control_L, Gdk.KEY_Control_R,
        Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Super_L, Gdk.KEY_Super_R,
        Gdk.KEY_Meta_L, Gdk.KEY_Meta_R, Gdk.KEY_Hyper_L, Gdk.KEY_Hyper_R, Gdk.KEY_ISO_Level3_Shift,
    }

    def __init__(self, title, current_label, on_apply, validator, parent=None):
        super().__init__(_("设置快捷键：{title}").format(title=title))
        self.on_apply = on_apply
        self.validator = validator
        self.binding = None
        if parent is not None:
            self.set_transient_for(parent)
            self.set_modal(True)
            self.set_destroy_with_parent(True)  # 设置窗口关了，弹窗一起关
        self.body.set_spacing(8)
        self.tip = Gtk.Label(label=_("按下「{title}」的新组合键").format(title=title))
        self.combo = Gtk.Label()
        self._show_combo(current_label)
        self.status = Gtk.Label(label=_("当前快捷键"))
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(40)
        self.status.set_justify(Gtk.Justification.CENTER)
        for w in (self.tip, self.combo, self.status):
            self.body.pack_start(w, False, False, 0)
        btns = Gtk.Box(spacing=6)
        btns.set_margin_top(8)
        cancel = Gtk.Button(label=_("取消"))
        cancel.set_can_focus(False)
        cancel.connect("clicked", lambda _b: self.destroy())
        self.ok_btn = Gtk.Button(label=_("应用"))
        self.ok_btn.set_can_focus(False)
        self.ok_btn.set_sensitive(False)
        self.ok_btn.get_style_context().add_class("suggested-action")
        self.ok_btn.connect("clicked", self._apply)
        btns.pack_end(self.ok_btn, False, False, 0)
        btns.pack_end(cancel, False, False, 0)
        self.body.pack_start(btns, False, False, 0)
        self.connect("key-press-event", self._on_key)
        self.show_all()

    def _show_combo(self, text):
        self.combo.set_markup(f'<span size="x-large" weight="bold">{GLib.markup_escape_text(text)}</span>')

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            return False
        if event.keyval in self.MODIFIER_KEYS:
            return True
        mods = event.state & Gtk.accelerator_get_default_mod_mask()
        keyval = Gdk.keyval_to_lower(event.keyval)
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and mods == 0 and self.binding:
            self._apply()  # 已捕获到可用组合时，回车等于点「应用」
            return True
        binding = Gtk.accelerator_name(keyval, mods).replace("<Primary>", "<Control>")
        self._show_combo(hotkey_label(binding))
        level, msg = self.validator(binding)
        esc = GLib.markup_escape_text(msg)
        if level == "error":
            self.binding = None
            self.ok_btn.set_sensitive(False)
            self.ok_btn.set_label(_("应用"))
            self.status.set_markup(f'<span foreground="#c0392b">✖ {esc}</span>')
        elif level == "warn":
            self.binding = binding
            self.ok_btn.set_sensitive(True)
            self.ok_btn.set_label(_("仍然应用"))
            self.status.set_markup(f'<span foreground="#d35400">⚠ {esc}</span>')
        else:
            self.binding = binding
            self.ok_btn.set_sensitive(True)
            self.ok_btn.set_label(_("应用"))
            self.status.set_text(_("点「应用」或回车生效"))
        return True

    def _apply(self, _b=None):
        if not self.binding:
            return
        ok, msg = self.on_apply(self.binding)
        if ok:
            self.destroy()
        else:
            self.status.set_markup(f'<span foreground="#c0392b">✖ {GLib.markup_escape_text(msg)}</span>')
