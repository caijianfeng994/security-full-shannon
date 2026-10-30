#!/usr/bin/env bash
# 把 GitLab 规范仓名 clone 到本地目录，供 Shannon -r 使用。
# 不定仓、不调 MCP；仓名由 Agent 用 CodeWiki/GitNexus 解析后传入。
set -euo pipefail

GITLAB_HOST="${SHANNON_GITLAB_HOST:-}"
BRANCH="${SHANNON_GIT_BRANCH:-}"

usage() {
  cat <<EOF
用法:
  clone_repos.sh -d <dest_dir> <group/repo> [group/repo ...]

环境:
  SHANNON_GITLAB_HOST   必填，GitLab 主机名。不要把内网地址或密钥写进本仓库
  SHANNON_GIT_BRANCH    可选，指定 clone 的分支（应尽量对齐被扫环境）
EOF
}

DEST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -d) DEST="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) echo "未知参数: $1" >&2; usage; exit 2 ;;
    *) break ;;
  esac
done

if [[ -z "${DEST}" || $# -lt 1 ]]; then
  echo "必须提供 -d 与至少一个 group/repo" >&2
  usage
  exit 2
fi

if [[ -z "${GITLAB_HOST}" ]]; then
  echo "必须设置 SHANNON_GITLAB_HOST（GitLab 主机名）。不要把内网地址写进仓库。" >&2
  exit 2
fi

mkdir -p "${DEST}"
DEST="$(cd "${DEST}" && pwd)"

for spec in "$@"; do
  spec="${spec#/}"
  if [[ "${spec}" != */* ]]; then
    echo "仓名必须是 GitNexus/GitLab 规范名，如 backend/go-token，收到: ${spec}" >&2
    exit 2
  fi
  slug="${spec//\//__}"
  target="${DEST}/${slug}"
  url="git@${GITLAB_HOST}:${spec}.git"
  if [[ -d "${target}/.git" ]]; then
    echo "已存在，fetch: ${spec}"
    git -C "${target}" fetch --depth 1 origin
    if [[ -n "${BRANCH}" ]]; then
      git -C "${target}" checkout "${BRANCH}"
      git -C "${target}" pull --ff-only origin "${BRANCH}" || true
    fi
    continue
  fi
  echo "clone ${url} -> ${target}"
  if [[ -n "${BRANCH}" ]]; then
    git clone --depth 1 --branch "${BRANCH}" "${url}" "${target}"
  else
    git clone --depth 1 "${url}" "${target}"
  fi
done

echo "SHANNON_REPO_ROOT=${DEST}"
