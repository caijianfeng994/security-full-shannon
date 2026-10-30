"""Shared, stdlib-only source snapshot and attack-flow validation.

No target requests, shell execution, source execution, or generated code snippets.
This module travels with the standalone skill and is also loaded by the platform.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

EXTENSIONS = {".go", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".cs", ".php", ".rb", ".rs", ".c", ".cpp", ".h"}
IGNORE = {".git", ".venv", "venv", "node_modules", "vendor", "dist", "build", "target", "__pycache__", ".next"}
MAX_FILE = 512 * 1024
MAX_SOURCE = 12 * 1024 * 1024
KINDS = {"source", "step", "control", "sink", "terminal"}


class ArtifactError(ValueError): pass


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_root(value):
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or root == Path.home():
        raise ArtifactError("源码根目录必须是具体的项目目录")
    return root


def relative_name(value):
    name = str(value).replace("\\", "/")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or ".." in path.parts or ":" in name or any(part.startswith(".") for part in path.parts):
        raise ArtifactError("源码路径必须是项目内的相对路径")
    if path.suffix.lower() not in EXTENSIONS:
        raise ArtifactError("只允许提取源码文件")
    return str(path)


def read_source(root, name):
    """Open each path component without following symlinks on POSIX."""
    name = relative_name(name)
    path = root / name
    try:
        path.resolve(strict=True).relative_to(root)
        for parent in (path, *path.parents):
            if parent == root: break
            if parent.is_symlink(): raise ArtifactError("不读取符号链接源码")
        if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                parts = PurePosixPath(name).parts
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd); fd = child
                file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            finally:
                os.close(fd)
            stream = os.fdopen(file_fd, "rb")
        else:
            stream = path.open("rb")
        with stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE:
                raise ArtifactError("源码文件过大或不是普通文件")
            data = stream.read(MAX_FILE + 1)
        if len(data) > MAX_FILE: raise ArtifactError("源码文件超过大小限制")
        return data.decode("utf-8").replace("\r\n", "\n")
    except (OSError, UnicodeError, ValueError) as exc:
        if isinstance(exc, ArtifactError): raise
        raise ArtifactError(f"无法读取源码 {name}") from None


def snapshot(value):
    root = source_root(value)
    files, hashes, warnings = {}, {}, []
    size = 0
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE and not d.startswith(".") and not (Path(current) / d).is_symlink())
        for filename in sorted(names):
            if Path(filename).suffix.lower() not in EXTENSIONS: continue
            name = (Path(current) / filename).relative_to(root).as_posix()
            try: content = read_source(root, name)
            except ArtifactError: continue
            if len(files) >= 3000 or size + len(content.encode()) > MAX_SOURCE:
                warnings.append("源码索引达到容量限制，仅分析已读取部分")
                break
            files[name] = content; hashes[name] = digest(content); size += len(content.encode())
        if warnings: break
    if not files: raise ArtifactError("该目录没有可读取的受支持源码文件")
    fingerprint = digest(json.dumps(hashes, sort_keys=True))
    return {"root": str(root), "files": files, "hashes": hashes, "digest": fingerprint, "warnings": warnings}


def context_for(snapshot, finding):
    """Bounded retrieval; candidate snippets are context, never inferred edges."""
    blob = json.dumps(finding, ensure_ascii=False)
    hints = re.findall(r"[\w./-]+\.(?:go|py|tsx?|jsx?|java|kt|cs|php|rb|rs|cpp|c|h)(?::\d+(?:-\d+)?)?", blob)
    tokens = list(dict.fromkeys(re.findall(r"\b([A-Za-z_]\w{3,80})(?=\s*\()|`([A-Za-z_]\w{3,80})`", blob)))
    words = list(dict.fromkeys(a or b for a, b in tokens if a or b))[:50]
    words += re.findall(r"/[A-Za-z0-9_/-]{5,100}", blob)[:20]
    # Plain endpoint names and a few high-signal identifiers help legacy reports
    # which contain API paths but no source path.
    words += [word for word in ("pprof", "GetUserAuthList", "DoZlibUnCompress") if word.lower() in blob.lower()]
    explicit = {}
    for hint in hints:
        parts = hint.split(":", 1)
        matches = [name for name in snapshot["files"] if name == parts[0] or name.endswith("/" + parts[0]) or parts[0].endswith("/" + name)]
        if len(matches) == 1:
            explicit[matches[0]] = int(parts[1].split("-")[0]) if len(parts) > 1 else None
    ranked = []
    for name, content in snapshot["files"].items():
        score = (100 if name in explicit else 0) + sum(min(content.count(word), 4) for word in words)
        if score: ranked.append((score, name))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    slices, used, total = [], {}, 0
    for _, name in ranked[:10]:
        lines = snapshot["files"][name].splitlines()
        anchors = [explicit[name]] if explicit.get(name) else []
        anchors += [i + 1 for i, line in enumerate(lines) if any(word in line for word in words)]
        if not anchors and name in explicit: anchors = [1]
        last_end = 0
        for anchor in anchors:
            start, end = max(1, anchor - 18), min(len(lines), anchor + 30)
            if start <= last_end: continue
            snippet = "\n".join(f"{i}: {lines[i-1]}" for i in range(start, end + 1))
            if total + len(snippet) > 45000: break
            slices.append({"file_path": name, "start_line": start, "end_line": end, "text": snippet})
            used.setdefault(name, []).append((start, end))
            total += len(snippet); last_end = end
            if len(used[name]) >= 2: break
    return {"snippets": slices, "allowed": used, "search_terms": words, "preferred_files": list(explicit)}


def locate_evidence(context):
    """Degraded operation: locate an identifier, without asserting a vulnerability or edge."""
    candidates = []
    preferred = context.get("preferred_files", [])
    terms = context.get("search_terms", [])
    for snippet in context["snippets"]:
        if preferred and snippet["file_path"] not in preferred: continue
        for numbered in snippet["text"].splitlines():
            number, _, line = numbered.partition(": ")
            if not number.isdigit() or line.strip().startswith(("#", "//", "/*", "*", "import ", "from ", '"')): continue
            matched = [term for term in terms if term in line]
            if not matched: continue
            score = len(matched) + (3 if "(" in line else 0)
            candidates.append((score, int(number), snippet))
    if not candidates: raise ArtifactError("未定位到可降级展示的源码标识符；保留原始证据")
    _, anchor, snippet = max(candidates, key=lambda item: item[0])
    return {"summary": "仅定位原报告关联的源码标识符；尚未完成攻击链分析，不据此确认漏洞或动态可利用性。", "nodes": [{
        "id": "source-location", "kind": "step", "label": "源码证据定位（链路待分析）",
        "description": "按原报告中的文件及标识符定位；此节点不是已验证攻击链。",
        "file_path": snippet["file_path"], "line": max(snippet["start_line"], anchor - 8),
        "end_line": min(snippet["end_line"], anchor + 8)}], "edges": []}


def _snippet(snapshot, item, allowed=None):
    name = relative_name(item.get("file_path", ""))
    start, end = item.get("line"), item.get("end_line", item.get("line"))
    if type(start) is not int or type(end) is not int or start < 1 or end < start or end - start >= 80:
        raise ArtifactError("代码范围必须为有效的 1-based 行号，最多 80 行")
    if name not in snapshot["files"]: raise ArtifactError("节点文件不在本次源码快照内")
    if allowed is not None and not any(a <= start <= end <= b for a, b in allowed.get(name, [])):
        raise ArtifactError("节点引用了未提供给分析过程的代码位置")
    lines = snapshot["files"][name].splitlines()
    if end > len(lines): raise ArtifactError("节点行号超出真实文件范围")
    code = "\n".join(lines[start - 1:end])
    if len(code) > 16000: raise ArtifactError("单个代码片段超过 16,000 字符")
    if item.get("code") is not None and str(item["code"]).strip("\n") != code.strip("\n"):
        raise ArtifactError("提交的节点代码与真实源码不一致")
    return {"file_path": name, "line": start, "end_line": end, "code": code, "source_hash": snapshot["hashes"][name]}


def _code_only(content):
    # Preserve line numbers while excluding quoted examples and comments. This
    # is a conservative lexical check, not a language-specific call-graph proof.
    pattern = r'"""[\s\S]*?"""|\x27\x27\x27[\s\S]*?\x27\x27\x27|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|`[^`]*`|/\*[\s\S]*?\*/|//[^\n]*|\#[^\n]*'
    return re.sub(pattern, lambda match: "\n" * match.group(0).count("\n"), content)


def hydrate(snapshot, proposal, allowed=None, expected_digest=None):
    if expected_digest and expected_digest != snapshot["digest"]:
        raise ArtifactError("源码快照已变化，禁止将不同版本的代码拼接入库")
    if not isinstance(proposal, dict): raise ArtifactError("攻击路径必须是 JSON 对象")
    raw_nodes, raw_edges = proposal.get("nodes"), proposal.get("edges", [])
    if not isinstance(raw_nodes, list) or not 1 <= len(raw_nodes) <= 40 or not isinstance(raw_edges, list) or len(raw_edges) > 100:
        raise ArtifactError("每条路径需要 1–40 个真实节点，最多 100 条边")
    nodes, ids = [], set()
    for item in raw_nodes:
        if not isinstance(item, dict): raise ArtifactError("节点必须是对象")
        nid, kind = item.get("id"), item.get("kind")
        if not isinstance(nid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", nid) or nid in ids or kind not in KINDS:
            raise ArtifactError("节点 ID 重复、格式错误或节点类型无效")
        ids.add(nid)
        for key, limit in (("label", 300), ("function", 200), ("description", 4000)):
            if key in item and (not isinstance(item[key], str) or len(item[key]) > limit):
                raise ArtifactError("节点文本格式或长度无效")
        if "variables" in item and (not isinstance(item["variables"], list) or len(item["variables"]) > 50):
            raise ArtifactError("节点变量必须为最多 50 项的列表")
        for variable in item.get("variables", []):
            if not isinstance(variable, dict) or any(not isinstance(variable.get(key, ""), str) or len(variable.get(key, "")) > 300 for key in ("name", "kind")):
                raise ArtifactError("节点变量格式无效")
        nodes.append({**{key: item[key] for key in ("id", "kind", "label", "function", "description", "variables") if key in item}, **_snippet(snapshot, item, allowed)})
    edges = []
    by_id = {item["id"]: item for item in nodes}
    for edge in raw_edges:
        if not isinstance(edge, dict) or edge.get("source") not in ids or edge.get("target") not in ids or edge.get("source") == edge.get("target"):
            raise ArtifactError("连接必须引用不同的真实节点")
        proof = edge.get("evidence")
        if not isinstance(proof, dict): raise ArtifactError("每条连接必须提供源码证据位置")
        if edge.get("kind") not in {"call", "data_flow", "control_flow", "blocked"}:
            raise ArtifactError("连接类型无效")
        evidence = _snippet(snapshot, proof, allowed)
        if evidence["end_line"] - evidence["line"] >= 12:
            raise ArtifactError("连接证据最多 12 行")
        if edge.get("kind") == "call":
            caller, callee = by_id[edge["source"]], by_id[edge["target"]]
            function = str(callee.get("function", "")).split(".")[-1]
            code = _code_only(snapshot["files"][evidence["file_path"]]).splitlines()[evidence["line"] - 1:evidence["end_line"]]
            matches = [line for line in code if re.search(r"\b" + re.escape(function) + r"\s*\(", line) and not line.strip().startswith(("func ", "def ", "function ", "class "))]
            if not function or evidence["file_path"] != caller["file_path"] or not caller["line"] <= evidence["line"] <= evidence["end_line"] <= caller["end_line"] or not matches:
                raise ArtifactError("调用边证据中未找到对应函数调用")
        edges.append({key: edge[key] for key in ("source", "target", "label", "kind") if key in edge} | {"evidence": evidence})
    # Re-read only referenced files, detecting edits during model analysis.
    for name in {item["file_path"] for item in nodes} | {edge["evidence"]["file_path"] for edge in edges}:
        if digest(read_source(Path(snapshot["root"]), name)) != snapshot["hashes"][name]:
            raise ArtifactError("分析期间源码已变化，请重新补全")
    return {"summary": str(proposal.get("summary", ""))[:4000], "nodes": nodes, "edges": edges,
            "provenance": {"snapshot_digest": snapshot["digest"], "analysis_kind": "static", "code_verified": True,
                           "historical_version_verified": False, "warnings": snapshot["warnings"],
                           "scope": "single_location" if len(nodes) == 1 else "source_trace"}}


# Review and patch validation shares the same source access boundary as the graph.
def _bounded_text(value, field, limit=4000, required=True):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ArtifactError(f'{field} 必须是非空文本且不超过 {limit} 字符')
    return value.strip()


def hydrate_review(snapshot, proposal, allowed=None):
    if not isinstance(proposal, dict): raise ArtifactError('审查产物必须是对象')
    verdict = proposal.get('verdict')
    if verdict not in {'trusted', 'untrusted', 'insufficient_evidence'}: raise ArtifactError('审查结论无效')
    confidence = proposal.get('confidence')
    if confidence is not None and (type(confidence) not in (int, float) or not 0 <= confidence <= 100):
        raise ArtifactError('审查置信度必须为 0–100 或 null')
    if verdict == 'insufficient_evidence': confidence = None
    severity = str(proposal.get('severity', '')).lower()
    if severity not in {'critical', 'high', 'medium', 'low', 'info'}: raise ArtifactError('审查严重性无效')
    refs = proposal.get('evidence_refs', [])
    if not isinstance(refs, list) or len(refs) > 20: raise ArtifactError('审查证据引用最多 20 项')
    if verdict != 'insufficient_evidence' and not refs: raise ArtifactError('确定性结论需要源码证据引用')
    hydrated = [_snippet(snapshot, ref, allowed) for ref in refs if isinstance(ref, dict)]
    if len(hydrated) != len(refs): raise ArtifactError('审查证据引用格式错误')
    result = {'verdict': verdict, 'confidence': confidence, 'severity': severity,
              'summary': _bounded_text(proposal.get('summary'), '危害摘要'), 'evidence_refs': hydrated}
    for key, fields, minimum in [('trigger_steps', ('stage','location','function','flow','protection'), 1),
                                  ('dimensions', ('name','conclusion','description'), 6)]:
        items = proposal.get(key)
        if not isinstance(items, list) or not minimum <= len(items) <= 20: raise ArtifactError(f'{key} 需要 {minimum}–20 项')
        if any(not isinstance(item, dict) for item in items): raise ArtifactError(f'{key} 格式错误')
        result[key] = [{field: _bounded_text(item.get(field), field, 3000) for field in fields} for item in items]
        if key=='dimensions' and len({item['name'] for item in result[key]}) != len(items): raise ArtifactError('审查维度不得重复')
    ruling = proposal.get('ruling', {})
    if not isinstance(ruling, dict): raise ArtifactError('裁决格式错误')
    result['ruling'] = {key: _bounded_text(ruling.get(key), key) for key in ('conclusion','feasibility','value','self_refutation')}
    upstream = proposal.get('upstream_verification', {})
    if not isinstance(upstream, dict) or upstream.get('method') != 'static' or upstream.get('status') not in {'confirmed','partial','unverified'}:
        raise ArtifactError('只读审查只允许静态触发链核对，不能声明动态验证通过')
    result['upstream_verification'] = {**{key: upstream[key] for key in ('method','status')}, 'summary': _bounded_text(upstream.get('summary'),'触发链说明')}
    limitations = proposal.get('limitations', [])
    if not isinstance(limitations,list) or len(limitations)>20: raise ArtifactError('限制说明格式错误')
    result['limitations'] = [_bounded_text(item,'限制说明',1000) for item in limitations]
    for ref in hydrated:
        if digest(read_source(Path(snapshot['root']),ref['file_path'])) != ref['source_hash']: raise ArtifactError('审查期间源码已变化')
    result['provenance'] = {'snapshot_digest':snapshot['digest'],'analysis_kind':'static_review','code_verified':bool(hydrated),
                            'historical_version_verified':False,'warnings':snapshot['warnings']}
    # Derive the readable report from the exact persisted structured result.
    result['report_markdown'] = '\n\n'.join(['# 对抗性审查',result['summary'],
        *[f"## {item['name']}\n{item['conclusion']}\n\n{item['description']}" for item in result['dimensions']],
        *[f'## {key}\n{value}' for key,value in result['ruling'].items()]])
    return result


def hydrate_patch(snapshot, proposal):
    import subprocess
    import tempfile
    if not isinstance(proposal, dict): raise ArtifactError('补丁产物必须是对象')
    disposition = proposal.get('disposition')
    if disposition not in {'candidate','blocked','not_applicable'}: raise ArtifactError('补丁处置类型无效')
    result = {'disposition':disposition,'summary':_bounded_text(proposal.get('summary'),'补丁摘要'),
              'explanation':_bounded_text(proposal.get('explanation'),'修复说明',12000),
              'base_snapshot_digest':snapshot['digest'],'requires_review':True,
              'limitations':[], 'diff':'','files':[]}
    limitations = proposal.get('limitations', [])
    if not isinstance(limitations,list) or len(limitations)>20: raise ArtifactError('补丁限制说明格式错误')
    result['limitations'] = [_bounded_text(item,'限制说明',1000) for item in limitations]
    result['provenance'] = {'snapshot_digest':snapshot['digest'],'analysis_kind':'candidate_patch','code_verified':False,
                            'historical_version_verified':False,'warnings':snapshot['warnings']}
    if disposition != 'candidate':
        if proposal.get('diff'): raise ArtifactError('受阻或无需补丁时不能附带可应用 Diff')
        result['blocked_reason'] = _bounded_text(proposal.get('blocked_reason'),'补丁原因')
        result['validation'] = {'status':'not_run','summary':'未生成候选 Diff；未运行源码或验证测试'}
        return result
    _bounded_text(proposal.get('diff'),'unified diff',120000)
    diff = proposal['diff'].rstrip('\n') + '\n'
    paths, before = [], None
    for line in diff.splitlines():
        if line.startswith(('GIT binary patch','Binary files','rename from ','rename to ','copy from ','copy to ','new file mode','deleted file mode')):
            raise ArtifactError('仅支持现有源码文件的文本修改')
        if line.startswith('--- '):
            name = line[4:]
            if not name.startswith('a/'): raise ArtifactError('Diff 原文件必须使用 a/ 项目相对路径')
            before = relative_name(name[2:])
        elif line.startswith('+++ '):
            name = line[4:]
            if not name.startswith('b/'): raise ArtifactError('Diff 目标必须使用 b/ 项目相对路径')
            after = relative_name(name[2:])
            if before != after or after not in snapshot['files'] or after in paths: raise ArtifactError('Diff 必须修改本次快照中的同一现有文件且不能重复')
            paths.append(after); before=None
    if not 1<=len(paths)<=10 or len(diff.splitlines())>1500 or '@@ ' not in diff: raise ArtifactError('补丁需要 1–10 个文件且不超过 1500 行')
    with tempfile.TemporaryDirectory(prefix='shannon-patch-check-') as directory:
        for name in paths:
            target=Path(directory)/name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(snapshot['files'][name],encoding='utf-8')
        env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'LC_ALL':'C'}
        try:
            checked = subprocess.run(['git','-c',f'core.hooksPath={os.devnull}','apply','--check','--whitespace=nowarn','-'],
                cwd=directory,env=env,input=diff,text=True,capture_output=True,timeout=10)
        except (OSError,subprocess.TimeoutExpired): raise ArtifactError('补丁适用性检查不可用或超时') from None
        if checked.returncode: raise ArtifactError('Diff 无法应用到指定源码快照；请基于实际源码重新生成')
    for name in paths:
        if digest(read_source(Path(snapshot['root']),name)) != snapshot['hashes'][name]: raise ArtifactError('生成补丁期间源码已变化')
    result.update(diff=diff,diff_hash=digest(diff),files=[{'file_path':name,'source_hash':snapshot['hashes'][name]} for name in paths],
                  validation={'status':'passed','check':'git apply --check','exit_code':0,'summary':'仅在临时源码副本检查 Diff 可应用；未应用到原仓库，未执行修复验证'})
    result['provenance']['code_verified']=True
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate and hydrate source-backed vulnerability artifacts")
    parser.add_argument("--source", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--kind", choices=["evidence","review","patch"], default="evidence")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    validator = {"evidence":hydrate,"review":hydrate_review,"patch":hydrate_patch}[args.kind]
    result = validator(snapshot(args.source),payload)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
