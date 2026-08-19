# NGS × Agent 工作坊 —— RNA-seq 實作環境

用自然語言指揮 AI agent，跑完一條 RNA-seq 差異表現分析流程。

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/tuxinhe152xd-cyber/2026_workshop?quickstart=1)

> **課堂實作請開這一頁 → [note.md](note.md)**
> 從頭到尾要打的字都在裡面，照順序複製貼上就好。

---

## 開始之前（課前請先做完）

1. **有 GitHub 帳號** —— 沒開會建不了 Codespace。
2. **申請一把 NVIDIA NIM API key** —— <https://build.nvidia.com>，
   右上角 **Get API Key**，複製那串 `nvapi-` 開頭的字串。免費。

> **費用**：Codespaces 個人帳號每月有 120 core-hours 免費額度，
> 這門課用 2 核跑 90 分鐘 = **3 core-hours**。
> 預設消費上限是 $0，沒有綁付款方式就不可能被扣錢 —— 額度用完只會停用。
> **課後記得把 Codespace 刪掉**（不是停止，是刪除），才不會佔用儲存額度。

---

## 三步驟

### 1. 開 Codespace

點上面那顆綠色按鈕，或到本 repo 的 **Code → Codespaces → Create codespace on main**。

第一次約 1–2 分鐘：拉環境 image、下載課程資料（約 244 MB）。
看到終端機出現 `準備完成` 就可以了。

---

## 實作請開
**實作程式碼跟prompt -> [note.md](note.md)**

---

## 這裡面有什麼

```
.
├── raw/                 8 個 FASTQ（4 樣本 × R1/R2，只取 chr20）
├── ref/                 kallisto index（chr20 專用，82 MB）
├── .agents/skills/      五份分析步驟指引 ← agent 看得到
├── skills-locked/       第六份，課堂上才會用到
├── AGENTS.md            專案層規則
├── PyDESeq2/metadata.csv
└── scripts/fetch_data.sh
```

### 樣本

| 樣本 | 病人 | 組織 |
|---|---|---|
| `11N_chr20` | 11 | Normal（正常） |
| `11T_chr20` | 11 | Tumor（腫瘤） |
| `13N_chr20` | 13 | Normal |
| `13T_chr20` | 13 | Tumor |

讀長 151 bp，每個檔案約 0.31–0.40 M reads。同一位病人的正常／腫瘤配對設計。

### 六個步驟

| Step | Skill | 做什麼 |
|---|---|---|
| 1 | `rnaseq-qc-raw` | FastQC + MultiQC，看原始品質 |
| 2a | `rnaseq-trim-params` | **決定**修剪參數（課堂上才發） |
| 2b | `rnaseq-trim-run` | 執行 Trimmomatic |
| 3 | `rnaseq-qc-trimmed` | 修剪後再看一次 |
| 4 | `rnaseq-quant-kallisto` | pseudoalignment 定量 |
| 5 | `rnaseq-deseq2` | 聚合到基因層級 + PyDESeq2 |

每份 skill 都有三樣東西：**執行前的輸入驗證**（`validate.py`）、**精確的指令**、
以及**這個步驟特有的領域知識** —— 哪些看起來錯的其實正常、哪些看起來對的其實錯。

---

## 卡住了

| 症狀 | 處理 |
|---|---|
| `raw/` 是空的 | `bash scripts/fetch_data.sh` |
| opencode 說沒有模型 | `export NVIDIA_API_KEY=...` 打了嗎？或在 opencode 裡打 `/models` |
| agent 只講不做 | 回一句「請真的執行這些指令」 |
| 看不到 HTML 報告 | 左側檔案樹對 `multiqc_report.html` 按右鍵 → **Open with Live Preview** |
| Codespace 建不起來 | 檢查 GitHub 帳號是否已開 2FA、本月免費額度是否用完 |

---

## 資料來源

chr20 子集，取自教學用 RNA-seq 資料集，僅供本工作坊教學使用。
kallisto index 由 GENCODE v49 的 chr20 轉錄本建立（7,269 條）。
