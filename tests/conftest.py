"""测试只碰纯逻辑模块；数据目录和配置目录指向临时目录，绝不碰真实数据。
必须在导入 easy_copy 之前设置 XDG 环境变量（GLib 只读一次）。"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
_tmp = tempfile.mkdtemp(prefix="easy-copy-test-")
os.environ["XDG_DATA_HOME"] = os.path.join(_tmp, "data")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_tmp, "config")
