"""Tests for tools API endpoints."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.user import User
from app.models.workspace import AgentWorkspace, Workspace


class TestToolExecution:
    """Test tool execution endpoint."""

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
            name="Tool Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.commit()
        await test_session.refresh(workspace)
        return workspace

    @pytest.fixture
    async def test_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> Agent:
        """Create a test agent with tools enabled."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Tool Test Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            enabled_tools=["crm", "calendar"],
        )
        test_session.add(agent)
        await test_session.flush()

        # Link agent to workspace
        agent_workspace = AgentWorkspace(
            agent_id=agent.id,
            workspace_id=test_workspace.id,
        )
        test_session.add(agent_workspace)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_execute_tool_lookup_contact(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test executing lookup_contact tool."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "lookup_contact",
                "arguments": {"phone_number": "+15551234567"},
                "agent_id": str(test_agent.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Tool should return success (even if contact not found)
        assert "success" in data

    @pytest.mark.asyncio
    async def test_execute_tool_book_appointment(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test executing book_appointment tool."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "book_appointment",
                "arguments": {
                    "customer_name": "Test Customer",
                    "customer_phone": "+15551234567",
                    "datetime": "2024-12-20T10:00:00",
                    "service_type": "consultation",
                },
                "agent_id": str(test_agent.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_execute_tool_check_availability(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test executing check_availability tool."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "check_availability",
                "arguments": {"date": "2024-12-20"},
                "agent_id": str(test_agent.id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test executing tool with invalid agent ID."""
        client, _user = authenticated_test_client
        fake_agent_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "lookup_contact",
                "arguments": {"phone_number": "+15551234567"},
                "agent_id": fake_agent_id,
            },
        )

        # Should still work but without workspace context
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_tool_missing_required_fields(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test executing tool with missing required fields."""
        client, _user = authenticated_test_client

        # Missing tool_name
        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "arguments": {"phone_number": "+15551234567"},
                "agent_id": str(uuid.uuid4()),
            },
        )

        assert response.status_code == 422

        # Missing arguments
        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "lookup_contact",
                "agent_id": str(uuid.uuid4()),
            },
        )

        assert response.status_code == 422

        # Missing agent_id
        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "lookup_contact",
                "arguments": {"phone_number": "+15551234567"},
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test executing unknown tool name."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "unknown_tool_xyz",
                "arguments": {},
                "agent_id": str(test_agent.id),
            },
        )

        # Should return 500 or error response
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is False or "error" in data

    @pytest.mark.asyncio
    async def test_execute_tool_empty_arguments(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test executing tool with empty arguments."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "check_availability",
                "arguments": {},
                "agent_id": str(test_agent.id),
            },
        )

        # Tool should handle missing arguments gracefully
        assert response.status_code in [200, 500]


class TestToolExecutionAuthentication:
    """Test tool execution authentication requirements."""

    @pytest.mark.asyncio
    async def test_execute_tool_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test executing tool without authentication."""
        fake_agent_id = str(uuid.uuid4())

        response = await test_client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "lookup_contact",
                "arguments": {"phone_number": "+15551234567"},
                "agent_id": fake_agent_id,
            },
        )

        assert response.status_code == 401


class TestToolExecutionValidation:
    """Test tool execution request validation."""

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
            name="Validation Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.commit()
        await test_session.refresh(workspace)
        return workspace

    @pytest.fixture
    async def test_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> Agent:
        """Create a test agent."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Validation Test Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
            enabled_tools=["crm"],
        )
        test_session.add(agent)
        await test_session.flush()

        agent_workspace = AgentWorkspace(
            agent_id=agent.id,
            workspace_id=test_workspace.id,
        )
        test_session.add(agent_workspace)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_execute_tool_invalid_agent_id_format(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test executing tool with invalid agent ID format."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "lookup_contact",
                "arguments": {"phone_number": "+15551234567"},
                "agent_id": "not-a-uuid",
            },
        )

        # Should still work, just without workspace context
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_tool_various_argument_types(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test executing tools with various argument types."""
        client, _user = authenticated_test_client

        # String arguments
        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "lookup_contact",
                "arguments": {"phone_number": "+15551234567"},
                "agent_id": str(test_agent.id),
            },
        )
        assert response.status_code == 200

        # Nested object arguments
        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "book_appointment",
                "arguments": {
                    "customer_name": "Test",
                    "customer_phone": "+15551234567",
                    "datetime": "2024-12-20T10:00:00",
                    "service_type": "test",
                    "notes": "Nested test",
                },
                "agent_id": str(test_agent.id),
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_tool_with_null_arguments(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test executing tool with null values in arguments."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/tools/execute",
            json={
                "tool_name": "book_appointment",
                "arguments": {
                    "customer_name": "Test",
                    "customer_phone": "+15551234567",
                    "datetime": "2024-12-20T10:00:00",
                    "service_type": "test",
                    "notes": None,  # Null value
                },
                "agent_id": str(test_agent.id),
            },
        )

        assert response.status_code == 200
