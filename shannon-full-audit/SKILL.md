---
name: shannon-full-audit
description: >-
  自包含：Shannon CLI 动态渗透 + 白盒 SAST 补盲（业务逻辑/竞态/资源耗尽/Go）。
  用户说「Shannon 全量审」「补 Shannon 盲区」「动态+白盒一起扫」「shannon-full-audit」时使用。
  本目录含 scripts/ 与 vendors/，不依赖 sibling shannon-pentest。
  禁止本 Agent 自行写 exploit；禁止对未授权/生产目标做可用性压测。
---

# Shannon Full Audit（自包含：动态 + 白盒补盲）

## 定位

**本 Skill 是独立交付包。** 拷贝本目录即可使用，不依赖同级 `shannon-pentest` 或其他平台 Skill。

流水线：

| 阶段 | 内容 | 资产（均在本目录） |
|---|---|---|
| Phase A | Shannon CLI 动态利用 | `scripts/*.sh`、`references/config.md` |
| Phase B | 白盒补盲 | `vendors/**` |
| Phase C | 合并报告 | `references/report-merge.md`、`gap-map.md` |

| Shannon 默认范围外的缺口 | 怎么补 |
|---|---|
| 业务逻辑 / 工作流绕过 | `vendors/utkusen-sast-skills/sast-businesslogic` + `vendors/code-vulnscan/business-logic-analyzer.md` |
| 竞态 / TOCTOU | 同上 |
| 资源耗尽 / 扇出 DoS / 解压放大 | `vendors/cloudflare-security-audit/RESOURCE-EXHAUSTION-AND-AVAILABILITY.md`（只读推断） |
| 缓存投毒 / 租户隔离 / 删除生命周期 | `DATA-ISOLATION-AND-LIFECYCLE.md` + `application-vuln-reviewer.md` |
| 认证中间件 / 身份混淆 / HTTP 缓存键 | `WEB-PROTOCOL-AND-AUTH.md` + `auth-reviewer.md` + `api-security-reviewer.md` |
| Go / panic / 错误泄露 | `go-security-reviewer.md` + `error-handling-reviewer.md` |
| ReDoS | `regex-analyzer.md` |
| Auth / SSRF / IDOR 动态证实 | Phase A：本目录 `scripts/start.sh` → `npx @keygraph/shannon` |

许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。安装见 [INSTALL.md](INSTALL.md)。依赖速查见 [references/prerequisites.md](references/prerequisites.md)。

**SKILL_DIR**：本 `SKILL.md` 所在目录的绝对路径。下文 `$SKILL_DIR` 均指该路径。

## 何时用

- 已授权目标 URL + 本地源码（或可 clone）
- 需要动态利用证据 + 白盒补 DoS/逻辑/竞态

模式：`full`（默认）/ `whitebox-only` / `shannon-only`

## 输入与输出

| 槽位 | 必填 | 说明 |
|---|---|---|
| 目标 URL `-u` | Phase A | staging/本地；受授权门禁约束 |
| 源码 `-r` | A/B | 本地目录；可自动定仓后 clone |
| `-c` | 否 | 登录/TOTP YAML，见 `references/config.md` |
| `workspace` | 否 | 默认 `shannon-full-<YYYYMMDD-HHMM>` |

```text
web-output/shannon-full-audit/<workspace>/   # 或 SHANNON_OUTPUT_ROOT
  shannon/                 # Phase A Shannon 报告
  src/                     # 可选：自动 clone 的源码
  whitebox/
    architecture.md
    auth-middleware.md       # 认证/中间件/IDOR（P0）
    businesslogic-results.md
    resource-exhaustion.md
    cache-poisoning.md       # 缓存/租户隔离/删除（P0）
    go-review.md
    merged-report.md
    vulnerability-details.json # 每条漏洞的源码节点与连接证据
```

## 授权门禁（Phase A 不过不启动）

1. 用户明确授权本次目标（自有或书面授权）。
2. URL **不是**生产主站（无书面确认）。默认：`localhost`、内网、`*-stage*`、`*-test*`、白名单。
3. `SHANNON_I_AUTHORIZE=1`，或用户本轮明确写出「我授权扫描」并带完整 URL。
4. 可选：`SHANNON_ALLOWED_HOSTS=host1,host2`。

Phase B：默认只读源码；禁止对生产做真实可用性压测。动态利用 **只允许** Shannon CLI，禁止 Agent 自写 exploit。

## 本机依赖门禁（缺则先通知用户安装）

Phase A / `full` / `shannon-only` **开始前必须**：

```bash
bash "$SKILL_DIR/scripts/preflight.sh"
```

| 依赖 | 用途 | 用户未安装时 Agent 必须做的事 |
|---|---|---|
| Docker（daemon Running） | Shannon worker | 停止任务，给出 Desktop/Engine 安装链接与启动方法 |
| Node.js 18+ / npx | 调用 `@keygraph/shannon` | 停止任务，给出 nodejs.org / brew / nvm 安装方式 |
| Shannon CLI（经 npx） | 动态扫描 | 告知执行 `npx --yes @keygraph/shannon@3.3.0 setup`；链到 GitHub |
| LLM API Key | 模型调用 | 告知 setup 或配置 Key / `.env`，**不打印密钥** |

**硬性规则：**

1. `preflight.sh` 退出码非 0 → **禁止**调用 `start.sh` / `npx … start`。
2. 把脚本输出的每条 `FAIL` 与 `→` 安装提示 **原样转述给用户**（可用 `references/prerequisites.md` 话术模板）。
3. 等用户回复「依赖已就绪」后再重跑 preflight；通过后才继续。
4. 用户只要白盒、本机没有 Docker/Shannon → 建议改 `whitebox-only`，并说明将跳过动态利用。
5. 详细步骤以 [INSTALL.md](INSTALL.md) 与 [references/prerequisites.md](references/prerequisites.md) 为准，不要临场编造错误安装命令。
6. **禁止 `find /` 与全盘搜索**（会卡死）。白盒搜文件只用源码根，例如：
   `find /tmp/layer-src -name '*.go' | head` 或 `rg -n 'pattern' /tmp/layer-src`。

可选严格校验 CLI 可拉取：

```bash
SHANNON_PREFLIGHT_STRICT_CLI=1 bash "$SKILL_DIR/scripts/preflight.sh"
```

目标应用须已在跑（Phase A）。

## 执行流程

```
Task Progress:
- [ ] 确认模式与授权；解析 SKILL_DIR
- [ ] 若含 Phase A：先 preflight；失败则通知安装并停止
- [ ] 有本地 -r，否则自动定仓并 clone 到输出目录/src
- [ ] Phase A：本目录 scripts 启动 Shannon（仅用户明确 `shannon-only` 才可在此后停止）
- [ ] Phase A 结束判定：宿主机已有 `*_exploitation_evidence.md`。报告 agent 失败或停在 reporting 时，导出 deliverables 后继续，禁止空等
- [ ] Phase B：白盒补盲（默认必做；仅 `whitebox-only` 跳过 A，仅 `shannon-only` 跳过本步）
- [ ] Phase C：合并报告。`whitebox/auth-middleware.md`、`cache-poisoning.md`、`merged-report.md` 缺任一，不得把任务标完成
- [ ] 有源码的发现：按 references/attack-flow-artifacts.md 生成并校验结构化详情；源码/链路不足时单独登记原因，不伪造节点
```

---

### Phase A — Shannon 动态（本目录脚本）

Shannon Open Source 是白盒：`-r` 必须是本地目录。不会调 CodeWiki；定仓是 Agent 可选能力。

**自动取源（用户未给 `-r`）** — 可选，有 CodeWiki/GitNexus 时：

```
Resolve Progress:
- [ ] search_wiki / list_gitnexus_repos 定候选仓
- [ ] 置信度低或候选 >3：让用户确认
- [ ] bash "$SKILL_DIR/scripts/clone_repos.sh" -d '<outdir>/src' group/repo ...
- [ ] -r 指向该 src（或多仓父目录）
```

无 MCP 时：直接向用户要本地源码路径。

**启动：**

```bash
export SHANNON_I_AUTHORIZE=1
bash "$SKILL_DIR/scripts/start.sh" \
  -u 'https://staging.example.com' \
  -r '/abs/path/to/target-repo' \
  -w 'shannon-full-20260928-1500'
```

等价：

```bash
npx @keygraph/shannon@3.3.0 start \
  -u 'https://staging.example.com' \
  -r '/abs/path/to/target-repo' \
  -w 'shannon-full-20260928-1500' \
  -o 'web-output/shannon-full-audit/shannon-full-20260928-1500/shannon'
```

登录态加 `-c`；写法见 [references/config.md](references/config.md)。

完整扫描约 1–1.5h：`start` 必须后台（`block_until_ms: 0`），再轮询：

```bash
npx @keygraph/shannon@3.3.0 status --json
npx @keygraph/shannon@3.3.0 logs
npx @keygraph/shannon@3.3.0 stop   # 需用户确认
```

Phase A 结束以利用证据落盘为准，不以 Shannon 报告 agent 成功为准。宿主机出现 `*_exploitation_evidence.md` 后，`full` 模式必须进入 Phase B。报告 agent 失败或一直停在 reporting：把 worker 内 `/app/workspaces/<workspace>/.shannon/deliverables` 拷到 `<outdir>/shannon/deliverables/`，然后做白盒。禁止空等 Temporal 重试，禁止为此再次 `start`。

只把 **Exploited / 已利用** 记为「动态已证实」；不要复述可复制攻击手册。

---

### Phase B — 白盒补盲

产物：`<outdir>/whitebox/`。渐进 Read，勿一次塞满上下文。路径均相对 `$SKILL_DIR`。  
**登记粒度**：按 sink/函数拆条，禁止把多个 IDOR/缓存问题并成一条「大类」发现。

1. **架构** — Read `vendors/utkusen-sast-skills/sast-analysis/SKILL.md` → `architecture.md`
2. **认证 / 中间件 / IDOR（P0）** — Read  
   `vendors/cloudflare-security-audit/WEB-PROTOCOL-AND-AUTH.md`、  
   `vendors/code-vulnscan/auth-reviewer.md`、  
   `vendors/code-vulnscan/api-security-reviewer.md`  
   → `auth-middleware.md`（uid/header 信任、bd/fe 鉴权、水平越权、删除类副作用接口）
3. **业务逻辑+竞态** — Read `vendors/utkusen-sast-skills/sast-businesslogic/SKILL.md`；对照 `vendors/code-vulnscan/business-logic-analyzer.md` → `businesslogic-results.md`
4. **资源耗尽（静态）** — Read `vendors/cloudflare-security-audit/RESOURCE-EXHAUSTION-AND-AVAILABILITY.md`；RPC 扇出再读 `PROTOCOLS-RPC-AND-MESSAGING.md`；总览 `ATTACK-CLASSES.md` → `resource-exhaustion.md`  
   须覆盖：无界扇出、递归、**解压/表示放大（zip 等）**、断连后仍占用。  
   **不得**对线上打真实 DoS。沙箱执行不可用则只静态推断并标 `needs_validation`。
5. **缓存投毒 / 租户隔离 / 删除生命周期（P0）** — Read  
   `vendors/cloudflare-security-audit/DATA-ISOLATION-AND-LIFECYCLE.md`、  
   `vendors/code-vulnscan/application-vuln-reviewer.md`（cache/data leakage、upload）  
   → `cache-poisoning.md`（cache key 碰撞/跨租户、ACL 漂移、失败写缓存、无归属 DelCache）
6. **Go / 错误 / ReDoS** — `vendors/code-vulnscan/go-security-reviewer.md`、`error-handling-reviewer.md`、`regex-analyzer.md` → `go-review.md`
7. 大仓可选：`vendors/code-vulnscan/scan-strategy.md`

8. **源码证据与攻击路径** — Read [references/attack-flow-artifacts.md](references/attack-flow-artifacts.md)。
   对已定位的每条发现追踪入口、传播、条件分支与危险操作；每个节点提供真实文件及行号，连接提供对应源码证据。
   程序从源码读取代码，禁止模型补写代码片段。只确认单点就保存单点并标明未确认上游链，不为了图形完整添加节点。

---

### Phase C — 合并

Read [references/report-merge.md](references/report-merge.md)、[references/gap-map.md](references/gap-map.md)。  
写出 `whitebox/merged-report.md`：动态已证实与白盒候选分栏；白盒标 `source` / `confidence`。  
须并入 `auth-middleware.md` 与 `cache-poisoning.md`；若某 P0 文件为空，须在「明确未覆盖」写明原因与已读 vendor。

按 [结构化详情规范](references/attack-flow-artifacts.md) 写出 `whitebox/vulnerability-details.json`。
平台内先登记漏洞，再调用 `shannon_save_vulnerability_details` 校验并更新已有记录，回读核对 `attack_flow` 与节点 `code`、`adversarial_review` 的独立审查及反证、`patch` 的候选 Diff 与适用性检查。
每条漏洞必须交付审查产物；证据不足或无法形成补丁时保存具体原因。补丁不得自动应用，生成不改变 PoC/静态/回归验证结果。
平台外用本目录 `scripts/attack_flow_artifacts.py` 做源码校验并交付 JSON。扫描完成与详情完整度分别记录；缺源码或校验失败要给出原因。

## 用法示例

```text
用 shannon-full-audit 扫 https://xxx-stage.example.com，源码 /path/to/layer，完整动态+白盒。
```

```text
shannon-full-audit whitebox-only：只审 /path/to/layer 的业务逻辑/竞态/资源耗尽。
```

```text
Shannon 报告已在 …/shannon/，用 shannon-full-audit 只做 Phase B 并合并。
```

## 目录结构（交付包）

```text
shannon-full-audit/
├── SKILL.md
├── INSTALL.md
├── THIRD_PARTY_NOTICES.md
├── scripts/          # Phase A 自包含
├── references/       # config、合并模板、缺口映射、网关模型描述
└── vendors/          # MIT 白盒节选（utkusen / Code-VulnScan / Cloudflare）
```

## 明确不做

- 不依赖、不调用 sibling `shannon-pentest`
- 不 fork Shannon 源码；不改写 Shannon 内部阶段
- 不把 API Key 写入 Skill 或 git
- 不宣称可 100% 复现任意商业 SAST 全量发现
