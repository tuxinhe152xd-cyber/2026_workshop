---
name: rnaseq-quant-kallisto
description: >
  Step 4 of the RNA-seq pipeline — quantify transcript abundance with kallisto
  pseudoalignment against the prebuilt chr20 GENCODE index in ref/. Use when the user
  asks to run kallisto, to quantify, to do pseudoalignment, to 定量, or 比對. Contains
  what pseudoalignment does and does not produce, how to read run_info.json, and what a
  low pseudoalignment rate actually means.
---

# Step 4 — 定量（kallisto pseudoalignment）

## 這一步在做什麼

**比對參考資料庫，看誰是誰，然後算一算表現多少。** 傳統做法是把每條讀序在
基因體上找出精確位置（HISAT2 → BAM → featureCounts）。kallisto 跳過這件事。

## 執行前必須驗證

```bash
python3 .agents/skills/rnaseq-quant-kallisto/validate.py
```

## 指令

四個樣本各跑一次：

**先確認上一步實際產出的檔名** —— 不要假設，`validate.py` 會把配對列出來：

```bash
python3 .agents/skills/rnaseq-quant-kallisto/validate.py
```

它會印出每個樣本對應的兩個檔案。然後每個樣本跑一次：

```bash
mkdir -p quant/<樣本>
kallisto quant -t 2 \
  -i ref/gencode.v49.chr20.idx \
  -o quant/<樣本> \
  <該樣本的 R1 paired 檔> <該樣本的 R2 paired 檔> \
  2>&1 | tee quant/<樣本>/kallisto.log
```

> **`quant/<樣本>` 的資料夾名要跟 `PyDESeq2/metadata.csv` 的樣本名一致**
> （`11N_chr20`、`11T_chr20`、`13N_chr20`、`13T_chr20`），
> 否則 Step 5 會說「樣本對不起來」。

每個樣本約 3–5 秒。四個一起也不到 20 秒。

## pseudoalignment 是什麼

它**不問「這條讀序落在基因體哪個座標」**，只問**「這條讀序跟哪些轉錄本相容」**。

| | 傳統比對（HISAT2） | pseudoalignment（kallisto） |
|---|---|---|
| 比對對象 | 基因體 genome | 轉錄體 transcriptome |
| 產出 | BAM（每條讀序的座標） | 相容集合 + 定量 |
| 速度 | 慢 | 快一到兩個數量級 |
| 能不能看 IGV | 能 | **不能，沒有 BAM** |
| 能不能找新的剪接 | 能 | **不能，index 裡沒有的轉錄本看不到** |

**代價要講清楚：換到 kallisto 就放棄了「看讀序長在哪裡」的能力。**
這對差異表現分析沒差，但如果之後要找融合基因或新剪接，就得回頭跑真正的比對。

## 這顆 index 是 chr20 專用的

`ref/gencode.v49.chr20.idx` 只含 **chr20 的 7,269 條轉錄本**（82 MB），
不是完整的人類轉錄體（533,740 條、4.3 GB）。

因為這批讀序本來就只取自 chr20，用子集 index 是**刻意的取捨**：

| | chr20 index | 全轉錄體 index |
|---|---|---|
| 定量一個樣本 | 約 4 秒 | 約 54 秒 |
| 比對率 | **約 90%** | 約 95% |

**少掉的那 5% 是在其他染色體的轉錄本上比對得更好的讀序**（旁系同源基因、
多基因家族）。用子集 index 時它們找不到更好的歸屬，就落在 chr20 的近似轉錄本上或不比對。

**所以這裡的「正常值」是 90% 上下，不是 95%。** 這是 index 選擇造成的，不是資料問題。

## 輸出

| 檔案 | 內容 |
|---|---|
| `quant/<樣本>/abundance.tsv` | **主要輸出。** 每個轉錄本一列：`target_id`、`length`、`eff_length`、`est_counts`、`tpm` |
| `quant/<樣本>/abundance.h5` | 同樣的東西的二進位版 |
| `quant/<樣本>/run_info.json` | 這次執行的統計，**一定要看** |

### `run_info.json` 要看的兩個數字

```bash
cat quant/<樣本>/run_info.json
```

- `n_processed` —— 處理了幾對讀序，應該對得上修剪後的存活數
- `p_pseudoaligned` —— **比對率。這顆 chr20 index 的預期是 88–95%。**

`p_pseudoaligned` 掉到 50% 以下時，**幾乎不會是資料的問題，而是 index 的問題**：
物種不對、版本跟資料差太多、或者根本指到別的 index。
這種情況不要調參數，要回頭確認 index。

## 這個領域的陷阱

- **只能餵 paired 檔案，不要餵 unpaired。** 少給一個檔案時 kallisto 會轉成 single-end 模式，
  結果完全不同，而且不會有明顯的錯誤。
- **`est_counts` 和 `tpm` 不能混用。** 下一步的 DESeq2 需要的是 **`est_counts`**
  （未正規化的計數）。TPM 已經做過長度與深度正規化，餵進 DESeq2 會讓統計模型失效。
- 輸出是**轉錄本層級**（ENST），不是基因層級。聚合到基因是下一步的事。

## 驗收

```bash
ls quant/*/abundance.tsv | wc -l     # 應為 4
grep p_pseudoaligned quant/*/run_info.json
```

回報時要列出每個樣本的 `n_processed` 與 `p_pseudoaligned`，並判斷是否落在合理範圍。
