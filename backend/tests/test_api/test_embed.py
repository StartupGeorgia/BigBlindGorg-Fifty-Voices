"""Tests for public embed API endpoints."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.user import User
from app.models.workspace import AgentWorkspace, Workspace


class TestEmbedConfig:
    """Test embed configuration endpoints."""

    @pytest.fixture
    async def embed_enabled_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create an agent with embedding enabled."""
        _client, user = authenticated_test_client

        workspace = Workspace(
            user_id=user.id,
            name="Embed Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.flush()

        agent = Agent(
            user_id=user.id,
            name="Embed Test Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=True,
            is_active=True,
            allowed_domains=["example.com", "*.test.com"],
            embed_settings={
                "greeting_message": "Hello! How can I help?",
                "button_text": "Chat with us",
                "theme": "dark",
                "position": "bottom-right",
                "primary_color": "#ff0000",
            },
        )
        test_session.add(agent)
        await test_session.flush()

        # Create agent-workspace association
        agent_workspace = AgentWorkspace(
            agent_id=agent.id,
            workspace_id=workspace.id,
        )
        test_session.add(agent_workspace)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def embed_disabled_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create an agent with embedding disabled."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Non-Embed Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=False,
            is_active=True,
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_get_embed_config_success(
        self,
        test_client: AsyncClient,
        embed_enabled_agent: Agent,
    ) -> None:
        """Test getting embed config for an enabled agent."""
        response = await test_client.get(
            f"/api/public/embed/{embed_enabled_agent.public_id}/config",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["public_id"] == embed_enabled_agent.public_id
        assert data["name"] == "Embed Test Agent"
        assert data["greeting_message"] == "Hello! How can I help?"
        assert data["button_text"] == "Chat with us"
        assert data["theme"] == "dark"
        assert data["position"] == "bottom-right"
        assert data["primary_color"] == "#ff0000"

    @pytest.mark.asyncio
    async def test_get_embed_config_not_found(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test getting config for non-existent agent."""
        response = await test_client.get(
            "/api/public/embed/nonexistent-public-id/config",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    @pytest.mark.asyncio
    async def test_get_embed_config_disabled(
        self,
        test_client: AsyncClient,
        embed_disabled_agent: Agent,
    ) -> None:
        """Test getting config for agent with embedding disabled."""
        response = await test_client.get(
            f"/api/public/embed/{embed_disabled_agent.public_id}/config",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_embed_config_origin_not_allowed(
        self,
        test_client: AsyncClient,
        embed_enabled_agent: Agent,
    ) -> None:
        """Test getting config from non-allowed origin."""
        response = await test_client.get(
            f"/api/public/embed/{embed_enabled_agent.public_id}/config",
            headers={"Origin": "https://malicious-site.com"},
        )

        assert response.status_code == 403
        assert "not allowed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_embed_config_wildcard_domain(
        self,
        test_client: AsyncClient,
        embed_enabled_agent: Agent,
    ) -> None:
        """Test that wildcard domains work correctly."""
        # Should work with subdomain matching *.test.com
        response = await test_client.get(
            f"/api/public/embed/{embed_enabled_agent.public_id}/config",
            headers={"Origin": "https://app.test.com"},
        )

        assert response.status_code == 200


class TestEmbedSession:
    """Test embed session creation endpoints."""

    @pytest.fixture
    async def embed_enabled_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create an agent with embedding enabled."""
        _client, user = authenticated_test_client

        workspace = Workspace(
            user_id=user.id,
            name="Session Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.flush()

        agent = Agent(
            user_id=user.id,
            name="Session Test Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=True,
            is_active=True,
            allowed_domains=["example.com"],
        )
        test_session.add(agent)
        await test_session.flush()

        agent_workspace = AgentWorkspace(
            agent_id=agent.id,
            workspace_id=workspace.id,
        )
        test_session.add(agent_workspace)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_create_session_success(
        self,
        test_client: AsyncClient,
        embed_enabled_agent: Agent,
    ) -> None:
        """Test creating an embed session."""
        response = await test_client.post(
            f"/api/public/embed/{embed_enabled_agent.public_id}/session",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "expires_at" in data
        assert "websocket_url" in data
        assert embed_enabled_agent.public_id in data["websocket_url"]

    @pytest.mark.asyncio
    async def test_create_session_not_found(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test creating session for non-existent agent."""
        response = await test_client.post(
            "/api/public/embed/nonexistent-public-id/session",
            headers={"Origin": "https://example.com"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_session_origin_not_allowed(
        self,
        test_client: AsyncClient,
        embed_enabled_agent: Agent,
    ) -> None:
        """Test creating session from non-allowed origin."""
        response = await test_client.post(
            f"/api/public/embed/{embed_enabled_agent.public_id}/session",
            headers={"Origin": "https://malicious-site.com"},
        )

        assert response.status_code == 403


class TestEmbedToolCall:
    """Test embed tool call execution endpoint."""

    @pytest.fixture
    async def embed_agent_with_tools(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create an agent with tools enabled."""
        _client, user = authenticated_test_client

        workspace = Workspace(
            user_id=user.id,
            name="Tool Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.flush()

        agent = Agent(
            user_id=user.id,
            name="Tool Test Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=True,
            is_active=True,
            allowed_domains=["example.com"],
            enabled_tools=["crm"],
        )
        test_session.add(agent)
        await test_session.flush()

        agent_workspace = AgentWorkspace(
            agent_id=agent.id,
            workspace_id=workspace.id,
        )
        test_session.add(agent_workspace)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_tool_call_not_enabled(
        self,
        test_client: AsyncClient,
        embed_agent_with_tools: Agent,
    ) -> None:
        """Test calling a tool that is not enabled for the agent."""
        response = await test_client.post(
            f"/api/public/embed/{embed_agent_with_tools.public_id}/tool-call",
            headers={"Origin": "https://example.com"},
            json={
                "tool_name": "disabled_tool",
                "arguments": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not enabled" in data["error"]

    @pytest.mark.asyncio
    async def test_tool_call_origin_not_allowed(
        self,
        test_client: AsyncClient,
        embed_agent_with_tools: Agent,
    ) -> None:
        """Test tool call from non-allowed origin."""
        response = await test_client.post(
            f"/api/public/embed/{embed_agent_with_tools.public_id}/tool-call",
            headers={"Origin": "https://malicious-site.com"},
            json={
                "tool_name": "book_appointment",
                "arguments": {},
            },
        )

        assert response.status_code == 403


class TestEmbedTranscript:
    """Test embed transcript saving endpoint."""

    @pytest.fixture
    async def embed_agent_with_transcript(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create an agent with transcripts enabled."""
        _client, user = authenticated_test_client

        workspace = Workspace(
            user_id=user.id,
            name="Transcript Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.flush()

        agent = Agent(
            user_id=user.id,
            name="Transcript Test Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=True,
            is_active=True,
            allowed_domains=["example.com"],
            enable_transcript=True,
        )
        test_session.add(agent)
        await test_session.flush()

        agent_workspace = AgentWorkspace(
            agent_id=agent.id,
            workspace_id=workspace.id,
        )
        test_session.add(agent_workspace)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_save_transcript_success(
        self,
        test_client: AsyncClient,
        embed_agent_with_transcript: Agent,
    ) -> None:
        """Test saving a transcript."""
        response = await test_client.post(
            f"/api/public/embed/{embed_agent_with_transcript.public_id}/transcript",
            headers={"Origin": "https://example.com"},
            json={
                "session_id": "test-session-123",
                "transcript": "User: Hello\nAgent: Hi, how can I help?",
                "duration_seconds": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "call_id" in data

    @pytest.mark.asyncio
    async def test_save_empty_transcript_skipped(
        self,
        test_client: AsyncClient,
        embed_agent_with_transcript: Agent,
    ) -> None:
        """Test that empty transcripts are skipped."""
        response = await test_client.post(
            f"/api/public/embed/{embed_agent_with_transcript.public_id}/transcript",
            headers={"Origin": "https://example.com"},
            json={
                "session_id": "test-session-123",
                "transcript": "   ",  # Empty/whitespace
                "duration_seconds": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "skipped" in data["message"]

    @pytest.mark.asyncio
    async def test_save_transcript_origin_not_allowed(
        self,
        test_client: AsyncClient,
        embed_agent_with_transcript: Agent,
    ) -> None:
        """Test saving transcript from non-allowed origin."""
        response = await test_client.post(
            f"/api/public/embed/{embed_agent_with_transcript.public_id}/transcript",
            headers={"Origin": "https://malicious-site.com"},
            json={
                "session_id": "test-session-123",
                "transcript": "Test transcript",
                "duration_seconds": 30,
            },
        )

        assert response.status_code == 403


class TestOriginValidation:
    """Test origin validation edge cases."""

    @pytest.fixture
    async def agent_with_empty_domains(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create an agent with empty allowed domains (allows all)."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Open Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=True,
            is_active=True,
            allowed_domains=[],  # Empty = allow all
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_empty_allowed_domains_allows_all(
        self,
        test_client: AsyncClient,
        agent_with_empty_domains: Agent,
    ) -> None:
        """Test that empty allowed_domains allows any origin."""
        response = await test_client.get(
            f"/api/public/embed/{agent_with_empty_domains.public_id}/config",
            headers={"Origin": "https://any-site.com"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_origin_header_with_restrictions(
        self,
        test_client: AsyncClient,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> None:
        """Test request with no origin header when domains are restricted."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Restricted Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=True,
            is_active=True,
            allowed_domains=["example.com"],  # Restricted
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)

        # No Origin header
        response = await test_client.get(
            f"/api/public/embed/{agent.public_id}/config",
        )

        assert response.status_code == 403


class TestInactiveAgent:
    """Test handling of inactive agents."""

    @pytest.fixture
    async def inactive_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create an inactive agent."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Inactive Agent",
            pricing_tier="premium",
            system_prompt="You are a helpful assistant for testing purposes.",
            embed_enabled=True,
            is_active=False,  # Inactive
            allowed_domains=[],
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.mark.asyncio
    async def test_inactive_agent_config_forbidden(
        self,
        test_client: AsyncClient,
        inactive_agent: Agent,
    ) -> None:
        """Test that inactive agents return 403."""
        response = await test_client.get(
            f"/api/public/embed/{inactive_agent.public_id}/config",
        )

        assert response.status_code == 403
        assert "not active" in response.json()["detail"]
