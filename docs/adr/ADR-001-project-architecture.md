# ADR-001: Project Architecture

**Status**: Accepted  
**Date**: 2024-08-02  
**Decision Makers**: Development Team  

---

## Context

We need to choose an architecture for the Quantum-Resilient Communication System that balances security, scalability, maintainability, and real-time performance. The system must support post-quantum cryptography, AI features, and both web and desktop clients.

---

## Decision

We will use a **modular monolith** architecture with clear separation of concerns:

- **FastAPI** backend with routers, services, models, and schemas
- **WebSocket** support via `ConnectionManager` singleton
- **SQLAlchemy ORM** for database access
- **Alembic** for migrations
- **PostgreSQL** as primary database
- **ChromaDB** for vector embeddings
- **Ollama** for local LLM inference

---

## Alternatives Considered

### 1. Microservices Architecture

**Pros**:
- Independent scaling of services
- Technology diversity per service
- Fault isolation

**Cons**:
- Significant operational complexity
- Network latency between services
- Requires service mesh or API gateway
- Overkill for current team size and load

**Rejected because**: The project is in early stages; microservices add complexity without immediate benefit.

---

### 2. Serverless Functions (Lambda/Cloud Functions)

**Pros**:
- Automatic scaling
- Pay-per-use cost model
- No server management

**Cons**:
- Cold start latency (problematic for WebSockets)
- Limited execution time
- State management complexity
- Local LLM inference difficult

**Rejected because**: WebSocket connections require persistent connections; serverless is not suitable.

---

### 3. Monolithic FastAPI (no modules)

**Pros**:
- Simplest possible structure
- Fastest development initially

**Cons**:
- Poor long-term maintainability
- Hard to test in isolation
- Tight coupling between features
- Difficult to onboard new developers

**Rejected because**: Modular structure costs little upfront and pays off in maintainability.

---

## Consequences

### Positive
- Clear module boundaries (auth, messaging, AI, attachments)
- Easy to locate and update code
- Testable via dependency injection
- Can extract services later if needed
- FastAPI's `APIRouter` enables modular design

### Negative
- Still a single deployment unit (not independently scalable)
- Requires discipline to maintain boundaries

### Neutral
- Current structure supports Phase 1–7 requirements
- Can migrate to microservices in Phase 9 if needed

---

## Future Notes

- If scaling becomes necessary, extract AI service first (independent resource needs)
- Consider Redis for session sharing if multiple API instances deployed
- WebSocket `ConnectionManager` will need Redis pub/sub for horizontal scaling

---

## References

- [FastAPI Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [Modular Monolith Pattern](https://wiki.c2.com/?ModularMonolith)