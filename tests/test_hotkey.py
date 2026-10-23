import pytest
from gi.repository import Gdk

from easy_copy import hotkey


@pytest.mark.parametrize("text,expected", [
    ("Super+V", "<Super>v"), ("<Super>v", "<Super>v"), ("Ctrl+Alt+V", "<Control><Alt>v"),
    ("ctrl-shift-space", "<Control><Shift>space"), ("Win+C", "<Super>c"), ("F9", "F9"),
    ("v", None), ("Shift+V", None), ("Foo+V", None), ("", None),
])
def test_normalize(text, expected):
    assert hotkey.normalize_hotkey(text) == expected


def test_label_and_same_binding():
    assert hotkey.hotkey_label("<Super>v") == "Super+V"
    assert hotkey.hotkey_label("") == "未设置"
    assert hotkey.same_binding("<Control>p", "<Primary>p")


def test_panel_key_rules():
    assert hotkey.panel_key_acceptable(Gdk.KEY_Delete, Gdk.ModifierType.SHIFT_MASK)
    assert hotkey.panel_key_acceptable(Gdk.KEY_p, Gdk.ModifierType.CONTROL_MASK)
    assert not hotkey.panel_key_acceptable(Gdk.KEY_a, Gdk.ModifierType.SHIFT_MASK), "Shift+字母会和打字冲突"
    assert not hotkey.panel_key_acceptable(Gdk.KEY_Return, 0)


class Ev:
    def __init__(self, name, state):
        self.keyval = Gdk.keyval_from_name(name)
        self.state = state


def test_key_matches():
    assert hotkey.key_matches(Ev("p", Gdk.ModifierType.CONTROL_MASK), "<Control>p")
    assert hotkey.key_matches(Ev("Delete", Gdk.ModifierType.SHIFT_MASK), "<Shift>Delete")
    assert not hotkey.key_matches(Ev("P", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK), "<Control>p")
    assert hotkey.key_matches(Ev("p", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD2_MASK), "<Control>p"), "NumLock 不影响"
    assert not hotkey.key_matches(Ev("p", Gdk.ModifierType.CONTROL_MASK), "")
