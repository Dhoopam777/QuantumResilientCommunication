"""
Infrastructure verification tests.

These tests verify that the testing infrastructure is set up correctly.
"""


def test_pytest_works():
    """Verify pytest is working."""
    assert True


def test_imports():
    """Verify basic imports work."""
    from main import app
    from database.database import Base, get_db
    from models.user import User
    from models.conversation import Conversation
    from models.message import Message
    assert app is not None
    assert Base is not None
    assert get_db is not None