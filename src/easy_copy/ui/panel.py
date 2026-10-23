"""主面板：剪贴板列表与回收站视图。"""

import time

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango

from ..desktop import active_window_info, run_bg
from ..hotkey import hotkey_label, key_matches
from ..i18n import _
from ..util import fmt_time
from .style import PIN_ICON, SHADOW_MARGIN
from .widgets import Thumbnail

LIST_MIN_H = 320            # 列表区最小高度
PREVIEW_CHARS = 300         # 预览时每行最多取多少字符（防止超长单行拖慢渲染）
PREVIEW_WRAP_LINES = 3      # 单段长文本自动换行最多几行


class Panel(Gtk.Window):
    def __init__(self, app):
        super().__init__(title="easy-copy")
        self.app = app
        self.history = app.history
        self.prev_window = None
        self.prev_is_terminal = False
        self._shown_at = 0.0
        self._thumb_cache = {}

        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_position(Gtk.WindowPosition.NONE)
        self.connect("delete-event", self._on_delete)
        self.connect("focus-out-event", self._on_focus_out)
        self.connect("key-press-event", self._on_key_press)

        # 有合成器时用 RGBA 视觉：窗口本身透明，只画带圆角和阴影的面板
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        self.composited = visual is not None and screen.is_composited()
        if self.composited:
            self.set_visual(visual)
        self.margin = SHADOW_MARGIN if self.composited else 0
        self.set_default_size(self.width + 2 * self.margin, 520 + 2 * self.margin)
        ctx = self.get_style_context()
        ctx.add_class("ec-window")
        ctx.add_class("ec-shadow" if self.composited else "ec-flat")

        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        surface.get_style_context().add_class("ec-surface")
        self.add(surface)

        self.view = "main"  # "main" 剪贴板列表 / "trash" 回收站
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.get_style_context().add_class("ec-header")
        self.title = Gtk.Label(label=_("剪贴板"), xalign=0)
        self.title.get_style_context().add_class("ec-title")
        header.pack_start(self.title, True, True, 0)
        # 主视图：[回收站][清空]；回收站视图：[返回][清空回收站 / 行内确认]。pack_end 先放的在最右
        self.btn_trash = self._header_button(_("回收站"), lambda _b: self.switch_view("trash"))
        self.btn_clear = self._header_button(_("清空"), lambda _b: self.app.clear_history())
        self.btn_back = self._header_button(_("返回"), lambda _b: self.switch_view("main"))
        self.btn_purge = self._header_button(_("清空回收站"), lambda _b: self._ask_purge_all())
        self.btn_settings = Gtk.Button.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.MENU)
        self.btn_settings.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_settings.set_can_focus(False)
        self.btn_settings.set_tooltip_text(_("设置"))
        self.btn_settings.set_valign(Gtk.Align.CENTER)
        self.btn_settings.get_style_context().add_class("ec-hicon")
        self.btn_settings.set_no_show_all(True)
        self.btn_settings.get_child().show()
        self.btn_settings.connect("clicked", lambda _b: self._open_settings())
        self.purge_confirm = self._confirm_box(_("确定清空回收站？"), _("清空"),
                                               lambda _b: self._purge_all(),
                                               lambda _b: self._cancel_purge_all())
        for w in (self.btn_settings, self.purge_confirm, self.btn_purge, self.btn_back,
                  self.btn_clear, self.btn_trash):
            header.pack_end(w, False, False, 0)
        surface.pack_start(header, False, False, 0)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text(_("搜索…"))
        self.search.get_style_context().add_class("ec-search")
        self.search.connect("search-changed", self._on_search_changed)
        self.search.connect("activate", lambda _e: self._activate_selected())
        surface.pack_start(self.search, False, False, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.get_style_context().add_class("ec-list")
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_filter_func(self._filter_row)
        self.listbox.connect("row-activated", self._on_row_activated)
        self.listbox.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.listbox.connect("motion-notify-event", self._on_list_motion)
        self.listbox.set_header_func(self._row_header)
        self.empty_label = Gtk.Label(justify=Gtk.Justification.CENTER)
        self.empty_label.get_style_context().add_class("ec-empty")
        self.empty_label.show()
        self.listbox.set_placeholder(self.empty_label)
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.get_style_context().add_class("ec-scroll")
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.add(self.listbox)
        surface.pack_start(self.scrolled, True, True, 0)

        self.count_label = Gtk.Label(xalign=0)
        self.count_label.get_style_context().add_class("ec-footer")
        surface.pack_start(self.count_label, False, False, 0)

    @property
    def width(self):
        return self.app.cfg["panel_width"]

    def _open_settings(self):
        self.hide()
        self.app.open_settings()

    # ---- 显示 / 隐藏
    def toggle(self):
        if self.get_visible():
            self.hide()
        else:
            self.popup()

    def popup(self, view="main"):
        self.prev_window, self.prev_is_terminal = active_window_info()
        self.view = view
        self.search.set_text("")
        self.rebuild()
        self._fit_height()
        self._place_at_pointer()
        self.show_all()
        self._update_header()
        self.present()
        self.search.grab_focus()
        self._shown_at = time.monotonic()
        GLib.timeout_add(150, self._ensure_focus)

    def switch_view(self, view, select_id=None):
        self.view = view
        self.search.set_text("")
        self.rebuild(select_id=select_id)
        self._update_header()
        self._fit_height()
        self.search.grab_focus()

    def _update_header(self):
        trash = self.view == "trash"
        self.title.set_text(_("回收站") if trash else _("剪贴板"))
        self.btn_trash.set_visible(not trash)
        self.btn_clear.set_visible(not trash)
        self.btn_back.set_visible(trash)
        self.btn_purge.set_visible(trash)
        self.btn_settings.show()
        self.purge_confirm.hide()

    def _header_button(self, label, on_click):
        btn = Gtk.Button(label=label)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_can_focus(False)
        btn.set_no_show_all(True)
        btn.get_style_context().add_class("ec-clear")
        btn.connect("clicked", on_click)
        return btn

    @staticmethod
    def _confirm_box(question, ok_label, on_ok, on_cancel):
        """行内确认条：问题 + [确定] [取消]，默认隐藏，show() 即显示。"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.get_style_context().add_class("ec-confirm")
        box.set_no_show_all(True)
        box.set_valign(Gtk.Align.CENTER)  # 不随卡片（如高缩略图）纵向拉伸
        label = Gtk.Label(label=question)
        ok = Gtk.Button(label=ok_label)
        ok.get_style_context().add_class("destructive-action")
        cancel = Gtk.Button(label=_("取消"))
        for b, cb in ((ok, on_ok), (cancel, on_cancel)):
            b.set_can_focus(False)
            b.set_valign(Gtk.Align.CENTER)
            b.connect("clicked", cb)
        for w in (label, ok, cancel):
            box.pack_start(w, False, False, 0)
            w.show()
        return box

    @staticmethod
    def _icon_button(icon, tooltip, on_click, *classes):
        btn = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.MENU)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_can_focus(False)
        btn.set_tooltip_text(tooltip)
        btn.set_valign(Gtk.Align.CENTER)
        ctx = btn.get_style_context()
        ctx.add_class("ec-act")
        for c in classes:
            ctx.add_class(c)
        btn.connect("clicked", on_click)
        child = btn.get_child()
        if child is not None:
            child.show()  # 按钮本身设了 no_show_all 时，图标子控件也要显式 show
        return btn

    def _ensure_focus(self):
        """Muffin 偶尔会因焦点抢占保护不给焦点，用 xdotool 兜底。"""
        if not self.get_visible() or self.is_active():
            return False
        gdk_win = self.get_window()
        if gdk_win is not None and hasattr(gdk_win, "get_xid"):
            run_bg(["xdotool", "windowactivate", str(gdk_win.get_xid())])
        return False

    def _fit_height(self):
        """按内容高度设置列表区，再把窗口高度收到最小值（= 内容高度）。"""
        _min_h, nat_h = self.listbox.get_preferred_height_for_width(self.width - 2)
        max_h = self.app.cfg["list_max_height"]
        list_h = max(min(LIST_MIN_H, max_h), min(max_h, nat_h + 6))
        self.scrolled.set_size_request(-1, list_h)
        self.resize(self.width + 2 * self.margin, 1)

    def _place_at_pointer(self):
        display = Gdk.Display.get_default()
        _screen, px, py = display.get_default_seat().get_pointer().get_position()
        geo = display.get_monitor_at_point(px, py).get_workarea()
        m = self.margin
        total_w, total_h = self.width + 2 * m, self.get_preferred_height()[0]
        # 面板可见区的左上角落在指针处，整个窗口（含阴影边距）不超出工作区
        x = max(geo.x, min(px - m, geo.x + geo.width - total_w))
        y = max(geo.y, min(py - m, geo.y + geo.height - total_h))
        self.move(x, y)

    def _on_delete(self, *_):
        self.hide()
        return True

    def _on_focus_out(self, *_):
        # 刚显示时的焦点切换过程里也会触发 focus-out，给 300ms 宽限
        if time.monotonic() - self._shown_at > 0.3:
            self.hide()
        return False

    # ---- 列表
    def rebuild(self, select_id=None):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        source = self.history.trash if self.view == "trash" else self.history.items
        for item in source:
            self.listbox.add(self._make_row(item))
        self.listbox.show_all()
        self.listbox.invalidate_filter()
        target = next((r for r in self._visible_rows() if r.item["id"] == select_id), None)
        if target is not None:
            self.listbox.select_row(target)
            GLib.idle_add(self._scroll_to_row, target)
        else:
            self._select_first_visible()
        self._update_hints()

    def _scroll_to_row(self, row):
        alloc = row.get_allocation()
        self.scrolled.get_vadjustment().clamp_page(alloc.y, alloc.y + alloc.height)
        return False

    @staticmethod
    def _row_header(row, before):
        """置顶区和普通区之间画一条分隔线。"""
        if before is not None and before.item.get("pinned") and not row.item.get("pinned"):
            if row.get_header() is None:
                sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                sep.get_style_context().add_class("ec-sep")
                sep.show()
                row.set_header(sep)
        else:
            row.set_header(None)

    def _update_hints(self):
        cfg = self.app.cfg
        k_pin, k_del, k_trash = (hotkey_label(cfg[k]) for k in ("key_pin", "key_delete", "key_trash"))
        if self.view == "trash":
            n = len(self.history.trash)
            self.count_label.set_text(
                _("回收站 {n}/{limit} · Enter 恢复 · {k_del} 两次彻底删除 · {k_trash} 返回 · Esc 关闭").format(
                    n=n, limit=cfg["max_trash"], k_del=k_del, k_trash=k_trash))
            empty = _("回收站是空的")
        else:
            n = len(self.history.items)
            self.count_label.set_text(
                _("{n} 条 · Enter 粘贴 · {k_pin} 置顶 · {k_del} 删除 · {k_trash} 回收站 · Esc 关闭").format(
                    n=n, k_pin=k_pin, k_del=k_del, k_trash=k_trash))
            empty = _("还没有记录\n复制点什么，再按 {hotkey}").format(hotkey=self.app.hotkey_label())
        if n == 0:
            self.empty_label.set_text(empty)
        elif not self._visible_rows():
            self.empty_label.set_text(_("没有匹配的内容"))

    def _make_row(self, item):
        row = Gtk.ListBoxRow()
        row.item = item
        row.set_can_focus(False)
        row.get_style_context().add_class("ec-card")
        pinned = bool(item.get("pinned"))
        if pinned:
            row.get_style_context().add_class("ec-pinned")
        # 上层：正文（图片卡片就是缩略图本身，文本卡片是两行文字）+ 右侧 ✕；下层：说明行靠右下角
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        when = fmt_time(item.get("time", 0))
        if item["type"] == "image":
            thumb = self._thumb(item)
            main = Thumbnail(thumb) if thumb is not None else Gtk.Label(label=_("（图片文件已丢失）"), xalign=0)
            meta_text = _("{when} · 图片 {w}×{h}").format(when=when, w=item["w"], h=item["h"])
        else:
            text = item["text"]
            lines = text.strip("\n").splitlines()
            n_lines = len(lines)
            if n_lines > 1:
                # 多行文本：保留原始换行和缩进，只显示前几行，每行过长单独截断
                preview = "\n".join(line.rstrip()[:PREVIEW_CHARS]
                                    for line in lines[:self.app.cfg["preview_lines"]])
                main = Gtk.Label(label=preview, xalign=0, yalign=0)
                main.set_line_wrap(False)
                main.set_ellipsize(Pango.EllipsizeMode.END)
            else:
                # 单段文本：自动换行，最多几行后省略
                preview = " ".join(text.split())[:PREVIEW_CHARS * 2]
                main = Gtk.Label(label=preview, xalign=0, yalign=0)
                main.set_line_wrap(True)
                main.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                main.set_lines(PREVIEW_WRAP_LINES)
                main.set_ellipsize(Pango.EllipsizeMode.END)
            meta_text = _("{when} · {chars} 字").format(when=when, chars=len(text))
            if n_lines > 1:
                meta_text = _("{when} · {lines} 行 · {chars} 字").format(when=when, lines=n_lines, chars=len(text))
        main.set_hexpand(True)
        top.pack_start(main, True, True, 0)

        if self.view == "trash":
            deleted = _("删除于 {when}").format(when=fmt_time(item.get("deleted_time", 0)))
            meta_text = deleted + meta_text[meta_text.find(" · "):]
            purge_btn = self._icon_button("window-close-symbolic", _("彻底删除"),
                                          lambda _b, r=row: self._ask_purge(r))
            restore_btn = self._icon_button("edit-undo-symbolic", _("恢复到列表（Enter）"),
                                            lambda _b, r=row: self._restore_item(r.item))
            row.actions = (purge_btn, restore_btn)
            row.confirm = self._confirm_box(_("彻底删除？"), _("删除"),
                                            lambda _b, r=row: self._purge_row(r),
                                            lambda _b, r=row: self._cancel_purge(r))
            row.confirming = False
            top.pack_end(purge_btn, False, False, 0)
            top.pack_end(restore_btn, False, False, 0)
            top.pack_end(row.confirm, False, False, 0)
        else:
            del_btn = self._icon_button("window-close-symbolic", _("删除（进回收站）"),
                                        lambda _b, r=row: self._delete_row(r), "ec-del")
            pin_hint = hotkey_label(self.app.cfg["key_pin"])
            pin_btn = self._icon_button(PIN_ICON, (_("取消置顶（{key}）") if pinned else _("置顶（{key}）")).format(key=pin_hint),
                                        lambda _b, r=row: self._toggle_pin(r),
                                        "ec-pin", *(["ec-pin-on"] if pinned else []))
            top.pack_end(del_btn, False, False, 0)
            top.pack_end(pin_btn, False, False, 0)

        meta = Gtk.Label(label=meta_text, xalign=1)
        meta.set_halign(Gtk.Align.END)
        meta.get_style_context().add_class("ec-meta")
        box.pack_start(top, False, False, 0)
        box.pack_start(meta, False, False, 0)

        row.add(box)
        return row

    def _thumb(self, item):
        th = self.app.cfg["thumb_height"]
        tw = self.width - 90  # 卡片内正文可用宽度
        key = (item["id"], th, tw)
        thumb = self._thumb_cache.get(key)
        if thumb is None:
            try:
                if item.get("w", 0) <= tw and item.get("h", 0) <= th:
                    thumb = GdkPixbuf.Pixbuf.new_from_file(item["file"])  # 小图保持原尺寸
                else:
                    thumb = GdkPixbuf.Pixbuf.new_from_file_at_scale(item["file"], tw, th, True)
            except GLib.Error:
                return None
            self._thumb_cache[key] = thumb
        return thumb

    def _filter_row(self, row):
        q = self.search.get_text().strip().lower()
        if not q:
            return True
        item = row.item
        if item["type"] == "image":
            return q in "图片 image"
        return q in item["text"].lower()

    def _on_search_changed(self, _entry):
        self.listbox.invalidate_filter()
        self._select_first_visible()
        self._update_hints()

    def _visible_rows(self):
        return [r for r in self.listbox.get_children() if r.get_child_visible()]

    def _select_first_visible(self):
        rows = self._visible_rows()
        self.listbox.select_row(rows[0] if rows else None)
        self.scrolled.get_vadjustment().set_value(0)

    def _move_selection(self, delta):
        rows = self._visible_rows()
        if not rows:
            return
        cur = self.listbox.get_selected_row()
        idx = rows.index(cur) if cur in rows else -1
        idx = max(0, min(len(rows) - 1, idx + delta)) if idx >= 0 else 0
        self.listbox.select_row(rows[idx])
        alloc = rows[idx].get_allocation()
        self.scrolled.get_vadjustment().clamp_page(alloc.y, alloc.y + alloc.height)

    def _on_list_motion(self, _listbox, event):
        row = self.listbox.get_row_at_y(int(event.y))
        if row is not None and row.get_child_visible() and row is not self.listbox.get_selected_row():
            self.listbox.select_row(row)
        return False

    def _delete_row(self, row):
        if self.view == "trash":
            if getattr(row, "confirming", False):
                self._purge_row(row)
            else:
                self._ask_purge(row)
            return
        self.history.trash_item(row.item["id"])
        self.rebuild()

    def _toggle_pin(self, row):
        if self.view == "trash":
            return
        item = row.item
        self.history.set_pinned(item["id"], not item.get("pinned"))
        self.rebuild(select_id=item["id"])

    def _restore_item(self, item):
        self.history.restore(item["id"])
        self.switch_view("main", select_id=item["id"])

    def _ask_purge(self, row):
        # 同一时间只允许一张卡片处于确认状态
        for other in self.listbox.get_children():
            if other is not row and getattr(other, "confirming", False):
                self._cancel_purge(other)
        row.confirming = True
        for b in row.actions:
            b.hide()
        row.confirm.show()
        self.listbox.select_row(row)

    def _cancel_purge(self, row):
        row.confirming = False
        row.confirm.hide()
        for b in row.actions:
            b.show()

    def _purge_row(self, row):
        self.history.purge(row.item["id"])
        self.rebuild()

    def _ask_purge_all(self):
        self.btn_purge.hide()
        self.purge_confirm.show()

    def _cancel_purge_all(self):
        self.purge_confirm.hide()
        self.btn_purge.show()

    def _purge_all(self):
        self.history.purge_all()
        self.rebuild()
        self._update_header()

    # ---- 按键
    def _on_key_press(self, _w, event):
        key = event.keyval
        if key == Gdk.KEY_Escape:
            self.hide()
            return True
        if key in (Gdk.KEY_Down, Gdk.KEY_Up):
            self._move_selection(1 if key == Gdk.KEY_Down else -1)
            return True
        if key in (Gdk.KEY_Page_Down, Gdk.KEY_Page_Up):
            self._move_selection(8 if key == Gdk.KEY_Page_Down else -8)
            return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._activate_selected()
            return True
        cfg = self.app.cfg
        if key_matches(event, cfg["key_pin"]):
            row = self.listbox.get_selected_row()
            if row is not None:
                self._toggle_pin(row)
            return True
        if key_matches(event, cfg["key_trash"]):
            self.switch_view("main" if self.view == "trash" else "trash")
            return True
        if key_matches(event, cfg["key_delete"]):
            row = self.listbox.get_selected_row()
            if row is not None:
                self._delete_row(row)
            return True
        # 其他按键都交给搜索框，这样打开后直接打字就是过滤
        if not self.search.has_focus():
            self.search.grab_focus()
        return False

    # ---- 选中 → 写剪贴板 → 粘贴
    def _activate_selected(self):
        row = self.listbox.get_selected_row()
        if row is None:
            rows = self._visible_rows()
            row = rows[0] if rows else None
        if row is not None:
            self._use_item(row.item)

    def _on_row_activated(self, _listbox, row):
        self._use_item(row.item)

    def _use_item(self, item):
        if self.view == "trash":
            self._restore_item(item)
            return
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.app.watcher.ignore_briefly()
        if item["type"] == "image":
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(item["file"])
            except GLib.Error:
                self.history.remove(item["id"])
                self.rebuild()
                return
            clipboard.set_image(pixbuf)
        else:
            clipboard.set_text(item["text"], -1)
        self.history.touch(item["id"])
        self.hide()
        if self.app.cfg["auto_paste"] and self.prev_window:
            combo = "ctrl+shift+v" if self.prev_is_terminal else "ctrl+v"
            GLib.timeout_add(150, self._send_paste, self.prev_window, combo)

    def _send_paste(self, window_id, combo):
        run_bg(["xdotool", "windowactivate", "--sync", window_id,
                      "key", "--clearmodifiers", combo])
        return False
