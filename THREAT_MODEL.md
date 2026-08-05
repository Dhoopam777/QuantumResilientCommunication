# Threat Model — Quantum-Resilient Communication System

This document identifies assets, attack surface, threat actors, threat scenarios, mitigations, and residual risks for the Quantum-Resilient Communication System.

---

## 1. Assets

| Asset | Description | Sensitivity |
|-------|-------------|-------------|
| User credentials | Usernames, email addresses, password hashes | High |
| Message content | Encrypted message payloads | High |
| Cryptographic keys | ML-KEM/ML-DSA key pairs (future), AES-256-GCM session keys | High |
| Session tokens | JWT access and refresh tokens | High |
| Attachments | Uploaded images and future files | Medium |
| User profiles | Display names, bios, profile pictures | Low |
| Audit logs | Security event records | Medium |
| Database | All persistent application data | High |

---

## 2. Attack Surface

### External Interfaces
- REST API (`/api/v1/*`) — FastAPI endpoints over HTTPS
- WebSocket endpoint (`/ws`) — real-time messaging
- File upload/download endpoints (`/api/v1/attachments/*`)

### Data Stores
- PostgreSQL database (users, conversations, messages, refresh tokens, audit logs)
- ChromaDB vector store (AI embeddings)
- Local filesystem storage (attachments, thumbnails)

### Trust Boundaries
- Client → Server (untrusted internet)
- Server → Database (trusted internal network)
- Server → Ollama LLM (trusted internal service)

---

## 3. Threat Actors

| Actor | Motivation | Capability |
|-------|-----------|------------|
| External attacker | Data theft, service disruption | Moderate — can scan, probe, and exploit vulnerabilities |
| Malicious insider | Data exfiltration, sabotage | High — legitimate access, knowledge of internals |
| Quantum adversary (future) | Decrypt harvested communications | High — access to quantum computer, "harvest now, decrypt later" |
| Account takeover attacker | Impersonate users, access private messages | Moderate — credential stuffing, phishing |
| Automated scanner | Discover vulnerable endpoints | Low — automated tools, no manual exploitation |

---

## 4. Threat Scenarios & Mitigations

### 4.1 IDOR (Insecure Direct Object Reference)

**Scenario**: Attacker guesses or enumerates conversation/message/attachment UUIDs to access unauthorized resources.

**Mitigations**:
- UUIDv4 primary keys (unpredictable)
- `is_participant()` database check before every access
- Attachment access verified via conversation membership
- No object IDs exposed in WebSocket URLs
- 404 returned for missing resources (prevents enumeration)

**Residual Risk**: Low — UUID space is vast; DB authorization is enforced consistently.

---

### 4.2 SQL Injection

**Scenario**: Attacker injects SQL through input fields to read/modify database.

**Mitigations**:
- SQLAlchemy ORM used exclusively (no raw SQL)
- Parameterized queries via ORM
- Pydantic schema validation before DB access

**Residual Risk**: Very Low — ORM prevents classic injection; no raw SQL in codebase.

---

### 4.3 XSS (Cross-Site Scripting)

**Scenario**: Attacker injects malicious scripts into messages or profiles to execute in victims' browsers.

**Mitigations**:
- Message content stored encrypted (not rendered server-side)
- Pydantic serialization with auto-escaping
- No server-side HTML rendering of user content
- Content-Type headers set correctly
- `X-Content-Type-Options: nosniff` on responses

**Residual Risk**: Low — client-side rendering of decrypted content still requires client-side sanitization (frontend responsibility).

---

### 4.4 CSRF (Cross-Site Request Forgery)

**Scenario**: Attacker tricks authenticated user into sending unwanted requests.

**Mitigations**:
- JWT in Authorization header (not cookies by default)
- CORS configured to specific origins
- SameSite cookie consideration for future cookie-based auth

**Residual Risk**: Low — stateless JWT in headers is not automatically sent by browsers.

---

### 4.5 Path Traversal

**Scenario**: Attacker uses `../` sequences in filenames to access files outside intended directory.

**Mitigations**:
- `os.path.basename()` strips directory components
- Null byte removal
- Encoded traversal sequence decoding and stripping
- Path separator replacement
- UUIDv4 filenames for storage (client names never used for paths)

**Residual Risk**: Very Low — multiple layers of sanitization; storage outside web root.

---

### 4.6 File Upload Attacks

**Scenario**: Attacker uploads malicious files (executables, webshells, polyglots).

**Mitigations**:
- Allowlist-only MIME types (PNG, JPEG, WebP)
- Magic-byte MIME detection (not client headers)
- Extension validation against MIME type
- Double extension blocking
- Blocked extension list (`.exe`, `.js`, `.php`, etc.)
- EXIF stripping and image re-encoding
- Decompression bomb detection
- Files stored outside web root
- UUIDv4 filenames
- Rate limiting

**Residual Risk**: Low — image-only restriction limits attack surface; future file types require additional scanning.

---

### 4.7 Replay Attacks

**Scenario**: Attacker captures valid messages or tokens and replays them to gain unauthorized access or duplicate actions.

**Mitigations**:
- JWT expiration (15 minutes for access tokens)
- Refresh token rotation and revocation
- Nonce-based message processing (future)
- Timestamp validation in audit logs

**Residual Risk**: Low — short-lived tokens limit replay window; message-level nonces future enhancement.

---

### 4.8 WebSocket Abuse

**Scenario**: Attacker opens WebSocket connections to exhaust resources, send malicious messages, or intercept broadcasts.

**Mitigations**:
- Single `/ws` endpoint (simplifies monitoring)
- JWT authentication required before any action
- Per-conversation authorization via DB lookup
- Connection limits per user (future)
- Heartbeat timeout for dead connections
- Rate limiting on messages (future)

**Residual Risk**: Moderate — DoS protection via rate limiting and connection limits still being expanded.

---

### 4.9 Account Enumeration

**Scenario**: Attacker determines which usernames/emails are registered.

**Mitigations**:
- Generic error messages: `Invalid credentials` (no distinction between "user not found" and "wrong password")
- Same response time for existing and non-existing users (future)
- Registration endpoint does not confirm existing users in a distinguishable way

**Residual Risk**: Low — timing side-channels may still exist; constant-time comparison future improvement.

---

### 4.10 Brute Force Attacks

**Scenario**: Attacker tries many password combinations to guess credentials.

**Mitigations**:
- bcrypt cost factor 12 (intentionally slow hashing)
- Rate limiting on login (future: 5 attempts per 15 min per IP)
- Account lockout after failed attempts (future)
- Refresh token revocation on password change

**Residual Risk**: Moderate — rate limiting not yet implemented on login endpoint; planned for Phase 7.

---

### 4.11 Spam Accounts

**Scenario**: Attacker creates大量 fake accounts for abuse or to exhaust resources.

**Mitigations**:
- Registration rate limiting (future: 3 per hour per IP)
- Email verification requirement (future)
- CAPTCHA integration (future)
- Monitoring for suspicious registration patterns

**Residual Risk**: Moderate — rate limiting and email verification not yet implemented.

---

### 4.12 Quantum Harvest Attacks

**Scenario**: Adversary records encrypted communications today to decrypt when quantum computer becomes available.

**Mitigations**:
- AES-256-GCM for symmetric encryption (Grover's algorithm provides only sqrt speedup, still secure with 256-bit keys)
- Future: ML-KEM/ML-DSA integration for post-quantum key exchange and signatures
- Key rotation planned (limits exposure window)

**Residual Risk**: High until PQC algorithms integrated in Phase 10.

---

## 5. Mitigations Summary

| Threat | Status | Mitigation |
|--------|--------|------------|
| IDOR | Implemented | UUIDs + DB authorization on every access |
| SQL Injection | Implemented | SQLAlchemy ORM, no raw SQL |
| XSS | Partial | Encrypted storage, Pydantic serialization; client-side sanitization needed |
| CSRF | Implemented | JWT in headers, CORS restrictions |
| Path Traversal | Implemented | Multi-layer sanitization, basename extraction |
| File Upload Attacks | Implemented | Magic-byte MIME, allowlist, re-encoding, outside web root |
| Replay Attacks | Partial | JWT expiration; message nonces future |
| WebSocket Abuse | Partial | Auth required, per-conversation auth; connection limits future |
| Account Enumeration | Implemented | Generic error messages |
| Brute Force | Partial | bcrypt cost 12; rate limiting future |
| Spam Accounts | Partial | No current limits; rate limiting future |
| Quantum Harvest | Partial | AES-256-GCM; full PQC planned Phase 10 |

---

## 6. Residual Risks

1. **Classical Cryptography**: JWT HS256 and lack of perfect forward secrecy are acceptable for current phase but must be addressed before production.
2. **Testing Gaps**: Not all paths have automated test coverage; undiscovered vulnerabilities may exist.
3. **Rate Limiting**: In-memory implementation insufficient for multi-instance deployments.
4. **Client-Side Security**: XSS prevention depends on frontend sanitization of decrypted content.
5. **AI Prompt Injection**: No filtering of malicious prompts to LLM (future risk).
6. **Supply Chain**: Dependencies may contain vulnerabilities; need automated scanning (future).
7. **Operational Security**: No WAF, no DDoS protection, no intrusion detection in current deployment model.

---

## 7. Ongoing Risk Management

- Regular dependency updates and vulnerability scanning
- Expanding automated test coverage
- Implementing rate limiting on all sensitive endpoints
- Adding security headers (CSP, HSTS)
- Penetration testing before production
- Bug bounty program (post-launch)

---

## References

- [OWASP Top 10 (2021)](https://owasp.org/Top10/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [NIST Post-Quantum Cryptography](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)