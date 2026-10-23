# easy-copy

Linux Mint（Cinnamon / X11）上的极简剪贴板历史，对标 Windows 的 Win+V。
单文件 Python + GTK3，系统自带的库就够，不装任何依赖。

## 功能

- 后台记录复制过的**文本和图片**，去重，重复复制的条目置顶，上限 200 条
- **Super+V** 在鼠标位置弹出面板；直接打字即过滤
- `↑` `↓` 或鼠标移动即选中（只有一种高亮，就是 Enter 会粘贴的那条），`Enter` 或单击 = 写回剪贴板并**自动粘贴**到之前的窗口（终端自动用 Ctrl+Shift+V）
- **置顶**：卡片上的 📌 或 `Ctrl+P`（可改）切换。置顶条目固定在最上面的置顶区（最近置顶的在最前），琥珀色左侧色条 + 常亮图钉标记；不受 200 条上限淘汰，「清空」也不会清掉；再点一次取消
- **删除进回收站**：`Shift+Del`（可改）或卡片上的 ✕ 立即删除、不确认，条目进回收站（最多 50 条，超出丢弃最早删除的）；顶部「清空」也是把普通条目整体放进回收站（置顶的保留）。超过 200 条被自动淘汰的旧条目不进回收站
- **回收站**：顶部「回收站」按钮或 `Ctrl+T`（可改）切换，也可以给它单独设一个全局快捷键；卡片上 ↩ 或 `Enter` = 恢复到列表最前，✕ 或 `Shift+Del` = 彻底删除，需要在卡片内点「删除」确认（键盘再按一次 `Shift+Del` 也算确认）；「清空回收站」同样行内确认。也可以直接 `easy-copy trash` 打开回收站视图
- `Esc`、点别处 = 关闭
- 托盘图标（打开 / 清空 / 退出），开机自启
- 历史存在 `~/.local/share/easy-copy/`（`history.json` + `trash.json` + `images/*.png`），重启不丢
- 密码管理器复制的密码（带 `x-kde-passwordManagerHint` 标记）不记录

## 安装

```bash
./install.sh
```

做了三件事：`~/.local/bin/easy-copy` 软链到本目录的 `easy_copy.py`、写
`~/.config/autostart/easy-copy.desktop`、注册快捷键（默认 Super+V），
然后启动常驻进程。改了代码只需 `easy-copy quit && easy-copy &`。

## 设置

托盘图标 → 「设置…」，或面板标题栏右上角的 ⚙，或命令 `easy-copy settings`，都打开同一个设置窗口。
所有项改动即时生效并保存到 `~/.config/easy-copy/config.json`：

| 分组 | 项 | 默认 |
|---|---|---|
| 快捷键 | 全局：呼出面板 / 呼出回收站 | Super+V / 未设置 |
| 快捷键 | 面板内：置顶 / 删除 / 切换回收站 | Ctrl+P / Shift+Delete / Ctrl+T |
| 行为 | 选中后自动粘贴到原窗口 | 开 |
| 行为 | 开机自动启动（读写 `~/.config/autostart/easy-copy.desktop`） | 开 |
| 行为 | 显示托盘图标 | 开 |
| 容量 | 历史条数上限 | 200 |
| 容量 | 回收站条数上限 | 50 |
| 外观 | 面板宽度 / 列表最大高度 / 缩略图最大高度（px） | 440 / 640 / 120 |
| 外观 | 多行文本预览行数 | 5 |

每个快捷键都有「修改…」（弹窗里直接按下新组合键）和「恢复默认」，全局的还可「解除」。
按下组合键的瞬间就会校验并提示：

- 全局快捷键撞上系统快捷键或别的自定义快捷键：红字提示「已被 xxx 占用」，按钮变成「仍然应用」，由你决定；
- 两个全局快捷键互撞、面板内三个互撞、或撞上 Enter / Esc 这类固定键：禁止应用并说明原因；
- 全局快捷键必须带 Ctrl / Alt / Super（功能键可单独用）；面板内快捷键还允许 Shift + Delete 这类非打印键，但不允许会和打字冲突的组合。

Enter 粘贴 / 恢复、Esc 关闭、↑↓ 选择、直接打字搜索是固定的。「全部恢复默认」一键还原（含快捷键和自启动）。

### 快捷键也可以用命令行改

```bash
easy-copy hotkey                 # 看当前快捷键
easy-copy hotkey 'Ctrl+Alt+V'    # 改；也接受 GTK 写法 '<Control><Alt>v'
easy-copy hotkey --remove        # 解除全部全局快捷键绑定
EASY_COPY_HOTKEY='Ctrl+Alt+V' ./install.sh   # 安装时指定
```

- 组合键必须带 Ctrl / Alt / Super 之一（F1–F12 这类功能键可以单独用），否则会拒绝，避免打字就触发。
- 注册时会检查系统快捷键和其它自定义快捷键是否已占用同一组合，有冲突会提示。
- 自动注册支持 **Cinnamon** 和 **GNOME**；其它桌面（KDE / XFCE / MATE 等）请在系统的键盘快捷键设置里把命令 `~/.local/bin/easy-copy toggle` 绑到想要的键，程序本身不抓键盘。

## 命令

```
easy-copy          启动常驻进程
easy-copy toggle   弹出 / 隐藏面板（快捷键绑的就是这个）
easy-copy trash    直接打开回收站视图
easy-copy clear    清空历史（进回收站）
easy-copy settings 打开设置窗口
easy-copy quit     退出
```

## 调参

常用项都在「设置」窗口里。只剩几个很少动的常量在 `easy_copy.py` 顶部：`TERMINAL_CLASSES`（哪些窗口用 Ctrl+Shift+V 粘贴）、
`LIST_MIN_H`（列表最小高度）、`PREVIEW_CHARS`（预览每行最多取的字符数）。

## 实现要点

- 剪贴板监听：GTK `owner-change` 信号；有文本记文本，否则有图片记图片（存 PNG，按内容哈希去重）
- 单实例：`Gtk.Application` 的 DBus 机制，`easy-copy toggle` 第二次运行会自动转发给常驻进程
- 自动粘贴：弹窗前记下活动窗口 id，选中后 `xdotool windowactivate` 回去再发 Ctrl+V
- 全局快捷键不自己抓键盘，走桌面环境自带的自定义快捷键（Cinnamon / GNOME 自动注册，其它桌面手动绑定 `easy-copy toggle`）
