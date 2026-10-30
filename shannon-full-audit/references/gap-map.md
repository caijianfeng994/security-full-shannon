# Shannon 缺口 ↔ 白盒 vendor 映射

对照历史结论：Shannon 相对 Codebuddy `layer-master` 漏扫主要集中在 DoS / 业务逻辑 / 竞态 / 缓存 / panic / 认证中间件路径。

| 缺口类型 | 优先加载 | 产出文件 | 期望覆盖 |
|---|---|---|---|
| 业务逻辑缺陷 | `vendors/utkusen-sast-skills/sast-businesslogic/SKILL.md` + `vendors/code-vulnscan/business-logic-analyzer.md` | `businesslogic-results.md` | 高 |
| 竞态 / TOCTOU | 同上（竞态类别） | 同上 | 高 |
| 扇出 / 递归 / 无超时 / 解压放大 | `vendors/cloudflare-security-audit/RESOURCE-EXHAUSTION-AND-AVAILABILITY.md` | `resource-exhaustion.md` | 高（静态） |
| gRPC / 消息扇出 | `PROTOCOLS-RPC-AND-MESSAGING.md` | 可并入资源耗尽 | 中高 |
| 认证中间件 / 身份混淆 / HTTP 缓存键 | `WEB-PROTOCOL-AND-AUTH.md` + `auth-reviewer.md` + `api-security-reviewer.md` | `auth-middleware.md` | **高（P0）** |
| 缓存投毒 / 租户隔离 / 删除生命周期 | `DATA-ISOLATION-AND-LIFECYCLE.md` + `application-vuln-reviewer.md` | `cache-poisoning.md` | **高（P0）** |
| Go nil/panic、中间件、SSRF | `vendors/code-vulnscan/go-security-reviewer.md` | `go-review.md` | 中高 |
| 堆栈 / 错误信息泄露 | `error-handling-reviewer.md` | `go-review.md` | 中 |
| ReDoS | `regex-analyzer.md` | 可并入资源耗尽 | 中 |
| Auth / IDOR / SSRF 动态利用 | 本目录 Phase A `scripts/start.sh` | `shannon/` 报告 | 由 Shannon CLI 负责 |

## 与 Shannon 范围分工

- **不要**用白盒技能重复深挖已由 Shannon Exploited 的 SSRF/缺鉴权/IDOR，除非要补「源码根因定位」。
- **要**把白盒重点放在 Shannon scope 外或需静态根因的类（资源耗尽、缓存、panic、业务逻辑、竞态）。
- **P0 强制**：Phase B 必须写出非空的 `auth-middleware.md` 与 `cache-poisoning.md`（或「已排除」+ 证据行号）；合并报告不得省略这两栏。

## 登记粒度

对照 `layer-master` 细粒度报告：一 sink / 一函数一条候选，避免将多个水平越权或缓存问题合并为单条「大类」发现。
