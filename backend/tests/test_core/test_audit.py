"""Tests for audit logging in app/core/audit.py."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.core.audit import (
    AuditAction,
    _sanitize_details,
    audit_agent_change,
    audit_api_key_change,
    audit_data_export,
    audit_log,
)


class TestAuditAction:
    """Tests for AuditAction constants."""

    def test_authentication_actions_exist(self) -> None:
        """Test that authentication-related actions are defined."""
        assert AuditAction.LOGIN_SUCCESS == "auth.login.success"
        assert AuditAction.LOGIN_FAILED == "auth.login.failed"
        assert AuditAction.LOGOUT == "auth.logout"
        assert AuditAction.REGISTER == "auth.register"
        assert AuditAction.PASSWORD_CHANGE == "auth.password.change"

    def test_api_key_actions_exist(self) -> None:
        """Test that API key actions are defined."""
        assert AuditAction.API_KEY_CREATE == "api_key.create"
        assert AuditAction.API_KEY_UPDATE == "api_key.update"
        assert AuditAction.API_KEY_DELETE == "api_key.delete"

    def test_agent_actions_exist(self) -> None:
        """Test that agent actions are defined."""
        assert AuditAction.AGENT_CREATE == "agent.create"
        assert AuditAction.AGENT_UPDATE == "agent.update"
        assert AuditAction.AGENT_DELETE == "agent.delete"
        assert AuditAction.AGENT_ACTIVATE == "agent.activate"
        assert AuditAction.AGENT_DEACTIVATE == "agent.deactivate"

    def test_workspace_actions_exist(self) -> None:
        """Test that workspace actions are defined."""
        assert AuditAction.WORKSPACE_CREATE == "workspace.create"
        assert AuditAction.WORKSPACE_UPDATE == "workspace.update"
        assert AuditAction.WORKSPACE_DELETE == "workspace.delete"

    def test_contact_actions_exist(self) -> None:
        """Test that contact/CRM actions are defined."""
        assert AuditAction.CONTACT_CREATE == "contact.create"
        assert AuditAction.CONTACT_UPDATE == "contact.update"
        assert AuditAction.CONTACT_DELETE == "contact.delete"
        assert AuditAction.CONTACT_EXPORT == "contact.export"

    def test_compliance_actions_exist(self) -> None:
        """Test that compliance/privacy actions are defined."""
        assert AuditAction.DATA_EXPORT == "compliance.data_export"
        assert AuditAction.DATA_DELETE == "compliance.data_delete"
        assert AuditAction.CONSENT_UPDATE == "compliance.consent_update"


class TestSanitizeDetails:
    """Tests for _sanitize_details function."""

    def test_non_sensitive_fields_unchanged(self) -> None:
        """Test that non-sensitive fields are not modified."""
        details = {
            "user_id": 123,
            "email": "test@example.com",
            "action": "login",
            "ip_address": "192.168.1.1",
        }

        result = _sanitize_details(details)

        assert result == details

    def test_password_field_masked(self) -> None:
        """Test that password field is masked."""
        details = {"username": "user1", "password": "supersecretpassword"}

        result = _sanitize_details(details)

        assert result["username"] == "user1"
        assert result["password"] == "****word"  # Last 4 chars

    def test_api_key_field_masked(self) -> None:
        """Test that api_key field is masked."""
        details = {"api_key": "sk-12345678901234567890"}

        result = _sanitize_details(details)

        assert result["api_key"] == "****7890"

    def test_token_fields_masked(self) -> None:
        """Test that various token fields are masked."""
        details = {
            "token": "abcdefghijklmnop",
            "auth_token": "xyz123456789",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "refresh_token": "refresh_12345678",
        }

        result = _sanitize_details(details)

        assert result["token"] == "****mnop"
        assert result["auth_token"] == "****6789"
        assert result["access_token"] == "****VCJ9"  # Last 4 chars of the JWT
        assert result["refresh_token"] == "****5678"

    def test_provider_specific_keys_masked(self) -> None:
        """Test that provider-specific API keys are masked."""
        details = {
            "openai_api_key": "sk-openai1234567890",
            "telnyx_api_key": "KEY_telnyx123456",
            "twilio_auth_token": "twilio_secret_123",
            "deepgram_api_key": "deepgram_key_xyz",
            "elevenlabs_api_key": "elevenlabs_api_xyz",
        }

        result = _sanitize_details(details)

        assert result["openai_api_key"] == "****7890"
        assert result["telnyx_api_key"] == "****3456"
        assert result["twilio_auth_token"] == "****_123"
        assert result["deepgram_api_key"] == "****_xyz"
        assert result["elevenlabs_api_key"] == "****_xyz"

    def test_case_insensitive_matching(self) -> None:
        """Test that sensitive field detection is case-insensitive."""
        details = {
            "PASSWORD": "secret123",
            "Api_Key": "key12345",
            "SECRET": "mysecret1",
        }

        result = _sanitize_details(details)

        assert result["PASSWORD"] == "****t123"
        assert result["Api_Key"] == "****2345"
        assert result["SECRET"] == "****ret1"

    def test_short_value_fully_masked(self) -> None:
        """Test that short sensitive values are fully masked."""
        details = {
            "password": "abc",  # Less than 4 chars
            "api_key": "xy",  # Less than 4 chars
        }

        result = _sanitize_details(details)

        assert result["password"] == "****"
        assert result["api_key"] == "****"

    def test_non_string_sensitive_values_fully_masked(self) -> None:
        """Test that non-string sensitive values are fully masked."""
        details = {
            "password": 12345,  # Integer
            "api_key": None,  # None
            "token": ["a", "b"],  # List
        }

        result = _sanitize_details(details)

        assert result["password"] == "****"
        assert result["api_key"] == "****"
        assert result["token"] == "****"

    def test_partial_match_in_key_name(self) -> None:
        """Test that partial matches in key names are detected."""
        details = {
            "user_password_hash": "hashed_password_here",
            "my_api_key_value": "key_value_12345",
            "secret_code": "the_secret_code",
        }

        result = _sanitize_details(details)

        assert "****" in result["user_password_hash"]
        assert "****" in result["my_api_key_value"]
        assert "****" in result["secret_code"]

    def test_empty_details(self) -> None:
        """Test with empty details dict."""
        result = _sanitize_details({})
        assert result == {}

    def test_nested_dicts_not_deep_sanitized(self) -> None:
        """Test that nested dicts are passed through as-is (not deep sanitized)."""
        details = {
            "user": {"name": "Test", "password": "should_not_be_masked"},
            "password": "should_be_masked",
        }

        result = _sanitize_details(details)

        # Top-level password is masked
        assert result["password"] == "****sked"
        # Nested password is not masked (current implementation is shallow)
        assert result["user"]["password"] == "should_not_be_masked"


class TestAuditLog:
    """Tests for audit_log function."""

    def test_successful_action_logs_info(self) -> None:
        """Test that successful actions are logged at info level."""
        with patch("app.core.audit.logger") as mock_logger:
            audit_log(
                action=AuditAction.LOGIN_SUCCESS,
                user_id=123,
                success=True,
            )

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "audit_event"
            assert call_args[1]["action"] == AuditAction.LOGIN_SUCCESS
            assert call_args[1]["user_id"] == 123
            assert call_args[1]["success"] is True
            assert call_args[1]["audit"] is True

    def test_failed_action_logs_warning(self) -> None:
        """Test that failed actions are logged at warning level."""
        with patch("app.core.audit.logger") as mock_logger:
            audit_log(
                action=AuditAction.LOGIN_FAILED,
                user_id=123,
                success=False,
            )

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert call_args[1]["success"] is False

    def test_includes_resource_info(self) -> None:
        """Test that resource type and ID are included."""
        with patch("app.core.audit.logger") as mock_logger:
            audit_log(
                action=AuditAction.AGENT_UPDATE,
                user_id=1,
                resource_type="agent",
                resource_id="agent-123",
            )

            call_args = mock_logger.info.call_args
            assert call_args[1]["resource_type"] == "agent"
            assert call_args[1]["resource_id"] == "agent-123"

    def test_includes_ip_address(self) -> None:
        """Test that IP address is included when provided."""
        with patch("app.core.audit.logger") as mock_logger:
            audit_log(
                action=AuditAction.LOGIN_SUCCESS,
                user_id=1,
                ip_address="192.168.1.100",
            )

            call_args = mock_logger.info.call_args
            assert call_args[1]["ip_address"] == "192.168.1.100"

    def test_sanitizes_details(self) -> None:
        """Test that details are sanitized before logging."""
        with patch("app.core.audit.logger") as mock_logger:
            audit_log(
                action=AuditAction.API_KEY_UPDATE,
                user_id=1,
                details={"api_key": "sk-supersecretkey123"},
            )

            call_args = mock_logger.info.call_args
            sanitized_details = call_args[1]["details"]
            assert sanitized_details["api_key"] == "****y123"

    def test_optional_fields_excluded_when_none(self) -> None:
        """Test that optional fields are excluded when None."""
        with patch("app.core.audit.logger") as mock_logger:
            audit_log(action=AuditAction.LOGIN_SUCCESS)

            call_args = mock_logger.info.call_args
            assert "user_id" not in call_args[1]
            assert "resource_type" not in call_args[1]
            assert "resource_id" not in call_args[1]
            assert "ip_address" not in call_args[1]
            assert "details" not in call_args[1]

    def test_audit_flag_always_present(self) -> None:
        """Test that audit flag is always True for filtering."""
        with patch("app.core.audit.logger") as mock_logger:
            audit_log(action=AuditAction.LOGIN_SUCCESS)

            call_args = mock_logger.info.call_args
            assert call_args[1]["audit"] is True


class TestAuditApiKeyChange:
    """Tests for audit_api_key_change convenience function."""

    def test_create_action(self) -> None:
        """Test logging API key creation."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_api_key_change(
                user_id=1,
                workspace_id="ws-123",
                key_type="openai",
                action="create",
            )

            mock_audit_log.assert_called_once()
            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.API_KEY_CREATE
            assert call_kwargs["resource_type"] == "api_key"
            assert call_kwargs["resource_id"] == "ws-123"
            assert call_kwargs["details"]["key_type"] == "openai"
            assert call_kwargs["details"]["workspace_scoped"] is True

    def test_update_action(self) -> None:
        """Test logging API key update."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_api_key_change(
                user_id=1,
                workspace_id=None,
                key_type="telnyx",
                action="update",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.API_KEY_UPDATE
            assert call_kwargs["details"]["workspace_scoped"] is False

    def test_delete_action(self) -> None:
        """Test logging API key deletion."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_api_key_change(
                user_id=1,
                workspace_id="ws-456",
                key_type="twilio",
                action="delete",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.API_KEY_DELETE

    def test_unknown_action_defaults_to_update(self) -> None:
        """Test that unknown action defaults to update."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_api_key_change(
                user_id=1,
                workspace_id=None,
                key_type="custom",
                action="unknown_action",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.API_KEY_UPDATE

    def test_includes_ip_address(self) -> None:
        """Test that IP address is passed through."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_api_key_change(
                user_id=1,
                workspace_id=None,
                key_type="openai",
                action="create",
                ip_address="10.0.0.1",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["ip_address"] == "10.0.0.1"


class TestAuditAgentChange:
    """Tests for audit_agent_change convenience function."""

    def test_create_action(self) -> None:
        """Test logging agent creation."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_agent_change(
                user_id=1,
                agent_id="agent-abc",
                action="create",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.AGENT_CREATE
            assert call_kwargs["resource_type"] == "agent"
            assert call_kwargs["resource_id"] == "agent-abc"

    def test_update_action_with_changes(self) -> None:
        """Test logging agent update with change details."""
        changes = {"name": "New Name", "system_prompt": "Updated prompt"}

        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_agent_change(
                user_id=1,
                agent_id="agent-xyz",
                action="update",
                changes=changes,
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.AGENT_UPDATE
            assert call_kwargs["details"]["changes"] == changes

    def test_delete_action(self) -> None:
        """Test logging agent deletion."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_agent_change(
                user_id=1,
                agent_id="agent-123",
                action="delete",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.AGENT_DELETE

    def test_activate_action(self) -> None:
        """Test logging agent activation."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_agent_change(
                user_id=1,
                agent_id="agent-123",
                action="activate",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.AGENT_ACTIVATE

    def test_deactivate_action(self) -> None:
        """Test logging agent deactivation."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_agent_change(
                user_id=1,
                agent_id="agent-123",
                action="deactivate",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.AGENT_DEACTIVATE

    def test_no_changes_no_details(self) -> None:
        """Test that no details are added when changes is None."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_agent_change(
                user_id=1,
                agent_id="agent-123",
                action="update",
                changes=None,
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs.get("details") is None


class TestAuditDataExport:
    """Tests for audit_data_export convenience function."""

    def test_export_contacts(self) -> None:
        """Test logging contact data export."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_data_export(
                user_id=1,
                export_type="contacts",
                record_count=150,
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.DATA_EXPORT
            assert call_kwargs["resource_type"] == "contacts"
            assert call_kwargs["details"]["record_count"] == 150

    def test_export_calls(self) -> None:
        """Test logging call records export."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_data_export(
                user_id=2,
                export_type="calls",
                record_count=500,
                ip_address="203.0.113.50",
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["action"] == AuditAction.DATA_EXPORT
            assert call_kwargs["resource_type"] == "calls"
            assert call_kwargs["details"]["record_count"] == 500
            assert call_kwargs["ip_address"] == "203.0.113.50"

    def test_export_zero_records(self) -> None:
        """Test logging export with zero records."""
        with patch("app.core.audit.audit_log") as mock_audit_log:
            audit_data_export(
                user_id=1,
                export_type="appointments",
                record_count=0,
            )

            call_kwargs = mock_audit_log.call_args[1]
            assert call_kwargs["details"]["record_count"] == 0


class TestAuditIntegration:
    """Integration tests for audit logging."""

    def test_full_audit_workflow(self) -> None:
        """Test a complete audit workflow for a typical user session."""
        with patch("app.core.audit.logger") as mock_logger:
            # User logs in
            audit_log(
                action=AuditAction.LOGIN_SUCCESS,
                user_id=1,
                ip_address="192.168.1.1",
            )

            # User creates an agent
            audit_agent_change(
                user_id=1,
                agent_id="agent-new",
                action="create",
                ip_address="192.168.1.1",
            )

            # User updates API keys
            audit_api_key_change(
                user_id=1,
                workspace_id="ws-1",
                key_type="openai",
                action="update",
                ip_address="192.168.1.1",
            )

            # User exports data
            audit_data_export(
                user_id=1,
                export_type="contacts",
                record_count=100,
                ip_address="192.168.1.1",
            )

            # User logs out
            audit_log(
                action=AuditAction.LOGOUT,
                user_id=1,
                ip_address="192.168.1.1",
            )

            # Verify all logs were made
            assert mock_logger.info.call_count == 5

    def test_sensitive_data_never_logged_plain(self) -> None:
        """Test that sensitive data is always masked in audit logs."""
        sensitive_fields = [
            ("password", "my_super_secret_password"),
            ("api_key", "sk-1234567890abcdef"),
            ("secret", "the_secret_value_123"),
            ("token", "jwt_token_abc123xyz"),
            ("openai_api_key", "sk-openai-key-here"),
            ("twilio_auth_token", "twilio-token-123"),
        ]

        with patch("app.core.audit.logger") as mock_logger:
            for field_name, field_value in sensitive_fields:
                audit_log(
                    action=AuditAction.API_KEY_UPDATE,
                    user_id=1,
                    details={field_name: field_value},
                )

        # Check that none of the plain text values appear in logs
        for call in mock_logger.info.call_args_list:
            log_str = str(call)
            for _, plain_value in sensitive_fields:
                assert plain_value not in log_str, f"Plain value '{plain_value}' found in log"
