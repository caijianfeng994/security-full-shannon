# 本机依赖速查（缺则先装，再开扫）

Agent 在 Phase A **之前**必须执行：

```bash
bash "$SKILL_DIR/scripts/preflight.sh"
```

任意一项 `FAIL` → **立刻停止**，把下面对应安装步骤原样告诉用户，**禁止**假装已启动 Shannon。

仅 `whitebox-only` 时可跳过 Docker/Shannon CLI，但仍建议跑 preflight 并说明「本模式不启动态扫描」。

---

## 1. Docker

**用途：** Shannon worker 容器。

| 系统 | 安装 |
|---|---|
| macOS | [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) 或 `brew install --cask docker` |
| Windows | [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) |
| Linux | [Install Docker Engine](https://docs.docker.com/engine/install/) |

装完后打开 Docker Desktop（或 `sudo systemctl start docker`），确认：

```bash
docker info
```

---

## 2. Node.js 18+ 与 npx

**用途：** 通过 `npx` 调用 `@keygraph/shannon`。

| 方式 | 命令/链接 |
|---|---|
| 官方 | https://nodejs.org/ （LTS 18+） |
| macOS Homebrew | `brew install node` |
| nvm | https://github.com/nvm-sh/nvm → `nvm install 20` |

验证：

```bash
node -v    # 应 ≥ v18
npx -v
```

---

## 3. Shannon CLI

**用途：** Phase A 动态渗透引擎。本 Skill **不内置** Shannon 二进制，首次由 npx 下载。

```bash
# 推荐：交互配置 LLM 与本机环境
npx --yes @keygraph/shannon@3.3.0 setup

# 验证可调用
npx --yes @keygraph/shannon@3.3.0 --help
```

- 仓库与说明：https://github.com/KeygraphHQ/shannon  
- 许可：AGPL-3.0（使用者自行接受）  
- 需联网访问 npm registry（`registry.npmjs.org`）

严格检查（可选，会实际拉 CLI）：

```bash
SHANNON_PREFLIGHT_STRICT_CLI=1 bash "$SKILL_DIR/scripts/preflight.sh"
```

---

## 4. LLM API Key

Shannon 需要可用的模型密钥。任选：

1. `npx @keygraph/shannon@3.3.0 setup` 写入本机配置  
2. `export ANTHROPIC_API_KEY=...` / `OPENAI_API_KEY=...` 等（以 Shannon 文档为准）  
3. 项目 `.env`：`AI_GATEWAY_BASE_URL` / `AI_GATEWAY_API_KEY` / `AI_GATEWAY_MODEL`  
4. `export SHANNON_DOTENV=/绝对路径/.env`

**禁止**在对话或报告中打印密钥值。

---

## 5. 目标服务已运行

Phase A 打的是活 URL。确认 staging/本地应用可访问后再 `start.sh`。

---

## 通知用户时的话术模板

```text
当前环境还不能跑 Shannon 动态扫描，preflight 未通过：
- <FAIL 项原文>

请先安装/启动：
1. Docker Desktop 并保持 Running
2. Node.js 18+（含 npx）
3. npx --yes @keygraph/shannon@3.3.0 setup
4. 配置 LLM API Key

完成后告诉我「依赖已就绪」，我再继续 Phase A。
若只做白盒审查，可改用 whitebox-only 模式（不启 Shannon）。
```
