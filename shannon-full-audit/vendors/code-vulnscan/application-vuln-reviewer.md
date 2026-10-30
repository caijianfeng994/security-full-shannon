# application-vuln-reviewer

Read this for application-layer vulnerability coverage across web apps, APIs, SaaS workflows, admin panels, billing flows, file handling, account recovery, and user/tenant management.

## Goal

Find exploitable application vulnerabilities that static pattern matching misses because the bug is in workflow rules, authorization context, state transitions, or abuse controls.

## Required application checks

- IDOR/BOLA: every object ID, slug, UUID, tenant ID, project ID, file ID, and nested resource must be authorized against the current actor and tenant.
- Function-level authorization: admin, export, impersonation, billing, integration setup, key rotation, and destructive endpoints need explicit role checks.
- Mass assignment: request bodies must not update model/entity fields directly without an allowlist DTO or serializer.
- CSRF: cookie-authenticated state-changing routes need CSRF protection or SameSite constraints that match the deployment.
- Account recovery: password reset, email change, MFA reset, invitation acceptance, and magic links must be single-use, expiring, bound to the intended user, and atomically consumed.
- Session/JWT lifecycle: logout, password change, MFA changes, role changes, and tenant removal must revoke or invalidate relevant sessions/tokens.
- Rate limits and abuse controls: login, OTP, password reset, registration, invite send, export, search, upload, webhook, and expensive report endpoints.
- File upload/download: MIME sniffing, extension allowlist, malware scanning expectations, object-store ACLs, path traversal, signed URL scope, and download authorization.
- Cache/data leakage: user-specific or tenant-specific responses must not be shared through CDN, browser cache, Redis keys, search indexes, or server-side memoization.
- Business rules: price, balance, quota, coupon, approval, license, role, and status transitions must be computed and enforced server-side.

## Aggregate endpoint API key scope bypass

When an endpoint aggregates data from multiple resource domains (e.g., a campaign "results" endpoint that returns assessment outcomes, detection verdicts, findings, and report metadata), the route guard must enforce **all relevant scopes**, not just the root resource scope.

Check: for every endpoint whose response body includes data from more than one domain, does the middleware verify a scope for each included domain?

```
GET /api/v1/campaigns/{id}/results
Guard: requireAPIKeyScope("read:campaigns")         ← only campaigns scope checked
Response body: assessment test cases, findings, detection runs, detection verdicts, reports

Any API key with read:campaigns — intended only for campaign metadata — can retrieve
assessment and detection data that should require read:assessments + read:detections.
```

This is distinct from IDOR — the tenant's own data is returned, but the scope boundary is bypassed.

## Credential metadata information disclosure via lower-privilege endpoint

When a high-privilege resource (connector credential, integration secret) has metadata fields (fingerprint, last_used_at, profile_key, managed_by, rotation timestamps) and those fields are copied into a response from a **lower-privilege** endpoint (e.g., a read-only runtime profile endpoint):

- The primary credential endpoint may require `CanManageDetectionIntegrations` + session auth.
- The runtime profile endpoint may require only `CanReadDetections` + API key.
- If the runtime profile response includes credential fingerprints, ownership, and rotation timing, low-privilege callers now have operational reconnaissance data that was previously behind a stricter permission boundary.

Flag any endpoint where credential or key metadata fields appear in a response guarded by a weaker permission than the dedicated credential-management endpoint for the same resource.

## Cross-tenant global user mutation via tenant-scoped authorization

When a `users` table is global (shared across tenants) but a `tenant_memberships` table provides the many-to-many tenant relationship, an endpoint that:
1. Authorizes the actor only against the tenant membership (actor is OrgAdmin of tenant T)
2. Mutates the **global** user or credential row (password, account status, lock state)

...allows a tenant admin to affect a shared user's credentials across ALL tenants that user belongs to.

```
PATCH /api/v1/users/{user_id}
Actor: OrgAdmin in Tenant A
Check: target user is a member of Tenant A ✓
Action: UPDATE users SET password_hash = ... WHERE id = {user_id}
Effect: user's password changes globally — Tenant B where user is also a member is now compromised
```

The fix is either: (1) scope the mutation to a tenant-scoped credential table, or (2) require that the target user belongs to exactly one tenant before allowing global credential mutation.

## Import job source reference injection causing rollback to retire an unrelated resource

An import or ingest pipeline often assigns an internal `resource_id` to each import record by UUID-parsing a user-supplied identifier (version string, source ref, external ID). If the pipeline does not verify that the parsed UUID actually belongs to the object being imported, an attacker who controls the input can forge `resource_id` to point to a different tenant-visible resource. On rollback or cleanup, the job reads `resource_id` from the import record and retires/deletes whatever resource that UUID identifies — potentially a pack or resource the attacker did not create.

**Pattern to flag:**

```go
// Flag: source_ref from user-controlled manifest.Version used as resource_id without ownership check
for _, record := range importRecords {
    if isUUID(record.SourceRef) {
        record.ResourceID = uuid.MustParse(record.SourceRef)  // unvalidated — attacker sets SourceRef
    }
}
// If record is the import job's own content_pack_version and manifest.Version is a UUID
// belonging to another pack, rollback retires the wrong pack via appliedContentPackVersionID()
```

The critical path is:
1. User supplies a manifest where `version` is a UUID string matching a different, already-existing pack version.
2. The import job creates a `content_pack_version` import record with `source_ref = manifest.Version`.
3. `isUUID(source_ref)` returns true → `resource_id` is set to the attacker-supplied UUID.
4. Rollback calls `appliedContentPackVersionID()`, reads that `resource_id`, and retires the victim pack version.

Check: any pipeline that maps a user-supplied identifier to an internal `resource_id` by UUID-parsing the input must verify the parsed UUID belongs to the object currently being created or imported — not just that it is a syntactically valid UUID. The safest pattern is to assign `resource_id` only after the new resource row is persisted and the server-generated ID is known, never from client input. CWE-639. Severity: medium.

## Evidence requirements

Show the exact route/job/action, actor context, object or state being manipulated, missing enforcement, and a realistic exploit sequence. Prefer a short reproduction with two users or two tenants when proving access-control bugs.

## False-positive filters

- Authentication alone does not satisfy authorization.
- Middleware is sufficient only when it receives and checks the same resource/tenant used by the handler.
- A serializer is safe only if sensitive fields are excluded from both create and update paths.
- Rate limits are relevant only if applied before expensive work and keyed by the correct actor/IP/tenant dimension.
