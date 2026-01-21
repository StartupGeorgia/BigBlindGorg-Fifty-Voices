"""Tests for user settings API endpoints."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace


class TestUserSettings:
    """Test user settings endpoints."""

    @pytest.fixture
    async def test_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Workspace:
        """Create a test workspace."""
        _client, user = authenticated_test_client

        workspace = Workspace(
            user_id=user.id,
            name="Settings Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.commit()
        await test_session.refresh(workspace)
        return workspace

    @pytest.mark.asyncio
    async def test_get_settings_default(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting default settings when none are configured."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["openai_api_key_set"] is False
        assert data["deepgram_api_key_set"] is False
        assert data["elevenlabs_api_key_set"] is False
        assert data["telnyx_api_key_set"] is False
        assert data["twilio_account_sid_set"] is False

    @pytest.mark.asyncio
    async def test_get_settings_with_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test getting settings for a specific workspace."""
        client, _user = authenticated_test_client

        response = await client.get(f"/api/v1/settings?workspace_id={test_workspace.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == str(test_workspace.id)

    @pytest.mark.asyncio
    async def test_get_settings_invalid_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting settings with invalid workspace ID."""
        client, _user = authenticated_test_client
        fake_workspace_id = str(uuid.uuid4())

        response = await client.get(f"/api/v1/settings?workspace_id={fake_workspace_id}")

        assert response.status_code == 404
        assert "Workspace not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_settings_invalid_workspace_format(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting settings with invalid workspace ID format."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/settings?workspace_id=not-a-uuid")

        assert response.status_code == 400
        assert "Invalid workspace_id format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_settings_create_new(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating new settings."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/settings",
            json={
                "openai_api_key": "sk-test-key-12345",
                "telnyx_api_key": "telnyx-api-key",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Settings updated successfully"

        # Verify settings are set
        get_response = await client.get("/api/v1/settings")
        get_data = get_response.json()
        assert get_data["openai_api_key_set"] is True
        assert get_data["telnyx_api_key_set"] is True

    @pytest.mark.asyncio
    async def test_update_settings_workspace_specific(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test creating workspace-specific settings."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/api/v1/settings?workspace_id={test_workspace.id}",
            json={
                "openai_api_key": "sk-workspace-key",
                "twilio_account_sid": "AC12345",
                "twilio_auth_token": "auth-token-123",
            },
        )

        assert response.status_code == 200

        # Verify workspace settings
        get_response = await client.get(f"/api/v1/settings?workspace_id={test_workspace.id}")
        get_data = get_response.json()
        assert get_data["openai_api_key_set"] is True
        assert get_data["twilio_account_sid_set"] is True
        assert get_data["workspace_id"] == str(test_workspace.id)

    @pytest.mark.asyncio
    async def test_update_settings_partial(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test partial update of settings."""
        client, _user = authenticated_test_client

        # First set some settings
        await client.post(
            "/api/v1/settings",
            json={
                "openai_api_key": "sk-initial-key",
                "telnyx_api_key": "telnyx-initial",
            },
        )

        # Update only one key
        response = await client.post(
            "/api/v1/settings",
            json={"deepgram_api_key": "dg-key-12345"},
        )

        assert response.status_code == 200

        # Verify both old and new settings exist
        get_response = await client.get("/api/v1/settings")
        get_data = get_response.json()
        assert get_data["openai_api_key_set"] is True
        assert get_data["telnyx_api_key_set"] is True
        assert get_data["deepgram_api_key_set"] is True

    @pytest.mark.asyncio
    async def test_clear_api_key(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test clearing an API key by setting empty string."""
        client, _user = authenticated_test_client

        # First set a key
        await client.post(
            "/api/v1/settings",
            json={"openai_api_key": "sk-test-key"},
        )

        # Clear the key
        response = await client.post(
            "/api/v1/settings",
            json={"openai_api_key": ""},
        )

        assert response.status_code == 200

        # Verify key is cleared
        get_response = await client.get("/api/v1/settings")
        get_data = get_response.json()
        assert get_data["openai_api_key_set"] is False

    @pytest.mark.asyncio
    async def test_settings_isolation_between_workspaces(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> None:
        """Test that settings are isolated between workspaces."""
        client, user = authenticated_test_client

        # Create two workspaces
        workspace1 = Workspace(
            user_id=user.id,
            name="Workspace 1",
        )
        workspace2 = Workspace(
            user_id=user.id,
            name="Workspace 2",
        )
        test_session.add_all([workspace1, workspace2])
        await test_session.commit()
        await test_session.refresh(workspace1)
        await test_session.refresh(workspace2)

        # Set different keys for each workspace
        await client.post(
            f"/api/v1/settings?workspace_id={workspace1.id}",
            json={"openai_api_key": "sk-workspace1-key"},
        )

        await client.post(
            f"/api/v1/settings?workspace_id={workspace2.id}",
            json={"telnyx_api_key": "telnyx-workspace2-key"},
        )

        # Verify workspace 1 only has OpenAI key
        ws1_response = await client.get(f"/api/v1/settings?workspace_id={workspace1.id}")
        ws1_data = ws1_response.json()
        assert ws1_data["openai_api_key_set"] is True
        assert ws1_data["telnyx_api_key_set"] is False

        # Verify workspace 2 only has Telnyx key
        ws2_response = await client.get(f"/api/v1/settings?workspace_id={workspace2.id}")
        ws2_data = ws2_response.json()
        assert ws2_data["openai_api_key_set"] is False
        assert ws2_data["telnyx_api_key_set"] is True


class TestSettingsAuthentication:
    """Test settings authentication requirements."""

    @pytest.mark.asyncio
    async def test_get_settings_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test getting settings without authentication."""
        response = await test_client.get("/api/v1/settings")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_settings_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test updating settings without authentication."""
        response = await test_client.post(
            "/api/v1/settings",
            json={"openai_api_key": "test-key"},
        )

        assert response.status_code == 401


class TestSettingsSecurity:
    """Test settings security - API keys should never be exposed."""

    @pytest.mark.asyncio
    async def test_api_keys_not_returned(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test that actual API key values are never returned."""
        client, _user = authenticated_test_client

        secret_key = "sk-super-secret-key-12345"

        # Set a secret key
        await client.post(
            "/api/v1/settings",
            json={"openai_api_key": secret_key},
        )

        # Get settings
        response = await client.get("/api/v1/settings")
        data = response.json()

        # The actual key value should never be in the response
        assert secret_key not in str(data)
        # Only boolean indicating if it's set
        assert data["openai_api_key_set"] is True
