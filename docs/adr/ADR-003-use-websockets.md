# ADR-003: Use WebSockets for Real-Time Messaging

**Status**: Accepted  
**Date**: 2024-08-02  

---

## Context

Need real-time bidirectional communication for instant messaging, typing indicators, and presence updates.

## Decision

Use **WebSockets** via FastAPI for real-time communication.

## Alternatives Considered

- **Server-Sent Events**: Unidirectional only; rejected
- **Long Polling**: High latency and overhead; rejected
- **gRPC Streaming**: Limited browser support; rejected

## Consequences

### Positive
- Low-latency bidirectional communication
- Native browser support
- Enables typing indicators and presence

### Negative
- Connection management complexity
- Load balancer configuration required
- Stateful connections complicate scaling

## Future Notes
- Redis pub/sub needed for multi-instance scaling
- Connection limits per user to prevent DoS

## References
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)