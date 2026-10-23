"""通用控件：圆角缩略图、无边框圆角浮窗基类。"""

import math

from gi.repository import Gdk, Gtk

from .style import THUMB_RADIUS


class Thumbnail(Gtk.DrawingArea):
    """圆角缩略图，带一圈细边，浅色截图不会和卡片底色融在一起。"""

    def __init__(self, pixbuf):
        super().__init__()
        self.pixbuf = pixbuf
        self.set_size_request(pixbuf.get_width(), pixbuf.get_height())
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.connect("draw", self._on_draw)

    def _on_draw(self, widget, cr):
        w, h = self.pixbuf.get_width(), self.pixbuf.get_height()
        cr.save()
        self._rounded_rect(cr, 0, 0, w, h, THUMB_RADIUS)
        cr.clip()
        Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)
        cr.paint()
        cr.restore()
        color = widget.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        cr.set_source_rgba(color.red, color.green, color.blue, 0.18)
        cr.set_line_width(1)
        self._rounded_rect(cr, 0.5, 0.5, w - 1, h - 1, THUMB_RADIUS)
        cr.stroke()
        return True

    @staticmethod
    def _rounded_rect(cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


class FloatingWindow(Gtk.Window):
    """和面板同款的无系统边框圆角浮窗：透明窗口 + 圆角阴影面板 + 自绘标题栏（可拖动），Esc 关闭。
    子类把内容放进 self.body。"""

    def __init__(self, title):
        super().__init__(title=title)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_resizable(False)
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        composited = visual is not None and screen.is_composited()
        if composited:
            self.set_visual(visual)
        ctx = self.get_style_context()
        ctx.add_class("ec-window")
        ctx.add_class("ec-shadow" if composited else "ec-flat")

        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        surface.get_style_context().add_class("ec-surface")
        self.add(surface)
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.get_style_context().add_class("ec-header")
        label = Gtk.Label(label=title, xalign=0)
        label.get_style_context().add_class("ec-title")
        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.set_can_focus(False)
        close_btn.get_style_context().add_class("ec-hicon")
        close_btn.connect("clicked", lambda _b: self.destroy())
        bar.pack_start(label, True, True, 0)
        bar.pack_end(close_btn, False, False, 0)
        grip = Gtk.EventBox()
        grip.set_visible_window(False)
        grip.add(bar)
        grip.connect("button-press-event", self._on_bar_press)
        surface.pack_start(grip, False, False, 0)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.body.set_margin_start(18)
        self.body.set_margin_end(18)
        self.body.set_margin_bottom(18)
        self.body.set_margin_top(4)
        surface.pack_start(self.body, True, True, 0)
        self.connect("key-press-event", self._on_base_key)

    def _on_bar_press(self, _w, event):
        if event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        return False

    def _on_base_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False
