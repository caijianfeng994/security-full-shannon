# scan-strategy

Read this first whenever a new `vulnscan scan` request arrives.

## Goal

Build a concrete scan plan before any code is read. A good plan prevents wasted effort and ensures the highest-risk areas are analyzed first.

## Required decisions

### 1. Detect languages and frameworks

Identify every language present in the codebase. Do not scan auto-generated code, vendored dependencies, minified bundles, or test fixtures unless the user asks.

Map each language to its likely framework:

| Language | Frameworks to detect |
|----------|---------------------|
| Python | Flask, Django, FastAPI, Pyramid, Tornado, aiohttp |
| JavaScript/TypeScript | Express, Next.js, Nuxt, Koa, Hapi, NestJS, React, Vue, Angular |
| Java / Kotlin JVM | Spring Boot/MVC/Security/Data, Jakarta EE, Servlet, JAX-RS (Jersey/RESTEasy), Struts, JSF, Hibernate/JPA, Micronaut, Quarkus, Dropwizard, Ktor; Android routes additionally to the mobile reviewer |
| Go | net/http, Gin, Echo, Fiber, Chi, Gorilla |
| PHP | Laravel, Symfony, CodeIgniter, WordPress, Drupal, Yii |
| Ruby | Rails, Sinatra, Hanami |
| C/C++ | No standard framework; focus on input parsing, memory ops |
| C# | ASP.NET Core, .NET MVC, Blazor, Web API |
| Rust | Actix-web, Axum, Warp, Rocket |

Framework detection matters because each framework has its own:
- Request data access patterns (how user input enters)
- ORM and query patterns (how SQL is constructed)
- Template engine and output patterns (how responses are rendered)
- Auth middleware patterns (how access control works)

### 2. Map the attack surface

Enumerate every entry point: all places where external, user-controlled data can enter the application.

**Primary entry point types:**
- HTTP request parameters, body, headers, cookies
- CLI arguments and environment variables
- File uploads and file content reads
- Inter-process communication (message queues, sockets, pipes)
- Database content that was previously written by users (second-order injection sources)
- Configuration files parsed at runtime
- Deserialized data from external sources

**Entry point signals per language:**

Python/Flask: `@app.route`, `@blueprint.route`, handler function parameters
Python/Django: `urlpatterns`, views receiving `request`, `forms.py`
JavaScript/Express: `app.get`, `app.post`, `router.use`, middleware `(req, res, next)`
React/Next.js: route handlers, server actions, loaders/actions, middleware matchers, `useSearchParams`, `URLSearchParams`, `location.search`, `postMessage`, client-side auth guards
Java/JVM: Spring `@Controller`/`@RestController`/`@*Mapping`; Servlet `doGet`/`doPost`/`service`; JAX-RS `@Path` + `@GET`/`@POST`; Micronaut `@Controller`; Quarkus/Jakarta REST resources; Struts actions/setters; JSF action/value bindings; JMS/Kafka listeners; `@Async`/`@Scheduled` workers
Kotlin/Ktor: `routing`, `Route.get/post/...`, `call.parameters`, `call.receive*`, authentication plugins, status pages, WebSockets, coroutines, and queue consumers
Go/Gin: `r.GET`, `r.POST`, `r.Any`, handler `func(c *gin.Context)`, `ShouldBind*`, `Bind*`, `json.NewDecoder(r.Body).Decode`
PHP: Laravel/Symfony attributes and route files, WordPress REST/AJAX/admin hooks, Drupal/Yii/CodeIgniter controllers, superglobals, uploads, commands, cron, queues, and webhooks
Ruby: Rails routes/controllers/channels/jobs, Sinatra/Rack route blocks and middleware, Hanami actions, `params`, headers/cookies, uploads, and queue consumers
C#/.NET: controller and minimal-API endpoints, `[From*]` binding, SignalR hubs, Razor/Blazor events, middleware, hosted services, functions, and message consumers
Rust: Actix/Axum/Warp/Rocket routes and extractors, headers/cookies/body streams, WebSockets, Tokio tasks, CLI/environment input, and message consumers

List every identified entry point explicitly in your plan. Missing an entry point means missing every vulnerability reachable through it.

### 3. Prioritize files

Not all files carry equal risk. Rank files for deep analysis:

**Highest priority:**
- HTTP request handlers and controllers
- React/Next.js server actions, route handlers, middleware, and client routing/auth components
- Go handlers, middleware, request binding structs, and HTTP client wrappers
- Java/JVM controllers, servlet filters, security chains, request DTO/binder code, repositories, expression/template evaluation, message consumers, async executors, and management configuration
- PHP/Ruby controllers, route/hook/middleware policy code, binding/strong-parameter layers, raw ORM queries, templates, uploads/importers, and workers
- ASP.NET endpoint filters/controllers, authorization policies, model binders/DTO mapping, EF/Dapper queries, Razor/Blazor output, file endpoints, SignalR hubs, and hosted services
- Rust route/extractor code, middleware/layers, SQLx/Diesel queries, command/HTTP/file wrappers, templates, serde boundaries, and spawned tasks
- Files that query databases
- Files that execute OS commands
- Auth, session, and token management code
- File upload and file serving code
- Deserialization entry points
- Template rendering code
- Tenant, organization, project, and service-to-service boundary enforcement code
- Infrastructure that controls IAM, KMS, public network exposure, object storage, CI/CD deployment trust, runtime identity, and audit logging

**High priority:**
- Utility functions called by high-priority files
- Middleware and filters
- Configuration parsing
- Input validation modules

**Lower priority (but do not skip):**
- Helper utilities not on a request path
- Static configuration
- Pure data models with no query construction

### 4. Choose vulnerability categories

Based on the framework and entry points detected, decide which vulnerability categories are in scope. Do not do a generic scan that ignores context.

For each category, confirm at minimum:
- Is there an entry point that could reach this sink type?
- Does the framework or ORM offer protections (e.g., Django ORM auto-escapes SQL)?
- Are there any overrides or raw-mode patterns that disable those protections?

Known framework protections to verify are not bypassed:
- Django ORM: protects against SQLi unless `.raw()`, `extra()`, or `RawSQL()` is used
- Spring Data JPA: protects unless `@Query(nativeQuery=true)` with concatenation is used
- JDBC/JPA/Hibernate parameter binding protects values, but not concatenated JPQL/HQL/native SQL or user-selected identifiers and sort fragments
- Spring Security annotations protect routes only when method security is enabled and proxy/matcher coverage reaches the call; evaluate ordered `SecurityFilterChain` rules
- Java XML factories, Jackson, and object streams are not inherently safe: verify the effective parser/type/filter configuration on the untrusted path
- Ktor typed extractors constrain shape, not authorization, tenant scope, URL destinations, filenames, SQL fragments, or resource limits
- Active Record: protects unless `where("... #{params}")` string interpolation is used
- Rails strong parameters constrain writable fields but do not authorize the selected record or tenant; `permit!` and `to_unsafe_h` bypass the field allowlist
- Laravel Eloquent/Doctrine/WordPress helpers protect ordinary bound values only; raw fragments, identifiers, order clauses, and unscoped object lookup still require allowlists and authorization
- ASP.NET model binding and `[ApiController]` validate shape, not object authorization or overposting; EF LINQ is parameterized, while `FromSqlRaw`, interpolated/concatenated Dapper/ADO.NET SQL, and dynamic identifiers require review
- Rust type systems and serde extractors constrain representation, not authorization or destination policy; SQLx compile-time macros help fixed SQL but dynamic `query` strings and identifiers remain risky
- Hibernate: protects unless `createNativeQuery()` with concatenation is used
- React auto-escapes text nodes, but not `dangerouslySetInnerHTML`, DOM APIs, markdown renderers, postMessage sinks, browser token storage, or client-side redirects
- Go `html/template` auto-escapes HTML, but `text/template`, `template.HTML`, raw `fmt.Fprintf(w, ...)`, and bound structs still require manual review

### 5. Identify sanitization infrastructure

Before scanning, catalog what sanitization utilities already exist:
- Custom validators, sanitizers, escaping functions
- Allowlist/blocklist modules
- Framework-provided CSRF tokens, HTML escaping, parameterized queries
- Security middleware (CORS, CSP, rate limiting)

Understanding what protection exists tells you where protection is missing.

### 6. Plan analysis order

Execute analysis in this order to maximize signal early:

1. High-complexity entry point handlers (most likely to have missed validation)
2. Database query construction (SQL injection)
3. OS command construction (command injection)
4. File system access with user-controlled paths (path traversal)
5. HTML/template output (XSS)
6. HTTP client calls with user-controlled URLs (SSRF)
7. Deserialization entry points
8. Auth and session management — including:
   - MFA assertion scaffold bypass (non-empty check only, no factor verification)
   - Auth lifecycle gaps (soft-deleted memberships, archived tenant credentials, RBAC revocation not invalidating sessions)
   - BFF logout fail-open (upstream revocation response not checked)
9. Cryptographic operations and hardcoded secrets — including:
   - Probe/seed tools that create privileged accounts with predictable credentials
   - SSH `InsecureIgnoreHostKey()` usage
10. Framework-specific checks when present — including:
    - OAuth credential type confusion → file exfiltration (Go: `google.CredentialsFromJSON` without type check)
    - CSV formula injection in Go `csv.Writer` output
    - Unbounded external API pagination in connector workers
    - Attacker-controlled URLs in signed manifests
    - BFF protocol downgrade (internal upstream scheme leaking into browser-facing URLs)
    - Next.js `"use client"` RSC payload data leakage (wide server component props exposed to browser)
    - GET-triggered server-side mutations via `searchParams` (CSRF via navigation)
    - Hardcoded security assertions in BFF routes (e.g., constant `mfa_assertion`)
    - Clipboard pastejacking via `onCopy` override on sensitive content
    - UI redaction bypass (raw command field used before checking redacted variant)
    - Java framework authorization gaps (ordered Spring filter chains, uncovered HTTP methods, disabled/unreached method security)
    - Java request binding into entities or privileged fields; Struts/OGNL, SpEL, JSF/Jakarta EL, and dynamic template evaluation
    - JDBC/JPA/Hibernate raw query construction, unsafe deserialization/XML parsing, and JNDI/reflection/class-loading paths
    - JVM SSRF and redirect validation across DNS resolution and redirects; archive extraction/path containment and upload limits
    - Trust-all TLS, weak crypto, sensitive/log-forging output, exposed Actuator/admin/dev endpoints, and async tenant/security-context loss
    - PHP/Ruby route callback or middleware-order gaps, object/tenant policy misses, mass assignment, template escape bypasses, wrapper/open-uri SSRF, and worker context leakage
    - .NET fallback-policy/endpoint metadata gaps, overposting, Razor/Blazor raw output, forwarded-header trust, unsafe Data Protection usage, and hosted-service context leakage
    - Rust middleware-layer ordering, extractor/body limits, dynamic SQL identifiers, blocking/unbounded work in async handlers, unsafe/FFI edges, and task-local context leakage
11. Architecture and tenant-boundary review for multi-service or SaaS systems — including:
    - Delegated/MSSP self-approval and grant action limit bypass
    - Aggregate endpoint API key scope bypass (results endpoint returning multi-domain data)
    - Cross-tenant shared secret store with per-tenant DB uniqueness
    - Reserved service-account name collision causing cross-tenant availability impact
    - Agent/relay sequence integrity (per-task vs per-agent namespace; restart sequence reset)
    - Approval boundary bypass (resource mutation after parent is approved)
    - Scope parameter not gated by role (tenant role operating global scope)
    - Enrollment token RBAC bypass (lower-privilege token performing higher-privilege writes)
12. Infrastructure posture review when cloud/IaC/runtime/CI deployment config is present
13. Dependency manifest scan

**Go + Next.js codebases:** Steps 8–11 are especially productive. Run go-security-reviewer, react-security-reviewer, architecture-security-reviewer, and application-vuln-reviewer together before moving to infrastructure.

**Java/JVM services:** Run java-security-reviewer with auth-reviewer and application-vuln-reviewer. Add architecture-security-reviewer when security or tenant context crosses executors, reactive pipelines, queues, services, caches, or shared persistence. For Android, also run mobile-security-reviewer rather than treating the app as a server-only JVM target.

**PHP and Ruby web applications:** Run the matching framework reviewer with auth-reviewer and application-vuln-reviewer. Add architecture-security-reviewer for queue workers, multisite/multitenant state, shared caches, or long-lived process context.

**ASP.NET services:** Run dotnet-security-reviewer with auth-reviewer and application-vuln-reviewer. Add architecture-security-reviewer for SignalR, hosted services, distributed caches, message buses, or tenant/claims propagation.

**Rust services:** Run rust-security-reviewer with auth-reviewer and application-vuln-reviewer. Also run memory-safety-analyzer when request-reachable code crosses `unsafe`, FFI, native libraries, or raw-pointer boundaries.

### 6B. Commit / diff scan mode

When the user runs `vulnscan commit`, `vulnscan diff`, or `vulnscan pr`, use this abbreviated workflow instead of scanning the full codebase.

#### Step 1: Extract the diff

```bash
# Single commit
git -C <repo> show <hash> --name-only --diff-filter=ACMRT

# Commit range / branch diff
git -C <repo> diff <base>..<head> --name-only --diff-filter=ACMRT

# Get the actual unified diff (for reading changed code regions)
git -C <repo> diff <base>..<head> -- <changed_file>
```

Collect:
- List of changed files (added, modified, renamed — skip deleted)
- For each file: the added/modified line ranges from the diff hunks (`@@ -a,b +c,d @@`)
- Language of each changed file

#### Step 2: Scope analysis to changed regions + impact radius

For each changed file:
1. Read the **entire** changed file (not just the diff hunk) — you need full context to trace callers and callees.
2. Identify functions/methods that contain the changed lines.
3. Trace one level out: functions that **call** or are **called by** the changed functions — these are in scope even if their lines didn't change.
4. Apply the same analysis phases (taint, auth, business logic, architecture) but **only** to the in-scope functions.

Do not scan files not in the changed set or the one-level caller/callee radius. This keeps commit scans fast.

#### Step 3: Tag findings

For each finding, add:
- `introduced_in_diff: true` — the vulnerable code is in the diff itself (a line in the `+` side of the hunk is part of the finding)
- `introduced_in_diff: false` — the finding is in a caller/callee of changed code; the vulnerability existed before the commit but the change is near it

Prioritize `introduced_in_diff: true` findings in the report — they represent new risk introduced by this commit.

#### Step 4: High-value checks for commit scans

Commit scans should always run these checks regardless of what changed, because they catch common "forgot to update X when changing Y" patterns:

- **Auth lifecycle check:** if any auth, session, login, membership, or role-binding code changed — check whether the corresponding session/token invalidation was also updated in the same commit.
- **MFA scaffold check:** if any delegated session, step-up auth, or reauth flow changed — check whether MFA verification is real or just a non-empty assertion check.
- **Scope guard check:** if any API route registration changed — check whether all data domains in the response body have matching scope guards.
- **Approval boundary check:** if any resource mutation endpoint was added or changed — check whether campaign/workflow status is verified before the mutation proceeds.
- **CSV output check:** if any CSV-building or export code changed — check for formula injection.
- **SSH config check:** if any SSH client or server configuration changed — check for `InsecureIgnoreHostKey()` and missing `AllowUsers`.

#### Step 5: Report

Use the standard report format but add a `commit_scan` metadata block at the top:

```json
{
  "scan_mode": "commit",
  "commit": "<hash>",
  "base": "<base-hash or 'HEAD~1'>",
  "changed_files": 7,
  "functions_analyzed": 23,
  "findings_introduced_in_diff": 2,
  "findings_in_callers_callees": 1
}
```

### 7. Fresh or resume decision

Check scan state before starting:

```bash
python3 scripts/scan.py --status-only
```

If an incomplete recent run exists:
- Ask whether to resume or start fresh.
- On resume: skip already-analyzed files, carry forward confirmed findings.
- On fresh: use `--force` to reset state.

## Output contract

Produce a scan plan with:

- detected languages and frameworks
- entry point list (file, line, type)
- files ranked for priority analysis
- vulnerability categories in scope
- sanitization infrastructure found
- analysis order
- fresh or resume decision

State the entry point count explicitly. Do not begin analysis without a completed plan.
