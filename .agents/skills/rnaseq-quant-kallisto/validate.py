#!/usr/bin/env python3
"""Step 4 前置檢查：kallisto index 與修剪後的 paired 輸入是否就緒。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _find_paired import find_paired

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

# 2. 輸入 —— 不假設命名，自己認
pairs = find_paired(TRIM)
samples = sorted(pairs)
if not samples:
    errors.append(
        f"{TRIM}/ 底下找不到成對的 paired FASTQ —— Step 2b 還沒跑完，"
        "或檔名裡沒有 paired 標記（_P_ / .paired）"
    )

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
    print(f"    {s:<16} {pairs[s]['1'].name}  /  {pairs[s]['2'].name}")
print("  提示：這是 chr20 專用 index，比對率的預期是 88–95%，不是 95% 以上。")
