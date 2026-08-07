# Backend

FastAPI-based backend service for the Quantum-Resilient Communication System.

## Structure

- **api/** - API route handlers and endpoints
- **ai/** - AI/ML components for intelligent features
- **auth/** - Authentication and authorization modules
- **crypto/** - Post-quantum cryptography implementations
- **database/** - Database configuration and session management
- **messaging/** - Message handling and processing logic
- **websocket/** - WebSocket connection management
- **services/** - Business logic and service layer
- **core/** - Core configurations and shared utilities
- **tests/** - Unit and integration tests
- **migrations/** - Database migration scripts (Alembic) 
- **models/** - SQLAlchemy ORM models
- **schemas/** - Pydantic schemas for validation
- **routers/** - FastAPI router definitions
- **utils/** - Helper functions and utilities

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and configure
3. Run migrations: `alembic upgrade head`
4. Start server: `uvicorn main:app --reload`

## Post-quantum identity foundation

When enabled, registration generates standardized ML-KEM-768 and ML-DSA-65
identity keys through the maintained `pqcrypto` Python bindings. This is the
official naming used by the binding; no deprecated Kyber/Dilithium API is used.
Public keys are stored for identity exchange, while private keys are encrypted
with a Fernet key derived from the `PQC_MASTER_KEY` environment variable.
Message encryption is not part of this phase. Keep `PQC_ENABLED=false` for
development unless a strong master key is configured.