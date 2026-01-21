"""Tests for workspaces API endpoints."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.user import User
from app.models.workspace import AgentWorkspace, Workspace


class TestWorkspaceCRUD:
    """Test workspace CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_workspaces_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing workspaces when none exist."""
        client, _user = authenticated_test_client

        response = await client.get("/workspaces")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_create_workspace_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test successful workspace creation."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/workspaces",
            json={
                "name": "Test Workspace",
                "description": "A test workspace for testing",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workspace"
        assert data["description"] == "A test workspace for testing"
        assert data["is_default"] is False
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_workspace_with_settings(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating workspace with custom settings."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/workspaces",
            json={
                "name": "Custom Settings Workspace",
                "settings": {
                    "timezone": "America/New_York",
                    "booking_buffer_minutes": 30,
                    "max_advance_booking_days": 60,
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["settings"]["timezone"] == "America/New_York"
        assert data["settings"]["booking_buffer_minutes"] == 30

    @pytest.mark.asyncio
    async def test_create_workspace_minimal(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating workspace with minimal data."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/workspaces",
            json={"name": "Minimal Workspace"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Workspace"
        assert data["description"] is None
        assert data["settings"] == {}

    @pytest.mark.asyncio
    async def test_create_workspace_empty_name(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating workspace with empty name fails."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/workspaces",
            json={"name": ""},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_workspace_name_too_long(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating workspace with name exceeding max length."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/workspaces",
            json={"name": "A" * 201},  # Max is 200
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_workspace_description_too_long(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating workspace with description exceeding max length."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/workspaces",
            json={
                "name": "Test",
                "description": "A" * 2001,  # Max is 2000
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_workspaces_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing workspaces."""
        client, _user = authenticated_test_client

        # Create workspaces
        await client.post("/workspaces", json={"name": "Workspace 1"})
        await client.post("/workspaces", json={"name": "Workspace 2"})

        response = await client.get("/workspaces")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_workspace_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a specific workspace."""
        client, _user = authenticated_test_client

        # Create workspace
        create_response = await client.post(
            "/workspaces",
            json={"name": "Get Test Workspace"},
        )
        workspace_id = create_response.json()["id"]

        response = await client.get(f"/workspaces/{workspace_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workspace_id
        assert data["name"] == "Get Test Workspace"

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a non-existent workspace."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.get(f"/workspaces/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Workspace not found"

    @pytest.mark.asyncio
    async def test_get_workspace_invalid_id_format(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting workspace with invalid ID format."""
        client, _user = authenticated_test_client

        response = await client.get("/workspaces/not-a-uuid")

        assert response.status_code == 400
        assert "Invalid workspace ID format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_workspace_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating a workspace."""
        client, _user = authenticated_test_client

        # Create workspace
        create_response = await client.post(
            "/workspaces",
            json={"name": "Original Name"},
        )
        workspace_id = create_response.json()["id"]

        # Update workspace
        response = await client.put(
            f"/workspaces/{workspace_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_workspace_set_default(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test setting a workspace as default."""
        client, _user = authenticated_test_client

        # Create two workspaces
        create1 = await client.post("/workspaces", json={"name": "Workspace 1"})
        create2 = await client.post("/workspaces", json={"name": "Workspace 2"})

        workspace1_id = create1.json()["id"]
        workspace2_id = create2.json()["id"]

        # Set first as default
        await client.put(
            f"/workspaces/{workspace1_id}",
            json={"is_default": True},
        )

        # Set second as default (should unset first)
        response = await client.put(
            f"/workspaces/{workspace2_id}",
            json={"is_default": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

        # Verify first is no longer default
        get_first = await client.get(f"/workspaces/{workspace1_id}")
        assert get_first.json()["is_default"] is False

    @pytest.mark.asyncio
    async def test_update_workspace_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating a non-existent workspace."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.put(
            f"/workspaces/{fake_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_workspace_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test deleting a workspace."""
        client, _user = authenticated_test_client

        # Create workspace
        create_response = await client.post(
            "/workspaces",
            json={"name": "To Delete"},
        )
        workspace_id = create_response.json()["id"]

        # Delete workspace
        response = await client.delete(f"/workspaces/{workspace_id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(f"/workspaces/{workspace_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_default_workspace_fails(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test that deleting default workspace fails."""
        client, _user = authenticated_test_client

        # Create and set as default
        create_response = await client.post(
            "/workspaces",
            json={"name": "Default Workspace"},
        )
        workspace_id = create_response.json()["id"]

        await client.put(
            f"/workspaces/{workspace_id}",
            json={"is_default": True},
        )

        # Try to delete
        response = await client.delete(f"/workspaces/{workspace_id}")

        assert response.status_code == 400
        assert "Cannot delete the default workspace" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_workspace_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test deleting a non-existent workspace."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.delete(f"/workspaces/{fake_id}")

        assert response.status_code == 404


class TestWorkspaceAgentManagement:
    """Test workspace-agent association management."""

    @pytest.fixture
    async def test_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> dict[str, Any]:
        """Create a test workspace."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/workspaces",
            json={"name": "Agent Management Workspace"},
        )
        return response.json()

    @pytest.fixture
    async def test_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create a test agent."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Workspace Test Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_list_workspace_agents_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: dict[str, Any],
    ) -> None:
        """Test listing agents when none are assigned."""
        client, _user = authenticated_test_client

        response = await client.get(f"/workspaces/{test_workspace['id']}/agents")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_add_agent_to_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: dict[str, Any],
        test_agent: Agent,
    ) -> None:
        """Test adding an agent to a workspace."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/workspaces/{test_workspace['id']}/agents",
            json={"agent_id": str(test_agent.id)},
        )

        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_add_agent_to_workspace_as_default(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: dict[str, Any],
        test_agent: Agent,
    ) -> None:
        """Test adding an agent as default for workspace."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/workspaces/{test_workspace['id']}/agents",
            json={"agent_id": str(test_agent.id), "is_default": True},
        )

        assert response.status_code == 201

        # Verify it's in the list
        list_response = await client.get(f"/workspaces/{test_workspace['id']}/agents")
        agents = list_response.json()
        assert len(agents) == 1
        assert agents[0]["is_default"] is True

    @pytest.mark.asyncio
    async def test_add_agent_duplicate(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: dict[str, Any],
        test_agent: Agent,
    ) -> None:
        """Test adding the same agent twice fails."""
        client, _user = authenticated_test_client

        # Add first time
        await client.post(
            f"/workspaces/{test_workspace['id']}/agents",
            json={"agent_id": str(test_agent.id)},
        )

        # Add second time
        response = await client.post(
            f"/workspaces/{test_workspace['id']}/agents",
            json={"agent_id": str(test_agent.id)},
        )

        assert response.status_code == 409
        assert "already in this workspace" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_add_nonexistent_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: dict[str, Any],
    ) -> None:
        """Test adding a non-existent agent fails."""
        client, _user = authenticated_test_client
        fake_agent_id = str(uuid.uuid4())

        response = await client.post(
            f"/workspaces/{test_workspace['id']}/agents",
            json={"agent_id": fake_agent_id},
        )

        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_agent_from_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: dict[str, Any],
        test_agent: Agent,
    ) -> None:
        """Test removing an agent from a workspace."""
        client, _user = authenticated_test_client

        # Add agent
        await client.post(
            f"/workspaces/{test_workspace['id']}/agents",
            json={"agent_id": str(test_agent.id)},
        )

        # Remove agent
        response = await client.delete(
            f"/workspaces/{test_workspace['id']}/agents/{test_agent.id}"
        )

        assert response.status_code == 204

        # Verify removal
        list_response = await client.get(f"/workspaces/{test_workspace['id']}/agents")
        assert list_response.json() == []

    @pytest.mark.asyncio
    async def test_remove_agent_not_in_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: dict[str, Any],
        test_agent: Agent,
    ) -> None:
        """Test removing an agent that is not in the workspace."""
        client, _user = authenticated_test_client

        response = await client.delete(
            f"/workspaces/{test_workspace['id']}/agents/{test_agent.id}"
        )

        assert response.status_code == 404
        assert "Agent is not in this workspace" in response.json()["detail"]


class TestAgentWorkspaces:
    """Test agent's workspace associations."""

    @pytest.fixture
    async def test_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create a test agent."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Multi-Workspace Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def test_workspaces(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> list[dict[str, Any]]:
        """Create multiple test workspaces."""
        client, _user = authenticated_test_client

        workspaces = []
        for i in range(3):
            response = await client.post(
                "/workspaces",
                json={"name": f"Agent Workspace {i}"},
            )
            workspaces.append(response.json())

        return workspaces

    @pytest.mark.asyncio
    async def test_get_agent_workspaces_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test getting workspaces for an agent with none assigned."""
        client, _user = authenticated_test_client

        response = await client.get(f"/workspaces/agent/{test_agent.id}")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_agent_workspaces(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_workspaces: list[dict[str, Any]],
    ) -> None:
        """Test getting workspaces for an agent."""
        client, _user = authenticated_test_client

        # Add agent to first two workspaces
        await client.post(
            f"/workspaces/{test_workspaces[0]['id']}/agents",
            json={"agent_id": str(test_agent.id)},
        )
        await client.post(
            f"/workspaces/{test_workspaces[1]['id']}/agents",
            json={"agent_id": str(test_agent.id)},
        )

        response = await client.get(f"/workspaces/agent/{test_agent.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_agent_workspaces_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting workspaces for non-existent agent."""
        client, _user = authenticated_test_client
        fake_agent_id = str(uuid.uuid4())

        response = await client.get(f"/workspaces/agent/{fake_agent_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_set_agent_workspaces(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_workspaces: list[dict[str, Any]],
    ) -> None:
        """Test bulk setting workspaces for an agent."""
        client, _user = authenticated_test_client

        # Set workspaces
        response = await client.put(
            f"/workspaces/agent/{test_agent.id}/workspaces",
            json={"workspace_ids": [test_workspaces[0]["id"], test_workspaces[1]["id"]]},
        )

        assert response.status_code == 200

        # Verify
        get_response = await client.get(f"/workspaces/agent/{test_agent.id}")
        data = get_response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_set_agent_workspaces_replaces_existing(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_workspaces: list[dict[str, Any]],
    ) -> None:
        """Test that setting workspaces replaces existing ones."""
        client, _user = authenticated_test_client

        # Set initial workspaces
        await client.put(
            f"/workspaces/agent/{test_agent.id}/workspaces",
            json={"workspace_ids": [test_workspaces[0]["id"], test_workspaces[1]["id"]]},
        )

        # Set new workspaces (replacing)
        response = await client.put(
            f"/workspaces/agent/{test_agent.id}/workspaces",
            json={"workspace_ids": [test_workspaces[2]["id"]]},
        )

        assert response.status_code == 200

        # Verify only new workspace is assigned
        get_response = await client.get(f"/workspaces/agent/{test_agent.id}")
        data = get_response.json()
        assert len(data) == 1
        assert data[0]["workspace_id"] == test_workspaces[2]["id"]

    @pytest.mark.asyncio
    async def test_set_agent_workspaces_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_workspaces: list[dict[str, Any]],
    ) -> None:
        """Test clearing all workspaces for an agent."""
        client, _user = authenticated_test_client

        # Set initial workspaces
        await client.put(
            f"/workspaces/agent/{test_agent.id}/workspaces",
            json={"workspace_ids": [test_workspaces[0]["id"]]},
        )

        # Clear all
        response = await client.put(
            f"/workspaces/agent/{test_agent.id}/workspaces",
            json={"workspace_ids": []},
        )

        assert response.status_code == 200

        # Verify empty
        get_response = await client.get(f"/workspaces/agent/{test_agent.id}")
        assert get_response.json() == []

    @pytest.mark.asyncio
    async def test_set_agent_workspaces_invalid_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test setting invalid workspace ID."""
        client, _user = authenticated_test_client
        fake_workspace_id = str(uuid.uuid4())

        response = await client.put(
            f"/workspaces/agent/{test_agent.id}/workspaces",
            json={"workspace_ids": [fake_workspace_id]},
        )

        assert response.status_code == 400
        assert "Invalid workspace IDs" in response.json()["detail"]


class TestWorkspaceAuthentication:
    """Test workspace authentication requirements."""

    @pytest.mark.asyncio
    async def test_list_workspaces_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test listing workspaces without authentication."""
        response = await test_client.get("/workspaces")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_workspace_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test creating workspace without authentication."""
        response = await test_client.post(
            "/workspaces",
            json={"name": "Test"},
        )

        assert response.status_code == 401
