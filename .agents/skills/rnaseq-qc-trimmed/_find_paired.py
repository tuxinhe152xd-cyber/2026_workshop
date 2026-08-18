"""共用：找出修剪後的 paired FASTQ，不管上一步用什麼命名。

模型每次跑 Trimmomatic 都可能給不同的檔名
（`_P_R1.fastq.gz`、`_R1.paired.fq.gz`、`_1.paired.fastq.gz`…）。
與其要求它記住一種命名，不如讓下游自己認得出來。

樣本名用「R1 與 R2 檔名的共同前綴」推出來 —— 比正規表達式挖字穩。
"""
import os
import re
from pathlib import Path

_UNPAIRED = re.compile(r'(^|[._-])(un|u)[._-]?paired|(^|[._-])U[._-]?R?[12]([._-]|$)')
_PAIRED = re.compile(r'(^|[._-])(P|paired)([._-]|$)', re.I)
# read 標記：前後都要有分隔符或副檔名，避免咬到 11N / chr20 裡的數字
_READ = re.compile(r'[._-]R?([12])(?=[._-])')


def _read_of(name):
    hits = _READ.findall(name)
    return hits[-1] if hits else None      # 取最後一個，避開樣本名裡的數字


def find_paired(trim_dir="trim"):
    """回傳 {樣本名: {'1': Path, '2': Path}}，只含兩端都在的樣本。"""
    d = Path(trim_dir)
    if not d.is_dir():
        return {}

    buckets = {}
    for f in sorted(d.glob("*.gz")):
        n = f.name
        if _UNPAIRED.search(n) or not _PAIRED.search(n):
            continue
        r = _read_of(n)
        if r is None:
            continue
        # 把 read 標記換成佔位符，同一組配對會得到相同的鍵
        key = _READ.sub(lambda m: '[R]', n, count=0)
        buckets.setdefault(key, {})[r] = f

    out = {}
    for pair in buckets.values():
        if set(pair) != {'1', '2'}:
            continue
        sample = os.path.commonprefix([pair['1'].name, pair['2'].name]).rstrip('._-Rr')
        # 去掉尾端的 paired 標記（_P、.paired…），只留樣本名
        sample = re.sub(r'[._-]?(P|paired)$', '', sample, flags=re.I).rstrip('._-')
        if sample:
            out[sample] = pair
    return out
