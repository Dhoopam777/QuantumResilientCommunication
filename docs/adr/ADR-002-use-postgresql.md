# ADR-002: Use PostgreSQL as Primary Database

**Status**: Accepted  
**Date**: 2024-08-02  

---

## Context

Need a relational database for users, conversations, messages, and metadata. Must support complex queries, JSONB, and strong consistency.

## Decision

Use **PostgreSQL 12+** as the primary database.

## Alternatives Considered

### MySQL / MariaDB
- Pros: Wide adoption, good performance
- Cons: Inferior JSONB, fewer advanced types
- **Rejected**: PostgreSQL's JSONB and UUID support better match needs

### SQLite
- Pros: Zero config, single file
- Cons: No concurrent write scaling, not for production
- **Rejected**: Production requires concurrent writes

### MongoDB
- Pros: Schema flexibility, horizontal scaling
- Cons: Weaker consistency, complex relationships
- **Rejected**: Data model is strongly relational

## Consequences

### Positive
- ACID transactions ensure data integrity
- JSONB for flexible metadata (audit logs, AI data)
- Native UUID support
- Robust indexing (partial, composite, GIN)

### Negative
- Requires separate server process
- Connection pooling necessary

### Neutral
- Alembic migrations standard for PostgreSQL
- psycopg2 driver widely supported

## Future Notes

- Consider read replicas for query-heavy workloads
- Partition large tables by time if needed

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)