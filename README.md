# security-full-shannon

Shannon 全量审计技能 `shannon-full-audit`：动态渗透（Shannon CLI）加白盒补盲。

## 安装

```bash
git clone git@github.com:caijianfeng994/security-full-shannon.git
cp -R security-full-shannon/shannon-full-audit ~/.claude/skills/shannon-full-audit
```

安装后阅读 `shannon-full-audit/INSTALL.md`。

## 使用前必须改的配置

仓库里没有真实密钥和内网地址。下面三处用占位符，扫自己的目标前在本地改掉，不要把真实值提交回本仓库。

### 1. 网关地址和 API Key

文件：`shannon-full-audit/references/models.gateway.json`

| 字段 | 仓库里的占位值 | 要改成 |
|---|---|---|
| `baseUrl` | `https://YOUR_AI_GATEWAY_HOST/v1` | 自己的 OpenAI 兼容网关地址，以 `/v1` 结尾 |
| `apiKey` | `YOUR_API_KEY` | 自己的 API Key |

也可以不改文件，改用环境变量或项目 `.env`（`scripts/load_ai_gateway.sh` 会读取，且不会打印密钥）：

```bash
export AI_GATEWAY_BASE_URL='https://your-gateway.example.com/v1'
export AI_GATEWAY_API_KEY='your-api-key'
export AI_GATEWAY_MODEL='your-model-id'
```

`AI_GATEWAY_MODEL` 必须和 `models.gateway.json` 里某个模型的 `id` 一致。当前示例是 `deepseek-v4-pro`，换成别的模型时，同时改这个 `id` 和 `AI_GATEWAY_MODEL`。

### 2. 模型 provider 名称

provider 名固定为 `custom-gateway`，写在 `models.gateway.json` 的 `providers` 键上。

设置了 `AI_GATEWAY_MODEL` 后，启动脚本会把它映射成：

```text
SHANNON_AI_MODEL=custom-gateway:<AI_GATEWAY_MODEL>
SHANNON_MODELS_CONFIG=<技能目录>/references/models.gateway.json
```

不要改 provider 名。Shannon 用这个前缀到 `models.gateway.json` 里找网关；改了名字就会对不上。

### 3. GitLab 主机

`scripts/clone_repos.sh` 没有默认主机。自动克隆源码前必须设置：

```bash
export SHANNON_GITLAB_HOST='gitlab.example.com'
bash scripts/clone_repos.sh -d /path/to/src group/repo
```

可选：`SHANNON_GIT_BRANCH` 指定分支。已有本地源码、用 `-r` 直接传入时，不用设这个变量。

## 许可

白盒材料为 MIT 节选，见 `shannon-full-audit/THIRD_PARTY_NOTICES.md`。Shannon CLI 为 AGPL-3.0，不随本仓库分发。
