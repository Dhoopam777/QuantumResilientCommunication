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