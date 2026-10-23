"""每个 _("...") 的原文都必须有英文译文；切换语言后文案变化。"""
import re
from pathlib import Path

from easy_copy import i18n

SRC = Path(__file__).resolve().parents[1] / "src" / "easy_copy"


def test_every_source_string_has_english():
    pattern = re.compile(r'_\("((?:[^"\\]|\\.)*)"\)')
    missing = set()
    for path in SRC.rglob("*.py"):
        for m in pattern.finditer(path.read_text(encoding="utf-8")):
            key = m.group(1).encode().decode("unicode_escape").encode("latin-1").decode("utf-8")
            if key not in i18n.EN:
                missing.add(key)
    assert not missing, f"缺英文译文: {sorted(missing)}"


def test_switch_language():
    i18n.set_language("en")
    assert i18n._("剪贴板") == "Clipboard"
    assert i18n._("没有这句") == "没有这句", "缺译文时回退原文"
    i18n.set_language("zh")
    assert i18n._("剪贴板") == "剪贴板"


def test_auto_detect(monkeypatch):
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    assert i18n.detect_system_language() == "zh"
    monkeypatch.setenv("LANGUAGE", "en_US:zh")
    assert i18n.detect_system_language() == "en"
    i18n.set_language("zh")
