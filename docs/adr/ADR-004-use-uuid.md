# ADR-004: Use UUID Primary Keys

**Status**: Accepted  
**Date**: 2024-08-02  

---

## Context

Need primary keys for all database entities. Auto-increment integers are common but expose business metrics and enable enumeration attacks.

## Decision

Use **UUIDv4** (random) as primary keys for all database tables.

## Alternatives Considered

### Auto-increment Integer
- Pros: Small storage, fast indexing, human-readable
- Cons: Enables enumeration attacks, exposes business metrics (user count), merge conflicts
- **Rejected**: Security and privacy concerns outweigh benefits

### UUIDv7 (time-ordered)
- Pros: Sortable, better index locality
- Cons: Leaks creation time, less widely supported
- **Rejected**: UUIDv4 is more standard and privacy-preserving

### ULID / Snowflake
- Pros: Sortable, distributed-friendly
- Cons: Additional library dependency, complexity
- **Rejected**: Overkill for current single-database deployment

## Consequences

### Positive
- Prevents object enumeration (IDOR mitigation)
- Merge-friendly across data sources
- No business metric leakage
- Standard across PostgreSQL and SQLAlchemy

### Negative
- Larger storage footprint (16 bytes vs 4)
- Slightly slower index performance
- Not human-readable

## Future Notes
- Consider UUIDv7 if time-ordered indexing becomes a performance bottleneck
- PostgreSQL native UUID type used throughout

## References
- [RFC 4122: UUID](https://datatracker.ietf.org/doc/html/rfc4122)
- [PostgreSQL UUID Type](https://www.postgresql.org/docs/current/datatype-uuid.html)