#!/usr/bin/env bash
# 打 deb 包：./build-deb.sh → dist/easy-copy_<版本>_all.deb
# 只用 dpkg-deb，不需要 debhelper；版本号取自 src/easy_copy/__init__.py。
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$HERE/src/easy_copy/__init__.py")"
[ -n "$VERSION" ] || { echo "读不到版本号"; exit 1; }
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
PKG="$STAGE/easy-copy"
mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/lib/easy-copy" "$PKG/usr/share/applications" "$PKG/usr/share/doc/easy-copy"

cp -r "$HERE/src/easy_copy" "$PKG/usr/lib/easy-copy/"
find "$PKG/usr/lib/easy-copy" -name __pycache__ -type d -prune -exec rm -rf {} +
install -m 755 "$HERE/bin/easy-copy" "$PKG/usr/bin/easy-copy"
install -m 644 "$HERE/packaging/easy-copy.desktop" "$PKG/usr/share/applications/easy-copy.desktop"
install -m 644 "$HERE/README.md" "$HERE/README.en.md" "$PKG/usr/share/doc/easy-copy/"
install -m 644 "$HERE/LICENSE" "$PKG/usr/share/doc/easy-copy/copyright"
[ -f "$HERE/CHANGELOG.md" ] && install -m 644 "$HERE/CHANGELOG.md" "$PKG/usr/share/doc/easy-copy/changelog"

cat > "$PKG/DEBIAN/control" <<CONTROL
Package: easy-copy
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-gi, python3-gi-cairo, gir1.2-gtk-3.0, gir1.2-gdkpixbuf-2.0, xdotool, x11-utils
Recommends: gir1.2-ayatanaappindicator3-0.1, libnotify-bin
Maintainer: 1798972 <49218070+1798972@users.noreply.github.com>
Homepage: https://github.com/1798972/easy-copy
Description: clipboard history panel for Linux X11 (Win+V style)
 Records text and image clipboard entries and shows them in a rounded
 floating panel with search, pin and a recycle bin. Press Super+V to
 open it; the hotkey and everything else is configurable from the
 settings window. X11 sessions only.
CONTROL
find "$PKG" -type d -exec chmod 755 {} +
mkdir -p "$HERE/dist"
OUT="$HERE/dist/easy-copy_${VERSION}_all.deb"
dpkg-deb --build --root-owner-group "$PKG" "$OUT" >/dev/null
echo "已生成 $OUT"
dpkg-deb --info "$OUT" | sed -n '1,/Description/p' | grep -E "Package|Version|Depends|Architecture"
