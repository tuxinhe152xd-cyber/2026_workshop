#!/usr/bin/env python3
"""Step 2b 前置檢查：修剪參數是否齊全且合理，adapter 檔案是否真的存在。

用法：
  python3 validate.py --adapter <path> --minlen 60 --slidingwindow 4:20 \
                      --leading 3 --trailing 3
"""
import argparse
import csv
import re
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--adapter", required=True)
p.add_argument("--illuminaclip", required=True,
               help="ILLUMINACLIP 的數字欄位，例如 2:30:10:2:TRUE")
p.add_argument("--minlen", required=True, type=int)
p.add_argument("--slidingwindow", required=True)
p.add_argument("--leading", required=True, type=int)
p.add_argument("--trailing", required=True, type=int)
p.add_argument("--single-end", action="store_true")
a = p.parse_args()

errors, warnings = [], []

# 1. adapter FASTA 真的存在且看起來像 FASTA
ad = Path(a.adapter)
if not ad.is_file():
    errors.append(
        f"adapter 檔案不存在：{ad}\n"
        f"    可用的檔案："
        + ", ".join(
            f.name
            for f in sorted(Path("/opt/conda/envs/rnaseq-demo/share/trimmomatic/adapters").glob("*.fa"))
        )
    )
elif not ad.read_text(errors="ignore").lstrip().startswith(">"):
    errors.append(f"{ad} 不是 FASTA（第一個字元不是 '>'）")

# 2. SLIDINGWINDOW 格式
if not re.fullmatch(r"\d+:\d+", a.slidingwindow):
    errors.append(f"SLIDINGWINDOW 格式應為 <視窗>:<品質>，例如 4:20，收到的是 {a.slidingwindow!r}")

# 3. ILLUMINACLIP —— keepBothReads 是雙端定序最容易漏掉的那一格
clip = a.illuminaclip.split(":")
if len(clip) not in (3, 5):
    errors.append(
        f"ILLUMINACLIP 的欄位數應為 3 或 5，收到 {len(clip)} 個：{a.illuminaclip!r}\n"
        "    完整格式：<seedMismatches>:<palindromeClip>:<simpleClip>:<minAdapterLength>:<keepBothReads>"
    )
elif not a.single_end:
    if len(clip) == 3:
        errors.append(
            "ILLUMINACLIP 只填了 3 個欄位，第 6 個 keepBothReads 會用預設值 FALSE。\n"
            "    雙端定序時，插入片段比讀長短的 pair 會被判定 R2 多餘而丟掉，\n"
            "    大量 read pair 會從 paired 掉到 unpaired，而且不會有任何錯誤訊息。\n"
            "    請改成 5 個欄位並把最後一格設為 TRUE，例如 2:30:10:2:TRUE"
        )
    elif clip[4].upper() != "TRUE":
        errors.append(
            f"keepBothReads = {clip[4]!r}。雙端定序請設為 TRUE，"
            "否則短插入片段的 R2 會被丟掉（見上面的說明）"
        )

# 4. MINLEN 是否對得上實測讀長
stats = Path("qc/raw/multiqc_data/multiqc_general_stats.txt")
if stats.is_file():
    lens = []
    for r in csv.DictReader(stats.open(), delimiter="\t"):
        for k, v in r.items():
            if "avg_sequence_length" in k and v not in (None, "", "NA"):
                lens.append(float(v))
    if lens:
        read_len = min(lens)
        ratio = a.minlen / read_len
        if ratio < 0.25:
            errors.append(
                f"MINLEN {a.minlen} 只有實測讀長 {read_len:.0f} bp 的 {ratio:.0%}，過鬆。"
                f" 慣用值是 40%（約 {round(read_len * 0.4)}）"
            )
        elif ratio < 0.35 or ratio > 0.55:
            warnings.append(
                f"MINLEN {a.minlen} 是實測讀長 {read_len:.0f} bp 的 {ratio:.0%}，"
                f"偏離慣用的 40%（約 {round(read_len * 0.4)}）。確定的話可以繼續。"
            )
else:
    warnings.append("找不到 Step 1 的 MultiQC 統計檔，無法檢查 MINLEN 是否對得上實測讀長")

# 5. 輸入檔還在
n_raw = len(list(Path("raw").glob("*.fastq.gz"))) if Path("raw").is_dir() else 0
if n_raw == 0:
    errors.append("raw/ 底下沒有 FASTQ")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print("OK")
print(f"  adapter        : {ad}")
print(f"  ILLUMINACLIP   : {a.illuminaclip}")
print(f"  SLIDINGWINDOW  : {a.slidingwindow}")
print(f"  LEADING        : {a.leading}")
print(f"  TRAILING       : {a.trailing}")
print(f"  MINLEN         : {a.minlen}")
print(f"  輸入檔案數     : {n_raw}")
for w in warnings:
    print(f"  WARNING: {w}")
