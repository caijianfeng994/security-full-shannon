# go-security-reviewer

Read this when a codebase contains Go HTTP services, CLIs exposed to user input, Gin, Echo, Fiber, Chi, Gorilla, gRPC, or Go workers that process untrusted messages.

## Goal

Find Go-specific security bugs missed by generic source/sink scanning: request binding mass assignment, unsafe SQL construction, SSRF, path traversal, template misuse, command execution, server hardening gaps, and concurrency races.

## Source mapping

Treat these as user-controlled until proven otherwise:

- `r.URL.Query()`, `r.FormValue`, `r.PostFormValue`, `r.Header`, `r.Cookie`, `r.Body`, `r.URL.Path`.
- Gin/Echo/Fiber/Chi params and body binders: `Query`, `Param`, `PostForm`, `ShouldBind*`, `Bind*`, `BodyParser`.
- `json.NewDecoder(r.Body).Decode(&dst)`, gRPC request messages, queue payloads, CLI args, environment variables in hosted jobs.

## High-risk sinks and checks

- SQL injection: `fmt.Sprintf`, string concatenation, `db.Query/Exec/QueryRow`, `gorm.Raw`, `Where` with concatenated strings. Parameter placeholders are the mitigation; `fmt.Sprintf` is not.
- Command injection: `exec.Command`, `exec.CommandContext`, any `sh -c` or user-controlled executable/argument.
- SSRF: `http.Get`, `http.Post`, `http.NewRequest`, `client.Do`; verify scheme, host allowlist, DNS rebinding protection, private IP blocking, redirects, and metadata IP blocking.
- Path traversal: `os.Open`, `os.ReadFile`, `http.ServeFile`, `filepath.Join`; require `filepath.Clean` plus base-directory containment after symlink resolution where files are attacker-influenced.
- XSS/template: `text/template` for HTML, `template.HTML`, `template.JS`, `fmt.Fprintf(w, ...)`. Prefer `html/template`.
- Mass assignment: request body decoded into persistent domain structs. Check `isAdmin`, `role`, `tenantID`, `ownerID`, `balance`, `status`, and permission fields.
- Server hardening: bare `http.ListenAndServe`, no read/write/header timeouts, no body size limits, permissive CORS with credentials, missing request context deadlines.
- Concurrency: check-then-act on balances, quotas, coupons, OTPs, password reset tokens, file creation, and map access without locks.

## OAuth credential type confusion → SSRF / file exfiltration

When a Go service accepts tenant-supplied OAuth credential JSON and passes it directly to a Google/cloud OAuth library (e.g., `google.CredentialsFromJSON`, `oauth2/google.CredentialsFromJSON`), the library supports multiple credential types including `external_account`. An `external_account` credential can:
- Read a local file specified in `credential_source.file` and POST it to `token_url`
- Send the file contents to an attacker-controlled HTTPS endpoint

This means a tenant with integration-management access can exfiltrate server-readable files (config, mounted secrets, signing keys) by supplying a crafted `external_account` JSON blob as a "service account" credential.

```go
// Flag: credential type not validated before passing to Google OAuth library
creds, err := google.CredentialsFromJSON(ctx, req.ServiceAccountJSON, scope)
// If req.ServiceAccountJSON is type "external_account", the library reads local files
// and POSTs them to token_url — no type check here

// Correct: validate type field before calling library
var m map[string]any
json.Unmarshal(req.ServiceAccountJSON, &m)
if m["type"] != "service_account" {
    return ErrInvalidCredentialType
}
```

Flag any path where: (1) credential JSON is tenant-controlled, (2) it is passed to an OAuth library without validating `type == "service_account"`, and (3) the library is called in a context that performs network I/O (token minting, connection test).

## SSH host key verification disabled

Flag any use of `ssh.InsecureIgnoreHostKey()` in Go SSH client configurations. Without host key verification, an on-path attacker can present a fake server, receive the client's credentials (password or key), and return tampered data.

```go
// Flag: accepts any SSH server key — MitM trivial
cfg := &ssh.ClientConfig{
    User:            username,
    Auth:            []ssh.AuthMethod{ssh.Password(password)},
    HostKeyCallback: ssh.InsecureIgnoreHostKey(),  // never acceptable outside local testing
}

// Correct: load known_hosts or pin the expected host key
cb, err := knownhosts.New(knownHostsPath)
cfg.HostKeyCallback = cb
```

Any collector, probe, or worker that SSHes to a remote host and uses `InsecureIgnoreHostKey()` is a finding regardless of whether the host is "internal" — DNS/routing manipulation still applies.

## CSV formula injection

When a Go service generates CSV output from tenant-controlled string fields (action names, ticket titles, campaign names, display names), values beginning with `=`, `+`, `-`, `@`, tab, or CR/LF are interpreted as formulas by Excel, LibreOffice, and Google Sheets.

```go
// Flag: Go csv.Writer handles quoting/escaping CSV syntax but does NOT prevent formula injection
w := csv.NewWriter(buf)
w.Write([]string{record.DisplayName, record.Tactic, record.Description})
// If record.DisplayName = "=HYPERLINK(\"http://attacker.com\")" — formula executes on open

// Correct: prefix dangerous leading characters
func csvSafeCell(s string) string {
    if len(s) > 0 && strings.ContainsRune("=+-@\t\r", rune(s[0])) {
        return "'" + s  // apostrophe prefix prevents formula execution
    }
    return s
}
```

Flag every `csv.NewWriter` or CSV-building path where cell values come from user-controlled database fields without a formula-injection sanitizer.

## Unbounded connector/external API pagination

When Go workers loop through paginated results from external APIs (SIEMs, EDRs, detection tools), verify there is a maximum page count, maximum elapsed time, or total result cap:

```go
// Flag: unbounded loop — a tenant-configured endpoint returning stable cursors loops forever
for {
    page, nextToken, err := client.ListRules(ctx, nextToken, pageSize)
    results = append(results, page...)  // unbounded memory growth
    if nextToken == "" { break }
    // No max pages, no timeout check, no total cap
}

// Correct: enforce a ceiling
const maxPages = 100
for i := 0; i < maxPages; i++ {
    page, nextToken, err := client.ListRules(ctx, nextToken, pageSize)
    results = append(results, page...)
    if nextToken == "" { break }
}
```

This is especially relevant when the connector base URL is tenant-configured and the tenant can control the response (e.g., returning a stable non-empty cursor on every page).

## Attacker-controlled URL in signed/trusted manifest

When a signed or cryptographically bound manifest includes a URL field (e.g., `server_url`, `hostprep_server_url`, `download_url`) that was accepted from API input rather than derived from trusted server configuration:

- The signature provides integrity (the URL hasn't changed since signing) but not origin safety (the URL may point to an attacker host).
- Downstream consumers that trust the signed manifest unconditionally will connect to the attacker-supplied URL with sensitive material (enrollment tokens, SSH keys, credentials).

```go
// Flag: hostprep_server_url taken from enrollment token metadata (client input) and signed
manifest := &HostprepManifest{
    ServerURL: enrollmentToken.Metadata.HostprepServerURL,  // client-controlled
    // ...
}
sign(manifest)  // signature proves URL is unmodified, not that it's safe

// Correct: derive from server configuration, reject or override client-supplied URLs
manifest.ServerURL = s.config.ControlPlaneURL  // always from server config
```

Flag any signed manifest, signed envelope, or token where a URL field originates from user/API-supplied input rather than server-side configuration.

## Encrypted dispatch validation order (CWE-696)

When a service encrypts a signed task envelope and then immediately validates it, the validator operates on the ciphertext rather than the original plaintext claims. Because the encrypted wrapper contains none of the expected fields (`campaign_id`, `task_key`, `expires_at`), the validator finds zero-valued fields and rejects every encrypted dispatch before it can be persisted.

```go
// Flag: validation runs AFTER encryption has already replaced the plaintext envelope
encryptedEnvelope := encryptDispatchEnvelope(job.SignedEnvelope)
job.SignedEnvelope = encryptedEnvelope          // plaintext is gone
err := validateDispatchEnvelopeClaims(job)      // still tries to parse as plaintext claims
// validateDispatchEnvelopeClaims unmarshals job.SignedEnvelope expecting campaign_id, task_key,
// expires_at — these fields are absent in the encrypted wrapper → validation always fails

// Correct: validate claims BEFORE encrypting, or pass original claims separately to the validator
err := validateDispatchEnvelopeClaims(job)      // validate first
encryptedEnvelope := encryptDispatchEnvelope(job.SignedEnvelope) // then encrypt
```

Flag any dispatch or job-submission path where an encryption call reassigns the envelope field before a claim-validation call reads that same field. Trace the assignment chain: if `job.SignedEnvelope` (or equivalent) is overwritten by an encrypt/wrap call and the next operation unmarshals it expecting plaintext fields, the order is wrong. Severity: medium.

## Relay signing payload mismatch (CWE-347)

When the compiler signs a subset payload struct (containing only executable claims) but the relay verifier canonicalizes and verifies the full envelope struct (which includes metadata fields like `envelope_key_id`, `envelope_algorithm`, `envelope_payload_hash`, `envelope_signature`), the signed bytes and verified bytes differ, causing every legitimate task envelope to fail signature verification on the relay.

```go
// Flag: verifier canonicalizes the full envelope, but signer signed only a subset payload
func (v *Verifier) Verify(envelope TaskEnvelope) error {
    canonical, _ := json.Marshal(envelope)          // includes ALL fields: envelope_key_id, etc.
    return ed25519.Verify(pubKey, canonical, envelope.Signature)
    // But compiler's signTaskEnvelope() signed only:
    //   taskEnvelopeSigningPayload{TaskKey, CampaignID, ExpiresAt, Commands, ...}
    // The two byte sequences differ → signature always fails
}
// Correct: verifier must canonicalize the same signing payload struct the compiler signed
func (v *Verifier) Verify(envelope TaskEnvelope) error {
    payload := taskEnvelopeSigningPayload{
        TaskKey:    envelope.TaskKey,
        CampaignID: envelope.CampaignID,
        ExpiresAt:  envelope.ExpiresAt,
        Commands:   envelope.Commands,
    }
    canonical, _ := json.Marshal(payload)
    return ed25519.Verify(pubKey, canonical, envelope.Signature)
}
```

To find this pattern: locate the sign function and the verify function for the same envelope type. Extract the type passed to `json.Marshal` (or equivalent canonicalization) in each. If they differ — one is a subset struct and the other is the full envelope — flag it. Severity: medium.

## Watchdog bootstrap hash supplied by caller without server derivation (CWE-345)

When issuing a watchdog or agent certificate, a service may compute the canonical bootstrap metadata hash only as a fallback when the caller omits the field. If the caller supplies any valid-looking hash, the service accepts it without ever comparing it to the server-derived canonical value. An authorized caller can mint a certificate bound to arbitrary attacker-chosen bootstrap state.

```go
// Flag: caller-supplied BootstrapConfigHash accepted without server-side derivation check
func (s *Service) IssueWatchdogCertificate(ctx context.Context, req *IssueRequest) (*Cert, error) {
    hash := req.BootstrapConfigHash
    if hash == "" {
        hash = computeCanonicalHash(req.AssignmentID, req.TenantID, req.PackageID)
    }
    // If caller supplies a 64-char hex string, it is used directly — never verified against
    // the canonical hash computed from server-trusted assignment metadata
    return s.persistCert(ctx, hash, ...)
}

// Correct: always compute server-side; reject or ignore caller-supplied hash
func (s *Service) IssueWatchdogCertificate(ctx context.Context, req *IssueRequest) (*Cert, error) {
    hash := computeCanonicalHash(req.AssignmentID, req.TenantID, req.PackageID)
    return s.persistCert(ctx, hash, ...)
}
```

Flag any certificate or token issuance function that uses a caller-supplied hash, nonce, or binding value with an `if field == ""` fallback pattern. The fallback means the server knows the correct value — so it should always be used, ignoring the caller-supplied value entirely. Severity: medium.

## Package kind binding bypass (CWE-285)

When a backend authorization check rejects a package download only when both a capability flag is false AND a profile string is empty, an attacker who sets the profile to any non-empty value while leaving the flag false bypasses the check. The frontend may hide the download URL based on the flag alone, but the API remains callable.

```go
// Flag: backend allows hostprep download unless BOTH conditions are false
func authorizeHostprepDownload(token *EnrollmentToken) error {
    if !token.Metadata.HostprepEnabled && token.Metadata.HostCollectorProfile == "" {
        return ErrForbidden  // only rejected when BOTH are absent
    }
    return nil
    // Attacker sets profile=auditd, hostprep_enabled=false → passes this check
    // Frontend hides hostprep download URL, but API call is still valid
}

// Correct: require BOTH hostprep_enabled=true AND a valid hostprep profile
func authorizeHostprepDownload(token *EnrollmentToken) error {
    if !token.Metadata.HostprepEnabled || !isHostprepProfile(token.Metadata.HostCollectorProfile) {
        return ErrForbidden
    }
    return nil
}
```

Flag any authorization guard that uses `conditionA && conditionB` where both must be false to deny — meaning either condition alone is sufficient to bypass. The correct pattern for "require feature X" is `||` (deny if either required condition is absent), not `&&` (deny only when all conditions are absent). Check that the backend enforcement is independent of any frontend gating that hides UI elements based on the same flags. Severity: medium.

## Evidence requirements

For every candidate, show the handler or worker entry point, the data-bearing variable, the sink, and the missing Go-specific mitigation. If a sanitizer exists, verify it protects the exact sink and is applied before every sink use.
