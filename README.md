# security-full-shannon

Shannon 全量审计技能 `shannon-full-audit`：动态渗透（Shannon CLI）加白盒补盲。

## 安装

```bash
git clone git@github.com:caijianfeng994/security-full-shannon.git
cp -R security-full-shannon/shannon-full-audit ~/.claude/skills/shannon-full-audit
```

安装后阅读 `shannon-full-audit/INSTALL.md`。

## 配置

本仓库不包含密钥、内网网关地址或代码托管主机。

- LLM：在本地环境变量或项目 `.env` 中设置 `AI_GATEWAY_BASE_URL`、`AI_GATEWAY_API_KEY`、`AI_GATEWAY_MODEL`。`references/models.gateway.json` 里的 `baseUrl` 与 `apiKey` 是占位符，请改成自己的值，不要把真实密钥提交回本仓库。
- 克隆源码：执行 `scripts/clone_repos.sh` 前必须设置 `SHANNON_GITLAB_HOST`。

## 许可

白盒材料为 MIT 节选，见 `shannon-full-audit/THIRD_PARTY_NOTICES.md`。Shannon CLI 为 AGPL-3.0，不随本仓库分发。
