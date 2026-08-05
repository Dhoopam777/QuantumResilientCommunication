# ADR-006: Attachment Framework

**Status**: Accepted  
**Date**: 2024-08-02  

---

## Context

Need a secure file-sharing capability within conversations. File uploads are a top attack vector (OWASP A04:2021 Insecure Design, A03:2021 Injection). The framework must prevent malicious file execution, path traversal, MIME spoofing, and resource exhaustion.

## Decision

Implement a **security-hardened attachment framework** with:

- Image-only uploads in Phase 8.1 (PNG, JPEG, WebP)
- Server-side MIME detection via magic bytes (never trust client headers)
- EXIF stripping and image re-encoding server-side
- UUIDv4 filenames for on-disk storage outside web root
- SHA-256 checksums computed server-side
- Server-side thumbnail generation
- Filename sanitization (path traversal, null bytes, double extensions)
- Rate limiting (10 uploads/min/user, 3 concurrent)
- Dedicated audit logging
- Soft delete in DB + hard delete on disk

## Alternatives Considered

### Client-Side Validation Only
- Pros: Simple, fast
- Cons: Trivially bypassed, no real security
- **Rejected**: Security must be enforced server-side

### Store Files in Database (BLOB)
- Pros: Single data store, transactional
- Cons: Database bloat, poor performance for large files, backup complexity
- **Rejected**: Filesystem storage is more appropriate

### Direct S3/Cloud Storage
- Pros: Scalable, managed
- Cons: External dependency, cost, complexity for local dev
- **Rejected**: Overkill for current phase; can be added later

### Accept All File Types
- Pros: Maximum flexibility
- Cons: High risk of malicious uploads (webshells, executables)
- **Rejected**: Security-first approach requires allowlist

## Consequences

### Positive
- Strong defense against file-upload attacks
- No filesystem path disclosure
- Integrity verification via SHA-256
- Audit trail for all uploads
- Rate limiting prevents abuse

### Negative
- Image-only restriction limits functionality (Phase 8.1)
- Re-encoding adds CPU overhead
- Requires storage directory management

## Future Notes
- Broaden file types with content scanning (Phase 8+)
- Add virus/malware scanning
- Consider S3/cloud storage for horizontal scaling
- Add content-based deduplication

## References
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [OWASP Top 10 (2021)](https://owasp.org/Top10/)