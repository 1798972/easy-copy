"""界面常量与 CSS。颜色全部取自主题变量，深浅主题自动适配。"""

from gi.repository import Gdk, Gtk

SHADOW_MARGIN = 16          # 有合成器时，面板四周留给阴影的透明边距
THUMB_RADIUS = 6
PIN_ICON = "view-pin-symbolic"

CSS = b"""
@define-color ec_pin #e0962e;
window.ec-window.ec-shadow { background-color: transparent; }
window.ec-window.ec-flat   { background-color: @theme_bg_color; }

.ec-surface {
  background-color: @theme_bg_color;
  border: 1px solid alpha(@theme_fg_color, 0.14);
  border-radius: 12px;
}
.ec-shadow .ec-surface {
  margin: 16px;
  box-shadow: 0 8px 28px alpha(black, 0.28), 0 1px 3px alpha(black, 0.16);
}

.ec-header { padding: 12px 10px 6px 16px; }
.ec-title  { font-weight: bold; font-size: 1.1em; }
.ec-clear {
  min-height: 0; padding: 3px 10px; border-radius: 6px; font-size: 0.9em;
  color: alpha(@theme_fg_color, 0.65);
}
.ec-clear:hover { color: @theme_fg_color; background-color: alpha(@theme_fg_color, 0.08); }

.ec-search { margin: 0 12px 6px 12px; border-radius: 8px; }
.ec-hicon { opacity: 0.55; min-width: 0; min-height: 0; padding: 4px; border-radius: 50%; }
.ec-hicon:hover { opacity: 1; background-color: alpha(@theme_fg_color, 0.08); }

.ec-scroll, .ec-scroll viewport, list.ec-list, list.ec-list row { background-color: transparent; }
list.ec-list row.ec-card {
  margin: 3px 12px;
  padding: 9px 10px 8px 12px;
  border-radius: 9px;
  border: 1px solid alpha(@theme_fg_color, 0.10);
  background-color: @theme_base_color;
  color: @theme_text_color;
  transition: border-color 120ms ease, background-color 120ms ease;
}
list.ec-list row.ec-card:selected {
  background-color: alpha(@theme_selected_bg_color, 0.13);
  border-color: @theme_selected_bg_color;
}
list.ec-list row.ec-card:selected label { color: @theme_text_color; }
list.ec-list row.ec-card.ec-pinned {
  border-color: alpha(@ec_pin, 0.6);
  border-left: 3px solid @ec_pin;
  padding-left: 10px;
}
list.ec-list row.ec-card.ec-pinned:selected { border-color: @theme_selected_bg_color; border-left-color: @ec_pin; }
separator.ec-sep { margin: 4px 24px 2px 24px; }
.ec-meta { font-size: 0.82em; color: alpha(@theme_text_color, 0.55); }
list.ec-list row.ec-card:selected .ec-meta { color: alpha(@theme_text_color, 0.6); }

/* card action buttons: only visible on the selected card */
.ec-act { opacity: 0; min-width: 0; min-height: 0; padding: 3px; border-radius: 50%; }
list.ec-list row.ec-card:selected .ec-act,
list.ec-list row.ec-card:selected .ec-act image { color: @theme_text_color; -gtk-icon-shadow: none; }
list.ec-list row.ec-card:selected .ec-act { opacity: 0.6; }
list.ec-list row.ec-card .ec-act:hover { opacity: 1; background-color: alpha(@theme_fg_color, 0.1); }
/* inline confirm (permanent delete / empty trash) */
.ec-confirm label { font-size: 0.88em; color: alpha(@theme_text_color, 0.75); }
.ec-confirm button { min-height: 0; min-width: 0; padding: 2px 10px; font-size: 0.88em; border-radius: 6px; }
/* pinned: pin icon always on, amber, acts as the marker */
list.ec-list row.ec-card .ec-pin-on,
list.ec-list row.ec-card .ec-pin-on image,
list.ec-list row.ec-card:selected .ec-pin-on,
list.ec-list row.ec-card:selected .ec-pin-on image { opacity: 1; color: @ec_pin; }

.ec-empty  { color: alpha(@theme_fg_color, 0.45); }
.ec-footer { padding: 6px 16px 10px; font-size: 0.82em; color: alpha(@theme_fg_color, 0.5); }
"""


def install_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
