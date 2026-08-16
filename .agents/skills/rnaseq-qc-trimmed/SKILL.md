---
name: rnaseq-qc-trimmed
description: >
  Step 3 of the RNA-seq pipeline — re-run FastQC and MultiQC on the trimmed paired
  reads and compare against the raw report. Use when the user asks to check quality
  after trimming, to run QC again, or asks 修剪後有沒有改善. Contains which FastQC
  modules are expected to improve after trimming and which will not change at all,
  so an unchanged module is not misread as a failed trim.
---

# Step 3 — 修剪後品管

## 這一步在做什麼

**看看定序品質有沒有改善。** 確認修剪真的做到了該做的事，而且沒有做過頭。

## 執行前必須驗證

```bash
python3 .agents/skills/rnaseq-qc-trimmed/validate.py
```

## 指令

只跑 paired 檔案（`_P_`），unpaired 的不用：

```bash
mkdir -p qc/trim
fastqc -o qc/trim -f fastq -t 2 trim/*_P_R?.fastq.gz
multiqc -o qc/trim --force qc/trim
```

## 這個領域的陷阱

修剪之後**只有一件事該改善**。其他模組沒有變化是**正常的，不代表修剪失敗**。

| 模組 | 修剪後預期 | 沒變化代表什麼 |
|---|---|---|
| **Adapter Content** | **FAIL → PASS** | 沒改善才是問題 —— 幾乎都是 adapter 檔案指錯（見 `rnaseq-trim-params`） |
| Sequence Length Distribution | 從單一長度變成一個分布 | 這是修剪有作用的直接證據 |
| Per Base Sequence Quality | 尾段略為改善或不變 | 本來就 PASS 的話不會有明顯變化 |
| **Per Base Sequence Content** | **仍然 FAIL** | **正常。** random hexamer priming 的偏差不是 adapter，剪不掉 |
| **Sequence Duplication Levels** | **仍然 FAIL** | **正常。** 那是高表現基因，不是 adapter |
| Per Sequence GC Content | 大致不變 | 正常 |

**「修剪完還是有 FAIL」不等於修剪沒用。** 要看的是**哪一個** FAIL 消失了。

### 讀數流失要分清楚是哪一種

`trim/*.trimmomatic.log` 那一行有四個數字，**只看 `Both Surviving` 會誤判**：

| 哪個數字高 | 代表什麼 | 怎麼辦 |
|---|---|---|
| `Forward Only Surviving` 高（>20%） | **R2 被 ILLUMINACLIP 的規則丟掉了**，不是品質問題 | 回頭把 `keepBothReads` 設成 TRUE |
| `Dropped` 高（>10%） | 真的被品質或長度門檻刷掉 | 回頭看 MINLEN 與 SLIDINGWINDOW |

**`Both Surviving` 只有五成、但 `Dropped` 只有 2%** —— 這種組合幾乎一定是
`keepBothReads` 沒開，不是資料不好。

## 驗收

```bash
ls qc/trim/*_fastqc.zip | wc -l     # 應為 8
ls -l qc/trim/multiqc_report.html
```

回報給使用者時，要做**修剪前後的對照**，至少涵蓋三件事：

1. Adapter Content 是否從 FAIL 變成 PASS
2. 讀數流失多少（存活率）
3. 哪些模組**照預期沒有變化**，以及為什麼那是對的
