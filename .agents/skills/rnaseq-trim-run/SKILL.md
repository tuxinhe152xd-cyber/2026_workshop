---
name: rnaseq-trim-run
description: >
  Step 2b — EXECUTE Trimmomatic PE once the parameter values are already known.
  Use ONLY when the user has already supplied concrete parameter values in their
  own message (an adapter filename plus ILLUMINACLIP numbers) and wants those run.
  Contains the PE output ordering and how to read the four numbers in the log.
  Do NOT use when the user is asking which parameters to choose, what values to
  use, or to decide/recommend settings — that is a different concern and this
  skill has nothing to say about it.
---

# Step 2b — 執行修剪（Trimmomatic）

## 這一步在做什麼

**刪掉品質不佳的序列。** 把上一步決定好的參數真的套下去。

## 執行前必須驗證

```bash
python3 .agents/skills/rnaseq-trim-run/validate.py \
  --adapter <adapter FASTA 的完整路徑> \
  --illuminaclip <使用者給的 ILLUMINACLIP 數字欄位> \
  --minlen <MINLEN> --slidingwindow <SLIDINGWINDOW> \
  --leading <LEADING> --trailing <TRAILING>
```

參數值由使用者在訊息裡給定。**這一步不決定參數，只執行。**

## 指令

每個樣本一條，四個樣本共四條：

```bash
mkdir -p trim
trimmomatic PE -threads 2 \
  raw/<樣本>_R1.fastq.gz  raw/<樣本>_R2.fastq.gz \
  trim/<樣本>_P_R1.fastq.gz  trim/<樣本>_U_R1.fastq.gz \
  trim/<樣本>_P_R2.fastq.gz  trim/<樣本>_U_R2.fastq.gz \
  ILLUMINACLIP:<使用者給的 adapter 與欄位> \
  LEADING:<L> TRAILING:<T> SLIDINGWINDOW:<W> MINLEN:<M> \
  2>&1 | tee trim/<樣本>.trimmomatic.log
```

### 四個輸出檔的意思

| 檔名 | 內容 | 下游要用嗎 |
|---|---|---|
| `_P_R1` / `_P_R2` | **P = paired**，R1 和 R2 兩邊都通過門檻 | **要**，kallisto 只吃這兩個 |
| `_U_R1` / `_U_R2` | U = unpaired，另一端被剪掉了，只剩單邊 | 不要，但**不能不寫**，Trimmomatic PE 一定要六個輸出路徑 |

**輸出順序是固定的：forward-paired、forward-unpaired、reverse-paired、reverse-unpaired。**
寫錯順序不會報錯，只會讓下游拿到 unpaired 檔案當成 paired 用。

## 這個領域的陷阱

- **步驟順序就是參數順序。** Trimmomatic 是照你寫的順序執行的。
  `ILLUMINACLIP` 一定要放在最前面 —— 先剪掉 adapter，再看品質。
  如果 `MINLEN` 放在 `ILLUMINACLIP` 前面，會先用未剪 adapter 的長度去篩，
  等於這道篩子沒作用。
- **log 一定要留，而且要看兩行不是一行。**

## 驗收

```bash
ls trim/*_P_R1.fastq.gz trim/*_P_R2.fastq.gz | wc -l    # 應為 8
grep "Input Read Pairs" trim/*.trimmomatic.log
```

log 的那一行有四個數字，**兩個都要看**：

| 欄位 | 意思 | 判讀 |
|---|---|---|
| `Both Surviving` | R1 R2 都留下的比例 | 下游真正能用的量 |
| **`Forward Only Surviving`** | **只剩 R1 的比例** | **超過 20% → `keepBothReads` 沒開** |
| `Reverse Only Surviving` | 只剩 R2 | 通常很小 |
| `Dropped` | 兩邊都沒了 | 通常很小 |

回報給使用者時**四個數字都要列出來**，並判斷：

- `Forward Only` 很高 → 不是品質問題，是規則把 R2 丟掉了，回頭改 `keepBothReads`
- `Dropped` 很高 → 才是品質或 MINLEN 的問題
