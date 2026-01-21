"""Tests for campaigns API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.campaign import Campaign, CampaignContact, CampaignStatus
from app.models.contact import Contact
from app.models.user import User
from app.models.workspace import Workspace


class TestCampaignCRUD:
    """Test campaign CRUD operations."""

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
            name="Test Workspace",
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
            name="Campaign Test Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def test_contact(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> Contact:
        """Create a test contact."""
        _client, user = authenticated_test_client

        contact = Contact(
            user_id=user.id,
            workspace_id=test_workspace.id,
            first_name="John",
            last_name="Doe",
            phone_number="+11234567890",
        )
        test_session.add(contact)
        await test_session.commit()
        await test_session.refresh(contact)
        return contact

    @pytest.fixture
    def valid_campaign_data(
        self,
        test_workspace: Workspace,
        test_agent: Agent,
    ) -> dict[str, Any]:
        """Valid campaign creation data."""
        return {
            "workspace_id": str(test_workspace.id),
            "agent_id": str(test_agent.id),
            "name": "Test Campaign",
            "description": "A test outbound campaign",
            "from_phone_number": "+10987654321",
            "calls_per_minute": 2,
            "max_concurrent_calls": 1,
            "max_attempts_per_contact": 3,
            "retry_delay_minutes": 60,
        }

    @pytest.mark.asyncio
    async def test_create_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test successful campaign creation."""
        client, _user = authenticated_test_client

        response = await client.post("/campaigns", json=valid_campaign_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == valid_campaign_data["name"]
        assert data["status"] == "draft"
        assert data["from_phone_number"] == valid_campaign_data["from_phone_number"]
        assert data["calls_per_minute"] == 2
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_campaign_with_contacts(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
        test_contact: Contact,
    ) -> None:
        """Test campaign creation with initial contacts."""
        client, _user = authenticated_test_client

        valid_campaign_data["contact_ids"] = [test_contact.id]

        response = await client.post("/campaigns", json=valid_campaign_data)

        assert response.status_code == 200
        data = response.json()
        assert data["total_contacts"] == 1

    @pytest.mark.asyncio
    async def test_create_campaign_with_scheduler(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test campaign creation with scheduler settings."""
        client, _user = authenticated_test_client

        valid_campaign_data.update({
            "calling_hours_start": "09:00",
            "calling_hours_end": "17:00",
            "calling_days": [0, 1, 2, 3, 4],  # Monday-Friday
            "timezone": "America/New_York",
        })

        response = await client.post("/campaigns", json=valid_campaign_data)

        assert response.status_code == 200
        data = response.json()
        assert data["calling_hours_start"] == "09:00"
        assert data["calling_hours_end"] == "17:00"
        assert data["calling_days"] == [0, 1, 2, 3, 4]
        assert data["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_create_campaign_missing_name(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test campaign creation with missing name."""
        client, _user = authenticated_test_client
        del valid_campaign_data["name"]

        response = await client.post("/campaigns", json=valid_campaign_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test campaign creation with invalid agent ID."""
        client, _user = authenticated_test_client
        valid_campaign_data["agent_id"] = str(uuid.uuid4())

        response = await client.post("/campaigns", json=valid_campaign_data)

        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_time_format(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test campaign creation with invalid time format."""
        client, _user = authenticated_test_client
        valid_campaign_data["calling_hours_start"] = "9am"

        response = await client.post("/campaigns", json=valid_campaign_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_calls_per_minute(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test campaign creation with invalid calls per minute."""
        client, _user = authenticated_test_client
        valid_campaign_data["calls_per_minute"] = 50  # Max is 30

        response = await client.post("/campaigns", json=valid_campaign_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_campaigns_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing campaigns when none exist."""
        client, _user = authenticated_test_client

        response = await client.get("/campaigns")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_list_campaigns_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test listing campaigns."""
        client, _user = authenticated_test_client

        # Create campaigns
        await client.post("/campaigns", json=valid_campaign_data)
        valid_campaign_data["name"] = "Second Campaign"
        await client.post("/campaigns", json=valid_campaign_data)

        response = await client.get("/campaigns")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_by_workspace(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
        test_workspace: Workspace,
    ) -> None:
        """Test filtering campaigns by workspace."""
        client, _user = authenticated_test_client

        await client.post("/campaigns", json=valid_campaign_data)

        response = await client.get(f"/campaigns?workspace_id={test_workspace.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["workspace_id"] == str(test_workspace.id)

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_by_status(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test filtering campaigns by status."""
        client, _user = authenticated_test_client

        await client.post("/campaigns", json=valid_campaign_data)

        response = await client.get("/campaigns?status=draft")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "draft"

    @pytest.mark.asyncio
    async def test_get_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test getting a specific campaign."""
        client, _user = authenticated_test_client

        create_response = await client.post("/campaigns", json=valid_campaign_data)
        campaign_id = create_response.json()["id"]

        response = await client.get(f"/campaigns/{campaign_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == campaign_id
        assert data["name"] == valid_campaign_data["name"]

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a non-existent campaign."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.get(f"/campaigns/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test updating a campaign."""
        client, _user = authenticated_test_client

        create_response = await client.post("/campaigns", json=valid_campaign_data)
        campaign_id = create_response.json()["id"]

        response = await client.put(
            f"/campaigns/{campaign_id}",
            json={"name": "Updated Campaign", "description": "Updated description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Campaign"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_running_campaign_fails(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
        test_contact: Contact,
        test_session: AsyncSession,
    ) -> None:
        """Test that updating a running campaign fails."""
        client, _user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        # Create and start campaign
        valid_campaign_data["contact_ids"] = [test_contact.id]
        create_response = await client.post("/campaigns", json=valid_campaign_data)
        campaign_id = create_response.json()["id"]
        await client.post(f"/campaigns/{campaign_id}/start")

        response = await client.put(
            f"/campaigns/{campaign_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 400
        assert "Cannot update a running" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
    ) -> None:
        """Test deleting a campaign."""
        client, _user = authenticated_test_client

        create_response = await client.post("/campaigns", json=valid_campaign_data)
        campaign_id = create_response.json()["id"]

        response = await client.delete(f"/campaigns/{campaign_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify deletion
        get_response = await client.get(f"/campaigns/{campaign_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_running_campaign_fails(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        valid_campaign_data: dict[str, Any],
        test_contact: Contact,
    ) -> None:
        """Test that deleting a running campaign fails."""
        client, _user = authenticated_test_client

        valid_campaign_data["contact_ids"] = [test_contact.id]
        create_response = await client.post("/campaigns", json=valid_campaign_data)
        campaign_id = create_response.json()["id"]
        await client.post(f"/campaigns/{campaign_id}/start")

        response = await client.delete(f"/campaigns/{campaign_id}")

        assert response.status_code == 400
        assert "running" in response.json()["detail"].lower()


class TestCampaignContactManagement:
    """Test campaign contact management endpoints."""

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
            name="Contact Test Workspace",
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
            name="Contact Test Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def test_contacts(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> list[Contact]:
        """Create multiple test contacts."""
        _client, user = authenticated_test_client

        contacts = []
        for i in range(5):
            contact = Contact(
                user_id=user.id,
                workspace_id=test_workspace.id,
                first_name=f"Contact{i}",
                last_name="Test",
                phone_number=f"+1123456789{i}",
                status="new" if i < 3 else "contacted",
            )
            test_session.add(contact)
            contacts.append(contact)

        await test_session.commit()
        for c in contacts:
            await test_session.refresh(c)
        return contacts

    @pytest.fixture
    async def test_campaign(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_agent: Agent,
    ) -> dict[str, Any]:
        """Create a test campaign."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/campaigns",
            json={
                "workspace_id": str(test_workspace.id),
                "agent_id": str(test_agent.id),
                "name": "Contact Test Campaign",
                "from_phone_number": "+10987654321",
            },
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_add_contacts_to_campaign(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
        test_contacts: list[Contact],
    ) -> None:
        """Test adding contacts to a campaign."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/campaigns/{test_campaign['id']}/contacts",
            json={"contact_ids": [c.id for c in test_contacts[:2]]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 2

    @pytest.mark.asyncio
    async def test_add_duplicate_contacts(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
        test_contacts: list[Contact],
    ) -> None:
        """Test that duplicate contacts are not added."""
        client, _user = authenticated_test_client

        # Add contacts first time
        await client.post(
            f"/campaigns/{test_campaign['id']}/contacts",
            json={"contact_ids": [test_contacts[0].id]},
        )

        # Try to add same contact again
        response = await client.post(
            f"/campaigns/{test_campaign['id']}/contacts",
            json={"contact_ids": [test_contacts[0].id, test_contacts[1].id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 1  # Only 1 new contact added

    @pytest.mark.asyncio
    async def test_list_campaign_contacts(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
        test_contacts: list[Contact],
    ) -> None:
        """Test listing contacts in a campaign."""
        client, _user = authenticated_test_client

        # Add contacts
        await client.post(
            f"/campaigns/{test_campaign['id']}/contacts",
            json={"contact_ids": [c.id for c in test_contacts]},
        )

        response = await client.get(f"/campaigns/{test_campaign['id']}/contacts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_list_campaign_contacts_with_status_filter(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
        test_contacts: list[Contact],
    ) -> None:
        """Test filtering campaign contacts by status."""
        client, _user = authenticated_test_client

        # Add contacts
        await client.post(
            f"/campaigns/{test_campaign['id']}/contacts",
            json={"contact_ids": [c.id for c in test_contacts]},
        )

        response = await client.get(f"/campaigns/{test_campaign['id']}/contacts?status=pending")

        assert response.status_code == 200
        data = response.json()
        # All added contacts start as pending
        assert len(data) == 5

    @pytest.mark.asyncio
    async def test_remove_contact_from_campaign(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
        test_contacts: list[Contact],
    ) -> None:
        """Test removing a contact from a campaign."""
        client, _user = authenticated_test_client

        # Add contacts
        await client.post(
            f"/campaigns/{test_campaign['id']}/contacts",
            json={"contact_ids": [test_contacts[0].id]},
        )

        response = await client.delete(
            f"/campaigns/{test_campaign['id']}/contacts/{test_contacts[0].id}"
        )

        assert response.status_code == 200

        # Verify removal
        list_response = await client.get(f"/campaigns/{test_campaign['id']}/contacts")
        assert len(list_response.json()) == 0

    @pytest.mark.asyncio
    async def test_add_contacts_by_filter_preview(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
        test_contacts: list[Contact],
    ) -> None:
        """Test previewing contacts by filter."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/campaigns/{test_campaign['id']}/contacts/filter/preview",
            json={"status": ["new"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_matching"] == 3  # 3 contacts have status "new"
        assert data["already_in_campaign"] == 0
        assert data["will_be_added"] == 3

    @pytest.mark.asyncio
    async def test_add_contacts_by_filter(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
        test_contacts: list[Contact],
    ) -> None:
        """Test adding contacts by filter."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/campaigns/{test_campaign['id']}/contacts/filter",
            json={"status": ["new"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 3
        assert data["total_matching"] == 3


class TestCampaignControl:
    """Test campaign control endpoints (start, pause, stop, restart)."""

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
            name="Control Test Workspace",
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
            name="Control Test Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def test_contact(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> Contact:
        """Create a test contact."""
        _client, user = authenticated_test_client

        contact = Contact(
            user_id=user.id,
            workspace_id=test_workspace.id,
            first_name="Test",
            last_name="Contact",
            phone_number="+11234567890",
        )
        test_session.add(contact)
        await test_session.commit()
        await test_session.refresh(contact)
        return contact

    @pytest.fixture
    async def test_campaign_with_contacts(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_agent: Agent,
        test_contact: Contact,
    ) -> dict[str, Any]:
        """Create a campaign with contacts."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/campaigns",
            json={
                "workspace_id": str(test_workspace.id),
                "agent_id": str(test_agent.id),
                "name": "Control Test Campaign",
                "from_phone_number": "+10987654321",
                "contact_ids": [test_contact.id],
            },
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_start_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign_with_contacts: dict[str, Any],
    ) -> None:
        """Test starting a campaign."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/campaigns/{test_campaign_with_contacts['id']}/start"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["started_at"] is not None

    @pytest.mark.asyncio
    async def test_start_campaign_without_contacts_fails(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_agent: Agent,
    ) -> None:
        """Test that starting a campaign without contacts fails."""
        client, _user = authenticated_test_client

        # Create campaign without contacts
        create_response = await client.post(
            "/campaigns",
            json={
                "workspace_id": str(test_workspace.id),
                "agent_id": str(test_agent.id),
                "name": "Empty Campaign",
                "from_phone_number": "+10987654321",
            },
        )
        campaign_id = create_response.json()["id"]

        response = await client.post(f"/campaigns/{campaign_id}/start")

        assert response.status_code == 400
        assert "no contacts" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_pause_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign_with_contacts: dict[str, Any],
    ) -> None:
        """Test pausing a running campaign."""
        client, _user = authenticated_test_client

        # Start first
        await client.post(f"/campaigns/{test_campaign_with_contacts['id']}/start")

        response = await client.post(
            f"/campaigns/{test_campaign_with_contacts['id']}/pause"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    @pytest.mark.asyncio
    async def test_pause_non_running_campaign_fails(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign_with_contacts: dict[str, Any],
    ) -> None:
        """Test that pausing a non-running campaign fails."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/campaigns/{test_campaign_with_contacts['id']}/pause"
        )

        assert response.status_code == 400
        assert "running" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_stop_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign_with_contacts: dict[str, Any],
    ) -> None:
        """Test stopping a campaign."""
        client, _user = authenticated_test_client

        # Start first
        await client.post(f"/campaigns/{test_campaign_with_contacts['id']}/start")

        response = await client.post(
            f"/campaigns/{test_campaign_with_contacts['id']}/stop"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "canceled"
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_restart_campaign_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign_with_contacts: dict[str, Any],
    ) -> None:
        """Test restarting a completed campaign."""
        client, _user = authenticated_test_client

        # Start and stop
        await client.post(f"/campaigns/{test_campaign_with_contacts['id']}/start")
        await client.post(f"/campaigns/{test_campaign_with_contacts['id']}/stop")

        response = await client.post(
            f"/campaigns/{test_campaign_with_contacts['id']}/restart"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["completed_at"] is None

    @pytest.mark.asyncio
    async def test_restart_draft_campaign_fails(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign_with_contacts: dict[str, Any],
    ) -> None:
        """Test that restarting a draft campaign fails."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/campaigns/{test_campaign_with_contacts['id']}/restart"
        )

        assert response.status_code == 400
        assert "completed or canceled" in response.json()["detail"].lower()


class TestCampaignStats:
    """Test campaign statistics endpoints."""

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
            name="Stats Test Workspace",
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
            name="Stats Test Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def test_campaign(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_agent: Agent,
    ) -> dict[str, Any]:
        """Create a test campaign."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/campaigns",
            json={
                "workspace_id": str(test_workspace.id),
                "agent_id": str(test_agent.id),
                "name": "Stats Test Campaign",
                "from_phone_number": "+10987654321",
            },
        )
        return response.json()

    @pytest.mark.asyncio
    async def test_get_campaign_stats(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
    ) -> None:
        """Test getting campaign statistics."""
        client, _user = authenticated_test_client

        response = await client.get(f"/campaigns/{test_campaign['id']}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_contacts" in data
        assert "contacts_pending" in data
        assert "contacts_completed" in data
        assert "completion_rate" in data

    @pytest.mark.asyncio
    async def test_get_disposition_stats(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_campaign: dict[str, Any],
    ) -> None:
        """Test getting disposition statistics."""
        client, _user = authenticated_test_client

        response = await client.get(f"/campaigns/{test_campaign['id']}/dispositions")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_disposition" in data
        assert "callbacks_pending" in data

    @pytest.mark.asyncio
    async def test_get_disposition_options(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting available disposition options."""
        client, _user = authenticated_test_client

        response = await client.get("/campaigns/dispositions/options")

        assert response.status_code == 200
        data = response.json()
        assert "positive" in data
        assert "neutral" in data
        assert "negative" in data
        assert "technical" in data
