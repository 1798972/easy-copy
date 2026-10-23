"""easy-copy：极简剪贴板历史（Linux / X11），对标 Windows 的 Win+V。"""

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("GdkPixbuf", "2.0")

__version__ = "0.1.0"
