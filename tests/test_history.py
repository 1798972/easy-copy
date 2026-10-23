import os
import time

import pytest
from gi.repository import GdkPixbuf

from easy_copy import config, history


@pytest.fixture
def hist(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_FILE", tmp_path / "history.json")
    monkeypatch.setattr(history, "TRASH_FILE", tmp_path / "trash.json")
    monkeypatch.setattr(history, "IMG_DIR", tmp_path / "images")
    cfg = dict(config.DEFAULTS, max_items=3, max_trash=2)
    return history.History(cfg)


def texts(items):
    return [i.get("text", "IMG") for i in items]


def add(h, *values):
    for v in values:
        h.add_text(v)
        time.sleep(0.002)


def test_newest_first_dedupe_and_limit(hist):
    add(hist, "a", "b", "c", "a")
    assert texts(hist.items) == ["a", "c", "b"]
    add(hist, "d")
    assert texts(hist.items) == ["d", "a", "c"], "超过上限淘汰最旧的"


def test_pinned_stay_on_top_and_survive_limit_and_clear(hist):
    add(hist, "a", "b", "c")
    b = next(i for i in hist.items if i["text"] == "b")
    hist.set_pinned(b["id"], True)
    add(hist, "d", "e")
    assert texts(hist.items) == ["b", "e", "d", "c"]
    hist.add_text("b")
    assert texts(hist.items) == ["b", "e", "d", "c"], "重复复制置顶内容不产生第二条"
    hist.clear()
    assert texts(hist.items) == ["b"]
    assert texts(hist.trash) == ["e", "d"], "清空进回收站，只留最新的 max_trash 条"


def test_trash_restore_purge(hist):
    add(hist, "a", "b")
    a = next(i for i in hist.items if i["text"] == "a")
    hist.trash_item(a["id"])
    assert texts(hist.items) == ["b"] and texts(hist.trash) == ["a"]
    assert hist.restore(a["id"]) and texts(hist.items) == ["a", "b"]
    hist.trash_item(a["id"])
    hist.purge(a["id"])
    assert hist.trash == [] and texts(hist.items) == ["b"]


def test_image_file_shared_until_unreferenced(hist):
    pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 4, 4)
    pb.fill(0x336699FF)
    hist.add_image(pb)
    img = hist.items[0]
    hist.trash_item(img["id"])
    hist.add_image(pb)  # 同一张图再复制：列表和回收站各一条，共用一个文件
    assert os.path.exists(img["file"])
    hist.purge(img["id"])
    assert os.path.exists(img["file"]), "列表里还引用着，不能删文件"
    hist.trash_item(img["id"])
    hist.purge(img["id"])
    assert not os.path.exists(img["file"])


def test_persist_and_reload(hist):
    add(hist, "a", "b")
    hist.set_pinned(hist.items[1]["id"], True)
    hist.trash_item(hist.items[1]["id"])
    again = history.History(hist.cfg)
    assert texts(again.items) == ["a"] and again.items[0]["pinned"]
    assert texts(again.trash) == ["b"]


def test_enforce_limits_after_shrinking(hist):
    add(hist, "a", "b", "c")
    hist.cfg["max_items"] = 1
    hist.enforce_limits()
    assert texts(hist.items) == ["c"]
