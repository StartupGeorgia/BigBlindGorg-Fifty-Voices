"""Tests for circuit breaker pattern in app/services/circuit_breaker.py."""

import asyncio
import time
from typing import Any

import pytest

from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
)


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_closed_state(self) -> None:
        """Test CLOSED state represents normal operation."""
        assert CircuitState.CLOSED.value == "closed"

    def test_open_state(self) -> None:
        """Test OPEN state represents failing state."""
        assert CircuitState.OPEN.value == "open"

    def test_half_open_state(self) -> None:
        """Test HALF_OPEN state represents recovery testing."""
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerInitialization:
    """Tests for CircuitBreaker initialization."""

    def test_default_initialization(self) -> None:
        """Test circuit breaker initializes with default values."""
        cb = CircuitBreaker(name="test")

        assert cb.name == "test"
        assert cb.failure_threshold == 5
        assert cb.timeout == 60.0
        assert cb.recovery_timeout == 30.0
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    def test_custom_initialization(self) -> None:
        """Test circuit breaker with custom values."""
        cb = CircuitBreaker(
            name="custom",
            failure_threshold=3,
            timeout=30.0,
            recovery_timeout=15.0,
        )

        assert cb.name == "custom"
        assert cb.failure_threshold == 3
        assert cb.timeout == 30.0
        assert cb.recovery_timeout == 15.0


class TestCircuitBreakerClosedState:
    """Tests for circuit breaker in CLOSED state."""

    @pytest.mark.asyncio
    async def test_successful_call_returns_result(self) -> None:
        """Test that successful calls return the function result."""
        cb = CircuitBreaker(name="test")

        async def success_func() -> str:
            return "success"

        result = await cb.call(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_successful_call_resets_failure_count(self) -> None:
        """Test that successful calls reset the failure counter."""
        cb = CircuitBreaker(name="test", failure_threshold=5)
        cb.failure_count = 3  # Simulate some failures

        async def success_func() -> str:
            return "success"

        await cb.call(success_func)

        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    @pytest.mark.asyncio
    async def test_function_args_passed_correctly(self) -> None:
        """Test that function arguments are passed correctly."""
        cb = CircuitBreaker(name="test")

        async def add_func(a: int, b: int, c: int = 0) -> int:
            return a + b + c

        result = await cb.call(add_func, 1, 2, c=3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_failure_increments_counter(self) -> None:
        """Test that failures increment the failure counter."""
        cb = CircuitBreaker(name="test", failure_threshold=5)

        async def fail_func() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await cb.call(fail_func)

        assert cb.failure_count == 1
        assert cb.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_failure_preserves_exception(self) -> None:
        """Test that the original exception is re-raised."""
        cb = CircuitBreaker(name="test")

        class CustomError(Exception):
            pass

        async def fail_func() -> None:
            raise CustomError("custom error message")

        with pytest.raises(CustomError) as exc_info:
            await cb.call(fail_func)

        assert str(exc_info.value) == "custom error message"


class TestCircuitBreakerTripping:
    """Tests for circuit breaker opening (tripping)."""

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self) -> None:
        """Test that circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(name="test", failure_threshold=3)

        async def fail_func() -> None:
            raise RuntimeError("error")

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_opens_exactly_at_threshold(self) -> None:
        """Test circuit opens exactly at threshold, not before."""
        cb = CircuitBreaker(name="test", failure_threshold=3)

        async def fail_func() -> None:
            raise RuntimeError("error")

        # First two failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail_func)
            assert cb.state == CircuitState.CLOSED

        # Third failure triggers opening
        with pytest.raises(RuntimeError):
            await cb.call(fail_func)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_successful_call_between_failures_resets_count(self) -> None:
        """Test that a successful call resets the failure count."""
        cb = CircuitBreaker(name="test", failure_threshold=3)

        async def fail_func() -> None:
            raise RuntimeError("error")

        async def success_func() -> str:
            return "ok"

        # Two failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail_func)

        assert cb.failure_count == 2

        # One success resets
        await cb.call(success_func)
        assert cb.failure_count == 0

        # Two more failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail_func)

        # Still closed because we reset
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerOpenState:
    """Tests for circuit breaker in OPEN state."""

    @pytest.mark.asyncio
    async def test_rejects_calls_immediately(self) -> None:
        """Test that open circuit rejects calls with CircuitBreakerError."""
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout=60.0)

        async def fail_func() -> None:
            raise RuntimeError("error")

        # Trip the circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        # Next call should be rejected
        async def any_func() -> str:
            return "should not reach"

        with pytest.raises(CircuitBreakerError) as exc_info:
            await cb.call(any_func)

        assert "OPEN" in str(exc_info.value)
        assert "test" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_message_contains_circuit_name(self) -> None:
        """Test that error message contains the circuit breaker name."""
        cb = CircuitBreaker(name="external-api", failure_threshold=1)

        async def fail_func() -> None:
            raise RuntimeError("error")

        with pytest.raises(RuntimeError):
            await cb.call(fail_func)

        with pytest.raises(CircuitBreakerError) as exc_info:
            await cb.call(fail_func)

        assert "external-api" in str(exc_info.value)


class TestCircuitBreakerRecovery:
    """Tests for circuit breaker recovery (HALF_OPEN state)."""

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self) -> None:
        """Test that circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout=0.1)

        async def fail_func() -> None:
            raise RuntimeError("error")

        async def success_func() -> str:
            return "recovered"

        # Trip the circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Next call should transition to HALF_OPEN and succeed
        result = await cb.call(success_func)

        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED  # Success in HALF_OPEN closes circuit

    @pytest.mark.asyncio
    async def test_successful_half_open_call_closes_circuit(self) -> None:
        """Test that successful call in HALF_OPEN state closes the circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout=0.05)

        async def fail_func() -> None:
            raise RuntimeError("error")

        async def success_func() -> str:
            return "success"

        # Trip the circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail_func)

        await asyncio.sleep(0.1)  # Wait for timeout

        # Successful call should close the circuit
        await cb.call(success_func)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_failed_half_open_call_reopens_circuit(self) -> None:
        """Test that failed call in HALF_OPEN state reopens the circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=1, timeout=0.05)

        async def fail_func() -> None:
            raise RuntimeError("error")

        # Trip the circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail_func)

        await asyncio.sleep(0.1)  # Wait for timeout

        # Failed call should reopen circuit
        with pytest.raises(RuntimeError):
            await cb.call(fail_func)

        # Circuit should be open again (went HALF_OPEN then back to OPEN)
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerReset:
    """Tests for manual circuit breaker reset."""

    def test_reset_from_closed(self) -> None:
        """Test resetting from CLOSED state."""
        cb = CircuitBreaker(name="test")
        cb.failure_count = 3

        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    def test_reset_from_open(self) -> None:
        """Test resetting from OPEN state."""
        cb = CircuitBreaker(name="test")
        cb.state = CircuitState.OPEN
        cb.failure_count = 5
        cb.last_failure_time = time.time()

        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None

    def test_reset_from_half_open(self) -> None:
        """Test resetting from HALF_OPEN state."""
        cb = CircuitBreaker(name="test")
        cb.state = CircuitState.HALF_OPEN
        cb.failure_count = 3

        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


class TestCircuitBreakerGetState:
    """Tests for get_state method."""

    def test_get_state_returns_dict(self) -> None:
        """Test that get_state returns a dictionary with all info."""
        cb = CircuitBreaker(name="api-service", failure_threshold=5)

        state = cb.get_state()

        assert isinstance(state, dict)
        assert state["name"] == "api-service"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["failure_threshold"] == 5
        assert state["last_failure_time"] is None

    def test_get_state_after_failures(self) -> None:
        """Test get_state reflects failure information."""
        cb = CircuitBreaker(name="test", failure_threshold=3)
        cb.failure_count = 2
        cb.last_failure_time = 1234567890.0

        state = cb.get_state()

        assert state["failure_count"] == 2
        assert state["last_failure_time"] == 1234567890.0

    def test_get_state_when_open(self) -> None:
        """Test get_state when circuit is open."""
        cb = CircuitBreaker(name="test")
        cb.state = CircuitState.OPEN
        cb.failure_count = 5

        state = cb.get_state()

        assert state["state"] == "open"
        assert state["failure_count"] == 5


class TestCircuitBreakerShouldAttemptRecovery:
    """Tests for _should_attempt_recovery internal method."""

    def test_returns_true_when_no_last_failure(self) -> None:
        """Test that recovery is attempted when no failure recorded."""
        cb = CircuitBreaker(name="test", timeout=60.0)
        cb.last_failure_time = None

        assert cb._should_attempt_recovery() is True

    def test_returns_false_when_recently_failed(self) -> None:
        """Test that recovery is not attempted immediately after failure."""
        cb = CircuitBreaker(name="test", timeout=60.0)
        cb.last_failure_time = time.time()  # Just now

        assert cb._should_attempt_recovery() is False

    def test_returns_true_after_timeout(self) -> None:
        """Test that recovery is attempted after timeout period."""
        cb = CircuitBreaker(name="test", timeout=0.1)
        cb.last_failure_time = time.time() - 0.2  # 0.2 seconds ago

        assert cb._should_attempt_recovery() is True


class TestCircuitBreakerConcurrency:
    """Tests for circuit breaker concurrent access."""

    @pytest.mark.asyncio
    async def test_concurrent_calls_handled_correctly(self) -> None:
        """Test that concurrent calls are handled thread-safely."""
        cb = CircuitBreaker(name="test", failure_threshold=10)
        call_count = 0

        async def success_func() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate some work
            return "success"

        # Make 20 concurrent calls
        tasks = [cb.call(success_func) for _ in range(20)]
        results = await asyncio.gather(*tasks)

        assert all(r == "success" for r in results)
        assert call_count == 20
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_failures_trip_circuit_once(self) -> None:
        """Test that concurrent failures don't trip circuit multiple times."""
        cb = CircuitBreaker(name="test", failure_threshold=3)
        fail_count = 0

        async def fail_func() -> None:
            nonlocal fail_count
            fail_count += 1
            await asyncio.sleep(0.01)
            raise RuntimeError("error")

        # Make 10 concurrent failing calls
        tasks = [cb.call(fail_func) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should have raised errors
        assert all(isinstance(r, (RuntimeError, CircuitBreakerError)) for r in results)

        # Circuit should be open
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Test complete circuit breaker lifecycle."""
        cb = CircuitBreaker(name="test", failure_threshold=2, timeout=0.1)
        call_log: list[str] = []

        async def flaky_service(should_fail: bool) -> str:
            if should_fail:
                call_log.append("fail")
                raise RuntimeError("service error")
            call_log.append("success")
            return "ok"

        # Phase 1: Normal operation
        result = await cb.call(flaky_service, False)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

        # Phase 2: Service starts failing
        with pytest.raises(RuntimeError):
            await cb.call(flaky_service, True)
        with pytest.raises(RuntimeError):
            await cb.call(flaky_service, True)

        # Phase 3: Circuit is now open
        assert cb.state == CircuitState.OPEN

        # Phase 4: Calls rejected while open
        with pytest.raises(CircuitBreakerError):
            await cb.call(flaky_service, False)

        # Phase 5: Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Phase 6: Service recovers - circuit closes
        result = await cb.call(flaky_service, False)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

        # Verify call sequence
        assert call_log == ["success", "fail", "fail", "success"]

    @pytest.mark.asyncio
    async def test_with_real_world_scenario(self) -> None:
        """Test circuit breaker with realistic API call simulation."""
        cb = CircuitBreaker(name="external-api", failure_threshold=3, timeout=0.2)

        api_available = True
        request_count = 0

        async def call_external_api(endpoint: str) -> dict[str, Any]:
            nonlocal request_count
            request_count += 1

            if not api_available:
                raise ConnectionError("API unavailable")

            return {"endpoint": endpoint, "status": "ok"}

        # Normal operation
        for i in range(5):
            result = await cb.call(call_external_api, f"/endpoint/{i}")
            assert result["status"] == "ok"

        assert request_count == 5
        assert cb.state == CircuitState.CLOSED

        # API goes down
        api_available = False

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cb.call(call_external_api, "/data")

        assert cb.state == CircuitState.OPEN
        assert request_count == 8  # 5 + 3

        # Calls are blocked
        for _ in range(10):
            with pytest.raises(CircuitBreakerError):
                await cb.call(call_external_api, "/blocked")

        assert request_count == 8  # No additional requests made

        # API recovers
        api_available = True
        await asyncio.sleep(0.25)

        # Circuit allows recovery attempt
        result = await cb.call(call_external_api, "/recovery")
        assert result["status"] == "ok"
        assert cb.state == CircuitState.CLOSED
