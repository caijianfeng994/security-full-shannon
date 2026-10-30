#!/usr/bin/env bash
# 从 .env 读取 AI_GATEWAY_*，映射为 Shannon 环境变量。不打印密钥。
# 由 start.sh / preflight.sh source，不要单独执行。
# 可移植：不依赖 sibling shannon-pentest；.env 查找顺序见下。

_shannon_skill_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_shannon_models="${_shannon_skill_dir}/../references/models.gateway.json"

# .env 查找：显式路径 > 当前工作目录 > 向上最多 6 层找含 .env 的目录
_find_dotenv() {
  if [[ -n "${SHANNON_DOTENV:-}" && -f "${SHANNON_DOTENV}" ]]; then
    printf '%s\n' "${SHANNON_DOTENV}"
    return 0
  fi
  if [[ -f "$(pwd)/.env" ]]; then
    printf '%s\n' "$(pwd)/.env"
    return 0
  fi
  local d
  d="$(pwd)"
  local i
  for i in 1 2 3 4 5 6; do
    if [[ -f "${d}/.env" ]]; then
      printf '%s\n' "${d}/.env"
      return 0
    fi
    d="$(cd "${d}/.." && pwd)"
  done
  return 1
}

_shannon_env=""
if _shannon_env="$(_find_dotenv)"; then
  :
else
  _shannon_env=""
fi

_read_dotenv() {
  local key="$1"
  local file="$2"
  [[ -f "${file}" ]] || return 0
  python3 - "${file}" "${key}" <<'PY'
import sys
from pathlib import Path
path, key = Path(sys.argv[1]), sys.argv[2]
for raw in path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    name, value = line.split("=", 1)
    if name.strip() != key:
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    print(value)
    break
PY
}

if [[ -n "${_shannon_env}" ]]; then
  if [[ -z "${AI_GATEWAY_BASE_URL:-}" ]]; then
    AI_GATEWAY_BASE_URL="$(_read_dotenv AI_GATEWAY_BASE_URL "${_shannon_env}")"
  fi
  if [[ -z "${AI_GATEWAY_API_KEY:-}" ]]; then
    AI_GATEWAY_API_KEY="$(_read_dotenv AI_GATEWAY_API_KEY "${_shannon_env}")"
  fi
  if [[ -z "${AI_GATEWAY_MODEL:-}" ]]; then
    AI_GATEWAY_MODEL="$(_read_dotenv AI_GATEWAY_MODEL "${_shannon_env}")"
  fi
fi

if [[ -n "${AI_GATEWAY_API_KEY:-}" ]]; then
  export SHANNON_AI_API_KEY="${SHANNON_AI_API_KEY:-${AI_GATEWAY_API_KEY}}"
fi
if [[ -n "${AI_GATEWAY_BASE_URL:-}" ]]; then
  export SHANNON_AI_BASE_URL="${SHANNON_AI_BASE_URL:-${AI_GATEWAY_BASE_URL}}"
fi
if [[ -n "${AI_GATEWAY_MODEL:-}" ]]; then
  export SHANNON_AI_MODEL="${SHANNON_AI_MODEL:-custom-gateway:${AI_GATEWAY_MODEL}}"
  if [[ -f "${_shannon_models}" ]]; then
    export SHANNON_MODELS_CONFIG="${SHANNON_MODELS_CONFIG:-${_shannon_models}}"
  fi
fi
