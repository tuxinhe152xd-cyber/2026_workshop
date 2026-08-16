#!/usr/bin/env python3
"""把 kallisto 的轉錄本層級輸出聚合成基因層級的 counts 矩陣。

這支腳本取代了傳統流程裡的 R + tximport。可以這樣做的原因是：
GENCODE 建的 kallisto index，abundance.tsv 的 target_id 本身就帶著基因 ID ——

    ENST00000832824.1|ENSG00000290825.2|-|-|DDX11L16-260|DDX11L16|1379|lncRNA|
    ^ 轉錄本 ENST      ^ 基因 ENSG                          ^ 基因代號

用 '|' 切開取第 2 欄就是 ENSG，第 6 欄是基因代號，不需要另外做對照表。

輸出：
  PyDESeq2/counts.tsv      列 = 基因、欄 = 樣本、值 = 整數 counts
  PyDESeq2/gene_names.tsv  ENSG → 基因代號（下一步會併進結果表）
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--quant-dir", default="quant")
ap.add_argument("--out", default="PyDESeq2/counts.tsv")
ap.add_argument("--strip-version", action="store_true",
                help="把 ENSG00000290825.2 的版本號 .2 去掉")
a = ap.parse_args()

quant = Path(a.quant_dir)
tsvs = sorted(quant.glob("*/abundance.tsv"))
if not tsvs:
    print(f"ERROR: 在 {quant}/*/abundance.tsv 找不到任何檔案", file=sys.stderr)
    sys.exit(1)

cols = {}
names = {}
for t in tsvs:
    sample = t.parent.name
    df = pd.read_csv(t, sep="\t", usecols=["target_id", "est_counts"])

    parts = df["target_id"].str.split("|", expand=True)
    if parts.shape[1] < 2 or parts[1].isna().all():
        print(
            f"ERROR: {t} 的 target_id 沒有 '|' 分隔的基因 ID。\n"
            f"       第一列長這樣：{df['target_id'].iloc[0]}\n"
            f"       這代表 kallisto index 不是用 GENCODE 的 transcripts FASTA 建的，"
            f"需要另外準備 transcript-to-gene 對照表。",
            file=sys.stderr,
        )
        sys.exit(1)

    df["gene"] = parts[1]
    if a.strip_version:
        df["gene"] = df["gene"].str.replace(r"\.\d+$", "", regex=True)

    # 第 6 欄是基因代號（例如 HNF4A）。有代號的話留一份對照表，
    # 讓最後的結果表看得懂是哪個基因，而不是一串 ENSG。
    if parts.shape[1] > 5 and not names:
        sym = parts[5]
        names = dict(zip(df["gene"], sym.where(sym.notna() & (sym != "-"), df["gene"])))

    cols[sample] = df.groupby("gene")["est_counts"].sum()
    print(f"  {sample:<22} 轉錄本 {len(df):>7,} → 基因 {cols[sample].shape[0]:>7,}")

counts = pd.DataFrame(cols).fillna(0)

# DESeq2 的模型要的是整數計數。kallisto 的 est_counts 是期望值（小數），四捨五入。
counts = counts.round().astype(int)
counts.index.name = "gene_id"

out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
counts.to_csv(out, sep="\t")

if names:
    nm = pd.Series(names, name="gene_name").reindex(counts.index)
    nm.index.name = "gene_id"
    nm.to_csv(out.parent / "gene_names.tsv", sep="\t")

nz = (counts.sum(axis=1) > 0).sum()
print()
print(f"已寫出 {out}")
if names:
    print(f"已寫出 {out.parent / 'gene_names.tsv'}（ENSG → 基因代號）")
print(f"  基因數：{counts.shape[0]:,}（其中 {nz:,} 個至少有一條讀序）")
print(f"  樣本  ：{', '.join(counts.columns)}")
print()
print("注意：這裡是直接把轉錄本的 est_counts 相加。嚴謹做法（R 的 tximport）還會")
print("      帶入有效長度的 offset 修正。課堂用的簡化版，方向不會變，數值會略有差異。")
