# Contributing — Quantum-Resilient Communication System

Thank you for your interest in contributing. This document provides guidelines and instructions for contributing to this project.

---

## Table of Contents

1. [Code of Conduct](#1-code-of-conduct)
2. [Getting Started](#2-getting-started)
3. [Development Setup](#3-development-setup)
4. [Backend Development](#4-backend-development)
5. [Frontend Development](#5-frontend-development)
6. [Testing](#6-testing)
7. [Code Style](#7-code-style)
8. [Commit Guidelines](#8-commit-guidelines)
9. [Pull Request Process](#9-pull-request-process)
10. [Security Policy](#10-security-policy)
11. [Documentation](#11-documentation)

---

## 1. Code of Conduct

- Be respectful and constructive
- Focus on the issue, not the person
- Welcome newcomers and help them get started
- Report security vulnerabilities privately (see [Security Policy](#10-security-policy))

---

## 2. Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL 12+
- Git
- Ollama (for AI features)

### Clone Repository

```bash
git clone https://github.com/your-org/quantum-resilient-communication.git
cd quantum-resilient-communication
```

---

## 3. Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your local settings

# Run migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload
```

API available at `http://localhost:8000`
API docs at `http://localhost:8000/api/docs`

### Frontend (Web)

```bash
cd web

# Install dependencies
npm install

# Start development server
npm run dev
```

Web app available at `http://localhost:3000`

### Frontend (Desktop)

```bash
cd desktop

# Install dependencies
npm install

# Start development
npm run dev
```

### AI Services

```bash
# Ensure Ollama is running
ollama serve

# Pull required models
ollama pull llama3:8b
ollama pull nomic-embed-text
```

---

## 4. Backend Development

### Project Structure

```
backend/
├── api/                 # API route handlers (legacy)
├── ai/                  # AI/ML components
├── auth/                # Authentication modules
├── core/                # Core configurations, security, rate limiter
├── crypto/              # Post-quantum cryptography (future)
├── database/            # Database configuration
├── managers/            # ConnectionManager for WebSockets
├── messaging/           # Message processing
├── migrations/          # Alembic database migrations
├── models/              # SQLAlchemy ORM models
├── routers/             # FastAPI routers (auth, conversation, message, attachment, websocket)
├── schemas/             # Pydantic schemas
├── services/            # Business logic layer
├── utils/               # Utility functions
├── websocket/           # WebSocket management
├── tests/               # Test suites
├── main.py              # Application entry point
└── requirements.txt     # Python dependencies
```

### Adding a New Feature

1. Create models in `models/`
2. Create Pydantic schemas in `schemas/`
3. Implement business logic in `services/`
4. Create router in `routers/`
5. Add tests in `tests/`
6. Create Alembic migration if schema changes

### Security Requirements

- All routes requiring authentication must use `get_current_user` dependency
- All object access must validate authorization (no IDOR)
- Never trust client input — validate via Pydantic
- Never log sensitive data (tokens, passwords, file contents)
- Use `AttachmentService` patterns for any file operations

---

## 5. Frontend Development

### Web Application

```
web/
├── src/
│   ├── components/      # Reusable UI components
│   ├── pages/           # Page components
│   ├── lib/             # Utilities (WebSocket client, crypto)
│   ├── store/           # State management
│   └── styles/          # Global styles
├── public/              # Static assets
└── package.json
```

### Desktop Application

```
desktop/
├── src/
│   ├── main/            # Electron main process
│   ├── renderer/        # React renderer process
│   └── shared/          # Shared code
├── public/              # Static assets
└── package.json
```

---

## 6. Testing

### Running Tests

```bash
cd backend
pytest tests/ -v
```

### Test Structure

```
tests/
├── conftest.py          # Fixtures (test DB, client, users)
├── test_infrastructure.py
├── routers/             # Router tests
│   ├── test_auth.py
│   ├── test_conversation.py
│   ├── test_message.py
│   ├── test_attachment.py
│   └── test_websocket.py
└── services/            # Service tests
    ├── test_user_service.py
    ├── test_conversation_service.py
    ├── test_message_service.py
    └── test_attachment_service.py
```

### Writing Tests

- Use fixtures from `conftest.py`
- Test both success and failure paths
- Test authorization edge cases (non-participant, inactive user)
- Test input validation
- Test rate limiting behavior

---

## 7. Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints
- Maximum line length: 100 characters
- Use `snake_case` for functions/variables
- Use `PascalCase` for classes
- Use docstrings for all public functions/classes

```python
def send_message(
    db: Session,
    conversation_id: uuid.UUID,
    sender_id: uuid.UUID,
    content_encrypted: str,
    content_hash: str,
    message_type: str = "text",
    reply_to: Optional[uuid.UUID] = None,
) -> Message:
    """
    Send a message in a conversation.

    Args:
        db: Database session
        conversation_id: UUID of the conversation
        ...

    Returns:
        Message: The created message object

    Raises:
        ValueError: If sender is not a participant
    """
```

### TypeScript/React

- Follow [Airbnb Style Guide](https://airbnb.io/javascript/)
- Use functional components with hooks
- Use TypeScript for all new code
- Use descriptive component names

### Git Hooks

Pre-commit hooks run:
- `black` (Python formatting)
- `flake8` (Python linting)
- `eslint` (JavaScript linting)
- `prettier` (code formatting)

---

## 8. Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build)

### Examples

```
feat(auth): add refresh token rotation
fix(attachment): prevent double extension uploads
docs(readme): update setup instructions
test(websocket): add IDOR prevention tests
```

---

## 9. Pull Request Process

1. **Fork** the repository
2. Create a **feature branch** from `main`
3. Make your changes with **clear commit messages**
4. Add **tests** for new functionality
5. Ensure all tests **pass** (`pytest tests/`)
6. Update **documentation** if needed
7. Submit **pull request** with description:
   - What does this PR do?
   - Why is this change needed?
   - How does it work?
   - Screenshots (if UI changes)
8. Address **review comments**
9. Squash commits before merging

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No sensitive data in code or logs
- [ ] Input validation implemented
- [ ] Authorization checks in place
- [ ] Error handling appropriate
- [ ] No hardcoded secrets
- [ ] Performance considerations addressed

---

## 10. Security Policy

### Reporting Vulnerabilities

**Do not report security vulnerabilities through public GitHub issues.**

Email: security@your-org.com (replace with actual)

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge within 24 hours and provide a detailed response within 72 hours.

### Security Best Practices for Contributors

- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all user inputs
- Implement authorization checks consistently
- Use parameterized queries (ORM)
- Sanitize filenames and paths
- Log security events without sensitive data

---

## 11. Documentation

### Updating Documentation

- Update `README.md` for setup changes
- Update `docs/` for architecture changes
- Update docstrings for code changes
- Add inline comments for complex logic
- Update `ROADMAP.md` for phase changes

### Documentation Style

- Use Markdown
- Use tables for structured data
- Use Mermaid diagrams for flows/architecture
- Use code blocks with language tags
- Keep it concise and professional

---

## Questions?

Open a GitHub issue or reach out to the maintainers.

Thank you for contributing!