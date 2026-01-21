"""Tests for agents API endpoints."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.user import User


class TestAgentCRUD:
    """Test agent CRUD operations."""

    @pytest.fixture
    def valid_agent_data(self) -> dict[str, Any]:
        """Valid agent creation data."""
        return {
            "name": "Test Voice Agent",
            "description": "A test agent for customer service",
            "pricing_tier": "balanced",
            "system_prompt": "You are a helpful customer service agent that assists users with their questions.",
            "language": "en-US",
            "voice": "shimmer",
            "enabled_tools": ["crm"],
            "enabled_tool_ids": {"crm": ["book_appointment", "lookup_contact"]},
            "enable_recording": False,
            "enable_transcript": True,
            "turn_detection_mode": "normal",
            "turn_detection_threshold": 0.5,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

    @pytest.mark.asyncio
    async def test_create_agent_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_agent_data: dict[str, Any],
    ) -> None:
        """Test successful agent creation."""
        client, user = authenticated_test_client

        response = await client.post("/api/v1/agents", json=valid_agent_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == valid_agent_data["name"]
        assert data["pricing_tier"] == valid_agent_data["pricing_tier"]
        assert data["system_prompt"] == valid_agent_data["system_prompt"]
        assert data["language"] == valid_agent_data["language"]
        assert data["voice"] == valid_agent_data["voice"]
        assert data["is_active"] is True
        assert data["is_published"] is False
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_agent_minimal_data(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test agent creation with minimal required fields."""
        client, _user = authenticated_test_client

        minimal_data = {
            "name": "Minimal Agent",
            "pricing_tier": "budget",
            "system_prompt": "You are a helpful assistant that helps users.",
        }

        response = await client.post("/api/v1/agents", json=minimal_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Agent"
        assert data["pricing_tier"] == "budget"
        # Check defaults
        assert data["language"] == "en-US"
        assert data["voice"] == "shimmer"
        assert data["enable_transcript"] is True
        assert data["enable_recording"] is False

    @pytest.mark.asyncio
    async def test_create_agent_all_pricing_tiers(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test agent creation with all valid pricing tiers."""
        client, _user = authenticated_test_client
        tiers = ["budget", "balanced", "premium-mini", "premium"]

        for tier in tiers:
            data = {
                "name": f"Agent {tier}",
                "pricing_tier": tier,
                "system_prompt": "You are a helpful assistant for testing purposes.",
            }
            response = await client.post("/api/v1/agents", json=data)

            assert response.status_code == 201, f"Failed for tier: {tier}"
            assert response.json()["pricing_tier"] == tier

    @pytest.mark.asyncio
    async def test_create_agent_invalid_pricing_tier(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test agent creation with invalid pricing tier."""
        client, _user = authenticated_test_client

        invalid_data = {
            "name": "Invalid Agent",
            "pricing_tier": "invalid_tier",
            "system_prompt": "You are a helpful assistant for testing purposes.",
        }

        response = await client.post("/api/v1/agents", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_agent_missing_required_fields(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test agent creation with missing required fields."""
        client, _user = authenticated_test_client

        # Missing name
        response = await client.post(
            "/api/v1/agents",
            json={
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant.",
            },
        )
        assert response.status_code == 422

        # Missing pricing_tier
        response = await client.post(
            "/api/v1/agents",
            json={"name": "Test", "system_prompt": "You are helpful."},
        )
        assert response.status_code == 422

        # Missing system_prompt
        response = await client.post(
            "/api/v1/agents",
            json={"name": "Test", "pricing_tier": "balanced"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_agent_system_prompt_too_short(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test agent creation with system prompt too short."""
        client, _user = authenticated_test_client

        data = {
            "name": "Test Agent",
            "pricing_tier": "balanced",
            "system_prompt": "Short",  # Less than 10 characters
        }

        response = await client.post("/api/v1/agents", json=data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_agent_name_too_long(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test agent creation with name exceeding max length."""
        client, _user = authenticated_test_client

        data = {
            "name": "A" * 201,  # 201 characters, max is 200
            "pricing_tier": "balanced",
            "system_prompt": "You are a helpful assistant for testing purposes.",
        }

        response = await client.post("/api/v1/agents", json=data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_agent_unauthenticated(
        self,
        test_client: AsyncClient,
        valid_agent_data: dict[str, Any],
    ) -> None:
        """Test agent creation without authentication."""
        response = await test_client.post("/api/v1/agents", json=valid_agent_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_agents_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing agents when none exist."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/agents")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_list_agents_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing multiple agents."""
        client, _user = authenticated_test_client

        # Create multiple agents
        for i in range(3):
            await client.post(
                "/api/v1/agents",
                json={
                    "name": f"Agent {i}",
                    "pricing_tier": "balanced",
                    "system_prompt": f"You are test agent number {i} for testing.",
                },
            )

        response = await client.get("/api/v1/agents")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_list_agents_pagination(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test agent listing with pagination."""
        client, _user = authenticated_test_client

        # Create 5 agents
        for i in range(5):
            await client.post(
                "/api/v1/agents",
                json={
                    "name": f"Agent {i}",
                    "pricing_tier": "balanced",
                    "system_prompt": f"You are test agent number {i} for testing.",
                },
            )

        # Test skip and limit
        response = await client.get("/api/v1/agents?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_agents_invalid_skip(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing agents with invalid skip parameter."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/agents?skip=-1")

        assert response.status_code == 400
        assert "Skip must be non-negative" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_agents_invalid_limit(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing agents with invalid limit parameter."""
        client, _user = authenticated_test_client

        # Limit less than 1
        response = await client.get("/api/v1/agents?limit=0")
        assert response.status_code == 400
        assert "Limit must be at least 1" in response.json()["detail"]

        # Limit exceeds max
        response = await client.get("/api/v1/agents?limit=101")
        assert response.status_code == 400
        assert "Limit cannot exceed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_agent_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a specific agent."""
        client, _user = authenticated_test_client

        # Create an agent
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Get the agent
        response = await client.get(f"/api/v1/agents/{agent_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == agent_id
        assert data["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_get_agent_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a non-existent agent."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.get(f"/api/v1/agents/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    @pytest.mark.asyncio
    async def test_get_agent_invalid_uuid(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting an agent with invalid UUID format."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/agents/invalid-uuid")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_agent_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating an agent."""
        client, _user = authenticated_test_client

        # Create an agent
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Original Name",
                "pricing_tier": "balanced",
                "system_prompt": "You are the original agent for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Update the agent
        response = await client.put(
            f"/api/v1/agents/{agent_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
                "is_active": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_agent_pricing_tier(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating agent pricing tier updates provider config."""
        client, _user = authenticated_test_client

        # Create an agent with budget tier
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "pricing_tier": "budget",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Update to premium tier
        response = await client.put(
            f"/api/v1/agents/{agent_id}",
            json={"pricing_tier": "premium"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pricing_tier"] == "premium"

    @pytest.mark.asyncio
    async def test_update_agent_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating a non-existent agent."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.put(
            f"/api/v1/agents/{fake_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_agent_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test deleting an agent."""
        client, _user = authenticated_test_client

        # Create an agent
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Agent to Delete",
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Delete the agent
        response = await client.delete(f"/api/v1/agents/{agent_id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(f"/api/v1/agents/{agent_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test deleting a non-existent agent."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.delete(f"/api/v1/agents/{fake_id}")

        assert response.status_code == 404


class TestAgentEmbedSettings:
    """Test agent embed settings endpoints."""

    @pytest.mark.asyncio
    async def test_get_embed_settings_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting embed settings for an agent."""
        client, _user = authenticated_test_client

        # Create an agent
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Embed Test Agent",
                "pricing_tier": "premium",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Get embed settings
        response = await client.get(f"/api/v1/agents/{agent_id}/embed")

        assert response.status_code == 200
        data = response.json()
        assert "public_id" in data
        assert "embed_enabled" in data
        assert "allowed_domains" in data
        assert "embed_settings" in data
        assert "script_tag" in data
        assert "iframe_code" in data

    @pytest.mark.asyncio
    async def test_get_embed_settings_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting embed settings for non-existent agent."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.get(f"/api/v1/agents/{fake_id}/embed")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_embed_settings_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating embed settings."""
        client, _user = authenticated_test_client

        # Create an agent
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Embed Test Agent",
                "pricing_tier": "premium",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Update embed settings
        response = await client.patch(
            f"/api/v1/agents/{agent_id}/embed",
            json={
                "embed_enabled": True,
                "allowed_domains": ["example.com", "*.example.org"],
                "embed_settings": {"theme": "dark", "primary_color": "#ff0000"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["embed_enabled"] is True
        assert "example.com" in data["allowed_domains"]
        assert data["embed_settings"]["theme"] == "dark"
        assert data["embed_settings"]["primary_color"] == "#ff0000"

    @pytest.mark.asyncio
    async def test_update_embed_settings_auto_whitelist_production_url(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test that production_url automatically adds domain to allowed list."""
        client, _user = authenticated_test_client

        # Create an agent
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Embed Test Agent",
                "pricing_tier": "premium",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Update with production_url
        response = await client.patch(
            f"/api/v1/agents/{agent_id}/embed",
            json={
                "embed_settings": {"production_url": "https://myapp.example.com/page"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "myapp.example.com" in data["allowed_domains"]

    @pytest.mark.asyncio
    async def test_regenerate_public_id_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test regenerating public ID for an agent."""
        client, _user = authenticated_test_client

        # Create an agent
        create_response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Embed Test Agent",
                "pricing_tier": "premium",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )
        agent_id = create_response.json()["id"]

        # Get initial public_id
        initial_response = await client.get(f"/api/v1/agents/{agent_id}/embed")
        initial_public_id = initial_response.json()["public_id"]

        # Regenerate public ID
        response = await client.post(f"/api/v1/agents/{agent_id}/embed/regenerate-id")

        assert response.status_code == 200
        data = response.json()
        assert data["public_id"] != initial_public_id

    @pytest.mark.asyncio
    async def test_regenerate_public_id_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test regenerating public ID for non-existent agent."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.post(f"/api/v1/agents/{fake_id}/embed/regenerate-id")

        assert response.status_code == 404


class TestAgentValidation:
    """Test agent validation edge cases."""

    @pytest.mark.asyncio
    async def test_create_agent_turn_detection_validation(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test turn detection parameter validation."""
        client, _user = authenticated_test_client

        # Invalid turn detection mode
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant for testing purposes.",
                "turn_detection_mode": "invalid_mode",
            },
        )
        assert response.status_code == 422

        # Threshold out of range
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant for testing purposes.",
                "turn_detection_threshold": 1.5,  # Max is 1.0
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_agent_llm_settings_validation(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test LLM settings validation."""
        client, _user = authenticated_test_client

        # Temperature out of range
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant for testing purposes.",
                "temperature": 3.0,  # Max is 2.0
            },
        )
        assert response.status_code == 422

        # Max tokens out of range
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Test Agent",
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant for testing purposes.",
                "max_tokens": 50,  # Min is 100
            },
        )
        assert response.status_code == 422
