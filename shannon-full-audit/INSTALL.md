# 安装与独立使用

`shannon-full-audit` 是 **自包含 Skill 目录**。拷贝本文件夹即可，**不需要**同级 `shannon-pentest`。

但 Phase A（Shannon 动态）还依赖本机三件套：**Docker + Node/npx + Shannon CLI（经 npx）**，以及 LLM Key。  
**缺任何一项时，Agent 必须先通知用户安装，禁止直接开扫。**

速查与话术：[references/prerequisites.md](references/prerequisites.md)

---

## 1. 安装本 Skill

```bash
# Claude Code / 兼容布局
cp -R shannon-full-audit ~/.claude/skills/shannon-full-audit

# Codex
mkdir -p ~/.codex/skills
cp -R shannon-full-audit ~/.codex/skills/shannon-full-audit

# 项目内
mkdir -p .claude/skills
cp -R shannon-full-audit .claude/skills/shannon-full-audit
```

---

## 2. 安装本机运行时（用户侧）

### 2.1 Docker

| 系统 | 链接 / 命令 |
|---|---|
| macOS | https://docs.docker.com/desktop/setup/install/mac-install/ · `brew install --cask docker` |
| Windows | https://docs.docker.com/desktop/setup/install/windows-install/ |
| Linux | https://docs.docker.com/engine/install/ |

安装后启动 Docker Desktop / `systemctl start docker`，执行 `docker info` 应成功。

### 2.2 Node.js 18+（提供 npx）

- https://nodejs.org/（推荐 LTS）
- macOS: `brew install node`
- 或 [nvm](https://github.com/nvm-sh/nvm): `nvm install 20`

验证：`node -v`、`npx -v`

### 2.3 Shannon CLI

本包不内置 Shannon。首次：

```bash
npx --yes @keygraph/shannon@3.3.0 setup
npx --yes @keygraph/shannon@3.3.0 --help
```

仓库：https://github.com/KeygraphHQ/shannon（AGPL-3.0）

### 2.4 LLM Key

`setup` 交互配置，或 export Shannon 文档要求的 Key，或项目 `.env` 的 `AI_GATEWAY_*` / `SHANNON_DOTENV`。

---

## 3. 一键检查（必做）

```bash
SKILL_DIR=/path/to/shannon-full-audit
bash "$SKILL_DIR/scripts/preflight.sh"
```

出现 `FAIL` → 按脚本打印的 `→` 提示安装，通过后再扫。  
可选严格校验 CLI：`SHANNON_PREFLIGHT_STRICT_CLI=1 bash "$SKILL_DIR/scripts/preflight.sh"`

---

## 4. 授权与启动

```bash
export SHANNON_I_AUTHORIZE=1
# 可选
export SHANNON_ALLOWED_HOSTS='staging.example.com'
export SHANNON_OUTPUT_ROOT='/path/to/reports'

bash "$SKILL_DIR/scripts/start.sh" \
  -u 'https://staging.example.com' \
  -r '/path/to/app-source' \
  -w 'demo-001'
```

报告默认：`./web-output/shannon-full-audit/<workspace>/shannon/`。

仅白盒、本机没有 Docker/Shannon 时：对 Agent 说 `whitebox-only`，跳过 Phase A。

---

## 许可说明

- Skill 编排与 `scripts/`：随本目录分发  
- `vendors/`：MIT 上游节选，见 `THIRD_PARTY_NOTICES.md`  
- Shannon CLI：AGPL-3.0，使用者自行安装并接受其许可  
