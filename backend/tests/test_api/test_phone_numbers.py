"""Tests for phone numbers API endpoints."""

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.phone_number import PhoneNumber
from app.models.user import User
from app.models.workspace import Workspace


class TestPhoneNumberCRUD:
    """Test phone number CRUD operations."""

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
            name="Phone Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.commit()
        await test_session.refresh(workspace)
        return workspace

    @pytest.fixture
    async def test_phone_number(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> PhoneNumber:
        """Create a test phone number."""
        _client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        phone = PhoneNumber(
            user_id=user_id_to_uuid(user.id),
            phone_number="+15551234567",
            friendly_name="Test Line",
            provider="telnyx",
            provider_id="telnyx-123",
            workspace_id=test_workspace.id,
            can_receive_calls=True,
            can_make_calls=True,
        )
        test_session.add(phone)
        await test_session.commit()
        await test_session.refresh(phone)
        return phone

    @pytest.mark.asyncio
    async def test_list_phone_numbers_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing phone numbers when none exist."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/phone-numbers")

        assert response.status_code == 200
        data = response.json()
        assert data["phone_numbers"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_phone_numbers_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
    ) -> None:
        """Test listing phone numbers with existing records."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/phone-numbers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["phone_numbers"][0]["phone_number"] == "+15551234567"
        assert data["phone_numbers"][0]["provider"] == "telnyx"

    @pytest.mark.asyncio
    async def test_list_phone_numbers_pagination(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> None:
        """Test phone number listing with pagination."""
        client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        # Create 5 phone numbers
        for i in range(5):
            phone = PhoneNumber(
                user_id=user_id_to_uuid(user.id),
                phone_number=f"+1555123456{i}",
                provider="telnyx",
                provider_id=f"telnyx-{i}",
                workspace_id=test_workspace.id,
            )
            test_session.add(phone)
        await test_session.commit()

        # Test pagination
        response = await client.get("/api/v1/phone-numbers?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["phone_numbers"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_list_phone_numbers_filter_by_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
        test_workspace: Workspace,
    ) -> None:
        """Test filtering phone numbers by workspace."""
        client, _user = authenticated_test_client

        response = await client.get(f"/api/v1/phone-numbers?workspace_id={test_workspace.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["phone_numbers"]) == 1

    @pytest.mark.asyncio
    async def test_list_phone_numbers_filter_by_status(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
    ) -> None:
        """Test filtering phone numbers by status."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/phone-numbers?status=active")

        assert response.status_code == 200
        data = response.json()
        assert len(data["phone_numbers"]) == 1

    @pytest.mark.asyncio
    async def test_get_phone_number_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
    ) -> None:
        """Test getting a specific phone number."""
        client, _user = authenticated_test_client

        response = await client.get(f"/api/v1/phone-numbers/{test_phone_number.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_phone_number.id)
        assert data["phone_number"] == "+15551234567"
        assert data["friendly_name"] == "Test Line"

    @pytest.mark.asyncio
    async def test_get_phone_number_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a non-existent phone number."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.get(f"/api/v1/phone-numbers/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Phone number not found"

    @pytest.mark.asyncio
    async def test_create_phone_number_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test creating a phone number."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/phone-numbers",
            json={
                "phone_number": "+15559876543",
                "friendly_name": "New Line",
                "provider": "twilio",
                "provider_id": "twilio-456",
                "workspace_id": str(test_workspace.id),
                "can_receive_calls": True,
                "can_make_calls": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "+15559876543"
        assert data["friendly_name"] == "New Line"
        assert data["provider"] == "twilio"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_phone_number_minimal(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating a phone number with minimal data."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/phone-numbers",
            json={
                "phone_number": "+15551112222",
                "provider": "telnyx",
                "provider_id": "telnyx-minimal",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "+15551112222"
        assert data["can_receive_calls"] is True
        assert data["can_make_calls"] is True

    @pytest.mark.asyncio
    async def test_create_phone_number_invalid_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test creating phone number with invalid workspace ID."""
        client, _user = authenticated_test_client
        fake_workspace_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/phone-numbers",
            json={
                "phone_number": "+15559999999",
                "provider": "telnyx",
                "provider_id": "telnyx-invalid",
                "workspace_id": fake_workspace_id,
            },
        )

        assert response.status_code == 403
        assert "don't have access" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_phone_number_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
    ) -> None:
        """Test updating a phone number."""
        client, _user = authenticated_test_client

        response = await client.put(
            f"/api/v1/phone-numbers/{test_phone_number.id}",
            json={
                "friendly_name": "Updated Name",
                "notes": "Updated notes",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["friendly_name"] == "Updated Name"
        assert data["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_phone_number_status(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
    ) -> None:
        """Test updating phone number status."""
        client, _user = authenticated_test_client

        response = await client.put(
            f"/api/v1/phone-numbers/{test_phone_number.id}",
            json={"status": "inactive"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_update_phone_number_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating a non-existent phone number."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.put(
            f"/api/v1/phone-numbers/{fake_id}",
            json={"friendly_name": "Test"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_phone_number_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
    ) -> None:
        """Test deleting a phone number."""
        client, _user = authenticated_test_client

        response = await client.delete(f"/api/v1/phone-numbers/{test_phone_number.id}")

        assert response.status_code == 204

        # Verify deletion
        get_response = await client.get(f"/api/v1/phone-numbers/{test_phone_number.id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_phone_number_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test deleting a non-existent phone number."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.delete(f"/api/v1/phone-numbers/{fake_id}")

        assert response.status_code == 404


class TestPhoneNumberAuthentication:
    """Test phone number authentication requirements."""

    @pytest.mark.asyncio
    async def test_list_phone_numbers_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test listing phone numbers without authentication."""
        response = await test_client.get("/api/v1/phone-numbers")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_phone_number_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test creating phone number without authentication."""
        response = await test_client.post(
            "/api/v1/phone-numbers",
            json={
                "phone_number": "+15551234567",
                "provider": "telnyx",
                "provider_id": "test",
            },
        )

        assert response.status_code == 401


class TestPhoneNumberAgentAssignment:
    """Test phone number agent assignment."""

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
            name="Agent Assignment Workspace",
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
        test_session: AsyncSession,
    ) -> Agent:
        """Create a test agent."""
        _client, user = authenticated_test_client

        agent = Agent(
            user_id=user.id,
            name="Phone Assignment Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def test_phone_number(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> PhoneNumber:
        """Create a test phone number."""
        _client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        phone = PhoneNumber(
            user_id=user_id_to_uuid(user.id),
            phone_number="+15559998888",
            provider="telnyx",
            provider_id="telnyx-assignment",
            workspace_id=test_workspace.id,
        )
        test_session.add(phone)
        await test_session.commit()
        await test_session.refresh(phone)
        return phone

    @pytest.mark.asyncio
    async def test_assign_agent_to_phone_number(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
        test_agent: Agent,
    ) -> None:
        """Test assigning an agent to a phone number."""
        client, _user = authenticated_test_client

        response = await client.put(
            f"/api/v1/phone-numbers/{test_phone_number.id}",
            json={"assigned_agent_id": str(test_agent.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_agent_id"] == str(test_agent.id)

    @pytest.mark.asyncio
    async def test_unassign_agent_from_phone_number(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_phone_number: PhoneNumber,
        test_agent: Agent,
        test_session: AsyncSession,
    ) -> None:
        """Test unassigning an agent from a phone number."""
        client, _user = authenticated_test_client

        # First assign
        test_phone_number.assigned_agent_id = test_agent.id
        await test_session.commit()

        # Then unassign
        response = await client.put(
            f"/api/v1/phone-numbers/{test_phone_number.id}",
            json={"assigned_agent_id": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["assigned_agent_id"] is None
