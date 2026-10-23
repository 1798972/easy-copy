"""监听 X11 剪贴板变化并写入历史。"""

import time

from gi.repository import Gdk, Gtk


class ClipboardWatcher:
    """监听 X11 CLIPBOARD 的 owner-change，有文本记文本，否则有图片记图片。"""

    def __init__(self, history, on_change):
        self.history = history
        self.on_change = on_change
        self._ignore_until = 0.0
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", self._on_owner_change)

    def ignore_briefly(self):
        """自己写剪贴板之前调用，跳过随之而来的 owner-change。"""
        self._ignore_until = time.monotonic() + 0.5

    def _on_owner_change(self, clipboard, _event):
        if time.monotonic() < self._ignore_until:
            return
        clipboard.request_targets(self._on_targets)

    def _on_targets(self, clipboard, atoms, *_):
        if not atoms:
            return
        names = {a.name() for a in atoms}
        # 密码管理器（KeePassXC 等）复制密码时会带这个标记，不记录
        if "x-kde-passwordManagerHint" in names:
            return
        if Gtk.targets_include_text(atoms):
            clipboard.request_text(self._on_text)
        elif Gtk.targets_include_image(atoms, False):
            clipboard.request_image(self._on_image)

    def _on_text(self, _clipboard, text, *_):
        if text and self.history.add_text(text):
            self.on_change()

    def _on_image(self, _clipboard, pixbuf, *_):
        if pixbuf is not None and self.history.add_image(pixbuf):
            self.on_change()
