# 源码证据与攻击路径产物

Phase B 定位发现后读取本规范。此阶段只读本次任务源码和已有报告，不访问目标、不运行源码、不重新启动 Shannon，也不生成利用程序。

## 分析和溯源

- 按一条发现一个路径记录，以已有漏洞编号或数据库 ID 关联，禁止另建重复漏洞。
- 从真实危险操作向上检查调用者、参数传递与控制分支。只有确实来自外部可控输入才标 `source`；配置或内部调用不能默认当成攻击者输入。
- 每个节点都要定位相对文件路径和 1-based 行号。最多 40 个节点；单个代码范围最多 80 行且 16,000 字符。
- 每条连接都要提供源码证据位置，最多 12 行。`call` 边的证据中必须出现目标函数调用；`data_flow`、`control_flow`、`blocked` 保留真实的传值、分支或阻断证据。
- 不确定调用关系就省略连接并说明。仅确认单点时只交付一个 `sink`/`control` 节点，说明“未确认上游链”。无法确认单点就登记 blocked 原因，不产出假图。
- 节点 `code` 由程序从对应源码快照读取；如手动传入代码，必须逐字匹配。不得用模型改写或伪造的代码填充。

## 输出格式

写入 `<outdir>/whitebox/vulnerability-details.json`：

```json
{
  "artifacts": [
    {
      "vuln_id": "已有漏洞编号",
      "attack_flow": {
        "summary": "只陈述已从源码确认的路径及未确认部分",
        "nodes": [
          {"id":"entry","kind":"source","label":"入口函数","function":"Entry","file_path":"相对源码文件","line":1,"end_line":8,"description":"已确认的输入来源"},
          {"id":"sink","kind":"sink","label":"危险操作","function":"Sink","file_path":"相对源码文件","line":12,"end_line":18,"description":"已确认的操作"}
        ],
        "edges": [
          {"source":"entry","target":"sink","kind":"call","label":"真实调用","evidence":{"file_path":"调用方相对文件","line":5,"end_line":5}}
        ]
      }
    }
  ]
}
```

以上仅为字段示意，必须替换为本次真实源码位置。可用 `vulnerability_id` 替代 `vuln_id`；编号重复时必须用数据库 ID。
节点 kind 为 source/step/control/sink/terminal；可选 variables 为 `{name,kind}` 列表，不根据猜测标记污点。

## 程序校验和平台入库

平台：先将原报告及漏洞登记入现有任务，再调用：

```text
shannon_save_vulnerability_details(project_identifier=项目, job_id=后台任务编号,
  workspace=固定 workspace, artifact_filename="whitebox/vulnerability-details.json")
```

工具只合并已有漏洞的 `factors.attack_flow` 与详情完整度，不改变严重度、PoC 验证、人工审核或补丁。失败时修正实际位置或说明缺失原因，不绕过校验。成功后回读已有漏洞，核对每个节点已保存真实 code/source_hash。

独立使用本技能时，将单条 `attack_flow` 对象保存为输入 JSON，然后运行：

```sh
python "$SKILL_DIR/scripts/attack_flow_artifacts.py" --source 本次源码目录 --input 单条路径.json --output 已校验路径.json
```

此脚本不请求目标，不执行源码。它拒绝路径越界和符号链接、错误行号、虚构代码、无来源连接及读取后发生变化的源码。源码索引有容量上限，达到上限要注明覆盖不完整。

平台保存源码内容指纹。历史任务没有原始指纹时，只能说明“与当前任务源码副本核对”，不能宣称已证实与历史扫描版本一致；静态路径不等于动态利用成功。

## 历史补全

平台“补全攻击路径”入口使用同一个校验器，按已有记录后台逐条补全，记录进度与失败原因，进程重启后继续。它只使用任务已有的本地源码路径或该任务工作区的克隆副本，不重新 clone、不运行扫描、不新增漏洞。没有本地源码时恢复原目录/挂载后重试。

模型分析失败或超时时，历史补全可降级为“源码证据定位”单节点：只按报告标识符匹配真实源码，不标为已确认 source/sink，不添加推测连接，并保留链路未完成原因。此类结果必须为 partial，后续可以重试完整分析。

## 对抗性审查与候选补丁

同一个 artifacts 条目现在可以独立或同时包含 `attack_flow`、`adversarial_review`、`patch`，至少一项。仍只更新已有漏洞，不得提交或伪造 `verification`。平台工具名及文件名不变。每项产物绑定同一任务源码摘要；建议传入 `expected_snapshot_digest`，版本不匹配时停止并说明。

审查结构：

```json
{
  "verdict": "insufficient_evidence",
  "confidence": null,
  "severity": "low",
  "summary": "明确已核对的主张、证据与不足",
  "trigger_steps": [{"stage":"入口","location":"实际文件与行号或未确认","function":"实际函数或未确认","flow":"已核对流转或待核对","protection":"实际防护或待核对"}],
  "dimensions": [{"name":"鉴权","conclusion":"待核对","description":"具体依据与限制"}, {"name":"可达性","conclusion":"待核对","description":"具体依据与限制"}, {"name":"可控性","conclusion":"待核对","description":"具体依据与限制"}, {"name":"校验","conclusion":"待核对","description":"具体依据与限制"}, {"name":"防护","conclusion":"待核对","description":"具体依据与限制"}, {"name":"影响","conclusion":"待核对","description":"具体依据与限制"}],
  "ruling": {"conclusion":"证据不足","feasibility":"未确认","value":"影响未确认","self_refutation":"实际反证及剩余不确定性"},
  "upstream_verification": {"method":"static","status":"unverified","summary":"已核对和未核对的链路"},
  "evidence_refs": [],
  "limitations": ["未执行动态验证"]
}
```

这只是契约示例，不能把示例当作实际审查结果。verdict 为 trusted/untrusted/insufficient_evidence；确定性结论必须提供真实 `{file_path,line,end_line}` 源码引用。检查维度应覆盖入口可达性、输入可控性、身份与权限、参数校验、防护和实际影响。主动核对反证，不用扫描状态或固定置信度代替独立审查。平台从结构化数据生成可读全文，不能另写与字段矛盾的全文。

补丁结构：`{disposition,summary,explanation,diff,blocked_reason,limitations}`。disposition 为 candidate/blocked/not_applicable。candidate 必须提供真实 unified diff（`--- a/项目相对路径`、`+++ b/项目相对路径`），只修改本快照中现有源码文件，最多 10 文件、1500 行、120000 字符。不支持新增/删除文件、二进制、重命名。完整根因修复需要新增文件时明确受阻，不伪造缩减版修复。

平台把相关文件复制到临时目录，运行 `git apply --check` 检查适用性；不会执行源码、自动应用到原仓库或提交 Git。适用性通过不代表漏洞修复或任何测试通过。blocked/not_applicable 必须提供原因和修复/待确认说明，diff 为空。已应用补丁不得被候选覆盖。

独立交付时使用相同校验脚本，选择 `--kind review` 或 `--kind patch`；默认 `--kind evidence`。补丁校验需要已安装 Git。平台负责生成时间、来源、摘要、真实代码及验证元数据，不信任客户端声明的“检查通过”。

平台历史任务入口可选择补全全部详情，也可在三个 Tab 单独生成；重新生成失败应保留此前有效结果。模型超时时只保存明确的证据不足/补丁受阻说明，不假造报告或 Diff，不把任务执行成功当作风险已确认。
