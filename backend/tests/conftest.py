"""
Test Configuration and Fixtures for Quantum-Resilient Communication System

This module provides pytest fixtures for testing.
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Generator, Dict, Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from main import app
from database.database import Base, get_db
from models.user import User
from models.conversation import Conversation
from models.conversation_participant import ConversationParticipant
from models.message import Message
from core.security import hash_password
from core.config import Settings
from services.crypto_service import CryptoService


# Test database URL (PostgreSQL for UUID support)
TEST_DATABASE_URL = "postgresql://user:password@localhost:5432/quantum_resilient_test_db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

# Create test session factory
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db() -> Generator[Session, None, None]:
    """
    Override dependency to use test database.
    
    Yields:
        Session: SQLAlchemy database session for testing
    """
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Create all tables before tests run and drop them after.
    
    This fixture runs once per test session.
    """
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Provide a database session for each test.
    
    Yields:
        Session: SQLAlchemy database session
    """
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Provide a FastAPI test client with overridden database dependency.
    
    Yields:
        TestClient: FastAPI test client
    """
    # Override the database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Create a test user for authentication.
    
    Args:
        db_session: Database session fixture
        
    Returns:
        User: Created test user
    """
    # Use unique identifiers to avoid conflicts when tests run in same session
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com",
        password_hash=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Generate PQC identity keys so send_message() can sign messages when
    # PQC_ENABLED=true (the production default). This mirrors the production
    # device-onboarding path without modifying any crypto logic.
    try:
        CryptoService.generate_identity(user)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    except RuntimeError:
        # PQC unavailable in this environment — skip key generation.
        pass

    return user


@pytest.fixture
def auth_headers(client: TestClient, test_user: User) -> Dict[str, str]:
    """
    Generate authentication headers for a test user.
    
    Args:
        client: FastAPI test client fixture
        test_user: Test user fixture
        
    Returns:
        Dict with Authorization header containing Bearer token
    """
    from core.security import create_access_token
    
    access_token = create_access_token(subject=str(test_user.id))
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def test_user2(db_session: Session) -> User:
    """
    Create a second test user for multi-user scenarios.
    
    Args:
        db_session: Database session fixture
        
    Returns:
        User: Created test user
    """
    # Use unique identifiers to avoid conflicts when tests run in same session
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        username=f"testuser2_{unique_id}",
        email=f"test2_{unique_id}@example.com",
        password_hash=hash_password("testpassword123"),
        full_name="Test User 2",
        is_active=True,
        is_verified=True,
        is_email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Generate PQC identity keys so send_message() can sign messages when
    # PQC_ENABLED=true (the production default). This mirrors the production
    # device-onboarding path without modifying any crypto logic.
    try:
        CryptoService.generate_identity(user)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    except RuntimeError:
        # PQC unavailable in this environment — skip key generation.
        pass

    return user


@pytest.fixture
def test_conversation(db_session: Session, test_user: User, test_user2: User) -> Conversation:
    """
    Create a test conversation with participants.
    
    Args:
        db_session: Database session fixture
        test_user: First test user
        test_user2: Second test user
        
    Returns:
        Conversation: Created test conversation
    """
    conversation = Conversation(
        is_group=False,
        group_name=None,
        created_by=test_user.id,
        is_encrypted=True,
    )
    db_session.add(conversation)
    db_session.flush()
    
    # Add participants
    participant1 = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=test_user.id,
        role="admin",
    )
    participant2 = ConversationParticipant(
        conversation_id=conversation.id,
        user_id=test_user2.id,
        role="member",
    )
    db_session.add_all([participant1, participant2])
    db_session.commit()
    db_session.refresh(conversation)
    return conversation


@pytest.fixture
def test_message(db_session: Session, test_conversation: Conversation, test_user: User) -> Message:
    """
    Create a test message.
    
    Args:
        db_session: Database session fixture
        test_conversation: Test conversation fixture
        test_user: Test user fixture
        
    Returns:
        Message: Created test message
    """
    message = Message(
        conversation_id=test_conversation.id,
        sender_id=test_user.id,
        content_encrypted="encrypted_test_content",
        content_hash="abc123hash",
        message_type="text",
        is_edited=False,
        is_deleted=False,
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message
