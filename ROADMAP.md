# Roadmap — Quantum-Resilient Communication System

## Project Overview

A web-based secure communication platform implementing post-quantum cryptography (ML-KEM, ML-DSA) and AI-powered features. The system provides end-to-end encrypted messaging with WebSocket-based real-time delivery, designed to remain secure against both classical and quantum computing threats.

## Objectives

- Provide future-proof secure messaging resistant to quantum attacks
- Implement NIST-standardized post-quantum cryptographic algorithms
- Deliver real-time communication with strong security guarantees
- Integrate AI-assisted features for security analysis and user assistance
- Maintain production-grade security, performance, and usability

## Phase Breakdown

### ✅ Phase 1: Project Foundation & Database Design
- Status: Completed
- Deliverables: Database schema (Users, Conversations, Messages, Participants), Alembic migrations 001-004, base models, relationships

### ✅ Phase 2: Authentication & Authorization
- Status: Completed
- Deliverables: JWT access/refresh tokens, bcrypt password hashing, registration/login endpoints, protected route dependency, user profile management

### ✅ Phase 3: Core Messaging (REST)
- Status: Completed
- Deliverables: Conversation CRUD, message send/receive with pagination, participant management, read receipts infrastructure, soft deletes

### ✅ Phase 4: Real-Time WebSocket Messaging
- Status: Completed
- Deliverables: WebSocket endpoint `/ws`, JWT authentication over WS, per-conversation subscription, broadcast to participants, typing indicators/presence infrastructure, IDOR prevention

### ✅ Phase 5: AI Integration & RAG
- Status: Completed
- Deliverables: ChromaDB vector store, Ollama LLM integration, LangChain orchestration, AI conversation history, RAG context retrieval, embedding pipeline

### ✅ Phase 6: Attachment Framework
- Status: Completed
- Deliverables: Secure image upload (PNG/JPEG/WebP), server-side MIME detection via magic bytes, EXIF stripping, UUIDv4 filenames, SHA-256 checksums, thumbnail generation, rate limiting, audit logging, soft delete

### 🚧 Phase 7: Security Hardening & Testing
- Status: In Progress
- Deliverables: Comprehensive test suite, input validation review, rate limiting expansion, security headers, penetration testing, OWASP Top 10 verification

### ⬜ Phase 8: Advanced Features & Polish
- Status: Planned
- Deliverables: Message reactions, file sharing beyond images, message search, push notifications, mobile apps, key rotation UI

### ⬜ Phase 9: Production Deployment
- Status: Planned
- Deliverables: Docker production images, Nginx/Traefik reverse proxy, PostgreSQL HA, Redis for scaling, monitoring (Prometheus/Grafana), CI/CD, encrypted backups

### ⬜ Phase 10: Post-Quantum Cryptography Implementation
- Status: Planned
- Deliverables: liboqs integration for ML-KEM/ML-DSA, key generation on registration, key rotation, quantum-safe session establishment, migration from classical crypto

### ✅ Phase 11: Multi-Device Schema Foundation (QRC Secure V2 — Phase 1)
- Status: Completed
- Deliverables: Additive database schema for multi-device architecture — `devices`, `refresh_tokens`, `security_codes`, `link_tokens`, `device_public_key_history`, `encrypted_envelopes` tables; device FK columns on `session_keys`, `messages`, `attachments`; Alembic migrations 019–022
- Scope: Schema preparation only. Multi-device behavior is NOT activated. No device authentication, QR/OTC linking, Security Code flow, per-device message encryption, or WebSocket changes were implemented.
- Security: New schema stores public device keys only. Legacy server-side PQC private-key handling remains unchanged (removal deferred to a later phase). The `encrypted_envelopes` table is storage preparation, not active envelope encryption.

### ⬜ Phase 12: Research & Publication
- Status: Planned
- Deliverables: Final year project report, performance benchmarks, security analysis, academic paper draft, public demo

## Current Active Phase

**Phase 7: Security Hardening & Testing** — Expanding test coverage, validating OWASP mitigations, and hardening attachment and messaging paths.

## Future Enhancements

- Multi-modal AI (voice, image understanding)
- Group call/voice messaging
- End-to-end encrypted file sharing with DLP
- Decentralized identity / DID
- Quantum key distribution (QKD) exploration
- Plugin ecosystem for extensibility
- Open-source community launch