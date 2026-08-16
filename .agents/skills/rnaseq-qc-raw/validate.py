#!/usr/bin/env python3
"""Step 1 前置檢查：raw/ 裡的 FASTQ 是否齊全、成對、可讀。

通過印 OK 並 exit 0；任何一項不過就印出原因並 exit 1。
"""
import gzip
import re
import sys
from pathlib import Path

RAW = Path("raw")
errors = []

if not RAW.is_dir():
    print(f"ERROR: 找不到 {RAW.resolve()}")
    print("  - 確認目前在 repo 的根目錄（跟 AGENTS.md 同一層）")
    print("  - 資料還沒下載的話，執行：bash scripts/fetch_data.sh")
    sys.exit(1)

files = sorted(RAW.glob("*.fastq.gz"))
if not files:
    errors.append(f"{RAW}/ 底下沒有任何 .fastq.gz")

# 依樣本分組，檢查 R1/R2 成對
samples = {}
for f in files:
    m = re.match(r"^(?P<s>.+)_R(?P<r>[12])\.fastq\.gz$", f.name)
    if not m:
        errors.append(f"{f.name} 檔名不符合 <樣本>_R1.fastq.gz / <樣本>_R2.fastq.gz 的規則")
        continue
    samples.setdefault(m.group("s"), set()).add(m.group("r"))

for s, reads in sorted(samples.items()):
    if reads != {"1", "2"}:
        missing = {"1", "2"} - reads
        errors.append(f"樣本 {s} 缺少 R{','.join(sorted(missing))}")

# gzip 是否完整可讀（只讀開頭，不整檔解壓）
for f in files:
    try:
        with gzip.open(f, "rb") as fh:
            head = fh.readline()
        if not head.startswith(b"@"):
            errors.append(f"{f.name} 第一行不是 '@' 開頭，可能不是 FASTQ")
    except OSError as e:
        errors.append(f"{f.name} 無法讀取（gzip 可能損毀）：{e}")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print("OK")
print(f"  樣本數：{len(samples)}  檔案數：{len(files)}")
for s in sorted(samples):
    print(f"    {s}  R1+R2")
