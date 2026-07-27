# Quantum-Resilient Communication System

**Final Year Project**

A web-based secure communication system implementing post-quantum cryptography and AI-powered features for future-proof security.

## Overview

This project aims to develop a secure communication platform that is resilient against quantum computing threats. By implementing post-quantum cryptographic algorithms and leveraging AI for enhanced security features, this system provides a future-proof solution for secure messaging.

## Key Features

- **Post-Quantum Cryptography**: Implementation of quantum-resistant encryption algorithms
- **AI-Powered Security**: Intelligent threat detection and security analysis
- **Real-time Messaging**: WebSocket-based instant communication
- **End-to-End Encryption**: Secure message transmission
- **Cross-Platform**: Web application and desktop client support

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT with python-jose
- **AI/ML**: LangChain, Ollama, ChromaDB
- **Real-time**: WebSockets

### Frontend
- **Web**: React + TypeScript + Vite
- **Desktop**: Electron + React

## Project Structure

```
QuantumResilientCommunication/
├── backend/          # FastAPI backend service
│   ├── api/         # API route handlers
│   ├── ai/          # AI/ML components
│   ├── auth/        # Authentication modules
│   ├── crypto/      # Post-quantum cryptography
│   ├── database/    # Database configuration
│   ├── messaging/   # Message processing
│   ├── websocket/   # WebSocket management
│   ├── services/    # Business logic
│   ├── core/        # Core configurations
│   ├── tests/       # Test suites
│   ├── migrations/  # Database migrations
│   ├── models/      # SQLAlchemy models
│   ├── schemas/     # Pydantic schemas
│   ├── routers/     # FastAPI routers
│   └── utils/       # Utility functions
├── web/             # React web application
├── desktop/         # Electron desktop app
├── docs/            # Documentation
└── scripts/         # Utility scripts
```

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL 12+
- Ollama (for AI models)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/api/docs`

### Frontend Setup

See `web/README.md` and `desktop/README.md` for frontend setup instructions.

## Development

### Running Tests

```bash
cd backend
pytest tests/
```

### Code Style

- Backend: Follow PEP 8 guidelines
- Frontend: ESLint + Prettier configuration

## Documentation

See the `docs/` directory for:
- Final year project report
- Technical specifications
- API documentation
- Architecture diagrams

## License

This project is developed as part of a Final Year Project. All rights reserved.

## Contact

For questions or feedback, please contact the development team.