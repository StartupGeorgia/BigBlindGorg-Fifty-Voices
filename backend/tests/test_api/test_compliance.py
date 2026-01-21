"""Tests for compliance API endpoints (GDPR/CCPA)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class TestComplianceStatus:
    """Test compliance status endpoints."""

    @pytest.mark.asyncio
    async def test_get_compliance_status_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting compliance status."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/compliance/status")

        assert response.status_code == 200
        data = response.json()
        assert "gdpr" in data
        assert "ccpa" in data
        assert "completed" in data["gdpr"]
        assert "total" in data["gdpr"]
        assert "percentage" in data["gdpr"]
        assert "checks" in data["gdpr"]
        assert "completed" in data["ccpa"]
        assert "total" in data["ccpa"]
        assert "percentage" in data["ccpa"]
        assert "checks" in data["ccpa"]

    @pytest.mark.asyncio
    async def test_get_compliance_status_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test getting compliance status without authentication."""
        response = await test_client.get("/api/v1/compliance/status")

        assert response.status_code == 401


class TestPrivacySettings:
    """Test privacy settings endpoints."""

    @pytest.mark.asyncio
    async def test_get_privacy_settings_default(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test getting default privacy settings."""
        client, _user = authenticated_test_client

        response = await client.get("/api/v1/compliance/privacy-settings")

        assert response.status_code == 200
        data = response.json()
        assert "privacy_policy_url" in data
        assert "data_retention_days" in data
        assert "openai_dpa_signed" in data
        assert "telnyx_dpa_signed" in data
        assert "ccpa_opt_out" in data

    @pytest.mark.asyncio
    async def test_update_privacy_settings_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test updating privacy settings."""
        client, _user = authenticated_test_client

        response = await client.patch(
            "/api/v1/compliance/privacy-settings",
            json={
                "privacy_policy_url": "https://example.com/privacy",
                "data_retention_days": 90,
                "openai_dpa_signed": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["privacy_policy_url"] == "https://example.com/privacy"
        assert data["data_retention_days"] == 90
        assert data["openai_dpa_signed"] is True
        assert data["openai_dpa_signed_at"] is not None

    @pytest.mark.asyncio
    async def test_update_privacy_settings_partial(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test partial update of privacy settings."""
        client, _user = authenticated_test_client

        # Update only one field
        response = await client.patch(
            "/api/v1/compliance/privacy-settings",
            json={"telnyx_dpa_signed": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["telnyx_dpa_signed"] is True

    @pytest.mark.asyncio
    async def test_update_privacy_settings_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test updating privacy settings without authentication."""
        response = await test_client.patch(
            "/api/v1/compliance/privacy-settings",
            json={"data_retention_days": 90},
        )

        assert response.status_code == 401


class TestConsent:
    """Test consent recording endpoints."""

    @pytest.mark.asyncio
    async def test_record_consent_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test recording consent."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/compliance/consent",
            json={"consent_type": "data_processing", "granted": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "data_processing" in data["message"]

    @pytest.mark.asyncio
    async def test_record_consent_call_recording(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test recording call recording consent."""
        client, _user = authenticated_test_client

        response = await client.post(
            "/api/v1/compliance/consent",
            json={"consent_type": "call_recording", "granted": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert "call_recording" in data["message"]

    @pytest.mark.asyncio
    async def test_withdraw_consent_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test withdrawing consent."""
        client, _user = authenticated_test_client

        # First grant consent
        await client.post(
            "/api/v1/compliance/consent",
            json={"consent_type": "data_processing", "granted": True},
        )

        # Then withdraw
        response = await client.post(
            "/api/v1/compliance/consent/withdraw",
            json={"consent_type": "data_processing", "granted": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert "withdrawn" in data["message"]


class TestCCPAOptOut:
    """Test CCPA opt-out endpoints."""

    @pytest.mark.asyncio
    async def test_ccpa_opt_out_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test CCPA opt-out."""
        client, _user = authenticated_test_client

        response = await client.post("/api/v1/compliance/ccpa/opt-out")

        assert response.status_code == 200
        data = response.json()
        assert "opted out" in data["message"]

        # Verify in privacy settings
        settings_response = await client.get("/api/v1/compliance/privacy-settings")
        settings_data = settings_response.json()
        assert settings_data["ccpa_opt_out"] is True
        assert settings_data["ccpa_opt_out_at"] is not None

    @pytest.mark.asyncio
    async def test_ccpa_opt_in_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test CCPA opt-in after opt-out."""
        client, _user = authenticated_test_client

        # First opt out
        await client.post("/api/v1/compliance/ccpa/opt-out")

        # Then opt back in
        response = await client.post("/api/v1/compliance/ccpa/opt-in")

        assert response.status_code == 200
        data = response.json()
        assert "opted back in" in data["message"]

        # Verify in privacy settings
        settings_response = await client.get("/api/v1/compliance/privacy-settings")
        settings_data = settings_response.json()
        assert settings_data["ccpa_opt_out"] is False


class TestDataExport:
    """Test data export endpoints (GDPR Article 20)."""

    @pytest.mark.asyncio
    async def test_export_user_data_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test exporting user data."""
        client, user = authenticated_test_client

        response = await client.get("/api/v1/compliance/export")

        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "settings" in data
        assert "privacy_settings" in data
        assert "agents" in data
        assert "workspaces" in data
        assert "contacts" in data
        assert "appointments" in data
        assert "call_records" in data
        assert "consent_records" in data
        assert "exported_at" in data
        assert data["user"]["id"] == user.id

    @pytest.mark.asyncio
    async def test_export_updates_timestamp(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test that export updates last_data_export_at timestamp."""
        client, _user = authenticated_test_client

        # Export data
        await client.get("/api/v1/compliance/export")

        # Check privacy settings
        response = await client.get("/api/v1/compliance/privacy-settings")
        data = response.json()
        assert data["last_data_export_at"] is not None

    @pytest.mark.asyncio
    async def test_export_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test exporting data without authentication."""
        response = await test_client.get("/api/v1/compliance/export")

        assert response.status_code == 401


class TestDataDeletion:
    """Test data deletion endpoints (GDPR Article 17)."""

    @pytest.mark.asyncio
    async def test_delete_user_data_success(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
        test_session: AsyncSession,
    ) -> None:
        """Test deleting user data."""
        client, user = authenticated_test_client

        # First create some data
        await client.post(
            "/api/v1/agents",
            json={
                "name": "Agent to Delete",
                "pricing_tier": "balanced",
                "system_prompt": "You are a helpful assistant for testing purposes.",
            },
        )

        # Delete all user data
        response = await client.delete("/api/v1/compliance/data")

        assert response.status_code == 200
        data = response.json()
        assert "deleted_counts" in data
        assert "deleted_at" in data
        assert data["deleted_counts"]["agents"] >= 1

        # Verify agents are deleted
        list_response = await client.get("/api/v1/agents")
        assert len(list_response.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_data_unauthenticated(
        self,
        test_client: AsyncClient,
    ) -> None:
        """Test deleting data without authentication."""
        response = await test_client.delete("/api/v1/compliance/data")

        assert response.status_code == 401


class TestRetentionCleanup:
    """Test data retention cleanup endpoint."""

    @pytest.mark.asyncio
    async def test_trigger_retention_cleanup(
        self,
        authenticated_test_client: tuple[AsyncClient, User],
    ) -> None:
        """Test triggering retention cleanup."""
        client, _user = authenticated_test_client

        response = await client.post("/api/v1/compliance/retention/cleanup")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted_counts" in data
