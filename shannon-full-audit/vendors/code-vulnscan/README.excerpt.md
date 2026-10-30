# Code-VulnScan Skill

A deep, flow-aware vulnerability scanning skill for AI coding assistants. Finds real, exploitable vulnerabilities — not just keyword matches.

[![Supported IDEs](https://img.shields.io/badge/IDEs-Claude%20%7C%20Codex%20%7C%20Cursor%20%7C%20Windsurf%20%7C%20Copilot%20%7C%20Cline%20%7C%20Continue%20%7C%20Antigravity-blue)]()
[![Languages](https://img.shields.io/badge/Languages-10%2B-green)]()
[![CVEs](https://img.shields.io/badge/CVE%20Database-100%2B-orange)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What it does

- **Taint-flow analysis** — traces user input from sources to dangerous sinks (Python AST plus variable-aware JS/TS, PHP, Ruby, Go, Java, Kotlin, C#, and Rust analyzers)
- **Java/Kotlin JVM application security** — Spring, Ktor, Jakarta EE/Servlet/JAX-RS, Hibernate/JPA, Struts, Micronaut, and Quarkus entry points; JVM injection, expression-language, deserialization, XML, auth, Actuator/admin, and archive/file risks
- **PHP web application security** — Laravel, Symfony, WordPress, Drupal, Yii, and custom PHP authorization, binding, ORM/template, SSRF, upload/archive, deserialization, and worker risks
- **Ruby web application security** — Rails, Sinatra/Rack, and Hanami callback/policy, strong-parameter, ORM/template, URL/file, session, and job risks
- **.NET web application security** — ASP.NET Core/MVC/minimal APIs/Blazor, EF Core/Dapper, endpoint authorization, overposting, Razor output, parsers, files, and hosted services
- **Rust web service security** — Actix-web, Axum, Warp, and Rocket extractors, SQL/process/HTTP/file sinks, serde/async limits, and unsafe boundaries
- **React/Next.js security** — DOM XSS, open redirects, token storage, postMessage, hydration leaks, client-only auth
- **Go service security** — request binding, SQL/command/SSRF/file sinks, templates, HTTP hardening, concurrency races
- **Architecture security** — trust boundaries, tenant isolation, async workers, confused deputy paths, service privileges
- **Infrastructure security** — cloud IAM, network exposure, storage, KMS/secrets, runtime posture, CI/CD trust
- **Application-layer vulns** — account recovery, CSRF, uploads, cache leaks, workflow abuse, rate limits
- **Input validation review** — checks allowlists, regex anchoring, encoding bypasses, type juggling
- **Business logic analysis** — race conditions, TOCTOU, state machine bypasses, price manipulation
- **API security** — IDOR/BOLA, mass assignment, rate limiting gaps, GraphQL depth/complexity attacks
- **Auth & session review** — auth bypass, IDOR, JWT flaws, session fixation, privilege escalation
- **Cryptography review** — weak algorithms, ECB mode, insecure RNG, hardcoded keys
- **Secret detection** — entropy-based scanning + 45+ pattern rules for API keys, passwords, private keys; optional git history scan
- **Configuration audit** — debug mode, security headers, CORS, CSP, TLS misconfigurations
- **IaC security** — Dockerfile, Kubernetes, Terraform, GitHub Actions, GitLab CI, Docker Compose
- **Memory safety** — buffer overflows, use-after-free, format strings (C/C++/unsafe Rust)
- **ReDoS detection** — catastrophic backtracking analysis: nested quantifiers, alternation prefix overlap, complexity estimation
- **GraphQL security** — introspection exposure, depth/complexity limits, batching abuse, field-level auth gaps
- **Mobile security** — Android WebView/exported components, iOS ATS/Keychain/UIWebView, deep link hijacking
- **Error handling review** — stack trace leaks, enumeration oracles, sensitive data in logs
- **Dependency CVEs** — checks Maven/Gradle (including properties, version catalogs, and locks), pnpm/Yarn, Pipenv, NuGet central packages, and other ecosystem manifests against 100+ known-vulnerable version ranges

**False positives are reduced** through a three-pass verification protocol: source reachability → path completeness → exploitability context.

## Supported Languages

Python, JavaScript/TypeScript, Java/Kotlin, Go, PHP, Ruby, C/C++, C#, Rust, Swift, Bash — plus infrastructure files (Dockerfile, Kubernetes YAML, Terraform HCL, GitHub Actions, GitLab CI, Docker Compose).

## IDE Compatibility

| IDE | Target flag | Installed file |
|-----|-------------|---------------|
| Claude Code (CLI/Desktop) | `--target claude` | `~/.claude/skills/code-vulnscan/` |
| Claude Code / Cowork (project/team) | `--target cowork` | `<project>/.claude/skills/code-vulnscan/` |
| OpenAI Codex | `--target codex` | `~/.codex/skills/code-vulnscan/` |
| Cursor AI | `--target cursor` | `<project>/.cursor/rules/code-vulnscan.mdc` |
| Windsurf | `--target windsurf` | `<project>/.windsurf/rules/code-vulnscan.md` |
| GitHub Copilot Chat | `--target copilot` | `<project>/.github/copilot-instructions.md` |
| Cline (VS Code) | `--target cline` | `<project>/.clinerules` |
| Continue.dev | `--target continue` | `<project>/.continue/prompts/vulnscan.prompt` |
| Antigravity | `--target antigravity` | `<project>/.agent/skills/code-vulnscan/` |

## Installation

All `--online` commands below download the latest release package automatically.

## 本交付包已收录（节选）

| File | Purpose |
|------|---------|
| `go-security-reviewer.md` | Go sinks / SSRF / races |
| `business-logic-analyzer.md` | Business logic / TOCTOU |
| `error-handling-reviewer.md` | Stack / error disclosure |
| `regex-analyzer.md` | ReDoS |
| `scan-strategy.md` | Optional large-repo strategy |
| `auth-reviewer.md` | Auth bypass / session / privilege（P0） |
| `api-security-reviewer.md` | IDOR/BOLA / API authz（P0） |
| `application-vuln-reviewer.md` | Upload / cache leakage / workflow（P0） |
