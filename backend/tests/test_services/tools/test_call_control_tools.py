"""Tests for call control tools in app/services/tools/call_control_tools.py."""

from typing import Any

import pytest

from app.services.tools.call_control_tools import CallControlTools


class TestCallControlToolsDefinitions:
    """Tests for tool definitions."""

    def test_get_tool_definitions_returns_list(self) -> None:
        """Test that get_tool_definitions returns a list."""
        tools = CallControlTools.get_tool_definitions()
        assert isinstance(tools, list)
        assert len(tools) == 3

    def test_end_call_tool_definition(self) -> None:
        """Test end_call tool definition structure."""
        tools = CallControlTools.get_tool_definitions()
        end_call = next(t for t in tools if t["name"] == "end_call")

        assert end_call["type"] == "function"
        assert "description" in end_call
        assert "parameters" in end_call
        assert end_call["parameters"]["type"] == "object"
        assert "reason" in end_call["parameters"]["properties"]
        assert "reason" in end_call["parameters"]["required"]

    def test_transfer_call_tool_definition(self) -> None:
        """Test transfer_call tool definition structure."""
        tools = CallControlTools.get_tool_definitions()
        transfer = next(t for t in tools if t["name"] == "transfer_call")

        assert transfer["type"] == "function"
        assert "destination" in transfer["parameters"]["properties"]
        assert "announce" in transfer["parameters"]["properties"]
        assert "destination" in transfer["parameters"]["required"]
        # announce is optional
        assert "announce" not in transfer["parameters"]["required"]

    def test_send_dtmf_tool_definition(self) -> None:
        """Test send_dtmf tool definition structure."""
        tools = CallControlTools.get_tool_definitions()
        dtmf = next(t for t in tools if t["name"] == "send_dtmf")

        assert dtmf["type"] == "function"
        assert "digits" in dtmf["parameters"]["properties"]
        assert "duration_ms" in dtmf["parameters"]["properties"]
        assert "digits" in dtmf["parameters"]["required"]
        # duration_ms is optional
        assert "duration_ms" not in dtmf["parameters"]["required"]

    def test_all_tools_have_required_fields(self) -> None:
        """Test that all tools have required fields."""
        tools = CallControlTools.get_tool_definitions()

        for tool in tools:
            assert "type" in tool
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert tool["type"] == "function"
            assert len(tool["description"]) > 10  # Meaningful description


class TestEndCallExecution:
    """Tests for end_call tool execution."""

    @pytest.mark.asyncio
    async def test_end_call_with_reason(self) -> None:
        """Test end_call with explicit reason."""
        result = await CallControlTools.execute_tool(
            "end_call",
            {"reason": "conversation_complete"},
        )

        assert result["success"] is True
        assert result["action"] == "end_call"
        assert result["reason"] == "conversation_complete"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_end_call_default_reason(self) -> None:
        """Test end_call uses default reason when not provided."""
        result = await CallControlTools.execute_tool("end_call", {})

        assert result["success"] is True
        assert result["action"] == "end_call"
        assert result["reason"] == "conversation_complete"

    @pytest.mark.asyncio
    async def test_end_call_various_reasons(self) -> None:
        """Test end_call with various reason values."""
        reasons = [
            "caller_requested",
            "no_response",
            "transferred",
            "error",
            "timeout",
        ]

        for reason in reasons:
            result = await CallControlTools.execute_tool("end_call", {"reason": reason})
            assert result["success"] is True
            assert result["reason"] == reason


class TestTransferCallExecution:
    """Tests for transfer_call tool execution."""

    @pytest.mark.asyncio
    async def test_transfer_with_destination(self) -> None:
        """Test transfer with valid destination."""
        result = await CallControlTools.execute_tool(
            "transfer_call",
            {"destination": "+14155551234"},
        )

        assert result["success"] is True
        assert result["action"] == "transfer_call"
        assert result["destination"] == "+14155551234"
        assert result["announce"] is None
        assert "Transferring" in result["message"]

    @pytest.mark.asyncio
    async def test_transfer_with_announcement(self) -> None:
        """Test transfer with announcement message."""
        result = await CallControlTools.execute_tool(
            "transfer_call",
            {
                "destination": "+14155551234",
                "announce": "Incoming transfer from support queue",
            },
        )

        assert result["success"] is True
        assert result["action"] == "transfer_call"
        assert result["destination"] == "+14155551234"
        assert result["announce"] == "Incoming transfer from support queue"

    @pytest.mark.asyncio
    async def test_transfer_without_destination_fails(self) -> None:
        """Test transfer without destination fails."""
        result = await CallControlTools.execute_tool("transfer_call", {})

        assert result["success"] is False
        assert "error" in result
        assert "Destination" in result["error"]

    @pytest.mark.asyncio
    async def test_transfer_empty_destination_fails(self) -> None:
        """Test transfer with empty destination fails."""
        result = await CallControlTools.execute_tool(
            "transfer_call",
            {"destination": ""},
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_transfer_department_identifier(self) -> None:
        """Test transfer with department identifier instead of phone number."""
        result = await CallControlTools.execute_tool(
            "transfer_call",
            {"destination": "sales_department"},
        )

        assert result["success"] is True
        assert result["destination"] == "sales_department"


class TestSendDtmfExecution:
    """Tests for send_dtmf tool execution."""

    @pytest.mark.asyncio
    async def test_send_dtmf_basic_digits(self) -> None:
        """Test sending basic DTMF digits."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "1234"},
        )

        assert result["success"] is True
        assert result["action"] == "send_dtmf"
        assert result["digits"] == "1234"
        assert result["duration_ms"] == 250  # Default

    @pytest.mark.asyncio
    async def test_send_dtmf_with_custom_duration(self) -> None:
        """Test sending DTMF with custom duration."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "5678", "duration_ms": 500},
        )

        assert result["success"] is True
        assert result["duration_ms"] == 500

    @pytest.mark.asyncio
    async def test_send_dtmf_star_and_hash(self) -> None:
        """Test DTMF with star and hash characters."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "*1234#"},
        )

        assert result["success"] is True
        assert result["digits"] == "*1234#"

    @pytest.mark.asyncio
    async def test_send_dtmf_with_letters(self) -> None:
        """Test DTMF with A-D letters."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "1A2B3C4D"},
        )

        assert result["success"] is True
        assert result["digits"] == "1A2B3C4D"

    @pytest.mark.asyncio
    async def test_send_dtmf_lowercase_normalized(self) -> None:
        """Test that lowercase letters are normalized to uppercase."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "1a2b3c4d"},
        )

        assert result["success"] is True
        assert result["digits"] == "1A2B3C4D"

    @pytest.mark.asyncio
    async def test_send_dtmf_with_pause(self) -> None:
        """Test DTMF with pause character 'w'."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "123w456"},
        )

        assert result["success"] is True
        assert result["digits"] == "123w456"

    @pytest.mark.asyncio
    async def test_send_dtmf_uppercase_w_normalized(self) -> None:
        """Test that uppercase W is normalized to lowercase w."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "123W456"},
        )

        assert result["success"] is True
        assert result["digits"] == "123w456"

    @pytest.mark.asyncio
    async def test_send_dtmf_without_digits_fails(self) -> None:
        """Test that DTMF without digits fails."""
        result = await CallControlTools.execute_tool("send_dtmf", {})

        assert result["success"] is False
        assert "error" in result
        assert "Digits" in result["error"]

    @pytest.mark.asyncio
    async def test_send_dtmf_empty_digits_fails(self) -> None:
        """Test that DTMF with empty digits fails."""
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": ""},
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_send_dtmf_invalid_characters_fails(self) -> None:
        """Test that invalid DTMF characters fail validation."""
        invalid_cases = [
            "123X456",  # Invalid letter X
            "123!456",  # Special character
            "123 456",  # Space
            "123.456",  # Period
            "123-456",  # Hyphen
            "EFG",  # Invalid letters
        ]

        for invalid_digits in invalid_cases:
            result = await CallControlTools.execute_tool(
                "send_dtmf",
                {"digits": invalid_digits},
            )

            assert result["success"] is False, f"Expected failure for: {invalid_digits}"
            assert "Invalid DTMF" in result["error"]

    @pytest.mark.asyncio
    async def test_send_dtmf_all_valid_characters(self) -> None:
        """Test all valid DTMF characters."""
        valid_chars = "0123456789*#ABCDabcdwW"
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": valid_chars},
        )

        assert result["success"] is True


class TestUnknownTool:
    """Tests for unknown tool handling."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self) -> None:
        """Test that unknown tool returns error."""
        result = await CallControlTools.execute_tool(
            "nonexistent_tool",
            {"arg": "value"},
        )

        assert result["success"] is False
        assert "error" in result
        assert "Unknown" in result["error"]
        assert "nonexistent_tool" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_tool_name_returns_error(self) -> None:
        """Test that empty tool name returns error."""
        result = await CallControlTools.execute_tool("", {})

        assert result["success"] is False
        assert "Unknown" in result["error"]


class TestCallControlToolsIntegration:
    """Integration tests for call control tools."""

    @pytest.mark.asyncio
    async def test_typical_call_ending_workflow(self) -> None:
        """Test typical workflow of ending a call."""
        # AI decides to end the call after saying goodbye
        result = await CallControlTools.execute_tool(
            "end_call",
            {"reason": "conversation_complete"},
        )

        assert result["success"] is True
        assert result["action"] == "end_call"
        # The realtime session would handle this action

    @pytest.mark.asyncio
    async def test_transfer_to_human_workflow(self) -> None:
        """Test transferring to human agent workflow."""
        # Customer requests to speak to human
        result = await CallControlTools.execute_tool(
            "transfer_call",
            {
                "destination": "+18005551234",
                "announce": "Customer requesting billing assistance",
            },
        )

        assert result["success"] is True
        assert result["action"] == "transfer_call"

    @pytest.mark.asyncio
    async def test_ivr_navigation_workflow(self) -> None:
        """Test navigating an IVR system."""
        # Navigate through IVR: Press 1 for English, wait, then press 3 for support
        result = await CallControlTools.execute_tool(
            "send_dtmf",
            {"digits": "1w3", "duration_ms": 300},
        )

        assert result["success"] is True
        assert result["action"] == "send_dtmf"
        assert result["digits"] == "1w3"

    @pytest.mark.asyncio
    async def test_action_fields_for_realtime_session(self) -> None:
        """Test that action fields are correct for realtime session handling."""
        # Test all tools return proper action fields
        tools_and_actions = [
            ("end_call", {"reason": "test"}, "end_call"),
            ("transfer_call", {"destination": "+1234567890"}, "transfer_call"),
            ("send_dtmf", {"digits": "123"}, "send_dtmf"),
        ]

        for tool_name, args, expected_action in tools_and_actions:
            result = await CallControlTools.execute_tool(tool_name, args)
            assert result.get("action") == expected_action, f"Failed for {tool_name}"
            assert result["success"] is True

    def test_tool_definitions_match_openai_format(self) -> None:
        """Test that tool definitions match OpenAI function calling format."""
        tools = CallControlTools.get_tool_definitions()

        for tool in tools:
            # Must have these exact keys for OpenAI function calling
            assert "type" in tool
            assert tool["type"] == "function"
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

            # Parameters must be valid JSON Schema
            params = tool["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params
