# 實作：照順序複製貼上

**這一頁只有「要打的字」。** 每一格程式碼都是整段複製、貼上、Enter。

- 🖥 = 貼在**終端機**（Terminal）
- 🤖 = 貼在 **opencode 裡**（跟 agent 講話）
---

## 0　開環境（課前先做完）

1. 回本 repo 首頁 → 按綠色 **Open in GitHub Codespaces**
   （沒登入 GitHub 帳號會看不到這個選項）
2. 等 1–3 分鐘，終端機出現 **`準備完成`**
3. 等的時候去 <https://build.nvidia.com> 申請金鑰 → 右上 **Get API Key**
   → 複製 `nvapi-` 開頭那一串

> ⚠️ 金鑰**只會顯示一次**，先貼到記事本或寄給自己備份。

---

## 1　啟動 agent、接上金鑰

🖥
```bash
opencode
```

🤖 在 opencode 裡打（下面三步都在 opencode 裡）
```
/connect
```

搜尋框打
```
Nvidia
```

→ 貼上你的 `nvapi-...` 金鑰，Enter → 會自動跳到模型選擇畫面 → 搜尋
```
Nemotron
```

選 **Nemotron 3.5 Lightning 30B A3B**，Enter。
**確認下方狀態列的模型名稱換成它了**，才往下走。

---

## 2　先確認它真的會執行

🤖
```
列出 raw/ 底下有哪些樣本
```

**該看到**：它真的跑了 `ls`，回報 **4 個樣本、8 個檔案**。
只給你「你可以這樣打」而沒真的跑 → 回一句「請真的執行」。

---

## 3　原始資料品管（FastQC + MultiQC）

🤖
```
幫我對 raw/ 的 8 個檔案跑 FastQC 和 MultiQC，然後解讀結果
```

約 2 分鐘。**該看到**：`qc/raw/` 底下 8 個 `_fastqc.zip` + `multiqc_report.html`。

報告打開方式：左側檔案樹對 `qc/raw/multiqc_report.html` **按右鍵 → Open with Live Preview**。

**★ 這關要記一件事**：agent 有沒有建議你「去除重複序列 / deduplication」？
有的話記下來 —— 那是 RNA-seq 的經典錯誤。

---

## 4　決定修剪參數 —— 第一輪（**還沒有** skill）

🤖
```
根據剛剛的 QC 結果，決定 Trimmomatic 要用的完整參數，包含 ILLUMINACLIP 的所有欄位
```

**把答案抄下來**（等一下要比）——`ILLUMINACLIP` 整串、adapter 檔名、`MINLEN`。

**★ 數一下：`ILLUMINACLIP` 冒號後面有幾個數字？** 幾乎一定是三個（`2:30:10`）。

---

## 5　加上第 6 份 skill，再問一次一模一樣的話

**先按 `Ctrl-C` 完全離開 opencode**，然後在終端機一行一行貼：

🖥
```bash
cp -r skills-locked/rnaseq-trim-params .agents/skills/
```

🖥
```bash
ls .agents/skills/
```
**該看到 6 個**（本來是 5 個）。

🖥 看一眼你剛剛放進去的是什麼 —— 就是一份 markdown，沒有程式、沒有訓練
```bash
head -40 .agents/skills/rnaseq-trim-params/SKILL.md
```

🖥 **重新啟動**（skill 清單是啟動時掃的，`/new` 不夠）
```bash
opencode
```

🤖 確認新的 skill 有被讀到
```
/skill
```

🤖 確認模型還是 Nemotron（不是的話打 `/model` 重選）
```
/model
```

🤖 **問一模一樣的那句話**
```
根據剛剛的 QC 結果，決定 Trimmomatic 要用的完整參數，包含 ILLUMINACLIP 的所有欄位
```

**★ 三格對照**（唯一的差別是那份 markdown 進了它的視野）

| | 沒有 skill | 有 skill |
|---|---|---|
| `ILLUMINACLIP` | `2:30:10`（三欄） | `2:30:10:2:TRUE`（**五欄**） |
| adapter 檔 | `TruSeq3-PE.fa`（2 條序列） | `TruSeq3-PE-2.fa`（**6 條**） |
| `MINLEN` | `36`（記憶中的通則） | **`60`**（151 bp × 0.4，實測算的） |

**★ 也留意它有沒有主動跑 `validate.py`** —— 有跑 = 查了才答，不是憑記憶答。

---

## 6　修剪 + 修剪後再品管

🤖（整段貼，包含換行）
```
用 ILLUMINACLIP:TruSeq3-PE-2.fa:2:30:10:2:TRUE、LEADING=3、TRAILING=3、SLIDINGWINDOW=4:20、MINLEN=60 對四個樣本跑 Trimmomatic，然後對修剪後的 paired 檔案再跑一次 FastQC 和 MultiQC，並跟修剪前做對照
```

約 2.5 分鐘。**該看到**：存活率 **92.9–93.8%**、`qc/trim/multiqc_report.html`。

🖥 自己看 log 那一行的四個數字
```bash
grep "Input Read Pairs" trim/*.trimmomatic.log
```

| 欄位 | 應該是 |
|---|---|
| `Both Surviving` | 約 **93%** |
| `Forward Only Surviving` | 約 3%（**超過 20% 就是 `keepBothReads` 沒開**） |
| `Dropped` | 約 0.8% |

**★ 修剪後只有 Adapter Content 該從 FAIL 變 PASS。**
Per Base Sequence Content 和 Duplication **還是 FAIL —— 那是正常的。**

---

## 7　定量（kallisto pseudoalignment）

🤖
```
對四個樣本做 pseudoalignment
```

很快，四個樣本加起來不到 20 秒。

🤖
```
每個樣本的 pseudoalignment 比對率是多少
```

**預期 88–95%**，不是 95% 以上 —— 因為 `ref/` 那顆 index 只含 chr20 的 7,269 條轉錄本。
**這是刻意的取捨，不是資料有問題。**

---

## 8　差異表現分析（DEG + 火山圖）

🤖
```
把 kallisto 結果聚合到 gene level，跑腫瘤 vs 正常的差異表現分析，輸出結果表和火山圖
```

約 20 秒。**該看到** `PyDESeq2/output_files/` 底下有 `deseq2_results.csv`、
`deseq2_significant.csv`、`deseq2_candidates_unadjusted.csv`、`volcano.png`。

預期：有讀序 **1,075** 個基因 → **634** 個進統計 → 未校正 p<0.05 **39 個**
→ **校正後只有 1 個**：`CPXM1`，log2FC ≈ **−6.2**。

### ★ 三個一定要問的追問

🤖 ① 方向
```
padj 最小的前 10 個基因，分別是在腫瘤裡上升還是下降？
```

🤖 ② 設計公式
```
你用的設計公式是什麼？為什麼要有 patient 這一項？
```

🤖 ③ 這份結果能信到什麼程度
```
未校正有 39 個，校正後只剩 1 個。為什麼？這份結果能信到什麼程度？
```

**★ 如果 agent 把那 39 個講得像定論 —— 那比不做分析更危險。**

---

## 做完了？延伸

🤖
```
如果我要換成 HISAT2 + featureCounts 的路線，哪些步驟要改？
```

或把 `deseq2_candidates_unadjusted.csv` 的基因 ID 貼到 <https://www.webgestalt.org/> 做功能富集分析。

---

## 卡住了

| 症狀 | 怎麼辦 |
|---|---|
| `raw/` 或 `ref/` 是空的 | 🖥 `bash scripts/fetch_data.sh` |
| opencode 沒有模型 / 連不上 | 🤖 `/connect` 重接一次，或 🤖 `/model` 重選 |
| `403 Authorization failed` | 金鑰失效 → 回 build.nvidia.com **重產一把** |
| `404 Function not found` | 那顆模型後端沒部署 → 🤖 `/model` 換一個 |
| 它只講不做 | 🤖 `請真的執行這些指令` |
| 它一路跑到底不停 | 🤖 `一次只做一個步驟` |
| **第二輪答案跟第一輪一模一樣** | **沒有完全重開 opencode。`/new` 不會重掃 skill —— 要 `Ctrl-C` 再 `opencode`** |
| HTML 打不開 | 檔案樹按右鍵 → **Open with Live Preview** |

**課後記得把 Codespace 刪掉（Delete，不是 Stop）。**

---

## 帶回去的三件事

1. **模型不知道任何不在 context 裡的事。** 那 35 個百分點不是模型變聰明了，是那份 markdown 進了它的視野。
2. **可以判定真假的事交給程式，需要判斷的事交給模型。**
3. **會爆的錯誤是安全的，不會爆的才要人守著。**
