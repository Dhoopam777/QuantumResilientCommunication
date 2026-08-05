# Project Report — Quantum-Resilient Communication System

> **Purpose**: This document is the basis of the final-year project report. Each phase is documented with purpose, implementation summary, security considerations, outcomes, and lessons learned.

---

## Phase 1: Project Foundation & Database Design

**Purpose**
Establish a robust, secure database foundation with proper relationships, constraints, and migration management to support all subsequent features.

**Why This Phase Was Necessary**
Every feature depends on reliable data storage. A well-designed schema prevents data integrity issues, simplifies business logic, and enforces access-control foundations.

**Implementation Summary**
- Designed 4 core entities: `users`, `conversations`, `conversation_participants`, `messages`
- Created Alembic migrations 001–004 for versioned schema evolution
- Established UUID primary keys for all entities
- Implemented `TimestampMixin` for consistent `created_at` / `updated_at` / `deleted_at`
- Defined foreign keys with `RESTRICT` where appropriate
- Added soft-delete support via `is_deleted` and `deleted_at`

**Security Considerations**
- UUIDs prevent object enumeration (vs. auto-increment integers)
- Foreign keys restrict accidental cascading data loss
- Soft deletes preserve auditability and referential integrity

**Outcome**
Stable schema with 4 migrations applied successfully. Foundation ready for auth, messaging, and future extensions.

**Lessons Learned**
- UUIDs increase storage slightly but greatly improve security posture
- Soft deletes add complexity but are essential for messaging audit trails

---

## Phase 2: Authentication & Authorization

**Purpose**
Provide secure user identity, session management, and protected access to all endpoints.

**Why This Phase Was Necessary**
Secure communication requires verified identities and controlled access. JWT-based sessions enable stateless scaling while maintaining strong authentication.

**Implementation Summary**
- Implemented registration, login, token refresh, and profile update endpoints
- Used bcrypt (cost 12) for password hashing
- Issued short-lived access tokens (15 min) and long-lived refresh tokens (7 days)
- Created `get_current_user` dependency for route protection
- Refresh tokens stored in database with revocation support

**Security Considerations**
- Passwords never stored or returned in plaintext
- JWTs validated on every protected request
- Token type enforced (`access` vs. `refresh`)
- Inactive users denied access

**Outcome**
Functional authentication system with secure session lifecycle management.

**Lessons Learned**
- Refresh token storage enables immediate revocation and multi-device support
- Username-or-email login improves usability without sacrificing security

---

## Phase 3: Core Messaging (REST)

**Purpose**
Deliver persistent messaging with conversation management, pagination, and participant controls.

**Why This Phase Was Necessary**
Core user value depends on reliable message storage and retrieval. REST API provides the baseline contract that WebSocket later extends.

**Implementation Summary**
- Conversation creation with automatic participant enrollment
- Message send/receive with encrypted content and SHA-256 integrity hashes
- Paginated message retrieval (default 50, max 100)
- Soft deletes for messages (`is_deleted`, `deleted_at`)
- Participant listing with role tracking
- Last-message previews in conversation responses

**Security Considerations**
- Only active participants can send or read messages (`is_participant` check)
- Content stored encrypted; integrity verified via hash
- Pagination prevents unbounded memory usage

**Outcome**
REST messaging API fully operational. Foundation laid for WebSocket real-time layer.

**Lessons Learned**
- Reusing `is_participant` across routers prevents IDOR duplication
- Soft deletes preserve conversation history for compliance

---

## Phase 4: Real-Time WebSocket Messaging

**Purpose**
Add instant, bidirectional message delivery while preserving the same security model as the REST layer.

**Why This Phase Was Necessary**
Modern messaging requires real-time presence. WebSockets reduce latency and enable typing indicators, read receipts, and live updates.

**Implementation Summary**
- Single `/ws` endpoint — no conversation IDs in URLs
- JWT authentication via first `auth` message
- `ConnectionManager` singleton tracks connections and subscriptions
- Per-conversation authorization before subscription
- Broadcast scoped to authorized subscriptions only
- Graceful disconnect cleanup
- REST message router integrates with `ConnectionManager` for post-persist broadcast

**Security Considerations**
- IDOR prevented: subscription requires DB lookup (`is_participant`) every time
- Token never appears in URL (travels inside encrypted WebSocket frame)
- Unauthenticated connections cannot join conversations
- Dead connections removed from subscription sets automatically

**Outcome**
Real-time messaging operational with strong authorization guarantees.

**Lessons Learned**
- Single WebSocket endpoint simplifies firewall rules and logging
- Database authorization on every subscription is non-negotiable

---

## Phase 5: AI Integration & RAG

**Purpose**
Add intelligent assistant features using local LLM inference and retrieval-augmented generation.

**Why This Phase Was Necessary**
AI assistance differentiates the product and provides security explanations, smart search, and conversation summarization without sending data to third parties.

**Implementation Summary**
- Integrated Ollama for local LLM inference (Llama 3, Mistral)
- Added ChromaDB vector store for message embeddings
- Implemented LangChain orchestration for context-aware responses
- Created `AIConversations` and `AIMessages` tables for persistent chat history
- Designed embedding pipeline for semantic search over messages

**Security Considerations**
- All AI processing remains on local infrastructure
- No sensitive data (passwords, keys) injected into prompts
- Users control their AI conversation history

**Outcome**
AI assistant framework complete with RAG context retrieval.

**Lessons Learned**
- Local LLM inference preserves privacy but requires GPU for performance
- Context window management is critical to avoid truncation

---

## Phase 6: Attachment Framework

**Purpose**
Enable secure file sharing within conversations while preventing common file-upload attacks.

**Why This Phase Was Necessary**
Users expect to share images and files. Insecure implementations are a top attack vector; this phase demonstrates security-first attachment handling.

**Implementation Summary**
- Image-only uploads (PNG, JPEG, WebP) in Phase 8.1
- Server-side MIME detection via magic bytes (never trust client headers)
- EXIF metadata stripped; images re-encoded server-side
- UUIDv4 filenames for on-disk storage outside web root
- SHA-256 checksums computed server-side for integrity
- Thumbnail generation server-side
- Filename sanitization: path traversal, null bytes, double extensions blocked
- Rate limiting: max 10 uploads/minute/user, max 3 concurrent
- Dedicated audit logger for attachment security events
- Soft delete in DB + hard delete on disk

**Security Considerations**
- OWASP A03:2021 (Injection) — magic-byte MIME detection prevents content-type spoofing
- OWASP A04:2021 (Insecure Design) — allowlist-only file types, reject all others
- OWASP A05:2021 (Security Misconfiguration) — files outside web root, never expose filesystem paths
- OWASP A07:2021 (Identification & Authentication Failures) — rate limiting prevents abuse
- IDOR prevention: attachment access verified via conversation membership

**Outcome**
Production-grade attachment pipeline with comprehensive attack mitigations.

**Lessons Learned**
- Magic-byte detection is essential; Content-Type headers are untrustworthy
- Re-encoding images removes hidden EXIF and malformed chunks

---

## Phase 7: Security Hardening & Testing (In Progress)

**Purpose**
Validate that all implemented features meet production security standards and OWASP Top 10 requirements.

**Why This Phase Is Necessary**
Security must be verified, not assumed. Automated and manual testing ensures mitigations hold under adversarial conditions.

**Implementation Summary**
- Infrastructure tests verified (pytest, FastAPI TestClient, SQLite in-memory DB)
- Developing router and service test suites
- Reviewing input validation across all routers
- Validating rate limiting behavior
- Expanding security headers

**Security Considerations**
- OWASP Top 10 coverage verification
- IDOR prevention validation across attachment, message, and conversation paths
- Brute-force and enumeration resistance

**Outcome**
Pending. Test coverage expanding; security posture improving.

**Lessons Learned**
- Test infrastructure setup pays immediate dividends
- Security is easier to build in from the start than to retrofit