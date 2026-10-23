"""小工具函数。"""

import sys
import time


def log(msg):
    sys.stderr.write(f"[easy-copy] {msg}\n")


def fmt_time(ts):
    def day(x):
        return x.tm_year, x.tm_yday
    t = time.localtime(ts)
    if day(t) == day(time.localtime()):
        return time.strftime("%H:%M", t)
    if day(t) == day(time.localtime(time.time() - 86400)):
        return time.strftime("昨天 %H:%M", t)
    return time.strftime("%m-%d %H:%M", t)
