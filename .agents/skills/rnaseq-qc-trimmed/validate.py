#!/usr/bin/env python3
"""Step 3 前置檢查：修剪後的 paired 檔案是否齊全，並印出各樣本存活率。"""
import gzip
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _find_paired import find_paired

TRIM = Path("trim")
errors = []

if not TRIM.is_dir():
    print("VALIDATION FAILED")
    print("  - 找不到 trim/ —— Step 2b（rnaseq-trim-run）還沒跑")
    sys.exit(1)

pairs = find_paired(TRIM)
samples = sorted(pairs)
paired = [f for v in pairs.values() for f in v.values()]

for s in samples:
    for r in ("1", "2"):
        f = pairs[s][r]
        if f.stat().st_size == 0:
            errors.append(f"{f} 是空檔案")

if not paired:
    errors.append(
        "trim/ 底下找不到成對的 paired FASTQ —— Step 2b 還沒跑完，"
        "或檔名裡沒有 paired 標記（_P_ / .paired）"
    )

# 空的 gz 也可能有幾十 bytes，實際讀一行確認
for f in paired:
    if f.is_file() and f.stat().st_size > 0:
        try:
            with gzip.open(f, "rb") as fh:
                if not fh.readline().startswith(b"@"):
                    errors.append(f"{f.name} 內容不像 FASTQ")
        except OSError as e:
            errors.append(f"{f.name} 無法讀取：{e}")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print("OK")
print(f"  樣本數：{len(samples)}  paired 檔案數：{len(paired)}")

# 從 log 撈四個數字。Both Surviving 低不一定是品質問題 ——
# 要看 Forward Only 才知道是「被丟掉」還是「被剪掉」。
pat = re.compile(
    r"Input Read Pairs:\s*(\d+)\s*"
    r"Both Surviving:\s*(\d+)\s*\(([\d.]+)%\)\s*"
    r"Forward Only Surviving:\s*(\d+)\s*\(([\d.]+)%\)\s*"
    r"Reverse Only Surviving:\s*(\d+)\s*\(([\d.]+)%\)\s*"
    r"Dropped:\s*(\d+)\s*\(([\d.]+)%\)"
)
logs = sorted(TRIM.glob("*.trimmomatic.log"))
if logs:
    print()
    print(f"  {'樣本':<22}{'輸入':>10}{'both':>8}{'fwd only':>10}{'dropped':>9}")
    notes = []
    for lg in logs:
        m = pat.search(lg.read_text(errors="ignore"))
        if not m:
            continue
        name = lg.name.replace(".trimmomatic.log", "")
        both, fwd, drop = float(m.group(3)), float(m.group(5)), float(m.group(9))
        print(f"  {name:<22}{int(m.group(1)):>10,}{both:>7.1f}%{fwd:>9.1f}%{drop:>8.1f}%")
        if fwd > 20:
            notes.append(
                f"{name}：Forward Only {fwd:.1f}% 偏高。這不是品質問題 —— "
                "是 ILLUMINACLIP 的 keepBothReads 沒開，短插入片段的 R2 被規則丟掉了。"
                "下游只吃 paired，等於直接損失這些 fragment。"
            )
        if drop > 10:
            notes.append(f"{name}：Dropped {drop:.1f}% 偏高，回頭看 MINLEN 或品質門檻")
    for n in notes:
        print(f"    WARNING: {n}")
else:
    print("  （找不到 trimmomatic log，無法檢查存活率）")
