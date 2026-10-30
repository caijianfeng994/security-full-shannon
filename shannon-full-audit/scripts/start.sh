#!/usr/bin/env bash
# 封装 npx @keygraph/shannon start。不做渗透，只拼参数并启动。
# 属于 shannon-full-audit 自包含脚本，不依赖 sibling shannon-pentest。
set -euo pipefail

usage() {
  cat <<'EOF'
用法:
  start.sh -u <url> -r <repo> [-w <workspace>] [-c <config.yaml>] [-o <outdir>] [--follow]

环境:
  SHANNON_I_AUTHORIZE=1          必须，或由 Agent 在用户口头授权后 export
  SHANNON_ALLOWED_HOSTS=host1,host2   可选，限制可扫 hostname
  SHANNON_OUTPUT_ROOT             可选，报告根目录；默认 <cwd>/web-output/shannon-full-audit
  SHANNON_DOTENV                  可选，.env 路径
EOF
}

URL=""
REPO=""
WORKSPACE=""
CONFIG=""
OUTDIR=""
FOLLOW=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -u) URL="${2:-}"; shift 2 ;;
    -r) REPO="${2:-}"; shift 2 ;;
    -w) WORKSPACE="${2:-}"; shift 2 ;;
    -c) CONFIG="${2:-}"; shift 2 ;;
    -o) OUTDIR="${2:-}"; shift 2 ;;
    --follow) FOLLOW=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "${URL}" || -z "${REPO}" ]]; then
  echo "必须提供 -u 与 -r" >&2
  usage
  exit 2
fi

if [[ "${SHANNON_I_AUTHORIZE:-}" != "1" ]]; then
  echo "拒绝启动：未设置 SHANNON_I_AUTHORIZE=1。确认用户已授权该 URL 后再启动。" >&2
  exit 3
fi

if [[ ! -d "${REPO}" ]]; then
  echo "源码路径不存在或不是目录: ${REPO}" >&2
  exit 2
fi

host="$(python3 - "${URL}" <<'PY'
import sys
from urllib.parse import urlparse
u = urlparse(sys.argv[1])
if u.scheme not in ("http", "https") or not u.hostname:
    sys.exit("URL 必须是 http(s) 且含 hostname")
print(u.hostname)
PY
)"

if [[ -n "${SHANNON_ALLOWED_HOSTS:-}" ]]; then
  IFS=',' read -r -a allowed <<< "${SHANNON_ALLOWED_HOSTS}"
  hit=0
  for h in "${allowed[@]}"; do
    h="${h// /}"
    if [[ -n "${h}" && "${host}" == "${h}" ]]; then
      hit=1
      break
    fi
  done
  if [[ "${hit}" -eq 0 ]]; then
    echo "拒绝启动：${host} 不在 SHANNON_ALLOWED_HOSTS 中" >&2
    exit 3
  fi
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=load_ai_gateway.sh
source "${SCRIPT_DIR}/load_ai_gateway.sh"
bash "${SCRIPT_DIR}/preflight.sh"

if [[ -z "${WORKSPACE}" ]]; then
  WORKSPACE="shannon-full-$(date +%Y%m%d-%H%M%S)"
fi
if [[ -z "${OUTDIR}" ]]; then
  OUTPUT_ROOT="${SHANNON_OUTPUT_ROOT:-$(pwd)/web-output/shannon-full-audit}"
  OUTDIR="${OUTPUT_ROOT}/${WORKSPACE}/shannon"
fi
mkdir -p "${OUTDIR}"

cmd=(npx --yes @keygraph/shannon@3.3.0 start -u "${URL}" -r "${REPO}" -w "${WORKSPACE}" -o "${OUTDIR}")
if [[ -n "${CONFIG}" ]]; then
  cmd+=(-c "${CONFIG}")
fi
if [[ -n "${SHANNON_MODELS_CONFIG:-}" ]]; then
  cmd+=(--models-config "${SHANNON_MODELS_CONFIG}")
fi
if [[ "${FOLLOW}" -eq 1 ]]; then
  cmd+=(--follow)
fi

echo "启动 Shannon: ${cmd[*]}"
echo "报告目录: ${OUTDIR}"
exec "${cmd[@]}"
