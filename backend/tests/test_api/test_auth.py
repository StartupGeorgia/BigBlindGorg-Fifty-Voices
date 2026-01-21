"""Tests for authentication API endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.models.user import User


class TestUserRegistration:
    """Test user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test successful user registration."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "New User",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "New User"
        assert "id" in data
        # Password should not be returned
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test registration with already existing email."""
        # First registration
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "User One",
                "password": "password123",
            },
        )

        # Second registration with same email
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "username": "User Two",
                "password": "password456",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Email already registered"

    @pytest.mark.asyncio
    async def test_register_invalid_email(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test registration with invalid email format."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "username": "Test User",
                "password": "password123",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_fields(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test registration with missing required fields."""
        # Missing email
        response = await test_client.post(
            "/api/v1/auth/register",
            json={"username": "Test", "password": "password123"},
        )
        assert response.status_code == 422

        # Missing username
        response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert response.status_code == 422

        # Missing password
        response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "username": "Test"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_empty_fields(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test registration with empty string fields."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "",
                "username": "",
                "password": "",
            },
        )

        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint."""

    @pytest.fixture
    async def registered_user(self, test_client: AsyncClient) -> dict[str, str]:
        """Create a registered user for login tests."""
        user_data = {
            "email": "loginuser@example.com",
            "username": "Login User",
            "password": "testpassword123",
        }
        await test_client.post("/api/v1/auth/register", json=user_data)
        return user_data

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        test_client: AsyncClient,
        registered_user: dict[str, str],
    ) -> None:
        """Test successful login returns access token."""
        response = await test_client.post(
            "/api/v1/auth/login",
            data={
                "username": registered_user["email"],
                "password": registered_user["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        test_client: AsyncClient,
        registered_user: dict[str, str],
    ) -> None:
        """Test login with wrong password."""
        response = await test_client.post(
            "/api/v1/auth/login",
            data={
                "username": registered_user["email"],
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test login with non-existent email."""
        response = await test_client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    @pytest.mark.asyncio
    async def test_login_missing_credentials(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test login with missing credentials."""
        # Missing password
        response = await test_client.post(
            "/api/v1/auth/login",
            data={"username": "test@example.com"},
        )
        assert response.status_code == 422

        # Missing username
        response = await test_client.post(
            "/api/v1/auth/login",
            data={"password": "password123"},
        )
        assert response.status_code == 422


class TestGetCurrentUser:
    """Test get current user endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting current user information."""
        client, user = authenticated_test_client

        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["username"] == user.full_name

    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test getting current user without authentication."""
        response = await test_client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestAuthenticationFlow:
    """Test complete authentication flows."""

    @pytest.mark.asyncio
    async def test_register_and_login_flow(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test complete registration and login flow."""
        # Register
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "flowtest@example.com",
                "username": "Flow Test User",
                "password": "securepassword123",
            },
        )
        assert register_response.status_code == 200
        user_data = register_response.json()

        # Login
        login_response = await test_client.post(
            "/api/v1/auth/login",
            data={
                "username": "flowtest@example.com",
                "password": "securepassword123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Access protected endpoint
        me_response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "flowtest@example.com"

    @pytest.mark.asyncio
    async def test_invalid_token(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test accessing protected endpoint with invalid token."""
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_authorization_header(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test accessing protected endpoint with malformed auth header."""
        # Missing Bearer prefix
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "some_token"},
        )
        assert response.status_code == 401

        # Empty header
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": ""},
        )
        assert response.status_code == 401


class TestPasswordSecurity:
    """Test password security features."""

    @pytest.mark.asyncio
    async def test_password_is_hashed(
        self,
        test_client: AsyncClient,
        test_session: Any,
    ) -> None:
        """Test that passwords are properly hashed in database."""
        from sqlalchemy import select

        # Register a user
        plain_password = "myplainpassword123"
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "hashtest@example.com",
                "username": "Hash Test",
                "password": plain_password,
            },
        )

        # Check database directly
        result = await test_session.execute(
            select(User).where(User.email == "hashtest@example.com")
        )
        user = result.scalar_one()

        # Password should be hashed, not plain
        assert user.hashed_password != plain_password
        # bcrypt hashes start with $2b$
        assert user.hashed_password.startswith("$2b$")

    @pytest.mark.asyncio
    async def test_case_sensitive_email(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test email case sensitivity in login."""
        # Register with lowercase email
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "casetest@example.com",
                "username": "Case Test",
                "password": "password123",
            },
        )

        # Login with same case should work
        response = await test_client.post(
            "/api/v1/auth/login",
            data={
                "username": "casetest@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 200
