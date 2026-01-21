"""Tests for telephony API endpoints."""

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.workspace import AgentWorkspace, Workspace


class TestTelephonyPhoneNumbers:
    """Test telephony phone number management endpoints."""

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
            name="Telephony Test Workspace",
            is_default=True,
        )
        test_session.add(workspace)
        await test_session.commit()
        await test_session.refresh(workspace)
        return workspace

    @pytest.fixture
    async def workspace_with_twilio_settings(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> Workspace:
        """Create a workspace with Twilio settings configured."""
        _client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        settings = UserSettings(
            user_id=user_id_to_uuid(user.id),
            workspace_id=test_workspace.id,
            twilio_account_sid="ACtest123",
            twilio_auth_token="test-auth-token",
        )
        test_session.add(settings)
        await test_session.commit()
        return test_workspace

    @pytest.fixture
    async def workspace_with_telnyx_settings(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
        test_session: AsyncSession,
    ) -> Workspace:
        """Create a workspace with Telnyx settings configured."""
        _client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        settings = UserSettings(
            user_id=user_id_to_uuid(user.id),
            workspace_id=test_workspace.id,
            telnyx_api_key="telnyx-test-key",
            telnyx_public_key="telnyx-public-key",
        )
        test_session.add(settings)
        await test_session.commit()
        return test_workspace

    @pytest.mark.asyncio
    async def test_list_phone_numbers_no_credentials(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test listing phone numbers when credentials not configured."""
        client, _user = authenticated_test_client

        # Should return empty list, not error
        response = await client.get(
            f"/api/v1/telephony/phone-numbers?provider=twilio&workspace_id={test_workspace.id}"
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_phone_numbers_invalid_provider(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test listing phone numbers with invalid provider."""
        client, _user = authenticated_test_client

        response = await client.get(
            f"/api/v1/telephony/phone-numbers?provider=invalid&workspace_id={test_workspace.id}"
        )

        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_phone_numbers_invalid_workspace_format(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing phone numbers with invalid workspace ID format."""
        client, _user = authenticated_test_client

        response = await client.get(
            "/api/v1/telephony/phone-numbers?provider=twilio&workspace_id=not-a-uuid"
        )

        assert response.status_code == 400
        assert "Invalid workspace_id format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_search_phone_numbers_no_credentials(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test searching phone numbers when credentials not configured."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/api/v1/telephony/phone-numbers/search?workspace_id={test_workspace.id}",
            json={
                "provider": "twilio",
                "country": "US",
                "area_code": "415",
            },
        )

        assert response.status_code == 400
        assert "credentials not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_search_phone_numbers_invalid_provider(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test searching phone numbers with invalid provider."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/api/v1/telephony/phone-numbers/search?workspace_id={test_workspace.id}",
            json={
                "provider": "invalid",
                "country": "US",
            },
        )

        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_purchase_phone_number_no_credentials(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test purchasing phone number when credentials not configured."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/api/v1/telephony/phone-numbers/purchase?workspace_id={test_workspace.id}",
            json={
                "provider": "twilio",
                "phone_number": "+15551234567",
            },
        )

        assert response.status_code == 400
        assert "credentials not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_release_phone_number_no_credentials(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test releasing phone number when credentials not configured."""
        client, _user = authenticated_test_client

        response = await client.delete(
            f"/api/v1/telephony/phone-numbers/PN123?provider=twilio&workspace_id={test_workspace.id}"
        )

        assert response.status_code == 400
        assert "credentials not configured" in response.json()["detail"]


class TestTelephonyOutboundCalls:
    """Test telephony outbound call endpoints."""

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
            name="Call Test Workspace",
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
            name="Call Test Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
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
    async def test_initiate_call_no_provider(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_workspace: Workspace,
    ) -> None:
        """Test initiating call when no provider is configured."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/api/v1/telephony/calls?workspace_id={test_workspace.id}",
            json={
                "to_number": "+15551234567",
                "from_number": "+15559876543",
                "agent_id": str(test_agent.id),
            },
        )

        assert response.status_code == 400
        assert "No telephony provider configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_initiate_call_agent_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test initiating call with non-existent agent."""
        client, _user = authenticated_test_client
        fake_agent_id = str(uuid.uuid4())

        response = await client.post(
            f"/api/v1/telephony/calls?workspace_id={test_workspace.id}",
            json={
                "to_number": "+15551234567",
                "from_number": "+15559876543",
                "agent_id": fake_agent_id,
            },
        )

        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_initiate_call_invalid_workspace_format(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test initiating call with invalid workspace ID format."""
        client, _user = authenticated_test_client
        fake_agent_id = str(uuid.uuid4())

        response = await client.post(
            "/api/v1/telephony/calls?workspace_id=not-a-uuid",
            json={
                "to_number": "+15551234567",
                "from_number": "+15559876543",
                "agent_id": fake_agent_id,
            },
        )

        assert response.status_code == 400
        assert "Invalid workspace_id format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_hangup_call_no_credentials(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test hanging up call when credentials not configured."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/api/v1/telephony/calls/call-123/hangup?provider=twilio&workspace_id={test_workspace.id}"
        )

        assert response.status_code == 500
        assert "Failed to hang up call" in response.json()["detail"]


class TestTelephonyAuthentication:
    """Test telephony authentication requirements."""

    @pytest.mark.asyncio
    async def test_list_phone_numbers_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test listing phone numbers without authentication."""
        fake_workspace_id = str(uuid.uuid4())

        response = await test_client.get(
            f"/api/v1/telephony/phone-numbers?provider=twilio&workspace_id={fake_workspace_id}"
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_initiate_call_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test initiating call without authentication."""
        fake_workspace_id = str(uuid.uuid4())
        fake_agent_id = str(uuid.uuid4())

        response = await test_client.post(
            f"/api/v1/telephony/calls?workspace_id={fake_workspace_id}",
            json={
                "to_number": "+15551234567",
                "from_number": "+15559876543",
                "agent_id": fake_agent_id,
            },
        )

        assert response.status_code == 401


class TestTelephonyWebhooks:
    """Test telephony webhook endpoints (these are public endpoints)."""

    @pytest.mark.asyncio
    async def test_twilio_voice_webhook_missing_signature(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test Twilio voice webhook without signature."""
        # Note: The webhook verification should fail without proper signature
        # In production, requests without valid signatures are rejected
        response = await test_client.post(
            "/webhooks/twilio/voice",
            data={
                "CallSid": "CA123",
                "From": "+15551234567",
                "To": "+15559876543",
                "CallStatus": "ringing",
            },
        )

        # Should fail signature verification
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_telnyx_voice_webhook_missing_signature(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test Telnyx voice webhook without signature."""
        response = await test_client.post(
            "/webhooks/telnyx/voice",
            json={
                "data": {
                    "event_type": "call.initiated",
                    "payload": {
                        "call_control_id": "test-123",
                        "from": "+15551234567",
                        "to": "+15559876543",
                    },
                }
            },
        )

        # Should fail signature verification
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_twilio_status_callback_missing_signature(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test Twilio status callback without signature."""
        response = await test_client.post(
            "/webhooks/twilio/status",
            data={
                "CallSid": "CA123",
                "CallStatus": "completed",
                "CallDuration": "120",
            },
        )

        # Should fail signature verification
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_telnyx_status_callback_missing_signature(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test Telnyx status callback without signature."""
        response = await test_client.post(
            "/webhooks/telnyx/status",
            json={
                "data": {
                    "event_type": "call.hangup",
                    "payload": {
                        "call_control_id": "test-123",
                        "hangup_cause": "NORMAL_CLEARING",
                    },
                }
            },
        )

        # Should fail signature verification
        assert response.status_code in [401, 403]


class TestTelephonyValidation:
    """Test telephony request validation."""

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

    @pytest.mark.asyncio
    async def test_search_phone_numbers_missing_provider(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test search request missing provider field."""
        client, _user = authenticated_test_client

        response = await client.post(
            f"/api/v1/telephony/phone-numbers/search?workspace_id={test_workspace.id}",
            json={"country": "US"},  # Missing provider
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_purchase_phone_number_missing_fields(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test purchase request missing required fields."""
        client, _user = authenticated_test_client

        # Missing phone_number
        response = await client.post(
            f"/api/v1/telephony/phone-numbers/purchase?workspace_id={test_workspace.id}",
            json={"provider": "twilio"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_initiate_call_missing_fields(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_workspace: Workspace,
    ) -> None:
        """Test initiate call request missing required fields."""
        client, _user = authenticated_test_client

        # Missing agent_id
        response = await client.post(
            f"/api/v1/telephony/calls?workspace_id={test_workspace.id}",
            json={
                "to_number": "+15551234567",
                "from_number": "+15559876543",
            },
        )

        assert response.status_code == 422
