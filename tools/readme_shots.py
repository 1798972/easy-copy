#!/usr/bin/env python3
"""重新生成 README 用的截图：screenshots/panel.png 与 screenshots/settings.png。

用一份程序生成的演示数据，在真实桌面上（要有合成器才有圆角和阴影）以不抢焦点的方式显示
面板和设置窗口，直接从窗口表面读像素（带透明阴影边）。不碰真实历史、不注册 D-Bus、不监听剪贴板。
"""
import hashlib
import json
import math
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = tempfile.mkdtemp(prefix="easy-copy-shots-")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "cfg")
sys.path.insert(0, os.path.join(ROOT, "src"))

from easy_copy import config  # noqa: E402  先导入包，让它声明 GTK 版本

import cairo  # noqa: E402
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from easy_copy.app import EasyCopyApp  # noqa: E402
from easy_copy.history import History  # noqa: E402
from easy_copy.ui.panel import Panel  # noqa: E402
from easy_copy.ui.settings import SettingsWindow  # noqa: E402
from easy_copy.ui.style import install_css  # noqa: E402

OUT = os.path.join(ROOT, "screenshots")


def sample_image(path):
    w, h = 480, 270
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surf)
    g = cairo.LinearGradient(0, 0, w, h)
    g.add_color_stop_rgb(0, 0.93, 0.96, 1.0)
    g.add_color_stop_rgb(1, 0.86, 0.93, 0.90)
    cr.set_source(g)
    cr.paint()
    for x, col in ((40, (0.29, 0.56, 0.85)), (180, (0.36, 0.69, 0.47)), (320, (0.88, 0.59, 0.18))):
        r = 16
        cr.new_sub_path()
        cr.arc(x + 120 - r, 70 + r, r, -math.pi / 2, 0)
        cr.arc(x + 120 - r, 200 - r, r, 0, math.pi / 2)
        cr.arc(x + r, 200 - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, 70 + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.set_source_rgb(*col)
        cr.fill()
    cr.set_source_rgb(0.25, 0.3, 0.35)
    cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(20)
    cr.move_to(40, 240)
    cr.show_text("sample image")
    surf.write_to_png(path)
    return w, h


def write_sample_data():
    config.IMG_DIR.mkdir(parents=True, exist_ok=True)
    config.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.CONFIG_FILE.write_text('{"language": "zh"}')
    autostart = config.CONFIG_FILE.parent.parent / "autostart"
    autostart.mkdir(exist_ok=True)
    (autostart / "easy-copy.desktop").write_text("[Desktop Entry]\nType=Application\nName=easy-copy\nExec=easy-copy\n")
    tmp = os.path.join(WORK, "sample.png")
    w, h = sample_image(tmp)
    data = open(tmp, "rb").read()
    digest = hashlib.sha1(data).hexdigest()
    img = config.IMG_DIR / f"{digest}.png"
    img.write_bytes(data)
    t = time.localtime()

    def at(hh, mm):
        return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, hh, mm, 0, 0, 0, -1))

    def text(s, hh, mm, pinned=False):
        return {"id": hashlib.sha1(s.encode()).hexdigest(), "type": "text", "text": s, "time": at(hh, mm),
                "pinned": pinned, "pin_time": at(9, 0) if pinned else 0}

    items = [
        text("https://github.com/1798972/easy-copy", 9, 30, pinned=True),
        {"id": digest, "type": "image", "file": str(img), "w": w, "h": h, "time": at(10, 20)},
        text("测试数据123", 10, 15),
        text("pip install -r requirements.txt", 10, 10),
        text('def greet(name):\n    return f"Hello, {name}!"', 10, 5),
        text("Hello, world!", 10, 0),
    ]
    config.HISTORY_FILE.write_text(json.dumps(items, ensure_ascii=False))


def grab(win, name):
    gw = win.get_window()
    pb = Gdk.pixbuf_get_from_window(gw, 0, 0, gw.get_width(), gw.get_height())
    path = os.path.join(OUT, f"{name}.png")
    pb.savev(path, "png", [], [])
    print("saved", path)


def quiet(win):
    win.set_accept_focus(False)
    win.set_focus_on_map(False)


def main():
    write_sample_data()
    os.makedirs(OUT, exist_ok=True)
    app = EasyCopyApp()  # 不 run()：不注册 D-Bus、不监听剪贴板
    app.history = History(app.cfg)
    install_css()
    panel = Panel(app)
    panel.rebuild()
    panel._fit_height()
    panel.move(200, 120)
    quiet(panel)
    panel.show_all()
    panel._update_header()

    def step2():
        grab(panel, "panel")
        panel.hide()
        s = SettingsWindow(app)
        quiet(s)
        s.move(700, 80)
        GLib.timeout_add(900, lambda: (grab(s, "settings"), s.destroy(), Gtk.main_quit()) and False)
        return False

    GLib.timeout_add(1200, step2)
    Gtk.main()


if __name__ == "__main__":
    main()
