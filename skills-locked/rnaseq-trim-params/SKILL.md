---
name: rnaseq-trim-params
description: >
  Step 2a of the RNA-seq pipeline — decide the Trimmomatic parameters (adapter FASTA,
  ILLUMINACLIP fields including keepBothReads, SLIDINGWINDOW, LEADING, TRAILING, MINLEN)
  from the raw MultiQC report before running the trimmer. Use when the user asks what
  trimming parameters to use, asks to decide Trimmomatic settings, or asks 修剪參數怎麼設.
  Contains why the default ILLUMINACLIP discards R2 on short-insert paired-end libraries,
  and why MINLEN must come from the measured read length.
---

# Step 2a — 決定修剪參數

## 這一步在做什麼

**在動手修剪之前，先決定要怎麼剪。** 這是整條流程唯一一個「判斷」的步驟。

## 執行前必須驗證

```bash
python3 .agents/skills/rnaseq-trim-params/validate.py
```

這支腳本會從 MultiQC 的統計檔讀出**實測的讀長**並印出來。
**下面所有計算都用它印出來的數字，不要用你記得的通則。**

---

## ★ 最重要的一件事：`ILLUMINACLIP` 的第六個欄位

到處都在流傳的那一串 `ILLUMINACLIP:adapter.fa:2:30:10`，**只填了三個欄位。**
完整的格式有六個：

```
ILLUMINACLIP:<fasta>:<seedMismatches>:<palindromeClipThreshold>:<simpleClipThreshold>:<minAdapterLength>:<keepBothReads>
             TruSeq3-PE-2.fa : 2 : 30 : 10 : 2 : TRUE
                                             ^^^^^^^^
                                             通常沒人填，預設是 FALSE
```

### 沒填會發生什麼

雙端定序時，如果**插入片段比讀長短**，R1 和 R2 會讀到同一段序列（互為反向互補）——
Trimmomatic 稱之為 **palindrome mode**。

這時候 `keepBothReads=FALSE`（預設）的行為是：**判定 R2 是多餘的，直接丟掉。**

```
keepBothReads=FALSE  →  這一對變成「只剩 R1」，從 paired 掉到 unpaired
keepBothReads=TRUE   →  R1 和 R2 都留下，維持 paired
```

**在 adapter 汙染嚴重、插入片段偏短的 library 上，這會影響非常大比例的 read pair。**
下游只吃 `_P_`（paired）檔案，所以掉到 unpaired 就等於沒了。

### 為什麼很難發現

- Trimmomatic **不會報錯**，正常結束、回報成功
- FastQC 看不出來 —— 剩下的 read 品質確實變好了
- kallisto 也不會抱怨，它只是拿到比較少的 fragment

**唯一的線索在 log 裡：**

```
Input Read Pairs: 352130  Both Surviving: 194673 (55.28%)  Forward Only Surviving: 145418 (41.30%)
                                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                            這一行才是重點
```

**`Forward Only Surviving` 超過 20% 就要懷疑 `keepBothReads` 沒開。**
它不是「品質不好」，是「被規則丟掉的」。

### 判斷規則

| 情況 | 怎麼設 |
|---|---|
| 雙端定序，Adapter Content 有 WARN/FAIL，下游要做定量 | **`keepBothReads=TRUE`** |
| 雙端定序，完全沒有 adapter 訊號 | 兩者差別不大，還是建議 TRUE |
| 單端定序 | 這個欄位不適用 |

**這批資料是雙端、Adapter Content FAIL —— 要填 TRUE。**

---

## Adapter FASTA —— 由 adapter family 決定，不是由汙染比例決定

FastQC 的 Adapter Content 會報**是哪一種** adapter。這個名字決定要指向哪個檔案：

| FastQC 報的名稱 | 建庫方式 | Trimmomatic 檔案 |
|---|---|---|
| Illumina Universal Adapter | TruSeq 接合 | `TruSeq3-PE-2.fa` |
| Nextera Transposase Sequence | Nextera 轉座 | `NexteraPE-PE.fa` |
| polyA | mRNA 的生物性尾巴，**不是 adapter** | 無 |
| polyG | 雙色定序的無訊號假象，**不是 adapter** | adapter 修剪剪不掉 |

檔案位置：

```bash
ls /opt/conda/envs/rnaseq-demo/share/trimmomatic/adapters/
```

**指錯檔案不會報錯。** Trimmomatic 會照跑、回報成功、剪掉零條 adapter。
**所以一定要把檔名講出來，不能只說「有 adapter 汙染，跑一下 trimmer」。**

---

## MINLEN —— 必須從實測讀長算

```
MINLEN = round(實測 avg_sequence_length × 0.4)
```

**「實測」指的是 validate.py 印出來的那個數字。**

常見的錯誤是套用記憶中的預設值。「MINLEN 36」「MINLEN 40」這類數字來自
Illumina 讀長還是 100 bp 的年代。**如果實際讀長是 151 bp，MINLEN 40 就只有 26%**，
遠比想要的 40% 寬鬆，會放行大量太短、在轉錄體上會多重比對的片段。

> 誠實補一句：在插入片段普遍偏短的 library 上，**MINLEN 對存活率的影響可能很小**
> ——因為主要的損失發生在 adapter 修剪那一步，不是長度篩選那一步。
> 但「從實測讀長推導」跟「套用記憶中的通則」是兩件事，
> **後者這次剛好影響不大，不代表下次也是。**

MINLEN 訂太鬆：短片段多重比對，定量雜訊上升。
MINLEN 訂太嚴：讀數損失，低表現基因被剪光。0.4 倍是常用的折衷。

---

## 其餘參數

| 參數 | 判斷依據 |
|---|---|
| `SLIDINGWINDOW` | 品質曲線整體在 Q20 以上就用 `4:20`；有明顯尾段掉落才收緊到 `4:25` |
| `LEADING` / `TRAILING` | 頭尾品質沒問題時用 `3`（保守、幾乎不損失） |

**參數的順序就是執行順序。** `ILLUMINACLIP` 一定要放第一個 ——
先剪掉 adapter，再看品質。放後面等於那道篩子作用在未剪 adapter 的序列上。

---

## 不該修剪的東西

- **Per Base Sequence Content FAIL 不是修剪的理由。** 那是 random hexamer priming
  造成的，剪掉前 13 個鹼基只會損失資料，偏差還是在。
- **Duplication FAIL 不是修剪的理由，更不是去重的理由。** 見 `rnaseq-qc-raw`。

這一步**只決定參數，不執行修剪**。決定完把參數列給使用者確認，再進 `rnaseq-trim-run`。

---

## 驗收

交給使用者一張表。**adapter 檔名只寫一次，就寫在 ILLUMINACLIP 裡** ——
不要另外開一列重複寫檔名，兩處很容易寫成不一致的值。

```
ILLUMINACLIP   : <adapter 檔名>:2:30:10:2:TRUE
                 依據：FastQC 報的 adapter family → 決定檔名
                       雙端 + 有 adapter 訊號     → keepBothReads=TRUE
SLIDINGWINDOW  : 4:20                     依據：<品質曲線的觀察>
LEADING        : 3
TRAILING       : 3
MINLEN         : <值>                     算式：<實測讀長> × 0.4 = <值>
```

**檔名必須是 `ls` 真的看得到的那個。** 常見的錯誤是把
`TruSeq3-PE.fa` 和 `TruSeq3-PE-2.fa` 混成 `TruSeq3-PE-PE.fa` 這種不存在的名字。
不確定就先跑：

```bash
ls /opt/conda/envs/rnaseq-demo/share/trimmomatic/adapters/
```

並提醒使用者：**跑完之後要看 log 的 `Forward Only Surviving`。**
