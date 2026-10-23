"""历史记录：内存列表 + JSON 持久化，含置顶与回收站。"""

import hashlib
import json
import os
import time

from .config import HISTORY_FILE, IMG_DIR, MAX_TEXT_BYTES, TRASH_FILE


class History:
    """内存列表 + history.json / trash.json 持久化；图片另存 PNG 文件，按内容哈希去重。

    删除的条目先进回收站（最多 cfg["max_trash"] 条），彻底删除或被挤出回收站时才删图片文件，
    且只在没有任何条目再引用该文件时删（同一内容的文件只有一份）。
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.items = []
        self.trash = []
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        self.items = self._read(HISTORY_FILE)
        self.trash = self._read(TRASH_FILE)
        self._sort()
        self.trash.sort(key=lambda t: -t.get("deleted_time", 0))

    @staticmethod
    def _read(path):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [
            it for it in data
            if it.get("type") == "text"
            or (it.get("type") == "image" and os.path.exists(it.get("file", "")))
        ]

    def _sort(self):
        """置顶区在前（最近置顶的在最上面），其余按复制时间倒序。"""
        self.items.sort(key=lambda it: (0, -it.get("pin_time", 0)) if it.get("pinned")
                        else (1, -it.get("time", 0)))

    def find(self, item_id):
        return next((it for it in self.items if it["id"] == item_id), None)

    def _save(self):
        self._write(HISTORY_FILE, self.items)

    def _save_trash(self):
        self._write(TRASH_FILE, self.trash)

    @staticmethod
    def _write(path, data):
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def add_text(self, text):
        if not text or not text.strip() or len(text.encode("utf-8")) > MAX_TEXT_BYTES:
            return False
        item_id = hashlib.sha1(text.encode("utf-8")).hexdigest()
        return self._push({"id": item_id, "type": "text", "text": text, "time": time.time()})

    def add_image(self, pixbuf):
        ok, data = pixbuf.save_to_bufferv("png", [], [])
        if not ok:
            return False
        item_id = hashlib.sha1(data).hexdigest()
        path = IMG_DIR / f"{item_id}.png"
        if not path.exists():
            path.write_bytes(data)
        return self._push({
            "id": item_id, "type": "image", "file": str(path),
            "w": pixbuf.get_width(), "h": pixbuf.get_height(), "time": time.time(),
        })

    def touch(self, item_id):
        """把某条移到最前（选中粘贴后的行为，和 Win+V 一致）。"""
        for it in self.items:
            if it["id"] == item_id:
                it["time"] = time.time()
                return self._push(it)
        return False

    def _push(self, item):
        old = self.find(item["id"])
        if old is not None:
            # 已有同样内容：保留置顶状态，只刷新时间
            item["pinned"] = old.get("pinned", False)
            item["pin_time"] = old.get("pin_time", 0)
            self.items.remove(old)
        self.items.append(item)
        self._sort()
        self._trim_items()
        self._save()
        return True

    def _trim_items(self):
        """超出上限只淘汰未置顶的最旧条目（自动淘汰不进回收站）。"""
        unpinned = [it for it in self.items if not it.get("pinned")]
        for dropped in unpinned[self.cfg["max_items"]:]:
            self.items.remove(dropped)
            self._drop_file_if_unreferenced(dropped)

    def enforce_limits(self):
        """设置里改小上限后立即生效。"""
        self._trim_items()
        self._trim_trash()
        self._save()
        self._save_trash()

    def set_pinned(self, item_id, pinned):
        it = self.find(item_id)
        if it is None:
            return False
        it["pinned"] = bool(pinned)
        it["pin_time"] = time.time() if pinned else 0
        self._sort()
        self._save()
        return True

    def remove(self, item_id):
        """直接移除（不进回收站），只用于图片文件已丢失之类的坏条目。"""
        gone = [it for it in self.items if it["id"] == item_id]
        self.items = [it for it in self.items if it["id"] != item_id]
        for it in gone:
            self._drop_file_if_unreferenced(it)
        self._save()

    # ---- 回收站
    def trash_item(self, item_id):
        it = self.find(item_id)
        if it is None:
            return False
        self.items.remove(it)
        self._add_to_trash(it)
        self._trim_trash()
        self._save()
        self._save_trash()
        return True

    def clear(self):
        """清空普通条目（进回收站），置顶的保留。"""
        gone = [it for it in self.items if not it.get("pinned")]
        self.items = [it for it in self.items if it.get("pinned")]
        for it in reversed(gone):  # 最新的最后放入，排在回收站最前
            self._add_to_trash(it)
        self._trim_trash()
        self._save()
        self._save_trash()

    def find_trashed(self, item_id):
        return next((t for t in self.trash if t["id"] == item_id), None)

    def restore(self, item_id):
        """从回收站恢复到列表最前（按当前时间排）。"""
        t = self.find_trashed(item_id)
        if t is None:
            return False
        self.trash.remove(t)
        it = dict(t)
        it.pop("deleted_time", None)
        it["time"] = time.time()
        self._push(it)
        self._save_trash()
        return True

    def purge(self, item_id):
        """彻底删除回收站里的一条。"""
        gone = [t for t in self.trash if t["id"] == item_id]
        self.trash = [t for t in self.trash if t["id"] != item_id]
        for t in gone:
            self._drop_file_if_unreferenced(t)
        self._save_trash()

    def purge_all(self):
        gone, self.trash = self.trash, []
        for t in gone:
            self._drop_file_if_unreferenced(t)
        self._save_trash()

    def _add_to_trash(self, it):
        t = dict(it)
        t["pinned"] = False
        t["pin_time"] = 0
        t["deleted_time"] = time.time()
        self.trash = [x for x in self.trash if x["id"] != t["id"]]
        self.trash.insert(0, t)

    def _trim_trash(self):
        limit = self.cfg["max_trash"]
        dropped = self.trash[limit:]
        del self.trash[limit:]
        for t in dropped:
            self._drop_file_if_unreferenced(t)

    def _referenced(self, item_id):
        return any(it["id"] == item_id for it in self.items) or \
            any(t["id"] == item_id for t in self.trash)

    def _drop_file_if_unreferenced(self, item):
        if item.get("type") == "image" and not self._referenced(item["id"]):
            try:
                os.remove(item["file"])
            except OSError:
                pass
