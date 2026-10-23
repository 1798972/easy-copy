# easy-copy

[English](README.en.md)

Linux 下的极简剪贴板历史，对标 Windows 的 Win+V：按一下快捷键弹出面板，选中就贴回去。
单纯的 Python + GTK3，Linux Mint / Ubuntu 上系统自带的库就够用。

![面板](screenshots/panel.png)

## 功能

- 后台记录复制过的**文本和图片**，按内容去重，重复复制的条目置顶，默认保留 200 条
- **Super+V** 在鼠标位置弹出面板；直接打字即过滤
- `↑` `↓` 或鼠标移动即选中，`Enter` 或单击 = 写回剪贴板并**自动粘贴**到之前的窗口（终端自动用 Ctrl+Shift+V）
- **置顶**：常用内容固定在最上面，不被新复制的挤走，「清空」也不清它
- **回收站**：删除不确认、先进回收站（默认 50 条），回收站里才需要确认彻底删除；可恢复
- 托盘图标、开机自启、桌面主题自适应（深色主题也行）
- 界面中 / 英文

## 系统要求

- X11 会话（Wayland 下拿不到其它程序的剪贴板变化，xdotool 也不工作；Mint 默认就是 X11，Ubuntu GNOME 请在登录界面选 Xorg）
- Python 3.10+、PyGObject、GTK 3；全局快捷键自动注册支持 **Cinnamon** 和 **GNOME**，其它桌面可手动绑定
- 依赖包（Debian / Ubuntu / Mint 包名）：`python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 xdotool x11-utils`，可选 `gir1.2-ayatanaappindicator3-0.1`（托盘图标）、`libnotify-bin`（首次运行提示）

## 安装

**方式一：deb 包**（Mint / Ubuntu / Debian，从 Releases 下载）

```bash
sudo apt install ./easy-copy_0.1.0_all.deb
```

装完在应用菜单里点「easy-copy」或按 Super+V：第一次启动会自动注册快捷键并设置开机自启。

**方式二：clone 即用**

```bash
git clone https://github.com/1798972/easy-copy.git
cd easy-copy
./install.sh
```

`install.sh` 把 `bin/easy-copy` 软链到 `~/.local/bin`，写开机自启，注册 Super+V，然后启动。
改快捷键：`EASY_COPY_HOTKEY='Ctrl+Alt+V' ./install.sh`。卸载：`./install.sh --uninstall`（历史数据保留）。

## 使用

| 操作 | 按键 |
|---|---|
| 呼出 / 隐藏面板 | Super+V（可改） |
| 过滤 | 直接打字 |
| 选择 | ↑ ↓ 或移动鼠标 |
| 粘贴 | Enter 或单击 |
| 置顶 / 取消 | Ctrl+P（可改）或卡片上的 📌 |
| 删除到回收站 | Shift+Delete（可改）或卡片上的 ✕ |
| 打开回收站 | Ctrl+T（可改）或标题栏「回收站」 |
| 回收站里恢复 / 彻底删除 | Enter / Shift+Delete 两次 |
| 关闭 | Esc 或点别处 |

## 设置

托盘图标 → 「设置…」，或面板右上角 ⚙，或 `easy-copy settings`。

![设置](screenshots/settings.png)

| 分组 | 项 |
|---|---|
| 语言 | 跟随系统 / 中文 / English |
| 快捷键 | 呼出面板、呼出回收站（全局）；置顶、删除、切换回收站（面板内）。改键时即时检查冲突：撞上系统快捷键会提示并可选择仍然应用，内部互撞直接禁止 |
| 行为 | 自动粘贴、开机自启、托盘图标 |
| 容量 | 历史条数上限（200）、回收站条数上限（50） |
| 外观 | 面板宽度、列表最大高度、缩略图最大高度、多行文本预览行数 |

配置存在 `~/.config/easy-copy/config.json`，历史存在 `~/.local/share/easy-copy/`。

## 命令行

```
easy-copy            启动常驻进程
easy-copy toggle     弹出 / 隐藏面板（快捷键绑的就是这个）
easy-copy trash      打开回收站
easy-copy clear      清空历史（进回收站）
easy-copy hotkey     查看快捷键；easy-copy hotkey 'Ctrl+Alt+V' 修改；--remove 解除
easy-copy settings   打开设置
easy-copy version    版本
easy-copy quit       退出
```

## 已知限制

- 只支持 X11；不支持 Wayland
- 全局快捷键只在 Cinnamon / GNOME 下自动注册，KDE / XFCE / MATE 请在系统快捷键设置里把 `easy-copy toggle` 绑到想要的键
- 自动粘贴依赖 xdotool，极少数程序会忽略合成的按键，此时内容已在剪贴板，手动 Ctrl+V 即可

## 开发

```bash
./bin/easy-copy          # 直接运行仓库里的代码
python3 -m pytest tests  # 纯逻辑测试（历史、配置、快捷键、翻译表）
python3 -m pyflakes src
./build-deb.sh           # 生成 dist/easy-copy_<版本>_all.deb
```

代码在 `src/easy_copy/`：`history.py` 历史与回收站，`hotkey.py` 组合键解析校验，`desktop.py` 桌面集成（快捷键注册、自启动、粘贴），`ui/` 界面，`i18n.py` 翻译表。

## 许可证

MIT
