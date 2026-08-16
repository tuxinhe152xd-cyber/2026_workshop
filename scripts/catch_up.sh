#!/usr/bin/env bash
# 接關用：把預跑好的中間結果補進來，讓落後的人接上進度。
#
#   bash scripts/catch_up.sh qc      補 Step 1 的 qc/raw/
#   bash scripts/catch_up.sh trim    補 Step 2b + 3 的 trim/ 與 qc/trim/
#   bash scripts/catch_up.sh quant   補 Step 4 的 quant/
#   bash scripts/catch_up.sh all     一次補到 Step 4 為止
#
# 只覆蓋指定的階段，不會動 raw/ 與 ref/。
set -euo pipefail

REPO="${WORKSHOP_REPO:-tuxinhe152xd-cyber/2026_workshop}"
TAG="${WORKSHOP_DATA_TAG:-data-v1}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/_gh_download.sh"
cd "$HERE/.."

STAGE="${1:-}"
case "$STAGE" in
  qc)    PATHS=(qc/raw) ;;
  trim)  PATHS=(trim qc/trim) ;;
  quant) PATHS=(quant) ;;
  all)   PATHS=(qc/raw trim qc/trim quant) ;;
  *)
    echo "用法：bash scripts/catch_up.sh {qc|trim|quant|all}" >&2
    exit 1 ;;
esac

CACHE=.prebaked.tar
if [[ ! -s "$CACHE" ]]; then
  echo "下載預跑結果 ..."
  URL="$(gh_asset_url "$REPO" "$TAG" prebaked.tar)"
  gh_fetch "$URL" "$CACHE.part" || { rm -f "$CACHE.part"; gh_diag "$REPO" "$TAG"; exit 1; }
  mv "$CACHE.part" "$CACHE"
fi

for p in "${PATHS[@]}"; do
  echo "  補上 $p/"
  rm -rf "$p"
  mkdir -p "$(dirname "$p")"
  tar -xf "$CACHE" "$p" 2>/dev/null || {
    echo "  警告：prebaked.tar 裡沒有 $p" >&2
  }
done

echo
echo "完成。目前狀態："
for d in qc/raw trim qc/trim quant; do
  n=$(find "$d" -type f 2>/dev/null | wc -l)
  printf "  %-10s %s 個檔案\n" "$d" "$n"
done
echo
echo "接下來可以直接跳到下一步問 agent。"
