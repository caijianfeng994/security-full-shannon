# auth-reviewer

Read this when auditing authentication and authorization logic.

## Goal

Find authentication bypass paths, session management weaknesses, broken access control, privilege escalation, and insecure token handling. These are consistently the highest-impact vulnerability class in web applications.

## Part 1: Authentication analysis

### 1.1 Authentication entry points

Find every place the application makes an authentication decision:
- Login endpoints (password, OAuth, SSO, magic link, API key, certificate)
- Password reset and account recovery flows
- "Remember me" / persistent session tokens
- Two-factor authentication check points
- API key validation middleware
- JWT/session token verification

For each: read the full logic, not just the happy path.

### 1.2 Authentication bypass patterns

**Missing authentication check:**
- Endpoint handler that accesses privileged data but never calls auth middleware
- Middleware applied to a route group that misses specific sub-routes
- Direct function call bypassing the auth decorator/middleware stack

```python
# Python/Flask — missing @login_required
@app.route('/admin/users')           # no auth decorator
def list_users():
    return User.query.all()          # protected data without auth check
```

**Broken "remember me" or persistent tokens:**
- Token stored in DB but not validated against current state (revoked, expired, changed password)
- Token generated with predictable algorithm (timestamp, user ID, static secret)
- Token not invalidated on logout or password change

**Account enumeration:**
- Login returns `"invalid username"` vs `"invalid password"` — allows username enumeration
- Password reset returns different messages for registered vs unregistered emails
- Response time difference for valid vs invalid usernames (timing oracle)

**Credential stuffing exposure:**
- No rate limiting on login endpoint
- No account lockout after N failures
- No CAPTCHA or bot detection

**SQL/NoSQL injection in auth:**
```python
# Direct SQLi in login
cursor.execute(f"SELECT * FROM users WHERE username='{user}' AND password='{pwd}'")
# username: admin'-- bypasses password check
```

```javascript
// NoSQL injection in MongoDB login
User.findOne({ username: req.body.username, password: req.body.password })
// With req.body.password = { $gt: "" } — always true
```

### 1.3 Password handling

- Passwords stored in cleartext or with reversible encoding → critical
- Passwords hashed with MD5 or SHA1 (unsalted or salted) → high
- Passwords hashed with bcrypt/argon2/scrypt → verify work factor is adequate (bcrypt cost ≥ 10, argon2 default params)
- Password stored in logs, error messages, or URL parameters → high

### 1.4 OAuth and SSO

- Missing `state` parameter validation → CSRF on OAuth login flow
- `redirect_uri` not strictly validated → open redirect stealing auth code
- Authorization code reuse not prevented → replay attack
- PKCE not enforced for public clients (mobile, SPA)
- `id_token` signature not verified in OIDC flows
- JWT `alg: none` accepted → signature bypass

### 1.5 Two-factor authentication

- 2FA bypass via direct navigation to post-login page (missing session state check)
- OTP code not rate-limited — brute-force 6-digit TOTP (1M combinations)
- OTP code valid for too long (> 5 minutes) or reusable
- Backup codes stored in plaintext
- SMS OTP interception via SIM swap not mitigated (not a code issue but note if SMS-only)

### 1.6 MFA assertion scaffold bypass

**Critical pattern — high-privilege step-up flows (delegated access, re-authentication, privilege escalation):**

A "verified MFA" gate that only checks whether an assertion field is non-empty (or syntactically safe) without cryptographically verifying it against an enrolled factor or challenge is a full MFA bypass.

Check every elevated-privilege flow that documents an MFA requirement:
- Does the server call a real factor verifier (TOTP, WebAuthn, SMS OTP) anywhere in the path? If `validateParams` only checks `len(assertion) > 0` or a regex, the gate is bypassed.
- Does the BFF/middleware upstream any client-supplied `mfa_assertion` value verbatim — or substitute a hardcoded constant (e.g., `"mfa_scaffold_assertion"`, `"mfa_safe"`, `"placeholder"`)? If so, any password-authenticated user can bypass MFA entirely.
- Is there a `TODO`/comment acknowledging MFA is not yet implemented while the code already creates sessions or issues tokens? Treat this as an active bypass if the endpoint is reachable.

```go
// Flag: MFA assertion accepted without factor verification
func (s *Service) StartDelegatedSession(ctx context.Context, req *StartRequest) (*Session, error) {
    if err := s.verifyReauthProof(ctx, req.ReauthProof); err != nil { // only checks password
        return nil, err
    }
    // req.MFAAssertion is validated only for non-empty — never verified against a real factor
    return s.issueSession(ctx, req) // MFA bypass
}
```

```typescript
// Flag: BFF hardcodes MFA assertion — bypasses backend non-empty check
const resp = await fetch('/api/v1/delegated-sessions/start', {
  body: JSON.stringify({
    ...req,
    mfa_assertion: 'mfa_scaffold_assertion',  // constant; always passes non-empty check
  }),
})
```

### 1.7 Auth lifecycle — credentials surviving entity deletion/revocation

**Critical pattern — tenant deletion, account removal, role binding revocation:**

Soft-deleting an entity (tenant, user, membership, role binding) does NOT automatically revoke existing live credentials. Check every deletion/revocation path for all credential types:

**Tenant deletion:**
- Does the refresh-token rotation query join `tenants` and require `status='active' AND deleted_at IS NULL`? Missing this join lets revoked tenants extend access indefinitely via token rotation.
- Do API key validation queries join `tenants` to check liveness? An API key from a deleted tenant should be rejected at the key-validation layer.
- Are existing session rows row-invalidated at deletion time, or only blocked at new-login time?

**Soft-deleted memberships:**
- Does the login identity query include `AND tm.deleted_at IS NULL`? Missing this condition lets a soft-deleted member log in with their normal password.

```sql
-- Flag: missing deleted_at guard — soft-deleted members can still log in
SELECT u.id, tm.tenant_id, tm.role
FROM users u
JOIN tenant_memberships tm ON tm.user_id = u.id
WHERE tm.tenant_id = $1 AND u.email = $2
-- MISSING: AND tm.deleted_at IS NULL
```

**RBAC role-binding revocation:**
- When a role binding is deleted, are all sessions and refresh tokens for the affected principal immediately invalidated? Without this, the principal's existing JWT retains the revoked role until expiry, and can use that window to recreate the binding.
- Check whether `deleteRoleBinding` issues session-revocation for every subject type (user, service account, group member). Missing any subject type is a partial bypass.

### 1.8 BFF/proxy logout fail-open

**High pattern — Next.js BFF and proxy session revocation:**

A frontend that always reports logout success regardless of whether upstream revocation succeeded leaves server-side sessions and refresh tokens valid. An attacker who copied a refresh token before the user logs out can continue using it.

Check the BFF logout route handler:
- Does it inspect `upstream.ok` before returning `{ ok: true }` to the client?
- Does it forward the upstream error (e.g., 401 when the access token has expired but refresh is still valid) as a Problem Details response rather than swallowing it?
- Does it still clear local HttpOnly cookies on failure as defense-in-depth, while surfacing the error?

```typescript
// Flag: always returns success regardless of upstream revocation result
export async function POST(req: Request) {
  await fetch('/api/v1/auth/logout', { method: 'POST', headers: { ... } })
  // upstream response never inspected — revocation may have silently failed (e.g. 401)
  clearCookies()
  return Response.json({ ok: true })
}
```

```typescript
// Correct: fail closed
const upstream = await fetch('/api/v1/auth/logout', { ... })
if (!upstream.ok) {
  clearCookies()  // still clear local cookies defensively
  return forwardAuthProblem(upstream, requestId)  // surface the failure to caller
}
```

## Part 2: Session management

### 2.1 Session token security

- Session ID in URL parameter → logged in server access logs, browser history → high
- Session ID not regenerated after privilege change (login, role change) → session fixation
- Session not invalidated server-side on logout → persistent access after logout
- Session expiry: check `PERMANENT_SESSION_LIFETIME`, `SESSION_COOKIE_AGE`, or equivalent

### 2.2 Session cookie attributes

Verify session cookies have:
- `HttpOnly`: prevents JavaScript access → mitigates XSS session theft
- `Secure`: only sent over HTTPS
- `SameSite=Strict` or `SameSite=Lax`: CSRF mitigation
- Reasonable expiry (not session for sensitive operations, not excessive for remember-me)

```python
# Django — check settings.py
SESSION_COOKIE_HTTPONLY = True      # should be True
SESSION_COOKIE_SECURE = True        # should be True in production
SESSION_COOKIE_SAMESITE = 'Lax'     # Strict or Lax
SESSION_COOKIE_AGE = 1209600        # 2 weeks — check if appropriate
```

### 2.3 CSRF protection

- CSRF token present on all state-changing requests?
- Token validated server-side (not just present)?
- CSRF token tied to session (not a static value)?
- SameSite cookies used as CSRF mitigation — verify it actually covers the attack vector
- `Origin` / `Referer` header validation as defense-in-depth?

## Part 3: Authorization and access control

### 3.1 Vertical privilege escalation

Can a low-privilege user reach high-privilege functionality?

- Admin routes not protected by role/permission check
- Role check only in UI (frontend) but not in API handler
- `if user.is_admin:` check on UI template but not in backend route
- Privilege check uses data from the request body instead of server-side session

```javascript
// Express — role in JWT payload, not validated against DB
app.post('/admin/delete-user', (req, res) => {
  if (req.body.role === 'admin') { // attacker controls req.body.role
    deleteUser(req.body.userId);
  }
});
```

### 3.2 Horizontal privilege escalation (IDOR)

Can a user access another user's resources by changing an ID?

Flag any endpoint that:
- Accepts a resource ID (user ID, order ID, document ID) in the request
- Does not verify the requesting user owns or is authorized to access that resource

```python
@app.route('/api/orders/<order_id>')
@login_required
def get_order(order_id):
    order = Order.query.get(order_id)   # no ownership check!
    return jsonify(order.to_dict())     # returns any user's order
```

Correct pattern requires ownership verification:
```python
order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
```

### 3.3 Missing function-level access control

- HTTP method confusion: endpoint checks auth for POST but not for GET on the same route
- Different paths to the same resource (e.g., `/api/v1/admin` protected, `/api/admin` not)
- GraphQL resolvers not checking authorization on each field independently
- Batch/bulk endpoints that bypass per-item authorization

### 3.4 JWT-specific issues

```python
# Critical: alg:none attack
jwt.decode(token, options={"verify_signature": False})

# Critical: algorithm confusion (RS256 → HS256)
# If server accepts HS256 with the public key as the HMAC secret

# High: missing expiry validation
jwt.decode(token, secret, algorithms=['HS256'], options={"verify_exp": False})

# High: sensitive data in JWT payload without encryption
# JWT is base64 encoded, not encrypted — visible to anyone

# Medium: no jti (JWT ID) for single-use tokens
```

Verify for each JWT endpoint:
- `alg` header is validated against an allowlist
- `exp` claim is checked
- `aud` and `iss` claims are validated where applicable
- Token revocation mechanism exists for critical tokens (logout, password change)

## Output format

For each auth/authz issue:

```json
{
  "file": "app/routes/admin.py",
  "line": 34,
  "category": "missing_authorization",
  "title": "Admin endpoint accessible without role check",
  "description": "The /admin/delete-user endpoint checks @login_required but does not verify admin role. Any authenticated user can delete accounts.",
  "evidence": "Route decorator at line 32 is @login_required only. No role/permission check in handler body lines 34-40.",
  "impact": "Authenticated users can delete any account, including admin accounts.",
  "cwe": "CWE-285",
  "severity": "critical"
}
```
