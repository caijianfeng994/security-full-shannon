# 第三方声明（THIRD_PARTY_NOTICES）

本目录为 **自包含** Skill：含 Phase A 启动脚本（本仓库编写）与 Phase B `vendors/` 节选。
不依赖 sibling `shannon-pentest`。

## MIT 白盒 vendor

| 组件 | 上游 | SPDX | 收录范围 |
|---|---|---|---|
| utkusen-sast-skills | [utkusen/sast-skills](https://github.com/utkusen/sast-skills) | MIT | `sast-analysis`、`sast-businesslogic` |
| code-vulnscan | [Bhanunamikaze/Code-VulnScan-Skill](https://github.com/Bhanunamikaze/Code-VulnScan-Skill) | MIT | `go-security-reviewer`、`business-logic-analyzer`、`error-handling-reviewer`、`regex-analyzer`、`scan-strategy`、`auth-reviewer`、`api-security-reviewer`、`application-vuln-reviewer` |
| cloudflare-security-audit | [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | MIT | `RESOURCE-EXHAUSTION-AND-AVAILABILITY`、`ATTACK-CLASSES`、`PROTOCOLS-RPC-AND-MESSAGING`、`DATA-ISOLATION-AND-LIFECYCLE`、`WEB-PROTOCOL-AND-AUTH` |

各组件完整 LICENSE 见对应 `vendors/*/LICENSE`。

## Shannon CLI（不入库）

[KeygraphHQ/shannon](https://github.com/KeygraphHQ/shannon) 为 **AGPL-3.0**。本 Skill **不 vendoring** 其源码，仅通过 `npx @keygraph/shannon` **调用已安装的 CLI**。

## Phase A 脚本

`scripts/`、`references/config.md`、`references/models.gateway.json` 为本交付包自有封装（启动 / 预检 / clone / 网关映射），可随本目录一并分发。网关地址与 API Key 使用占位符，由使用方本地填写，不要提交真实密钥。
