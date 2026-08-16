#!/usr/bin/env bash
# 共用的 Release 資產下載函式。fetch_data.sh 與 catch_up.sh 都 source 這支。
#
# 為什麼不能只用 curl 打 browser_download_url：
#   如果 repo 是 private，那個網址匿名存取一律回 404（GitHub 不回 403，
#   免得洩漏資源是否存在）。Codespace 的 postCreateCommand 會直接失敗，
#   而且失敗不會擋住 Codespace 開啟 —— 學員會拿到一個空的 raw/。
#
# 解法：有 token 就走 API（private / public 都通），沒有就走公開網址。
# Codespaces 預設會注入 GITHUB_TOKEN，所以私有 repo 也能正常運作。

gh_token() {
  echo "${GITHUB_TOKEN:-${GH_TOKEN:-}}"
}

# gh_asset_url <repo> <tag> <asset 檔名>
# 有 token → 回傳 API 的 asset 端點；沒有 → 回傳公開下載網址
gh_asset_url() {
  local repo="$1" tag="$2" asset="$3" tok
  tok="$(gh_token)"

  if [[ -z "$tok" ]]; then
    echo "https://github.com/${repo}/releases/download/${tag}/${asset}"
    return 0
  fi

  local id
  id=$(curl -fsSL --max-time 30 \
        -H "Authorization: Bearer ${tok}" \
        -H "Accept: application/vnd.github+json" \
        "https://api.github.com/repos/${repo}/releases/tags/${tag}" 2>/dev/null \
      | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
except Exception:
    sys.exit(1)
for a in d.get('assets',[]):
    if a['name']=='${asset}':
        print(a['id']); break
" 2>/dev/null) || true

  if [[ -n "$id" ]]; then
    echo "https://api.github.com/repos/${repo}/releases/assets/${id}"
  else
    # 找不到 asset id 就退回公開網址，讓後面的錯誤訊息去報
    echo "https://github.com/${repo}/releases/download/${tag}/${asset}"
  fi
}

# gh_fetch <url> <輸出路徑>
gh_fetch() {
  local url="$1" out="$2" tok
  tok="$(gh_token)"
  # --no-progress-meter：Codespace 的 setup log 是學員會看到的畫面，
  # curl 的進度條會把它洗掉。錯誤訊息仍然會出來（-S）。
  local args=(-fSL -S --no-progress-meter --retry 3 --retry-delay 2 --max-time 900 -o "$out")

  if [[ -n "$tok" ]]; then
    args+=(-H "Authorization: Bearer ${tok}")
    # API 的 asset 端點要靠這個 header 才會回二進位內容而不是 JSON
    [[ "$url" == https://api.github.com/* ]] && args+=(-H "Accept: application/octet-stream")
  fi

  curl "${args[@]}" "$url"
}

# gh_diag <repo> <tag> —— 下載失敗時印出可行動的診斷
gh_diag() {
  local repo="$1" tag="$2"
  echo >&2
  echo "下載失敗。依序確認：" >&2
  if [[ -z "$(gh_token)" ]]; then
    echo "  1. 環境裡沒有 GITHUB_TOKEN / GH_TOKEN。" >&2
    echo "     如果 ${repo} 是私有 repo，匿名下載一定會 404。" >&2
    echo "     在 Codespace 裡應該會自動注入；本機測試請自己 export。" >&2
  else
    echo "  1. token 有了，但仍失敗 —— 可能是 token 沒有這個 repo 的讀取權限。" >&2
  fi
  echo "  2. Release tag 是不是 '${tag}'？網頁上確認：" >&2
  echo "     https://github.com/${repo}/releases" >&2
  echo "  3. 三個檔案是不是都上傳完成（進度條 100%）？" >&2
  echo "  4. 換 repo 或 tag 的話：" >&2
  echo "     WORKSHOP_REPO=帳號/repo WORKSHOP_DATA_TAG=tag bash scripts/fetch_data.sh" >&2
}
