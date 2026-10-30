# 合并报告写法

## 原则

1. **来源分离**：动态已利用 vs 白盒候选，禁止混称「已利用」。
2. **中文列表字段**：标题、状态、对抗审查、分类等对用户展示用中文；路径/API/参数名保留原文。
3. **严重度**：Shannon 已用的 Critical/High/… 映射为 严重/高危/中危/低危；白盒自估需写依据一句。
4. **去重**：同一根因（如 fileUrl SSRF）只保留一条主记录，其它标为「同源变体」。

## merged-report.md 模板

```markdown
# 安全评估合并报告（Shannon + 白盒）

## 元信息
| 项 | 内容 |
|---|---|
| 目标 | |
| 源码 | |
| Shannon workspace | |
| 白盒模式 | full / whitebox-only |
| 日期 | |

## 覆盖摘要
| 类别 | Shannon | 白盒 | 备注 |
|---|---|---|---|
| 认证/授权/SSRF | | | 白盒：`auth-middleware.md` |
| 业务逻辑/竞态 | | | |
| 资源耗尽（含解压放大） | | | |
| 缓存投毒 / 租户隔离 / 删除 | | | 白盒：`cache-poisoning.md`（P0 强制） |

## A. 动态已证实（Shannon）
| 编号 | 标题 | 严重程度 | 证据摘要 |
|---|---|---|---|

## B. 白盒候选
| 编号 | 标题 | 严重程度 | 来源 | 置信度 | 文件 |
|---|---|---|---|---|---|
（按 sink 拆条；注明来自 auth-middleware / cache-poisoning / businesslogic / resource / go-review）

## C. 待验证（needs_validation）
- …

## D. 明确未覆盖
- 仅当某 P0 步骤无法完成时填写，并写已读 vendor 与排除证据
```

## 入库提示（可选）

若需写入平台 `pentest_vulnerabilities`：

- Shannon 条：`poc_verify_status=passed`（已利用），`scan_engine=Shannon`
- 白盒条：`poc_verify_status=unverified`，`scan_engine=shannon-full-audit-whitebox`，`factors` 中保留 `source` / `confidence`
- **粒度**：一 sink / 一函数一条；勿将多个 IDOR 或缓存问题合并为单条大类
