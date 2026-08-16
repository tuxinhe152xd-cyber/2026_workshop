#!/usr/bin/env python3
"""用 PyDESeq2 做差異表現分析，輸出結果表與火山圖。

取代傳統流程裡的 R DESeq2。統計模型是一樣的（負二項式 GLM + Wald test），
只是實作換成 Python。
"""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

ap = argparse.ArgumentParser()
ap.add_argument("--counts", default="PyDESeq2/counts.tsv")
ap.add_argument("--metadata", default="PyDESeq2/metadata.csv")
ap.add_argument("--design", default="~patient + group",
                help="設計公式。配對設計用 '~patient + group'；不配對用 '~group'")
ap.add_argument("--contrast", nargs=3, default=["group", "T", "N"],
                metavar=("因子", "實驗組", "對照組"))
ap.add_argument("--min-total-count", type=int, default=10)
ap.add_argument("--outdir", default="PyDESeq2/output_files")
ap.add_argument("--n-cpus", type=int, default=2)
a = ap.parse_args()

out = Path(a.outdir)
out.mkdir(parents=True, exist_ok=True)

counts = pd.read_csv(a.counts, sep="\t", index_col=0)
meta = pd.read_csv(a.metadata, index_col=0)

# 樣本必須完全對得上，而且順序要一致
missing = [s for s in counts.columns if s not in meta.index]
extra = [s for s in meta.index if s not in counts.columns]
if missing or extra:
    print("ERROR: counts 與 metadata 的樣本對不起來", file=sys.stderr)
    if missing:
        print(f"  counts 有但 metadata 沒有：{missing}", file=sys.stderr)
    if extra:
        print(f"  metadata 有但 counts 沒有：{extra}", file=sys.stderr)
    sys.exit(1)
meta = meta.loc[list(counts.columns)]

# 過濾掉幾乎沒有讀序的基因 —— 留著只會拖慢並增加多重檢定的負擔
keep = counts.sum(axis=1) >= a.min_total_count
filtered = counts[keep]
print(f"基因過濾：{counts.shape[0]:,} → {filtered.shape[0]:,}"
      f"（總計數 >= {a.min_total_count}）")
print(f"設計公式：{a.design}")
print(f"比較    ：{a.contrast[0]}  {a.contrast[1]} vs {a.contrast[2]}")
print(meta.to_string())
print()

dds = DeseqDataSet(
    counts=filtered.T,          # PyDESeq2 要的是 樣本 × 基因
    metadata=meta,
    design=a.design,
    refit_cooks=True,
    n_cpus=a.n_cpus,
)
dds.deseq2()

ds = DeseqStats(dds, contrast=list(a.contrast), n_cpus=a.n_cpus)
ds.summary()
res = ds.results_df.sort_values("padj")

# 併上基因代號 —— ENSG 看不出是什麼基因，代號才查得到文獻
names_f = Path(a.counts).parent / "gene_names.tsv"
if names_f.is_file():
    nm = pd.read_csv(names_f, sep="\t", index_col=0)["gene_name"]
    res.insert(0, "gene_name", res.index.map(nm))

res.to_csv(out / "deseq2_results.csv")

sig = res[(res.padj < 0.05) & (res.log2FoldChange.abs() > 1)]
sig.to_csv(out / "deseq2_significant.csv")

# 未校正的門檻也留一份 —— 樣本數小的時候，多重檢定校正後常常只剩個位數，
# 這一份是「值得後續驗證的候選清單」，不是結論。
loose = res[(res.pvalue < 0.05) & (res.log2FoldChange.abs() > 1)]
loose.to_csv(out / "deseq2_candidates_unadjusted.csv")

# ── 火山圖 ────────────────────────────────────────────────────────────────
d = res.dropna(subset=["pvalue", "log2FoldChange"]).copy()
d["-log10p"] = -np.log10(d["pvalue"].clip(lower=1e-300))
up = (d.log2FoldChange > 1) & (d.padj < 0.05)
dn = (d.log2FoldChange < -1) & (d.padj < 0.05)

plt.figure(figsize=(6, 5))
plt.scatter(d.log2FoldChange[~(up | dn)], d["-log10p"][~(up | dn)],
            s=4, c="lightgrey", label="ns")
plt.scatter(d.log2FoldChange[up], d["-log10p"][up], s=6, c="tab:red",
            label=f"up ({up.sum()})")
plt.scatter(d.log2FoldChange[dn], d["-log10p"][dn], s=6, c="tab:blue",
            label=f"down ({dn.sum()})")
# 顏色是用 padj 判的，所以水平線也要畫在「padj=0.05 對應到的 p 值」，
# 不能畫在未校正的 0.05 —— 否則線上面會有一堆灰點，看起來像畫錯。
passing = d.pvalue[d.padj < 0.05]
if len(passing):
    plt.axhline(-np.log10(passing.max()), ls="--", lw=0.8, c="grey")
    thr_label = "dashed line = padj 0.05"
else:
    thr_label = "no gene reaches padj 0.05"
plt.axvline(1, ls="--", lw=0.8, c="grey")
plt.axvline(-1, ls="--", lw=0.8, c="grey")

# 標出 p 值最小的幾個，讓圖上看得到基因名。
# 只標有代號的（沒代號的一串 ENSG 很長，會壓到旁邊的標籤）。
if "gene_name" in d.columns:
    named = d[d.gene_name.notna() & ~d.gene_name.astype(str).str.startswith("ENSG")]
    for _, row in named.nsmallest(5, "pvalue").iterrows():
        plt.annotate(row.gene_name, (row.log2FoldChange, row["-log10p"]),
                     fontsize=7, xytext=(4, 3), textcoords="offset points")

plt.xlabel("log2 fold change")
plt.ylabel("-log10 unadjusted p-value")
plt.title(f"{a.contrast[1]} vs {a.contrast[2]}  (colour by padj; {thr_label})", fontsize=10)
plt.legend(markerscale=2, fontsize=8)
plt.tight_layout()
plt.savefig(out / "volcano.png", dpi=150)

print()
print(f"已寫出 {out}/deseq2_results.csv                （全部 {len(res):,} 個基因）")
print(f"已寫出 {out}/deseq2_significant.csv            （padj<0.05 且 |log2FC|>1：{len(sig):,} 個）")
print(f"已寫出 {out}/deseq2_candidates_unadjusted.csv  （未校正 p<0.05 且 |log2FC|>1：{len(loose):,} 個）")
print(f"已寫出 {out}/volcano.png")
print()
print(f"padj 最小的前 10 個基因（正值 = {a.contrast[1]} 高於 {a.contrast[2]}）：")
print(res.head(10).to_string())
print()
print(f"多重檢定校正前 {len(loose)} 個 → 校正後 {len(sig)} 個。")
print("差距這麼大是樣本數小的必然結果。校正後的那幾個才有統計依據，")
print("未校正的那份只能當候選清單，不能當結論。")
