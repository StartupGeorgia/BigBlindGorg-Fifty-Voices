"""Tests for call history API endpoints."""

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.call_record import CallDirection, CallRecord, CallStatus
from app.models.user import User


class TestCallRecordEndpoints:
    """Test call record CRUD operations."""

    @pytest.fixture
    async def test_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> Agent:
        """Create a test agent for call records."""
        _client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        agent = Agent(
            user_id=user.id,
            name="Test Call Agent",
            pricing_tier="balanced",
            system_prompt="You are a helpful assistant for testing purposes.",
        )
        test_session.add(agent)
        await test_session.commit()
        await test_session.refresh(agent)
        return agent

    @pytest.fixture
    async def test_call_record(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_session: AsyncSession,
    ) -> CallRecord:
        """Create a test call record."""
        _client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        user_uuid = user_id_to_uuid(user.id)
        call = CallRecord(
            user_id=user_uuid,
            provider="telnyx",
            provider_call_id=f"test-{uuid.uuid4()}",
            agent_id=test_agent.id,
            direction=CallDirection.INBOUND.value,
            status=CallStatus.COMPLETED.value,
            from_number="+11234567890",
            to_number="+10987654321",
            duration_seconds=120,
            started_at=datetime.now(UTC),
        )
        test_session.add(call)
        await test_session.commit()
        await test_session.refresh(call)
        return call

    @pytest.mark.asyncio
    async def test_list_calls_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test listing calls when none exist."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/calls")

        assert response.status_code == 200
        data = response.json()
        assert data["calls"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_calls_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_call_record: CallRecord,
    ) -> None:
        """Test listing calls with existing records."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/calls")

        assert response.status_code == 200
        data = response.json()
        assert len(data["calls"]) == 1
        assert data["total"] == 1
        assert data["calls"][0]["id"] == str(test_call_record.id)
        assert data["calls"][0]["direction"] == "inbound"
        assert data["calls"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_calls_pagination(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_session: AsyncSession,
    ) -> None:
        """Test call listing with pagination."""
        client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        user_uuid = user_id_to_uuid(user.id)

        # Create 5 calls
        for i in range(5):
            call = CallRecord(
                user_id=user_uuid,
                provider="telnyx",
                provider_call_id=f"test-{uuid.uuid4()}",
                agent_id=test_agent.id,
                direction=CallDirection.INBOUND.value,
                status=CallStatus.COMPLETED.value,
                from_number=f"+1123456789{i}",
                to_number="+10987654321",
                duration_seconds=60 + i,
                started_at=datetime.now(UTC),
            )
            test_session.add(call)

        await test_session.commit()

        # Test pagination
        response = await client.get("/api/v1/calls?page=1&page_size=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["calls"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_list_calls_filter_by_agent(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_call_record: CallRecord,
        test_session: AsyncSession,
    ) -> None:
        """Test filtering calls by agent ID."""
        client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        user_uuid = user_id_to_uuid(user.id)

        # Create another agent with a call
        other_agent = Agent(
            user_id=user.id,
            name="Other Agent",
            pricing_tier="budget",
            system_prompt="Another helpful assistant for testing purposes.",
        )
        test_session.add(other_agent)
        await test_session.commit()
        await test_session.refresh(other_agent)

        other_call = CallRecord(
            user_id=user_uuid,
            provider="twilio",
            provider_call_id=f"other-{uuid.uuid4()}",
            agent_id=other_agent.id,
            direction=CallDirection.OUTBOUND.value,
            status=CallStatus.COMPLETED.value,
            from_number="+10987654321",
            to_number="+11234567890",
            duration_seconds=60,
            started_at=datetime.now(UTC),
        )
        test_session.add(other_call)
        await test_session.commit()

        # Filter by first agent
        response = await client.get(f"/api/v1/calls?agent_id={test_agent.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["calls"]) == 1
        assert data["calls"][0]["agent_id"] == str(test_agent.id)

    @pytest.mark.asyncio
    async def test_list_calls_filter_by_direction(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_session: AsyncSession,
    ) -> None:
        """Test filtering calls by direction."""
        client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        user_uuid = user_id_to_uuid(user.id)

        # Create inbound call
        inbound = CallRecord(
            user_id=user_uuid,
            provider="telnyx",
            provider_call_id=f"inbound-{uuid.uuid4()}",
            agent_id=test_agent.id,
            direction=CallDirection.INBOUND.value,
            status=CallStatus.COMPLETED.value,
            from_number="+11234567890",
            to_number="+10987654321",
            duration_seconds=60,
            started_at=datetime.now(UTC),
        )
        test_session.add(inbound)

        # Create outbound call
        outbound = CallRecord(
            user_id=user_uuid,
            provider="telnyx",
            provider_call_id=f"outbound-{uuid.uuid4()}",
            agent_id=test_agent.id,
            direction=CallDirection.OUTBOUND.value,
            status=CallStatus.COMPLETED.value,
            from_number="+10987654321",
            to_number="+11234567890",
            duration_seconds=90,
            started_at=datetime.now(UTC),
        )
        test_session.add(outbound)
        await test_session.commit()

        # Filter by inbound
        response = await client.get("/api/v1/calls?direction=inbound")

        assert response.status_code == 200
        data = response.json()
        assert len(data["calls"]) == 1
        assert data["calls"][0]["direction"] == "inbound"

    @pytest.mark.asyncio
    async def test_list_calls_filter_by_status(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_session: AsyncSession,
    ) -> None:
        """Test filtering calls by status."""
        client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        user_uuid = user_id_to_uuid(user.id)

        # Create completed call
        completed = CallRecord(
            user_id=user_uuid,
            provider="telnyx",
            provider_call_id=f"completed-{uuid.uuid4()}",
            agent_id=test_agent.id,
            direction=CallDirection.INBOUND.value,
            status=CallStatus.COMPLETED.value,
            from_number="+11234567890",
            to_number="+10987654321",
            duration_seconds=60,
            started_at=datetime.now(UTC),
        )
        test_session.add(completed)

        # Create failed call
        failed = CallRecord(
            user_id=user_uuid,
            provider="telnyx",
            provider_call_id=f"failed-{uuid.uuid4()}",
            agent_id=test_agent.id,
            direction=CallDirection.OUTBOUND.value,
            status=CallStatus.FAILED.value,
            from_number="+10987654321",
            to_number="+11234567890",
            duration_seconds=0,
            started_at=datetime.now(UTC),
        )
        test_session.add(failed)
        await test_session.commit()

        # Filter by completed
        response = await client.get("/api/v1/calls?status=completed")

        assert response.status_code == 200
        data = response.json()
        assert len(data["calls"]) == 1
        assert data["calls"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_calls_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test listing calls without authentication."""
        response = await test_client.get("/api/v1/calls")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_call_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_call_record: CallRecord,
    ) -> None:
        """Test getting a specific call record."""
        client, _user = authenticated_test_client

        response = await client.get(f"/api/v1/calls/{test_call_record.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_call_record.id)
        assert data["provider"] == "telnyx"
        assert data["direction"] == "inbound"
        assert data["status"] == "completed"
        assert data["from_number"] == "+11234567890"
        assert data["to_number"] == "+10987654321"
        assert data["duration_seconds"] == 120

    @pytest.mark.asyncio
    async def test_get_call_not_found(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a non-existent call record."""
        client, _user = authenticated_test_client
        fake_id = str(uuid.uuid4())

        response = await client.get(f"/api/v1/calls/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Call record not found"

    @pytest.mark.asyncio
    async def test_get_call_invalid_uuid(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting a call with invalid UUID format."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/calls/invalid-uuid")

        assert response.status_code == 422


class TestAgentCallStats:
    """Test agent call statistics endpoint."""

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

    @pytest.mark.asyncio
    async def test_get_agent_stats_empty(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
    ) -> None:
        """Test getting stats for an agent with no calls."""
        client, _user = authenticated_test_client

        response = await client.get(f"/api/v1/calls/agent/{test_agent.id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 0
        assert data["completed_calls"] == 0
        assert data["inbound_calls"] == 0
        assert data["outbound_calls"] == 0
        assert data["total_duration_seconds"] == 0
        assert data["average_duration_seconds"] == 0

    @pytest.mark.asyncio
    async def test_get_agent_stats_with_calls(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_agent: Agent,
        test_session: AsyncSession,
    ) -> None:
        """Test getting stats for an agent with multiple calls."""
        client, user = authenticated_test_client
        from app.core.auth import user_id_to_uuid

        user_uuid = user_id_to_uuid(user.id)

        # Create various calls
        calls_data = [
            (CallDirection.INBOUND.value, CallStatus.COMPLETED.value, 60),
            (CallDirection.INBOUND.value, CallStatus.COMPLETED.value, 120),
            (CallDirection.OUTBOUND.value, CallStatus.COMPLETED.value, 90),
            (CallDirection.OUTBOUND.value, CallStatus.FAILED.value, 0),
        ]

        for direction, status, duration in calls_data:
            call = CallRecord(
                user_id=user_uuid,
                provider="telnyx",
                provider_call_id=f"test-{uuid.uuid4()}",
                agent_id=test_agent.id,
                direction=direction,
                status=status,
                from_number="+11234567890",
                to_number="+10987654321",
                duration_seconds=duration,
                started_at=datetime.now(UTC),
            )
            test_session.add(call)

        await test_session.commit()

        response = await client.get(f"/api/v1/calls/agent/{test_agent.id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 4
        assert data["completed_calls"] == 3
        assert data["inbound_calls"] == 2
        assert data["outbound_calls"] == 2
        assert data["total_duration_seconds"] == 270
        assert data["average_duration_seconds"] == 67.5

    @pytest.mark.asyncio
    async def test_get_agent_stats_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test getting agent stats without authentication."""
        fake_id = str(uuid.uuid4())

        response = await test_client.get(f"/api/v1/calls/agent/{fake_id}/stats")

        assert response.status_code == 401
