"""Tests for integrations API endpoints."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace


class TestIntegrationCRUD:
    """Test integration CRUD operations."""

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
            name="Integration Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.commit()
        await test_session.refresh(workspace)
        return workspace

    @pytest.fixture
    def valid_integration_data(self, test_workspace: Workspace) -> dict[str, Any]:
        """Valid integration connection data."""
        return {
            "integration_id": "hubspot",
            "integration_name": "HubSpot",
            "workspace_id": str(test_workspace.id),
            "credentials": {"api_key": "test-api-key-12345"},
            "metadata": {"account_name": "Test Account"},
        }

    @pytest.mark.asyncio
    async def test_connect_integration_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
    ) -> None:
        """Test successfully connecting an integration."""
        client, _user = authenticated_test_client

        response = await client.post("/api/v1/integrations", json=valid_integration_data)

        assert response.status_code == 201
        data = response.json()
        assert data["integration_id"] == "hubspot"
        assert data["integration_name"] == "HubSpot"
        assert data["is_active"] is True
        assert data["is_connected"] is True
        assert data["has_credentials"] is True
        assert "api_key" in data["credential_fields"]
        # Actual credentials should not be returned
        assert "test-api-key" not in str(data)

    @pytest.mark.asyncio
    async def test_connect_integration_user_level(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test connecting a user-level integration (no workspace)."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/integrations",
            json={
                "integration_id": "slack",
                "integration_name": "Slack",
                "workspace_id": None,
                "credentials": {"access_token": "xoxb-token"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["workspace_id"] is None
        assert data["is_connected"] is True

    @pytest.mark.asyncio
    async def test_connect_integration_duplicate(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
    ) -> None:
        """Test connecting same integration twice fails."""
        client, _user = authenticated_test_client

        # First connection
        await client.post("/api/v1/integrations", json=valid_integration_data)

        # Duplicate connection
        response = await client.post("/api/v1/integrations", json=valid_integration_data)

        assert response.status_code == 409
        assert "already connected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_connect_integration_invalid_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test connecting integration with invalid workspace ID."""
        client, _user = authenticated_test_client
        fake_workspace_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/integrations",
            json={
                "integration_id": "hubspot",
                "integration_name": "HubSpot",
                "workspace_id": fake_workspace_id,
                "credentials": {"api_key": "test"},
            },
        )

        assert response.status_code == 404
        assert "Workspace not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_connect_integration_invalid_workspace_format(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test connecting integration with invalid workspace ID format."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/integrations",
            json={
                "integration_id": "hubspot",
                "integration_name": "HubSpot",
                "workspace_id": "not-a-uuid",
                "credentials": {"api_key": "test"},
            },
        )

        assert response.status_code == 400
        assert "Invalid workspace_id format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_integrations_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing integrations when none exist."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/integrations")

        assert response.status_code == 200
        data = response.json()
        assert data["integrations"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_integrations_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
    ) -> None:
        """Test listing connected integrations."""
        client, _user = authenticated_test_client

        # Connect an integration
        await client.post("/api/v1/integrations", json=valid_integration_data)

        response = await client.get("/api/v1/integrations")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["integrations"][0]["integration_id"] == "hubspot"

    @pytest.mark.asyncio
    async def test_list_integrations_filter_by_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
        test_workspace: Workspace,
    ) -> None:
        """Test filtering integrations by workspace."""
        client, _user = authenticated_test_client

        # Connect workspace integration
        await client.post("/api/v1/integrations", json=valid_integration_data)

        # Connect user-level integration
        await client.post(
            "/api/v1/integrations",
            json={
                "integration_id": "slack",
                "integration_name": "Slack",
                "workspace_id": None,
                "credentials": {"token": "test"},
            },
        )

        # Filter by workspace
        response = await client.get(f"/api/v1/integrations?workspace_id={test_workspace.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["integrations"][0]["integration_id"] == "hubspot"

    @pytest.mark.asyncio
    async def test_get_integration_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
        test_workspace: Workspace,
    ) -> None:
        """Test getting a specific integration."""
        client, _user = authenticated_test_client

        # Connect an integration
        await client.post("/api/v1/integrations", json=valid_integration_data)

        response = await client.get(
            f"/api/v1/integrations/hubspot?workspace_id={test_workspace.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["integration_id"] == "hubspot"
        assert data["is_connected"] is True

    @pytest.mark.asyncio
    async def test_get_integration_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a non-connected integration."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/integrations/hubspot")

        assert response.status_code == 404
        assert "not connected" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_integration_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
        test_workspace: Workspace,
    ) -> None:
        """Test updating an integration."""
        client, _user = authenticated_test_client

        # Connect an integration
        await client.post("/api/v1/integrations", json=valid_integration_data)

        # Update credentials
        response = await client.put(
            f"/api/v1/integrations/hubspot?workspace_id={test_workspace.id}",
            json={
                "credentials": {"api_key": "new-api-key"},
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert "api_key" in data["credential_fields"]

    @pytest.mark.asyncio
    async def test_update_integration_partial(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
        test_workspace: Workspace,
    ) -> None:
        """Test partial update of integration."""
        client, _user = authenticated_test_client

        # Connect an integration
        await client.post("/api/v1/integrations", json=valid_integration_data)

        # Update only metadata
        response = await client.put(
            f"/api/v1/integrations/hubspot?workspace_id={test_workspace.id}",
            json={"metadata": {"new_field": "value"}},
        )

        assert response.status_code == 200
        data = response.json()
        # Original credentials should still be there
        assert "api_key" in data["credential_fields"]

    @pytest.mark.asyncio
    async def test_update_integration_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating a non-connected integration."""
        client, _user = authenticated_test_client

        response = await client.put(
            "/api/v1/integrations/hubspot",
            json={"is_active": False},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_disconnect_integration_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_integration_data: dict[str, Any],
        test_workspace: Workspace,
    ) -> None:
        """Test disconnecting an integration."""
        client, _user = authenticated_test_client

        # Connect an integration
        await client.post("/api/v1/integrations", json=valid_integration_data)

        # Disconnect
        response = await client.delete(
            f"/api/v1/integrations/hubspot?workspace_id={test_workspace.id}"
        )

        assert response.status_code == 204

        # Verify disconnected
        get_response = await client.get(
            f"/api/v1/integrations/hubspot?workspace_id={test_workspace.id}"
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_disconnect_integration_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test disconnecting a non-connected integration."""
        client, _user = authenticated_test_client

        response = await client.delete("/api/v1/integrations/hubspot")

        assert response.status_code == 404


class TestIntegrationAuthentication:
    """Test integration authentication requirements."""

    @pytest.mark.asyncio
    async def test_list_integrations_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test listing integrations without authentication."""
        response = await test_client.get("/api/v1/integrations")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_connect_integration_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test connecting integration without authentication."""
        response = await test_client.post(
            "/api/v1/integrations",
            json={
                "integration_id": "hubspot",
                "integration_name": "HubSpot",
                "credentials": {"api_key": "test"},
            },
        )

        assert response.status_code == 401


class TestCredentialMasking:
    """Test that credentials are properly masked in responses."""

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
            name="Masking Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.commit()
        await test_session.refresh(workspace)
        return workspace

    @pytest.mark.asyncio
    async def test_credentials_not_exposed(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test that actual credential values are never exposed."""
        client, _user = authenticated_test_client

        secret_key = "super-secret-api-key-12345"

        # Connect integration with secret
        await client.post(
            "/api/v1/integrations",
            json={
                "integration_id": "hubspot",
                "integration_name": "HubSpot",
                "workspace_id": str(test_workspace.id),
                "credentials": {"api_key": secret_key, "secret": "another-secret"},
            },
        )

        # List integrations
        list_response = await client.get("/api/v1/integrations")
        list_data = list_response.json()

        # Get specific integration
        get_response = await client.get(
            f"/api/v1/integrations/hubspot?workspace_id={test_workspace.id}"
        )
        get_data = get_response.json()

        # Verify secrets are not in any response
        assert secret_key not in str(list_data)
        assert secret_key not in str(get_data)
        assert "another-secret" not in str(list_data)
        assert "another-secret" not in str(get_data)

        # But field names should be listed
        assert "api_key" in list_data["integrations"][0]["credential_fields"]
        assert "secret" in list_data["integrations"][0]["credential_fields"]
