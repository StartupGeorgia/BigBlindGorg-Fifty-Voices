"""Tests for webhook signature validation in app/core/webhook_security.py."""

import base64
import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.webhook_security import (
    validate_telnyx_signature,
    validate_twilio_signature,
    verify_telnyx_webhook,
    verify_twilio_webhook,
)


class TestValidateTwilioSignature:
    """Tests for validate_twilio_signature function."""

    def test_valid_signature(self) -> None:
        """Test validation of valid Twilio signature."""
        auth_token = "test-auth-token-12345"
        url = "https://example.com/webhooks/twilio"
        params = {"AccountSid": "AC123", "From": "+1234567890", "Body": "Hello"}

        # Calculate expected signature
        sorted_params = sorted(params.items())
        data = url + "".join(f"{k}{v}" for k, v in sorted_params)
        expected_sig = base64.b64encode(
            hmac.new(
                auth_token.encode("utf-8"),
                data.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("utf-8")

        result = validate_twilio_signature(expected_sig, url, params, auth_token)
        assert result is True

    def test_invalid_signature(self) -> None:
        """Test that wrong signature fails validation."""
        auth_token = "test-auth-token-12345"
        url = "https://example.com/webhooks/twilio"
        params = {"AccountSid": "AC123"}

        result = validate_twilio_signature("wrong-signature", url, params, auth_token)
        assert result is False

    def test_empty_signature(self) -> None:
        """Test that empty signature fails validation."""
        result = validate_twilio_signature("", "https://example.com", {}, "token")
        assert result is False

    def test_empty_auth_token(self) -> None:
        """Test that empty auth token fails validation."""
        result = validate_twilio_signature("signature", "https://example.com", {}, "")
        assert result is False

    def test_none_signature(self) -> None:
        """Test that None signature fails validation."""
        result = validate_twilio_signature(None, "https://example.com", {}, "token")  # type: ignore[arg-type]
        assert result is False

    def test_none_auth_token(self) -> None:
        """Test that None auth token fails validation."""
        result = validate_twilio_signature("sig", "https://example.com", {}, None)  # type: ignore[arg-type]
        assert result is False

    def test_params_sorted_correctly(self) -> None:
        """Test that params are sorted alphabetically for signature."""
        auth_token = "token123"
        url = "https://test.com/webhook"

        # Params in unsorted order
        params = {"Zebra": "last", "Apple": "first", "Middle": "mid"}

        # Calculate signature with sorted params
        sorted_params = sorted(params.items())  # Apple, Middle, Zebra
        data = url + "".join(f"{k}{v}" for k, v in sorted_params)
        expected_sig = base64.b64encode(
            hmac.new(
                auth_token.encode("utf-8"),
                data.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("utf-8")

        result = validate_twilio_signature(expected_sig, url, params, auth_token)
        assert result is True

    def test_empty_params(self) -> None:
        """Test validation with empty params."""
        auth_token = "token123"
        url = "https://test.com/webhook"

        # With empty params, signature is just HMAC of URL
        expected_sig = base64.b64encode(
            hmac.new(
                auth_token.encode("utf-8"),
                url.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("utf-8")

        result = validate_twilio_signature(expected_sig, url, {}, auth_token)
        assert result is True

    def test_timing_safe_comparison(self) -> None:
        """Test that signature comparison is timing-safe (uses hmac.compare_digest)."""
        # This is mostly a documentation test - the actual implementation
        # uses hmac.compare_digest which is timing-safe
        auth_token = "token"
        url = "https://test.com"

        data = url
        correct_sig = base64.b64encode(
            hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()
        ).decode()

        # Test passes with correct signature
        assert validate_twilio_signature(correct_sig, url, {}, auth_token) is True

        # Test fails with almost-correct signature (one char different)
        wrong_sig = correct_sig[:-1] + ("A" if correct_sig[-1] != "A" else "B")
        assert validate_twilio_signature(wrong_sig, url, {}, auth_token) is False


class TestValidateTelnyxSignature:
    """Tests for validate_telnyx_signature function."""

    def test_missing_signature_returns_false(self) -> None:
        """Test that missing signature returns False."""
        result = validate_telnyx_signature("", "1234567890", b"payload")
        assert result is False

    def test_missing_timestamp_returns_false(self) -> None:
        """Test that missing timestamp returns False."""
        result = validate_telnyx_signature("signature", "", b"payload")
        assert result is False

    def test_no_public_key_in_production(self) -> None:
        """Test behavior when no public key is configured in production."""
        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TELNYX_PUBLIC_KEY = None
            mock_settings.DEBUG = False

            result = validate_telnyx_signature("sig", "12345", b"payload")
            assert result is False

    def test_no_public_key_in_debug_mode(self) -> None:
        """Test that missing public key returns True in debug mode."""
        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TELNYX_PUBLIC_KEY = None
            mock_settings.DEBUG = True

            result = validate_telnyx_signature("sig", "12345", b"payload")
            assert result is True

    def test_invalid_public_key_returns_false(self) -> None:
        """Test that invalid public key format returns False."""
        # Invalid base64
        result = validate_telnyx_signature(
            "signature",
            "1234567890",
            b"payload",
            public_key="not-valid-base64!!!",
        )
        assert result is False

    def test_invalid_signature_returns_false(self) -> None:
        """Test that invalid signature returns False even with valid key format."""
        # Create a valid-looking but wrong key (32 bytes for ed25519)
        fake_key = base64.b64encode(b"\x00" * 32).decode()

        result = validate_telnyx_signature(
            "invalid-signature",
            "1234567890",
            b'{"data": "test"}',
            public_key=fake_key,
        )
        assert result is False


class TestVerifyTwilioWebhook:
    """Tests for verify_twilio_webhook async function."""

    @pytest.mark.asyncio
    async def test_missing_auth_token_debug_mode(self) -> None:
        """Test that missing auth token returns True in debug mode."""
        mock_request = AsyncMock()

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = None
            mock_settings.DEBUG = True

            result = await verify_twilio_webhook(mock_request)
            assert result is True

    @pytest.mark.asyncio
    async def test_missing_auth_token_production_raises(self) -> None:
        """Test that missing auth token raises HTTPException in production."""
        mock_request = AsyncMock()

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = None
            mock_settings.DEBUG = False

            with pytest.raises(HTTPException) as exc_info:
                await verify_twilio_webhook(mock_request)

            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_missing_signature_header_debug_mode(self) -> None:
        """Test that missing signature header returns True in debug mode."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = "token"
            mock_settings.DEBUG = True

            result = await verify_twilio_webhook(mock_request)
            assert result is True

    @pytest.mark.asyncio
    async def test_missing_signature_header_production_raises(self) -> None:
        """Test that missing signature header raises HTTPException in production."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = "token"
            mock_settings.DEBUG = False

            with pytest.raises(HTTPException) as exc_info:
                await verify_twilio_webhook(mock_request)

            assert exc_info.value.status_code == 403
            assert "Missing Twilio signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_signature_raises(self) -> None:
        """Test that invalid signature raises HTTPException."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "invalid-signature"
        mock_request.url = "https://example.com/webhook"

        # Mock form data - form itself is a dict-like that .items() works on
        mock_form = MagicMock()
        mock_form.items.return_value = [("Key", "Value")]
        mock_request.form = AsyncMock(return_value=mock_form)

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = "token"
            mock_settings.DEBUG = False

            with pytest.raises(HTTPException) as exc_info:
                await verify_twilio_webhook(mock_request)

            assert exc_info.value.status_code == 403
            assert "Invalid Twilio signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_signature_returns_true(self) -> None:
        """Test that valid signature returns True."""
        auth_token = "test-token"
        url = "https://example.com/webhook"
        params = {"From": "+1234567890"}

        # Calculate valid signature
        sorted_params = sorted(params.items())
        data = url + "".join(f"{k}{v}" for k, v in sorted_params)
        valid_sig = base64.b64encode(
            hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()
        ).decode()

        mock_request = MagicMock()
        mock_request.headers.get.return_value = valid_sig
        mock_request.url = url

        # Mock form data - form itself is a dict-like that .items() works on
        mock_form = MagicMock()
        mock_form.items.return_value = list(params.items())
        mock_request.form = AsyncMock(return_value=mock_form)

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = auth_token
            mock_settings.DEBUG = False

            result = await verify_twilio_webhook(mock_request)
            assert result is True


class TestVerifyTelnyxWebhook:
    """Tests for verify_telnyx_webhook async function."""

    @pytest.mark.asyncio
    async def test_missing_signature_debug_mode(self) -> None:
        """Test that missing signature returns True in debug mode."""
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda x, default="": ""

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.DEBUG = True

            result = await verify_telnyx_webhook(mock_request)
            assert result is True

    @pytest.mark.asyncio
    async def test_missing_signature_production_raises(self) -> None:
        """Test that missing signature raises HTTPException in production."""
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda x, default="": ""

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.DEBUG = False

            with pytest.raises(HTTPException) as exc_info:
                await verify_telnyx_webhook(mock_request)

            assert exc_info.value.status_code == 403
            assert "Missing Telnyx signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_timestamp_raises(self) -> None:
        """Test that missing timestamp raises HTTPException."""
        mock_request = MagicMock()

        def header_get(name: str, default: str = "") -> str:
            if name == "telnyx-signature-ed25519":
                return "some-signature"
            return default

        mock_request.headers.get.side_effect = header_get

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.DEBUG = False

            with pytest.raises(HTTPException) as exc_info:
                await verify_telnyx_webhook(mock_request)

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_signature_raises(self) -> None:
        """Test that invalid signature raises HTTPException."""
        mock_request = MagicMock()

        def header_get(name: str, default: str = "") -> str:
            headers = {
                "telnyx-signature-ed25519": "invalid-signature",
                "telnyx-timestamp": "1234567890",
            }
            return headers.get(name, default)

        mock_request.headers.get.side_effect = header_get
        mock_request.body = AsyncMock(return_value=b'{"data": "test"}')

        with patch("app.core.webhook_security.settings") as mock_settings:
            mock_settings.DEBUG = False
            mock_settings.TELNYX_PUBLIC_KEY = base64.b64encode(b"\x00" * 32).decode()

            with pytest.raises(HTTPException) as exc_info:
                await verify_telnyx_webhook(mock_request)

            assert exc_info.value.status_code == 403
            assert "Invalid Telnyx signature" in exc_info.value.detail


class TestWebhookSecurityIntegration:
    """Integration tests for webhook security."""

    def test_twilio_real_world_like_scenario(self) -> None:
        """Test Twilio validation with realistic webhook data."""
        auth_token = "your_auth_token_here"
        url = "https://your-app.com/api/v1/webhooks/twilio/voice"
        params = {
            "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "ApiVersion": "2010-04-01",
            "CallSid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "CallStatus": "ringing",
            "Called": "+15551234567",
            "Caller": "+15559876543",
            "Direction": "inbound",
            "From": "+15559876543",
            "To": "+15551234567",
        }

        # Generate signature
        sorted_params = sorted(params.items())
        data = url + "".join(f"{k}{v}" for k, v in sorted_params)
        signature = base64.b64encode(
            hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()
        ).decode()

        # Validate
        result = validate_twilio_signature(signature, url, params, auth_token)
        assert result is True

        # Tamper with one param - should fail
        params["CallStatus"] = "completed"
        result = validate_twilio_signature(signature, url, params, auth_token)
        assert result is False

    def test_twilio_signature_changes_with_url(self) -> None:
        """Test that different URLs produce different signatures."""
        auth_token = "token"
        params = {"Key": "Value"}

        url1 = "https://app1.com/webhook"
        url2 = "https://app2.com/webhook"

        # Generate signatures for different URLs
        sig1_data = url1 + "KeyValue"
        sig1 = base64.b64encode(
            hmac.new(auth_token.encode(), sig1_data.encode(), hashlib.sha1).digest()
        ).decode()

        sig2_data = url2 + "KeyValue"
        sig2 = base64.b64encode(
            hmac.new(auth_token.encode(), sig2_data.encode(), hashlib.sha1).digest()
        ).decode()

        # Signatures should be different
        assert sig1 != sig2

        # Each signature should validate only for its URL
        assert validate_twilio_signature(sig1, url1, params, auth_token) is True
        assert validate_twilio_signature(sig1, url2, params, auth_token) is False
        assert validate_twilio_signature(sig2, url2, params, auth_token) is True
        assert validate_twilio_signature(sig2, url1, params, auth_token) is False
