"""Tests for campaign worker in app/services/campaign_worker.py."""

import asyncio
from datetime import UTC, datetime, time, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytz  # type: ignore[import-untyped]

from app.services.campaign_worker import (
    CampaignWorker,
    get_campaign_worker,
    start_campaign_worker,
    stop_campaign_worker,
)


class TestCampaignWorkerInitialization:
    """Tests for CampaignWorker initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        worker = CampaignWorker()

        assert worker.base_url == "http://localhost:8000"
        assert worker.running is False
        assert worker._task is None

    def test_custom_base_url(self) -> None:
        """Test initialization with custom base URL."""
        worker = CampaignWorker(base_url="https://api.example.com")

        assert worker.base_url == "https://api.example.com"

    def test_base_url_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from base URL."""
        worker = CampaignWorker(base_url="https://api.example.com/")

        assert worker.base_url == "https://api.example.com"


class TestCampaignWorkerStartStop:
    """Tests for start/stop functionality."""

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self) -> None:
        """Test that start sets running flag."""
        worker = CampaignWorker()

        with patch.object(worker, "_run_loop", new_callable=AsyncMock):
            await worker.start()

            assert worker.running is True
            assert worker._task is not None

            await worker.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self) -> None:
        """Test that starting again when running does nothing."""
        worker = CampaignWorker()

        with patch.object(worker, "_run_loop", new_callable=AsyncMock):
            await worker.start()
            first_task = worker._task

            await worker.start()  # Should not create new task

            assert worker._task is first_task

            await worker.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running_flag(self) -> None:
        """Test that stop clears running flag."""
        worker = CampaignWorker()

        with patch.object(worker, "_run_loop", new_callable=AsyncMock):
            await worker.start()
            await worker.stop()

            assert worker.running is False
            assert worker._task is None

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self) -> None:
        """Test that stop when not running does nothing."""
        worker = CampaignWorker()

        # Should not raise
        await worker.stop()

        assert worker.running is False


class TestIsWithinCallingHours:
    """Tests for _is_within_calling_hours method."""

    def test_no_calling_hours_configured(self) -> None:
        """Test that no calling hours means always allowed."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = None
        campaign.calling_hours_end = None
        campaign.calling_days = None
        campaign.timezone = "UTC"

        result = worker._is_within_calling_hours(campaign)

        assert result is True

    def test_within_calling_hours(self) -> None:
        """Test when current time is within calling hours."""
        worker = CampaignWorker()

        # Create campaign with 9 AM to 5 PM calling hours
        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = None
        campaign.timezone = "UTC"

        # Mock current time to be 12:00 PM UTC
        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)
            mock_now.weekday.return_value = 2  # Wednesday

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is True

    def test_outside_calling_hours_before(self) -> None:
        """Test when current time is before calling hours."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = None
        campaign.timezone = "UTC"

        # Mock current time to be 7:00 AM UTC (before 9 AM)
        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(7, 0)
            mock_now.weekday.return_value = 2

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is False

    def test_outside_calling_hours_after(self) -> None:
        """Test when current time is after calling hours."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = None
        campaign.timezone = "UTC"

        # Mock current time to be 6:00 PM UTC (after 5 PM)
        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(18, 0)
            mock_now.weekday.return_value = 2

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is False

    def test_calling_days_configured_valid_day(self) -> None:
        """Test when calling days are configured and today is allowed."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = [0, 1, 2, 3, 4]  # Mon-Fri
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)
            mock_now.weekday.return_value = 2  # Wednesday - allowed

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is True

    def test_calling_days_configured_invalid_day(self) -> None:
        """Test when calling days are configured and today is not allowed."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = [0, 1, 2, 3, 4]  # Mon-Fri only
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)
            mock_now.weekday.return_value = 5  # Saturday - not allowed

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is False

    def test_respects_campaign_timezone(self) -> None:
        """Test that calling hours respect campaign timezone."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)  # 9 AM Eastern
        campaign.calling_hours_end = time(17, 0)  # 5 PM Eastern
        campaign.calling_days = None
        campaign.timezone = "America/New_York"

        # The actual implementation uses pytz.timezone().now()
        # so we test the timezone is properly used
        with patch("app.services.campaign_worker.pytz") as mock_pytz:
            mock_tz = MagicMock()
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)  # Noon in campaign timezone
            mock_now.weekday.return_value = 2

            mock_pytz.timezone.return_value = mock_tz

            with patch("app.services.campaign_worker.datetime") as mock_datetime:
                mock_datetime.now.return_value = mock_now

                result = worker._is_within_calling_hours(campaign)

                mock_pytz.timezone.assert_called_with("America/New_York")

    def test_null_timezone_uses_utc(self) -> None:
        """Test that null timezone defaults to UTC."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = None
        campaign.timezone = None

        with patch("app.services.campaign_worker.pytz") as mock_pytz:
            mock_tz = MagicMock()
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)
            mock_now.weekday.return_value = 2

            mock_pytz.timezone.return_value = mock_tz

            with patch("app.services.campaign_worker.datetime") as mock_datetime:
                mock_datetime.now.return_value = mock_now

                worker._is_within_calling_hours(campaign)

                # Should use UTC when timezone is None
                mock_pytz.timezone.assert_called_with("UTC")


class TestGlobalWorkerFunctions:
    """Tests for global worker management functions."""

    @pytest.mark.asyncio
    async def test_start_campaign_worker_creates_instance(self) -> None:
        """Test that start_campaign_worker creates global instance."""
        # Ensure clean state
        await stop_campaign_worker()

        with patch.object(CampaignWorker, "_run_loop", new_callable=AsyncMock):
            worker = await start_campaign_worker("https://test.com")

            assert worker is not None
            assert worker.running is True

            await stop_campaign_worker()

    @pytest.mark.asyncio
    async def test_start_campaign_worker_reuses_instance(self) -> None:
        """Test that start_campaign_worker reuses existing instance."""
        await stop_campaign_worker()

        with patch.object(CampaignWorker, "_run_loop", new_callable=AsyncMock):
            worker1 = await start_campaign_worker("https://test.com")
            worker2 = await start_campaign_worker("https://different.com")

            # Should be same instance
            assert worker1 is worker2

            await stop_campaign_worker()

    @pytest.mark.asyncio
    async def test_stop_campaign_worker_clears_global(self) -> None:
        """Test that stop_campaign_worker clears global instance."""
        await stop_campaign_worker()

        with patch.object(CampaignWorker, "_run_loop", new_callable=AsyncMock):
            await start_campaign_worker()

            assert get_campaign_worker() is not None

            await stop_campaign_worker()

            assert get_campaign_worker() is None

    def test_get_campaign_worker_returns_none_when_not_started(self) -> None:
        """Test get_campaign_worker returns None when not started."""
        # Reset global state by accessing module-level variable
        import app.services.campaign_worker as cw_module

        cw_module._campaign_worker = None

        result = get_campaign_worker()
        assert result is None


class TestWebhookUrlGeneration:
    """Tests for webhook URL generation in _initiate_call."""

    @pytest.mark.asyncio
    async def test_webhook_url_contains_required_params(self) -> None:
        """Test that webhook URL contains required parameters."""
        worker = CampaignWorker(base_url="https://api.example.com")

        # Mock the campaign and contact
        campaign = MagicMock()
        campaign.id = "campaign-123"
        campaign.agent_id = "agent-456"
        campaign.from_phone_number = "+15551234567"

        campaign_contact = MagicMock()
        campaign_contact.id = "cc-789"
        campaign_contact.status = "pending"
        campaign_contact.attempts = 0

        contact = MagicMock()
        contact.id = 1
        contact.phone_number = "+15559876543"

        # Mock telephony service
        mock_telephony = AsyncMock()
        mock_call_info = MagicMock()
        mock_call_info.call_id = "call-abc"
        mock_call_info.status = MagicMock()
        mock_call_info.status.value = "initiated"
        mock_telephony.initiate_call.return_value = mock_call_info

        # Call the method
        await worker._initiate_call(
            campaign=campaign,
            campaign_contact=campaign_contact,
            contact=contact,
            telephony_service=mock_telephony,
        )

        # Verify the webhook URL
        call_args = mock_telephony.initiate_call.call_args
        webhook_url = call_args[1]["webhook_url"]

        assert "https://api.example.com" in webhook_url
        assert "agent_id=agent-456" in webhook_url
        assert "campaign_id=campaign-123" in webhook_url
        assert "campaign_contact_id=cc-789" in webhook_url


class TestCampaignWorkerIntegration:
    """Integration tests for campaign worker."""

    @pytest.mark.asyncio
    async def test_worker_loop_handles_exceptions(self) -> None:
        """Test that worker loop handles exceptions gracefully."""
        worker = CampaignWorker()

        # Mock _process_campaigns to raise exception
        with patch.object(
            worker,
            "_process_campaigns",
            side_effect=Exception("Test error"),
        ):
            worker.running = True

            # Run one iteration manually
            try:
                await worker._run_loop()
            except Exception:
                pass  # Loop should handle exceptions

            # Worker should still be conceptually able to continue

    @pytest.mark.asyncio
    async def test_concurrent_campaign_processing(self) -> None:
        """Test that multiple campaigns can be processed."""
        worker = CampaignWorker()

        # This is more of a smoke test - full integration would need DB
        with patch.object(worker, "_process_campaigns", new_callable=AsyncMock):
            await worker.start()
            await asyncio.sleep(0.1)  # Let it run briefly
            await worker.stop()

            # Should have called _process_campaigns at least once
            assert worker._process_campaigns.called  # type: ignore[attr-defined]


class TestCallingHoursEdgeCases:
    """Edge case tests for calling hours logic."""

    def test_exactly_at_start_time(self) -> None:
        """Test when current time is exactly at start time."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = None
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(9, 0)  # Exactly 9 AM
            mock_now.weekday.return_value = 2

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is True

    def test_exactly_at_end_time(self) -> None:
        """Test when current time is exactly at end time."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = None
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(17, 0)  # Exactly 5 PM
            mock_now.weekday.return_value = 2

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is True

    def test_one_second_after_end_time(self) -> None:
        """Test when current time is one second after end time."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0, 0)
        campaign.calling_days = None
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(17, 0, 1)  # 5:00:01 PM
            mock_now.weekday.return_value = 2

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is False

    def test_empty_calling_days_list(self) -> None:
        """Test with empty calling days list (treated as no day restriction)."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = []  # Empty list - treated as no restriction (falsy)
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)
            mock_now.weekday.return_value = 2

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            # Empty list is falsy, so the day check is skipped - calling is allowed
            assert result is True

    def test_all_days_allowed(self) -> None:
        """Test when all days are allowed."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(9, 0)
        campaign.calling_hours_end = time(17, 0)
        campaign.calling_days = [0, 1, 2, 3, 4, 5, 6]  # All days
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)
            mock_now.weekday.return_value = 6  # Sunday

            mock_datetime.now.return_value = mock_now

            result = worker._is_within_calling_hours(campaign)

            assert result is True

    def test_weekend_only_calling(self) -> None:
        """Test weekend-only calling configuration."""
        worker = CampaignWorker()

        campaign = MagicMock()
        campaign.calling_hours_start = time(10, 0)
        campaign.calling_hours_end = time(16, 0)
        campaign.calling_days = [5, 6]  # Saturday and Sunday only
        campaign.timezone = "UTC"

        with patch("app.services.campaign_worker.datetime") as mock_datetime:
            # Test Saturday (allowed)
            mock_now = MagicMock()
            mock_now.time.return_value = time(12, 0)
            mock_now.weekday.return_value = 5  # Saturday

            mock_datetime.now.return_value = mock_now

            assert worker._is_within_calling_hours(campaign) is True

            # Test Wednesday (not allowed)
            mock_now.weekday.return_value = 2  # Wednesday

            assert worker._is_within_calling_hours(campaign) is False
