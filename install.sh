#!/usr/bin/env bash
# easy-copy 安装 / 卸载
#   ./install.sh              装到 ~/.local/bin，注册开机自启与 Super+V 快捷键，并启动
#   ./install.sh --uninstall  移除以上三项并停止进程（历史数据保留在 ~/.local/share/easy-copy）
#   EASY_COPY_HOTKEY='Ctrl+Alt+V' ./install.sh   自定义快捷键（装好后也可 easy-copy hotkey 'Ctrl+Alt+V' 或托盘菜单改）
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
BIN="$BIN_DIR/easy-copy"
AUTOSTART="$HOME/.config/autostart/easy-copy.desktop"
BINDING="${EASY_COPY_HOTKEY:-Super+V}"
APP_ID="io.github.yang37.EasyCopy"

is_running() {
  python3 - "$APP_ID" <<'PY'
import sys, gi
from gi.repository import Gio
app = Gio.Application.new(sys.argv[1], Gio.ApplicationFlags.FLAGS_NONE)
app.register(None)
sys.exit(0 if app.get_is_remote() else 1)
PY
}

if [[ "${1:-}" == "--uninstall" ]]; then
  is_running && "$BIN" quit && echo "已停止 easy-copy" || true
  sleep 0.5
  [ -x "$BIN" ] && "$BIN" hotkey --remove || true
  rm -f "$BIN" "$AUTOSTART"
  echo "已卸载。历史数据仍在 ~/.local/share/easy-copy，配置在 ~/.config/easy-copy，不需要可自行删除"
  exit 0
fi

for dep in python3 xdotool xprop; do
  command -v "$dep" >/dev/null || { echo "缺少依赖：$dep（sudo apt install $dep）"; exit 1; }
done
python3 -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk' 2>/dev/null \
  || { echo "缺少 PyGObject GTK3：sudo apt install python3-gi gir1.2-gtk-3.0"; exit 1; }

mkdir -p "$BIN_DIR" "$(dirname "$AUTOSTART")"
chmod +x "$HERE/bin/easy-copy"
ln -sfn "$HERE/bin/easy-copy" "$BIN"
echo "已链接 $BIN -> $HERE/bin/easy-copy"

cat > "$AUTOSTART" <<DESKTOP
[Desktop Entry]
Type=Application
Name=easy-copy
Comment=剪贴板历史
Exec=$BIN
Icon=edit-paste
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
DESKTOP
echo "已写入自启动 $AUTOSTART"

# 先停掉旧进程，再由主程序注册快捷键（存到 ~/.config/easy-copy/config.json），最后启动
if is_running; then
  "$BIN" quit
  sleep 0.8
fi
"$BIN" hotkey "$BINDING" || { echo "快捷键注册失败，可稍后用 easy-copy hotkey '<组合键>' 重试，或在系统快捷键设置里手动绑定 '$BIN toggle'"; }
setsid -f "$BIN" >/dev/null 2>&1
sleep 1.5
if is_running; then
  echo "easy-copy 已启动：托盘有图标，按 $BINDING 呼出"
else
  echo "启动失败，请手动运行 $BIN 看报错"
  exit 1
fi
