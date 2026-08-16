---
name: rnaseq-qc-raw
description: >
  Step 1 of the RNA-seq pipeline — run FastQC and MultiQC on the raw FASTQ files in
  raw/ and interpret the report. Use when the user asks to check sequencing quality,
  run FastQC, run MultiQC, look at the raw data quality, or asks "資料品質如何".
  Contains the RNA-seq-specific reading of FastQC modules: which FAIL flags are
  expected in RNA-seq and must NOT be acted on, and which one genuinely needs action.
---

# Step 1 — 原始資料品管（FastQC + MultiQC）

## 這一步在做什麼

**看看定序品質。** 拿到 FASTQ 之後，先確認資料本身能不能用，以及需不需要修剪。

## 執行前必須驗證

```bash
python3 .agents/skills/rnaseq-qc-raw/validate.py
```

失敗就停下來，把錯誤原文告訴使用者。不要自己想辦法繞過。

## 指令

```bash
mkdir -p qc/raw
fastqc -o qc/raw -f fastq -t 2 raw/*.fastq.gz
multiqc -o qc/raw --force qc/raw
```

- `-t 2` —— Codespaces 免費機型是 2 核
- `--force` —— 允許覆蓋前一次的報告

產出：
- `qc/raw/multiqc_report.html` —— 給人看的報告
- `qc/raw/multiqc_data/multiqc_general_stats.txt` —— 給程式讀的數字，**下一步會用到**

## 這個領域的陷阱

FastQC 是為「基因體定序」設計的。用在 RNA-seq 上，**有三個模組幾乎一定會亮
FAIL，其中兩個是正常現象，照著處理反而會毀掉資料**。

| 模組 | RNA-seq 的預期 | 該怎麼辦 |
|---|---|---|
| **Per Base Sequence Content** | **FAIL 是正常的** | **不處理。** 建庫時用 random hexamer priming，前 10–13 個鹼基本來就有系統性偏差。這是方法本身造成的，不是資料壞掉 |
| **Sequence Duplication Levels** | **FAIL 是正常的**（常見 50–80%） | **不處理，尤其不要去重。** 高表現量的基因本來就會被讀到很多次 —— 那是**訊號**，不是 PCR 假重複。去重會把真正的表現量差異刪掉 |
| **Adapter Content** | FAIL 需要處理 | **這個才要動作。** 進到下一步 `rnaseq-trim-params` |
| Per Sequence GC Content | WARN／FAIL 都可能 | 只取單一染色體的子集時分布會偏掉，屬預期 |
| Overrepresented Sequences | WARN 常見 | 通常是高表現轉錄本。看一下是什麼即可，不用處理 |
| Per Base Sequence Quality | 應該 PASS | 真的 FAIL 才是品質問題 |
| Per Base N Content / Length Distribution | 應該 PASS | 真的 FAIL 才是品質問題 |

**報告解讀時，「有幾個 FAIL」不是重點，「哪些 FAIL 需要動作」才是。**
不要因為 duplication 71% 就建議去重複序列 —— 在 RNA-seq 這是錯的。

## 驗收

```bash
ls qc/raw/*_fastqc.zip | wc -l          # 應為 8
ls -l qc/raw/multiqc_report.html
ls -l qc/raw/multiqc_data/multiqc_general_stats.txt
```

三項都通過才算完成。回報給使用者時要包含：

1. 8 個檔案的讀長與 read 數
2. 哪些模組 FAIL、哪些是 RNA-seq 的正常現象
3. **只有一件事需要動作**：adapter 汙染 → 下一步決定修剪參數
