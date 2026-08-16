#!/usr/bin/env python3
"""Step 4 前置檢查：kallisto index 與修剪後的 paired 輸入是否就緒。"""
import re
import sys
from pathlib import Path

REF = Path("ref")
TRIM = Path("trim")
errors = []

# 1. index
idx = sorted(REF.glob("*.idx")) if REF.is_dir() else []
if not idx:
    errors.append(
        f"在 {REF}/ 找不到 kallisto index（*.idx）。"
        " 執行 bash scripts/fetch_data.sh 把資料抓下來"
    )
else:
    size_mb = idx[0].stat().st_size / 1e6
    if size_mb < 10:
        errors.append(
            f"{idx[0].name} 只有 {size_mb:.1f} MB，chr20 index 應該是 80 MB 上下。"
            " 檔案可能沒下載完整"
        )

# 2. 輸入
paired = sorted(TRIM.glob("*_P_R?.fastq.gz")) if TRIM.is_dir() else []
samples = sorted({re.sub(r"_P_R[12]\.fastq\.gz$", "", f.name) for f in paired})
for s in samples:
    for r in ("1", "2"):
        if not (TRIM / f"{s}_P_R{r}.fastq.gz").is_file():
            errors.append(f"樣本 {s} 缺少 _P_R{r}")
if not samples:
    errors.append("trim/ 底下沒有 *_P_R?.fastq.gz —— Step 2b 還沒跑完")

# 3. 輸出目錄可寫
try:
    Path("quant").mkdir(exist_ok=True)
    probe = Path("quant/.write_probe")
    probe.write_text("x")
    probe.unlink()
except OSError as e:
    errors.append(f"quant/ 無法寫入：{e}")

if errors:
    print("VALIDATION FAILED")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print("OK")
print(f"  index          : {idx[0]}  ({idx[0].stat().st_size / 1e6:.0f} MB)")
print(f"  樣本數         : {len(samples)}")
for s in samples:
    print(f"    {s}")
print("  提示：這是 chr20 專用 index，比對率的預期是 88–95%，不是 95% 以上。")
