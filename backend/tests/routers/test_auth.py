"""
Authentication API Integration Tests

These tests verify the authentication endpoints behavior.
"""

import pytest
import uuid
from fastapi.testclient import TestClient

from models.user import User
from core.security import hash_password


class TestRegister:
    """Tests for POST /api/v1/auth/register"""

    def test_register_success(self, client: TestClient, db_session):
        """
        Test successful user registration.
        
        Verifies:
        - Status code 201
        - Response contains expected user fields
        - User is created in database
        - Password is hashed
        """
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!",
                "full_name": "New User",
                "is_active": True,
                "is_verified": False,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response contains expected fields
        assert "id" in data
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert "password_hash" not in data  # Never exposed
        
        # Verify user was created in database
        user = db_session.query(User).filter(User.email == "newuser@example.com").first()
        assert user is not None
        assert user.username == "newuser"
        assert user.password_hash != "SecurePass123!"  # Password should be hashed
        assert user.password_hash.startswith("$2b$")  # Bcrypt hash prefix

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """
        Test registration with duplicate email returns 409.
        
        Verifies:
        - Status code 409 (Conflict)
        - Error message indicates duplicate email
        """
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "differentuser",
                "email": test_user.email,  # Use existing email
                "password": "SecurePass123!",
                "full_name": "Different User",
            },
        )
        
        assert response.status_code == 409
        assert "email" in response.json()["detail"].lower() or "already exists" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client: TestClient, test_user):
        """
        Test registration with duplicate username returns 409.
        
        Verifies:
        - Status code 409 (Conflict)
        - Error message indicates duplicate username
        """
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user.username,  # Use existing username
                "email": "unique@example.com",
                "password": "SecurePass123!",
                "full_name": "Unique User",
            },
        )
        
        assert response.status_code == 409
        assert "username" in response.json()["detail"].lower() or "already exists" in response.json()["detail"].lower()

    def test_register_password_is_hashed(self, client: TestClient, db_session):
        """
        Test that password is hashed in database.
        
        Verifies:
        - Password is not stored in plain text
        - Password hash starts with bcrypt prefix
        """
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "hashtest",
                "email": "hashtest@example.com",
                "password": "MyPassword123!",
                "full_name": "Hash Test",
            },
        )
        
        assert response.status_code == 201
        
        # Verify password is hashed in database
        user = db_session.query(User).filter(User.email == "hashtest@example.com").first()
        assert user.password_hash != "MyPassword123!"
        assert user.password_hash.startswith("$2b$")


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_login_success(self, client: TestClient, test_user):
        """
        Test successful login returns tokens.
        
        Verifies:
        - Status code 200
        - Response contains access_token and refresh_token
        - Token type is 'bearer'
        """
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": test_user.username,
                "password": "testpassword123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_login_with_email(self, client: TestClient, test_user):
        """
        Test login with email works.
        
        Verifies:
        - Status code 200
        - Returns valid tokens
        """
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": test_user.email,
                "password": "testpassword123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_password(self, client: TestClient, test_user):
        """
        Test login with invalid password returns 401.
        
        Verifies:
        - Status code 401
        - Error message indicates invalid credentials
        """
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": test_user.username,
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() or "credentials" in response.json()["detail"].lower()

    def test_login_unknown_email(self, client: TestClient):
        """
        Test login with unknown email returns 401.
        
        Verifies:
        - Status code 401
        - Error message indicates invalid credentials
        """
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": "nonexistent@example.com",
                "password": "somepassword",
            },
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() or "credentials" in response.json()["detail"].lower()


class TestRefreshToken:
    """Tests for POST /api/v1/auth/refresh"""

    def test_refresh_token_success(self, client: TestClient, test_user):
        """
        Test successful token refresh.
        
        Verifies:
        - Status code 200
        - Returns new access token
        - Token type is 'bearer'
        """
        # First, login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username_or_email": test_user.username,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_refresh_token_invalid(self, client: TestClient):
        """
        Test refresh with invalid token returns 401.
        
        Verifies:
        - Status code 401
        - Error message indicates invalid token
        """
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token_12345"},
        )
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()

    def test_refresh_token_wrong_type(self, client: TestClient, test_user):
        """
        Test refresh with access token (wrong type) returns 401.
        
        Verifies:
        - Status code 401
        - Error message indicates invalid token type
        """
        # Create an access token (not a refresh token)
        from core.security import create_access_token
        access_token = create_access_token(subject=str(test_user.id))
        
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        
        assert response.status_code == 401
        assert "token type" in response.json()["detail"].lower() or "refresh" in response.json()["detail"].lower()


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me"""

    def test_get_me_success(self, client: TestClient, test_user, auth_headers):
        """
        Test getting current user with valid token.
        
        Verifies:
        - Status code 200
        - Response contains user data
        - Password hash is not exposed
        """
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(test_user.id)
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert "password_hash" not in data

    def test_get_me_missing_token(self, client: TestClient):
        """
        Test getting current user without token returns 401.
        
        Verifies:
        - Status code 401
        """
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """
        Test getting current user with invalid token returns 401.
        
        Verifies:
        - Status code 401
        - Error message indicates invalid token
        """
        headers = {
            "Authorization": "Bearer invalid_token_12345",
            "Content-Type": "application/json",
        }
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()