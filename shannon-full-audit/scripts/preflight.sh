#!/usr/bin/env bash
# Phase A 启动前检查。缺依赖时打印「如何安装」，不打印密钥。
# 退出码：0=通过；1=缺失或未就绪（Agent 必须停下来通知用户，禁止硬启 Shannon）
set -euo pipefail

fail=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=load_ai_gateway.sh
source "${SCRIPT_DIR}/load_ai_gateway.sh"

ok() { printf 'ok   %s\n' "$1"; }
bad() { printf 'FAIL %s\n' "$1"; fail=1; }
hint() { printf '     → %s\n' "$1"; }

echo "=== shannon-full-audit preflight ==="
echo ""

# --- Docker ---
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "Docker 已安装且 daemon 在运行"
  else
    bad "已安装 Docker，但 daemon 未运行"
    hint "macOS: 打开 Docker Desktop 并等待状态变为 Running"
    hint "Linux: sudo systemctl start docker"
  fi
else
  bad "未安装 Docker（Shannon worker 必需）"
  hint "macOS: https://docs.docker.com/desktop/setup/install/mac-install/"
  hint "  或: brew install --cask docker"
  hint "Linux: https://docs.docker.com/engine/install/"
  hint "Windows: https://docs.docker.com/desktop/setup/install/windows-install/"
fi

# --- Node / npx ---
if command -v node >/dev/null 2>&1; then
  node_v="$(node -v 2>/dev/null || true)"
  ok "Node.js ${node_v}"
  # 粗检主版本
  major="$(node -p "process.versions.node.split('.')[0]" 2>/dev/null || echo 0)"
  if [[ "${major}" -lt 18 ]]; then
    bad "Node.js 版本过低（需要 18+），当前 ${node_v}"
    hint "升级: https://nodejs.org/ 或 brew install node@20"
  fi
else
  bad "未安装 Node.js（需要 18+，以提供 npx）"
  hint "官方安装包: https://nodejs.org/"
  hint "macOS: brew install node"
  hint "Linux: 使用发行版包管理器或 nvm (https://github.com/nvm-sh/nvm)"
fi

if command -v npx >/dev/null 2>&1; then
  ok "npx 可用"
else
  bad "未找到 npx（通常随 Node.js 安装）"
  hint "重装 Node.js 18+ 后确认: which npx && npx -v"
fi

# --- Shannon CLI（通过 npx 拉取；此处检查网络可达的包名提示）---
if command -v npx >/dev/null 2>&1; then
  # 不强制每次拉包；检查用户是否跑过 setup / 缓存是否存在
  if [[ -d "${HOME}/.shannon" ]] || [[ -d "${HOME}/.keygraph/shannon" ]] || [[ -d "${HOME}/.npm/_npx" ]]; then
    ok "检测到本机可能已有 Shannon/npx 缓存或配置目录"
  else
    # 不算硬失败：首次 start 会 npx 下载；但提醒用户需联网
    printf 'warn 首次运行将通过 npx 下载 @keygraph/shannon（需联网）\n'
    hint "建议先执行: npx --yes @keygraph/shannon@3.3.0 setup"
    hint "文档/发行: https://github.com/KeygraphHQ/shannon"
  fi
  # 可选：用户设 SHANNON_PREFLIGHT_STRICT_CLI=1 时尝试 dry 拉取版本
  if [[ "${SHANNON_PREFLIGHT_STRICT_CLI:-}" == "1" ]]; then
    if npx --yes @keygraph/shannon@3.3.0 --help >/dev/null 2>&1; then
      ok "Shannon CLI 可通过 npx 调用"
    else
      bad "无法通过 npx 调用 @keygraph/shannon"
      hint "检查网络/npm registry，然后: npx --yes @keygraph/shannon@3.3.0 setup"
      hint "仓库: https://github.com/KeygraphHQ/shannon"
    fi
  fi
fi

# --- LLM Key ---
if [[ -n "${SHANNON_AI_API_KEY:-}" || -n "${AI_GATEWAY_API_KEY:-}" || -n "${ANTHROPIC_API_KEY:-}" || -n "${OPENAI_API_KEY:-}" || -n "${XAI_API_KEY:-}" || -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
  ok "检测到 LLM 相关环境变量（值已隐藏）"
  [[ -n "${SHANNON_AI_MODEL:-}" ]] && ok "SHANNON_AI_MODEL=${SHANNON_AI_MODEL}"
  [[ -n "${SHANNON_AI_BASE_URL:-}" ]] && ok "SHANNON_AI_BASE_URL=${SHANNON_AI_BASE_URL}"
elif [[ -f "${HOME}/.shannon/.env" ]] || [[ -f "${HOME}/.keygraph/shannon/.env" ]]; then
  ok "检测到本机 Shannon 配置文件（未读取内容）"
else
  bad "未检测到 LLM API Key"
  hint "任选其一:"
  hint "  1) npx --yes @keygraph/shannon@3.3.0 setup   # 交互写入本机配置"
  hint "  2) export ANTHROPIC_API_KEY=... 或 OPENAI_API_KEY=...（按 Shannon 文档）"
  hint "  3) 在项目 .env 配置 AI_GATEWAY_BASE_URL / AI_GATEWAY_API_KEY / AI_GATEWAY_MODEL"
  hint "  4) export SHANNON_DOTENV=/path/to/.env"
fi

echo ""
if [[ "${fail}" -ne 0 ]]; then
  echo "=== preflight 未通过：请先安装/启动上述依赖，再重试 Phase A ==="
  echo "完整安装说明见: ${SCRIPT_DIR}/../INSTALL.md"
  echo "依赖速查见: ${SCRIPT_DIR}/../references/prerequisites.md"
  exit 1
fi

echo "=== preflight 通过 ==="
exit 0
