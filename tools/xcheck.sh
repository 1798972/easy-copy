#!/usr/bin/env bash
# 在 Xephyr 嵌套 X 里跑一个隔离实例（独立数据 / 配置目录、私有 D-Bus）并截整屏，核对界面布局而不打扰真实桌面。
# 用法：tools/xcheck.sh OUT.png [PREP] [CMD] [KEYS]
#   PREP: none | pin（把两条标成置顶）| trash（挪一图一文进回收站）| en（英文界面）
#   CMD : toggle | trash | settings      KEYS: 截图前用 xdotool 发的按键，如 "shift+Delete Down"
# 数据用的是本机真实历史的副本，只读不写回。Xephyr 没有合成器，看不到圆角和阴影，只看布局。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$(realpath -m "$1")"; PREP="${2:-none}"; CMD="${3:-toggle}"; KEYS="${4:-}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
XD="$WORK/xdg"; mkdir -p "$XD/easy-copy" "$XD/cfg/easy-copy" "$XD/cfg/autostart"
cp -a "$HOME/.local/share/easy-copy/." "$XD/easy-copy/"
for f in history.json trash.json; do [ -f "$XD/easy-copy/$f" ] && sed -i "s|$HOME/.local/share/easy-copy/images/|$XD/easy-copy/images/|g" "$XD/easy-copy/$f"; done
echo '{"language": "zh"}' > "$XD/cfg/easy-copy/config.json"   # 有配置文件就不会触发首次运行初始化
python3 - "$XD/easy-copy" "$PREP" "$XD/cfg/easy-copy/config.json" <<'PY'
import json, sys, time
d, prep, cfg = sys.argv[1:4]
hist = json.load(open(f"{d}/history.json"))
if prep == "pin":
    for i, dt in ((1, 0), (3, 1)):
        if i < len(hist): hist[i]["pinned"] = True; hist[i]["pin_time"] = time.time() - dt
if prep == "trash":
    moved = [h for h in hist if h["type"] == "image"][:1] + [h for h in hist if h["type"] == "text"][:1]
    hist = [h for h in hist if h not in moved]
    for k, m in enumerate(moved): m["deleted_time"] = time.time() - k; m["pinned"] = False
    json.dump(moved, open(f"{d}/trash.json", "w"), ensure_ascii=False)
if prep == "en":
    json.dump({"language": "en"}, open(cfg, "w"))
json.dump(hist, open(f"{d}/history.json", "w"), ensure_ascii=False)
PY
Xephyr :99 -screen 560x820 -nolisten tcp -title "easy-copy-check" >/dev/null 2>&1 &
XPID=$!; sleep 1.2
W=$(xdotool search --name '^easy-copy-check$' | head -1); [ -n "$W" ] && xdotool windowminimize "$W"
XDG_DATA_HOME="$XD" XDG_CONFIG_HOME="$XD/cfg" DISPLAY=:99 ROOT="$ROOT" OUT="$OUT" CMD="$CMD" KEYS="$KEYS" dbus-run-session -- bash -c '
  cd "$ROOT"
  python3 ./bin/easy-copy >"$OUT.log" 2>&1 &
  DPID=$!; sleep 2.5
  xdotool mousemove 30 30
  python3 ./bin/easy-copy "$CMD"; sleep 1.5
  if [ -n "$KEYS" ]; then for k in $KEYS; do xdotool key "$k"; sleep 0.3; done; sleep 0.5; fi
  python3 - "$OUT" <<PY
import sys, gi
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk
root = Gdk.get_default_root_window()
Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height()).savev(sys.argv[1], "png", [], [])
print("saved", sys.argv[1])
PY
  python3 ./bin/easy-copy quit; sleep 0.5; kill $DPID 2>/dev/null
' 2>&1 | grep -E "^saved|Traceback|Error" || true
kill "$XPID" 2>/dev/null || true
grep -v "daemon started" "$OUT.log" || true; rm -f "$OUT.log"
