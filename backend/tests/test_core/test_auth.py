"""Tests for authentication utilities in app/core/auth.py."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, get_user_id_from_uuid, user_id_to_uuid
from app.core.config import settings
from app.models.user import User


class TestUserIdToUuid:
    """Tests for user_id_to_uuid function."""

    def test_returns_uuid_type(self) -> None:
        """Test that function returns a UUID object."""
        result = user_id_to_uuid(1)
        assert isinstance(result, uuid.UUID)

    def test_deterministic_output(self) -> None:
        """Test that same user_id always produces same UUID."""
        user_id = 42
        result1 = user_id_to_uuid(user_id)
        result2 = user_id_to_uuid(user_id)
        assert result1 == result2

    def test_different_ids_produce_different_uuids(self) -> None:
        """Test that different user IDs produce different UUIDs."""
        uuid1 = user_id_to_uuid(1)
        uuid2 = user_id_to_uuid(2)
        uuid3 = user_id_to_uuid(100)

        assert uuid1 != uuid2
        assert uuid2 != uuid3
        assert uuid1 != uuid3

    def test_handles_large_user_ids(self) -> None:
        """Test with large user ID values."""
        large_id = 999999999
        result = user_id_to_uuid(large_id)

        assert isinstance(result, uuid.UUID)
        # Should be deterministic
        assert result == user_id_to_uuid(large_id)

    def test_handles_zero(self) -> None:
        """Test with user_id of zero."""
        result = user_id_to_uuid(0)
        assert isinstance(result, uuid.UUID)

    def test_uuid_version_5(self) -> None:
        """Test that generated UUID is version 5."""
        result = user_id_to_uuid(1)
        # UUID version 5 has version bits set to 0101 (5)
        assert result.version == 5

    def test_uses_dns_namespace(self) -> None:
        """Test that UUID uses DNS namespace for consistency."""
        # The function uses the DNS namespace UUID
        namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        expected = uuid.uuid5(namespace, "user:1")
        actual = user_id_to_uuid(1)
        assert actual == expected


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, test_session: AsyncSession) -> None:
        """Test that valid JWT token returns the user."""
        # Create a test user
        test_user = User(
            email="test@example.com",
            hashed_password="hashed_pw",
            full_name="Test User",
            is_active=True,
        )
        test_session.add(test_user)
        await test_session.commit()
        await test_session.refresh(test_user)

        # Create valid token
        token = jwt.encode(
            {"sub": str(test_user.id)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        # Mock credentials
        credentials = MagicMock()
        credentials.credentials = token

        # Call get_current_user
        result = await get_current_user(credentials, test_session)

        assert result.id == test_user.id
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, test_session: AsyncSession) -> None:
        """Test that invalid token raises 401 HTTPException."""
        credentials = MagicMock()
        credentials.credentials = "invalid.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"

    @pytest.mark.asyncio
    async def test_token_without_sub_raises_401(self, test_session: AsyncSession) -> None:
        """Test that token without 'sub' claim raises 401."""
        # Create token without 'sub'
        token = jwt.encode(
            {"data": "no_sub_here"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        credentials = MagicMock()
        credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_401(self, test_session: AsyncSession) -> None:
        """Test that token for non-existent user raises 401."""
        # Create token for user_id that doesn't exist
        token = jwt.encode(
            {"sub": "99999"},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        credentials = MagicMock()
        credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self, test_session: AsyncSession) -> None:
        """Test that expired token raises 401."""
        import time

        # Create expired token
        token = jwt.encode(
            {"sub": "1", "exp": int(time.time()) - 3600},  # Expired 1 hour ago
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        credentials = MagicMock()
        credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_raises_401(self, test_session: AsyncSession) -> None:
        """Test that token signed with wrong secret raises 401."""
        token = jwt.encode(
            {"sub": "1"},
            "wrong-secret-key",
            algorithm=settings.ALGORITHM,
        )

        credentials = MagicMock()
        credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)

        assert exc_info.value.status_code == 401


class TestGetUserIdFromUuid:
    """Tests for get_user_id_from_uuid function."""

    @pytest.mark.asyncio
    async def test_finds_matching_user(self, test_session: AsyncSession) -> None:
        """Test that function finds user with matching UUID."""
        # Create test user
        test_user = User(
            email="uuid_test@example.com",
            hashed_password="hashed_pw",
            full_name="UUID Test User",
            is_active=True,
        )
        test_session.add(test_user)
        await test_session.commit()
        await test_session.refresh(test_user)

        # Generate UUID for this user
        user_uuid = user_id_to_uuid(test_user.id)

        # Look up the user
        result = await get_user_id_from_uuid(user_uuid, test_session)

        assert result == test_user.id

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_uuid(
        self, test_session: AsyncSession
    ) -> None:
        """Test that function returns None for UUID with no matching user."""
        # Generate a UUID for a user that doesn't exist
        fake_uuid = user_id_to_uuid(99999)

        result = await get_user_id_from_uuid(fake_uuid, test_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_finds_correct_user_among_many(
        self, test_session: AsyncSession
    ) -> None:
        """Test that function finds correct user when multiple users exist."""
        # Create multiple users
        users = []
        for i in range(5):
            user = User(
                email=f"user{i}@example.com",
                hashed_password="hashed_pw",
                full_name=f"User {i}",
                is_active=True,
            )
            test_session.add(user)
            users.append(user)

        await test_session.commit()
        for user in users:
            await test_session.refresh(user)

        # Look up the third user
        target_user = users[2]
        target_uuid = user_id_to_uuid(target_user.id)

        result = await get_user_id_from_uuid(target_uuid, test_session)

        assert result == target_user.id

    @pytest.mark.asyncio
    async def test_random_uuid_returns_none(self, test_session: AsyncSession) -> None:
        """Test that random UUID (not from user_id_to_uuid) returns None."""
        random_uuid = uuid.uuid4()

        result = await get_user_id_from_uuid(random_uuid, test_session)

        assert result is None
