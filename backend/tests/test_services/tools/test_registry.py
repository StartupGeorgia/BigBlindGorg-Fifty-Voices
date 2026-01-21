"""Tests for tool registry in app/services/tools/registry.py."""

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tools.registry import ToolRegistry


class TestToolRegistryInitialization:
    """Tests for ToolRegistry initialization."""

    def test_basic_initialization(self, test_session: AsyncSession) -> None:
        """Test basic initialization with required params."""
        registry = ToolRegistry(db=test_session, user_id=1)

        assert registry.db == test_session
        assert registry.user_id == 1
        assert registry.integrations == {}
        assert registry.workspace_id is None

    def test_initialization_with_integrations(self, test_session: AsyncSession) -> None:
        """Test initialization with integration credentials."""
        integrations = {
            "gohighlevel": {"access_token": "token123", "location_id": "loc123"},
            "calendly": {"access_token": "cal_token"},
        }
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations=integrations,
        )

        assert registry.integrations == integrations

    def test_initialization_with_workspace(self, test_session: AsyncSession) -> None:
        """Test initialization with workspace ID."""
        workspace_id = uuid.uuid4()
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            workspace_id=workspace_id,
        )

        assert registry.workspace_id == workspace_id

    def test_crm_tools_initialized(self, test_session: AsyncSession) -> None:
        """Test that CRM tools are initialized automatically."""
        registry = ToolRegistry(db=test_session, user_id=1)

        assert registry.crm_tools is not None
        assert registry.crm_tools.user_id == 1


class TestGetToolDefinitions:
    """Tests for get_all_tool_definitions method."""

    def test_empty_enabled_tools_returns_empty(
        self, test_session: AsyncSession
    ) -> None:
        """Test that no enabled tools returns empty list."""
        registry = ToolRegistry(db=test_session, user_id=1)

        tools = registry.get_all_tool_definitions(enabled_tools=[])

        assert tools == []

    def test_crm_tools_returned_when_enabled(
        self, test_session: AsyncSession
    ) -> None:
        """Test that CRM tools are returned when 'crm' is enabled."""
        registry = ToolRegistry(db=test_session, user_id=1)

        tools = registry.get_all_tool_definitions(enabled_tools=["crm"])

        # Should have CRM tool definitions
        tool_names = [t.get("name") for t in tools]
        assert "search_customer" in tool_names
        assert "create_contact" in tool_names
        assert "book_appointment" in tool_names

    def test_call_control_tools_returned_when_enabled(
        self, test_session: AsyncSession
    ) -> None:
        """Test that call control tools are returned when enabled."""
        registry = ToolRegistry(db=test_session, user_id=1)

        tools = registry.get_all_tool_definitions(enabled_tools=["call_control"])

        tool_names = [t.get("name") for t in tools]
        assert "end_call" in tool_names
        assert "transfer_call" in tool_names
        assert "send_dtmf" in tool_names

    def test_multiple_tool_types_enabled(self, test_session: AsyncSession) -> None:
        """Test enabling multiple tool types."""
        registry = ToolRegistry(db=test_session, user_id=1)

        tools = registry.get_all_tool_definitions(
            enabled_tools=["crm", "call_control"]
        )

        tool_names = [t.get("name") for t in tools]

        # Should have both CRM and call control tools
        assert "search_customer" in tool_names
        assert "end_call" in tool_names

    def test_ghl_tools_require_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test that GoHighLevel tools require credentials."""
        # Without credentials
        registry = ToolRegistry(db=test_session, user_id=1)
        tools = registry.get_all_tool_definitions(enabled_tools=["gohighlevel"])

        # Should be empty since no credentials
        ghl_tools = [t for t in tools if t.get("name", "").startswith("ghl_")]
        assert len(ghl_tools) == 0

    def test_ghl_tools_with_credentials(self, test_session: AsyncSession) -> None:
        """Test GoHighLevel tools with valid credentials."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={
                "gohighlevel": {
                    "access_token": "token123",
                    "location_id": "loc123",
                }
            },
        )

        tools = registry.get_all_tool_definitions(enabled_tools=["gohighlevel"])

        tool_names = [t.get("name") for t in tools]
        assert "ghl_search_contact" in tool_names
        assert "ghl_book_appointment" in tool_names

    def test_calendly_tools_require_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test that Calendly tools require credentials."""
        registry = ToolRegistry(db=test_session, user_id=1)
        tools = registry.get_all_tool_definitions(enabled_tools=["calendly"])

        calendly_tools = [t for t in tools if t.get("name", "").startswith("calendly_")]
        assert len(calendly_tools) == 0

    def test_calendly_tools_with_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test Calendly tools with valid credentials."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={"calendly": {"access_token": "cal_token"}},
        )

        tools = registry.get_all_tool_definitions(enabled_tools=["calendly"])

        tool_names = [t.get("name") for t in tools]
        assert "calendly_get_event_types" in tool_names

    def test_enabled_tool_ids_filtering(self, test_session: AsyncSession) -> None:
        """Test granular tool filtering with enabled_tool_ids."""
        registry = ToolRegistry(db=test_session, user_id=1)

        # Only enable specific CRM tools
        tools = registry.get_all_tool_definitions(
            enabled_tools=["crm"],
            enabled_tool_ids={"crm": ["search_customer", "create_contact"]},
        )

        tool_names = [t.get("name") for t in tools]

        # Only selected tools should be present
        assert "search_customer" in tool_names
        assert "create_contact" in tool_names
        assert "book_appointment" not in tool_names
        assert "cancel_appointment" not in tool_names

    def test_enabled_tool_ids_empty_list(self, test_session: AsyncSession) -> None:
        """Test enabled_tool_ids with empty list returns no tools."""
        registry = ToolRegistry(db=test_session, user_id=1)

        tools = registry.get_all_tool_definitions(
            enabled_tools=["crm"],
            enabled_tool_ids={"crm": []},  # Empty list
        )

        assert len(tools) == 0


class TestExecuteTool:
    """Tests for execute_tool method."""

    @pytest.mark.asyncio
    async def test_execute_call_control_tool(
        self, test_session: AsyncSession
    ) -> None:
        """Test executing call control tool."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "end_call",
            {"reason": "conversation_complete"},
        )

        assert result["success"] is True
        assert result["action"] == "end_call"

    @pytest.mark.asyncio
    async def test_execute_crm_tool(self, test_session: AsyncSession) -> None:
        """Test executing CRM tool."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "search_customer",
            {"query": "John"},
        )

        assert "success" in result
        # Will be True with found=False since no contacts exist
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_returns_error(
        self, test_session: AsyncSession
    ) -> None:
        """Test that unknown tool returns error."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "nonexistent_tool",
            {"arg": "value"},
        )

        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_ghl_tool_without_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test GHL tool execution without credentials."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "ghl_search_contact",
            {"query": "test"},
        )

        assert result["success"] is False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_calendly_tool_without_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test Calendly tool execution without credentials."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "calendly_get_event_types",
            {},
        )

        assert result["success"] is False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_shopify_tool_without_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test Shopify tool execution without credentials."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "shopify_search_orders",
            {"query": "test"},
        )

        assert result["success"] is False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_twilio_sms_without_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test Twilio SMS tool execution without credentials."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "twilio_send_sms",
            {"to": "+1234567890", "body": "Test"},
        )

        assert result["success"] is False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_telnyx_sms_without_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test Telnyx SMS tool execution without credentials."""
        registry = ToolRegistry(db=test_session, user_id=1)

        result = await registry.execute_tool(
            "telnyx_send_sms",
            {"to": "+1234567890", "body": "Test"},
        )

        assert result["success"] is False
        assert "not configured" in result["error"]


class TestIntegrationTools:
    """Tests for integration tool initialization."""

    def test_ghl_tools_lazy_initialization(
        self, test_session: AsyncSession
    ) -> None:
        """Test GHL tools are lazily initialized."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={
                "gohighlevel": {
                    "access_token": "token",
                    "location_id": "loc123",
                }
            },
        )

        # Initially None
        assert registry._ghl_tools is None

        # After getting, should be initialized
        ghl = registry._get_ghl_tools()
        assert ghl is not None

        # Second call returns same instance
        ghl2 = registry._get_ghl_tools()
        assert ghl is ghl2

    def test_ghl_tools_missing_location_id(
        self, test_session: AsyncSession
    ) -> None:
        """Test GHL tools not initialized without location_id."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={"gohighlevel": {"access_token": "token"}},  # No location_id
        )

        ghl = registry._get_ghl_tools()
        assert ghl is None

    def test_calendly_tools_lazy_initialization(
        self, test_session: AsyncSession
    ) -> None:
        """Test Calendly tools are lazily initialized."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={"calendly": {"access_token": "cal_token"}},
        )

        assert registry._calendly_tools is None

        cal = registry._get_calendly_tools()
        assert cal is not None

    def test_shopify_tools_require_shop_domain(
        self, test_session: AsyncSession
    ) -> None:
        """Test Shopify tools require shop_domain."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={"shopify": {"access_token": "token"}},  # No shop_domain
        )

        shopify = registry._get_shopify_tools()
        assert shopify is None

    def test_twilio_sms_requires_all_credentials(
        self, test_session: AsyncSession
    ) -> None:
        """Test Twilio SMS requires all credentials."""
        # Missing auth_token
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={
                "twilio-sms": {
                    "account_sid": "AC123",
                    "from_number": "+1234567890",
                }
            },
        )

        twilio = registry._get_twilio_sms_tools()
        assert twilio is None

    def test_telnyx_sms_requires_api_key_and_from(
        self, test_session: AsyncSession
    ) -> None:
        """Test Telnyx SMS requires api_key and from_number."""
        # Missing from_number
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={"telnyx-sms": {"api_key": "key123"}},
        )

        telnyx = registry._get_telnyx_sms_tools()
        assert telnyx is None


class TestToolRouting:
    """Tests for correct tool routing to handlers."""

    @pytest.mark.asyncio
    async def test_all_call_control_tools_routed(
        self, test_session: AsyncSession
    ) -> None:
        """Test all call control tools are routed correctly."""
        registry = ToolRegistry(db=test_session, user_id=1)

        call_control_tools = ["end_call", "transfer_call", "send_dtmf"]

        for tool in call_control_tools:
            # These should not raise "Unknown tool" error
            result = await registry.execute_tool(tool, {"reason": "test"})
            assert "Unknown tool" not in str(result.get("error", ""))

    @pytest.mark.asyncio
    async def test_all_crm_tools_routed(self, test_session: AsyncSession) -> None:
        """Test all CRM tools are routed correctly."""
        registry = ToolRegistry(db=test_session, user_id=1)

        crm_tools = [
            "search_customer",
            "create_contact",
            "check_availability",
            "book_appointment",
            "list_appointments",
            "cancel_appointment",
            "reschedule_appointment",
        ]

        for tool in crm_tools:
            result = await registry.execute_tool(tool, {"query": "test"})
            # Should not be "Unknown tool" - may have other errors
            assert "Unknown tool" not in str(result.get("error", ""))

    @pytest.mark.asyncio
    async def test_ghl_tools_routed_to_ghl_handler(
        self, test_session: AsyncSession
    ) -> None:
        """Test GHL tools are routed to GHL handler."""
        registry = ToolRegistry(db=test_session, user_id=1)

        ghl_tools = [
            "ghl_search_contact",
            "ghl_get_contact",
            "ghl_create_contact",
            "ghl_update_contact",
            "ghl_add_contact_tags",
            "ghl_get_calendars",
            "ghl_get_calendar_slots",
            "ghl_book_appointment",
            "ghl_get_appointments",
            "ghl_cancel_appointment",
            "ghl_get_pipelines",
            "ghl_create_opportunity",
        ]

        for tool in ghl_tools:
            result = await registry.execute_tool(tool, {})
            # Should be "not configured" not "Unknown tool"
            assert "not configured" in result.get("error", "") or "Unknown tool" not in str(
                result.get("error", "")
            )


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_without_integrations(
        self, test_session: AsyncSession
    ) -> None:
        """Test close works with no integrations initialized."""
        registry = ToolRegistry(db=test_session, user_id=1)

        # Should not raise
        await registry.close()

    @pytest.mark.asyncio
    async def test_close_closes_ghl_tools(self, test_session: AsyncSession) -> None:
        """Test close calls close on GHL tools."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            integrations={
                "gohighlevel": {
                    "access_token": "token",
                    "location_id": "loc123",
                }
            },
        )

        # Initialize GHL tools
        registry._get_ghl_tools()

        # Mock the close method
        registry._ghl_tools.close = AsyncMock()  # type: ignore[union-attr]

        await registry.close()

        registry._ghl_tools.close.assert_called_once()  # type: ignore[union-attr]


class TestToolRegistryIntegration:
    """Integration tests for ToolRegistry."""

    @pytest.mark.asyncio
    async def test_typical_voice_agent_workflow(
        self, test_session: AsyncSession
    ) -> None:
        """Test typical workflow for a voice agent."""
        registry = ToolRegistry(
            db=test_session,
            user_id=1,
            workspace_id=uuid.uuid4(),
        )

        # 1. Agent searches for customer
        search_result = await registry.execute_tool(
            "search_customer",
            {"query": "+1234567890"},
        )
        assert search_result["success"] is True

        # 2. Customer not found, create new contact
        create_result = await registry.execute_tool(
            "create_contact",
            {
                "first_name": "John",
                "phone_number": "+1234567890",
            },
        )
        # May fail due to validation, but should route correctly
        assert "success" in create_result

        # 3. End the call
        end_result = await registry.execute_tool(
            "end_call",
            {"reason": "conversation_complete"},
        )
        assert end_result["success"] is True
        assert end_result["action"] == "end_call"

    def test_get_tools_for_agent_configuration(
        self, test_session: AsyncSession
    ) -> None:
        """Test getting tools based on agent configuration."""
        # Simulate agent with CRM and call control enabled
        registry = ToolRegistry(db=test_session, user_id=1)

        enabled_tools = ["crm", "call_control"]
        enabled_tool_ids = {
            "crm": ["search_customer", "book_appointment"],
            "call_control": ["end_call", "transfer_call"],
        }

        tools = registry.get_all_tool_definitions(
            enabled_tools=enabled_tools,
            enabled_tool_ids=enabled_tool_ids,
        )

        tool_names = [t.get("name") for t in tools]

        # Should have only the specified tools
        assert "search_customer" in tool_names
        assert "book_appointment" in tool_names
        assert "end_call" in tool_names
        assert "transfer_call" in tool_names

        # Should NOT have these
        assert "create_contact" not in tool_names
        assert "send_dtmf" not in tool_names
