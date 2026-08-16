#!/usr/bin/env bash
# 把 FASTQ 與 chr20 kallisto index 從 GitHub Release 抓下來。
#
# Codespace 建立時由 devcontainer.json 的 postCreateCommand 自動執行。
# 手動重跑也安全 —— 已存在的檔案不會重抓。
set -euo pipefail

# 講師：把 tuxinhe152xd-cyber/2026_workshop 換成實際的 repo，TAG 換成 Release 的 tag
REPO="${WORKSHOP_REPO:-tuxinhe152xd-cyber/2026_workshop}"
TAG="${WORKSHOP_DATA_TAG:-data-v1}"
BASE="https://github.com/${REPO}/releases/download/${TAG}"

cd "$(dirname "${BASH_SOURCE[0]}")/.."

need() {   # need <目標路徑> <release 檔名>
  local dest="$1" asset="$2"
  if [[ -s "$dest" ]]; then
    echo "  已存在，略過：$dest"
    return 0
  fi
  echo "  下載 $asset ..."
  curl -fSL --retry 3 --retry-delay 2 -o "$dest.part" "$BASE/$asset" || {
    echo
    echo "下載失敗：$BASE/$asset" >&2
    echo "確認 Release '$TAG' 存在且該檔案已上傳，或用環境變數覆蓋：" >&2
    echo "  WORKSHOP_REPO=你的帳號/你的repo WORKSHOP_DATA_TAG=tag bash scripts/fetch_data.sh" >&2
    rm -f "$dest.part"
    exit 1
  }
  mv "$dest.part" "$dest"
}

echo "取得課程資料（約 244 MB，第一次約需 30 秒）"
mkdir -p raw ref qc/raw qc/trim trim quant PyDESeq2/output_files

# 1. chr20 kallisto index（82 MB）
need ref/gencode.v49.chr20.idx gencode.v49.chr20.idx

# 2. FASTQ（162 MB，打包成一個 tar 減少往返）
if compgen -G "raw/*.fastq.gz" > /dev/null; then
  echo "  已存在，略過：raw/*.fastq.gz"
else
  need raw/_fastq.tar fastq_chr20.tar
  tar -xf raw/_fastq.tar -C raw --strip-components=0
  rm -f raw/_fastq.tar
fi

echo
echo "檢查："
n_fq=$(ls raw/*.fastq.gz 2>/dev/null | wc -l)
echo "  raw/  : $n_fq 個 FASTQ（應為 8）"
if [[ -s ref/gencode.v49.chr20.idx ]]; then
  echo "  ref/  : $(du -h ref/gencode.v49.chr20.idx | cut -f1) index"
fi

if [[ "$n_fq" -ne 8 ]]; then
  echo
  echo "警告：FASTQ 數量不是 8，請重跑 bash scripts/fetch_data.sh" >&2
  exit 1
fi

echo
echo "準備完成。接下來："
echo "  export NVIDIA_API_KEY=nvapi-..."
echo "  opencode"
