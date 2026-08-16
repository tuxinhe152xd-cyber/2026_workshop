#!/usr/bin/env python3
"""Step 2a 前置檢查：確認 Step 1 的 MultiQC 統計檔存在，並印出實測讀長。

這支腳本只負責「把事實讀出來」。要用什麼參數是模型的判斷，不在這裡決定。
"""
import csv
import sys
from pathlib import Path

STATS = Path("qc/raw/multiqc_data/multiqc_general_stats.txt")

if not STATS.is_file():
    # MultiQC 版本之間檔名偶有差異，找一下同目錄下的替代檔
    alt = sorted(Path("qc/raw/multiqc_data").glob("*general_stats*")) \
        if Path("qc/raw/multiqc_data").is_dir() else []
    if alt:
        STATS = alt[0]
    else:
        print("VALIDATION FAILED")
        print(f"  - 找不到 {STATS}")
        print("  - Step 1（rnaseq-qc-raw）還沒跑完，或 MultiQC 沒有成功產生報告")
        sys.exit(1)

rows = list(csv.DictReader(STATS.open(), delimiter="\t"))
if not rows:
    print("VALIDATION FAILED")
    print(f"  - {STATS} 是空的")
    sys.exit(1)


def col(row, needle):
    for k, v in row.items():
        if needle in k and v not in (None, "", "NA"):
            return v
    return None


lengths, samples = [], []
for r in rows:
    name = r.get("Sample") or next(iter(r.values()))
    ln = col(r, "avg_sequence_length")
    if ln is None:
        continue
    lengths.append(float(ln))
    samples.append((name, float(ln), col(r, "total_sequences"), col(r, "percent_gc")))

if not lengths:
    print("VALIDATION FAILED")
    print(f"  - {STATS} 裡沒有 avg_sequence_length 欄位")
    sys.exit(1)

print("OK")
print(f"  來源：{STATS}")
print()
print(f"  {'樣本':<22}{'實測讀長 (bp)':>14}{'reads (M)':>12}{'%GC':>7}")
for name, ln, tot, gc in samples:
    tot_s = f"{float(tot):.3f}" if tot else "-"
    gc_s = f"{float(gc):.0f}" if gc else "-"
    print(f"  {name:<22}{ln:>14.1f}{tot_s:>12}{gc_s:>7}")

lo, hi = min(lengths), max(lengths)
print()
if lo == hi:
    print(f"  >>> 實測 avg_sequence_length = {lo:.1f} bp（{len(lengths)} 個檔案一致）")
else:
    print(f"  >>> 實測 avg_sequence_length = {lo:.1f} – {hi:.1f} bp（不一致，MINLEN 用最小值算）")
print("  >>> MINLEN 請用上面這個數字計算，不要用記憶中的預設讀長。")
