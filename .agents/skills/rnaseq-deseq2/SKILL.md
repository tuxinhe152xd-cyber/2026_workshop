---
name: rnaseq-deseq2
description: >
  Step 5 of the RNA-seq pipeline — aggregate kallisto transcript counts to gene level
  and run differential expression with PyDESeq2, producing a results table and volcano
  plot. Use when the user asks for differential expression, DEG, DESeq2, 差異表現,
  tumor vs normal comparison, or 哪些基因有變. Contains why no R tximport step is
  needed, why est_counts and not TPM, and how to read the result with only n=2.
---

# Step 5 — 差異表現分析（PyDESeq2）

## 這一步在做什麼

**去掉干擾因素，然後統計看看基因表現有沒有變。** kallisto 給的是每個樣本各自的
表現量，這一步要問的是：腫瘤跟正常之間，**哪些基因的差異大到不像是隨機波動**。

## 執行前必須驗證

```bash
python3 .agents/skills/rnaseq-deseq2/validate.py
```

## 兩個指令

### 5a. 轉錄本 → 基因

```bash
python3 .agents/skills/rnaseq-deseq2/build_counts.py
```

產出 `PyDESeq2/counts.tsv`。

**傳統流程在這裡需要 R 的 `tximport` 加一張 transcript-to-gene 對照表。這裡不用。**
因為 GENCODE 建的 index，`abundance.tsv` 的 `target_id` 自己就帶著基因 ID：

```
ENST00000832824.1|ENSG00000290825.2|-|-|DDX11L16-260|DDX11L16|1379|lncRNA|
^ 轉錄本 ENST      ^ 基因 ENSG
```

用 `|` 切開取第 2 欄就是 ENSG，同一個基因的轉錄本相加即可。

### 5b. 差異表現

```bash
python3 .agents/skills/rnaseq-deseq2/run_deseq2.py
```

預設用配對設計 `~patient + group`，比較 `group` 的 `T` vs `N`。
產出在 `PyDESeq2/output_files/`：`deseq2_results.csv`、`deseq2_significant.csv`、`volcano.png`。

不配對的話加 `--design '~group'`。

## 這個領域的陷阱

**① 要餵 `est_counts`，不能餵 `tpm`。**
DESeq2 的模型假設輸入是原始計數，它會自己做 size factor 正規化。
TPM 已經正規化過了，餵進去會讓變異數估計整個歪掉。`build_counts.py` 用的是 `est_counts`。

**② 這裡的加總是簡化版。**
嚴謹的 tximport 會帶入有效長度的 offset。直接相加在方向上不會錯，但數值會有差異。
**要對使用者說出來，不要當作等價。**

**③ 配對設計不是選配。**
`11N`／`11T` 是同一位病人的正常與腫瘤，`13N`／`13T` 是另一位。
用 `~group` 會把「病人之間的個體差異」算進誤差，`~patient + group` 才是把它扣掉。
這就是「去掉干擾因素」那句話的實際意思。

**④ n=2 對 n=2，檢定力非常低。**
這是課堂用的子集，只有 chr20、每組兩個樣本。
- 找得到的只會是差異很大的基因
- **沒有顯著不代表沒有差異**，只代表這個樣本數看不出來
- padj 很多是 NA 是正常的（DESeq2 的獨立過濾）

**這一點一定要跟使用者講。把 n=2 的結果講得像定論，比不做分析更危險。**

**⑤ log2FoldChange 的正負方向由 contrast 決定。**
`["group","T","N"]` 的正值代表**腫瘤高於正常**。講結果時要把方向講清楚。

## 驗收

```bash
ls -l PyDESeq2/counts.tsv
ls -l PyDESeq2/output_files/deseq2_results.csv PyDESeq2/output_files/volcano.png
head -3 PyDESeq2/output_files/deseq2_significant.csv
```

回報給使用者時要包含：

1. 過濾後剩下幾個基因、幾個達到 padj<0.05 且 |log2FC|>1
2. padj 最小的前幾個基因，**並標明上調還是下調**
3. **n=2 的限制**，以及這份結果能用到什麼程度
4. 下一步可以做什麼（例如把顯著基因清單丟到 WebGestalt 做功能富集分析）
