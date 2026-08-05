# ADR-005: Username-Based Identity

**Status**: Accepted  
**Date**: 2024-08-02  

---

## Context

Need a user identity system for authentication and display. Options include email-only, username-only, or a combination. The system must support login, profile display, and future public identity features.

## Decision

Use **username as the primary public identity**, with email as a secondary login credential. Users can log in with either username or email.

## Alternatives Considered

### Email-Only Identity
- Pros: Unique, standard, recoverable
- Cons: Exposes email publicly, privacy concern, harder to change
- **Rejected**: Privacy and public display concerns

### Phone-Number Identity
- Pros: Unique, widely used
- Cons: Requires SMS infrastructure, privacy concerns, harder to change
- **Rejected**: Infrastructure complexity and privacy

### Username + Email (chosen)
- Pros: Public identity is username (privacy), email enables recovery and verification
- Cons: Two fields to manage, username uniqueness enforcement needed
- **Accepted**: Best balance of privacy and functionality

## Consequences

### Positive
- Public identity (username) does not expose email
- Users can log in with either username or email (flexibility)
- Username is stable and user-controlled
- Email reserved for verification and recovery (future)

### Negative
- Username uniqueness must be enforced (handled in `create_user`)
- Usernames can be impersonated if not carefully managed
- Requires validation rules (length, character set)

## Future Notes
- Add email verification flow (currently `is_verified` defaults to False)
- Consider username change policy with history tracking
- Add password reset via email

## References
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)