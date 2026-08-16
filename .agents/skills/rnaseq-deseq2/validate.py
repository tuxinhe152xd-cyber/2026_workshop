#!/usr/bin/env python3
"""Step 5 前置檢查：kallisto 輸出、metadata、以及兩者的樣本名是否對得上。"""
import csv
import json
import sys
from pathlib import Path

QUANT = Path("quant")
META = Path("PyDESeq2/metadata.csv")
errors, warnings = [], []

# 1. kallisto 輸出
tsvs = sorted(QUANT.glob("*/abundance.tsv")) if QUANT.is_dir() else []
quant_samples = [t.parent.name for t in tsvs]
if not tsvs:
    errors.append("quant/*/abundance.tsv 一個都沒有 —— Step 4 還沒跑完")

for t in tsvs:
    if t.stat().st_size == 0:
        errors.append(f"{t} 是空檔案")
    else:
        with t.open() as fh:
            fh.readline()
            first = fh.readline()
        if first and "|" not in first.split("\t")[0]:
            warnings.append(
                f"{t.parent.name} 的 target_id 沒有 '|' 分隔的基因 ID，"
                "build_counts.py 會失敗（index 不是用 GENCODE FASTA 建的）"
            )

# 2. 比對率
for t in tsvs:
    ri = t.parent / "run_info.json"
    if ri.is_file():
        try:
            p = json.loads(ri.read_text()).get("p_pseudoaligned")
            if p is not None and p < 50:
                warnings.append(
                    f"{t.parent.name} 的 p_pseudoaligned 只有 {p}%，"
                    "index 可能不對，這樣算出來的差異表現不可信"
                )
        except (json.JSONDecodeError, OSError):
            pass

# 3. metadata
if not META.is_file():
    errors.append(f"找不到 {META}")
else:
    rows = list(csv.DictReader(META.open()))
    if not rows:
        errors.append(f"{META} 是空的")
    else:
        first_col = list(rows[0].keys())[0]
        meta_samples = [r[first_col] for r in rows]

        # 3a. 樣本名對不對得上 —— 這是最常見的卡關點
        only_quant = [s for s in quant_samples if s not in meta_samples]
        only_meta = [s for s in meta_samples if s not in quant_samples]
        if only_quant or only_meta:
            errors.append(
                "quant/ 的資料夾名稱與 metadata 的樣本名對不起來：\n"
                f"    quant/ 有 metadata 沒有：{only_quant}\n"
                f"    metadata 有 quant/ 沒有：{only_meta}\n"
                "    兩邊的名稱必須完全一致"
            )

        # 3b. 分組欄位與每組樣本數
        if "group" not in rows[0]:
            errors.append(f"{META} 沒有 group 欄位")
        else:
            counts = {}
            for r in rows:
                counts[r["group"]] = counts.get(r["group"], 0) + 1
            for g, n in counts.items():
                if n < 2:
                    errors.append(f"組別 {g} 只有 {n} 個樣本，DESeq2 至少需要 2 個")
            if len(counts) < 2:
                errors.append(f"只有 {len(counts)} 個組別，無法做比較")
            warnings.append(
                "各組樣本數："
                + "、".join(f"{g}={n}" for g, n in sorted(counts.items()))
                + " —— 樣本數這麼小，檢定力很低，結論要保守"
            )

        if "patient" not in rows[0]:
            warnings.append(
                "metadata 沒有 patient 欄位，無法用配對設計 ~patient + group，"
                "要改用 --design '~group'"
            )

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print("OK")
print(f"  kallisto 樣本  : {len(quant_samples)}  ({', '.join(quant_samples)})")
print(f"  metadata       : {META}")
for w in warnings:
    print(f"  WARNING: {w}")
