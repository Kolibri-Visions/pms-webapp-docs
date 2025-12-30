"""
Circuit Breaker Implementation
==============================

Redis-backed distributed circuit breaker for the Channel Manager.
Protects against cascading failures when external channel APIs are unavailable.

States:
- CLOSED: Normal operation, requests go through
- OPEN: Failing, all requests rejected immediately
- HALF_OPEN: Testing recovery, limited requests allowed

Features:
- Distributed state storage in Redis
- Per-channel circuit breakers
- Configurable thresholds
- Automatic recovery
- Metrics integration
"""

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

import redis.asyncio as aioredis
import structlog
from prometheus_client import Counter, Gauge

from .config import settings

logger = structlog.get_logger(__name__)

# Type variable for generic return types
T = TypeVar('T')


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

CIRCUIT_STATE = Gauge(
    "channel_circuit_breaker_state",
    "Current circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["channel_type"]
)

CIRCUIT_TRANSITIONS = Counter(
    "channel_circuit_breaker_transitions_total",
    "Circuit breaker state transitions",
    ["channel_type", "from_state", "to_state"]
)

CIRCUIT_REJECTIONS = Counter(
    "channel_circuit_breaker_rejections_total",
    "Requests rejected due to open circuit",
    ["channel_type"]
)

CIRCUIT_SUCCESSES = Counter(
    "channel_circuit_breaker_successes_total",
    "Successful requests through circuit",
    ["channel_type"]
)

CIRCUIT_FAILURES = Counter(
    "channel_circuit_breaker_failures_total",
    "Failed requests that impact circuit state",
    ["channel_type", "error_type"]
)


# =============================================================================
# CIRCUIT BREAKER CONFIGURATION
# =============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: int = 60  # Seconds in open state before half-open
    half_open_max_calls: int = 3  # Max calls in half-open state
    window_size: int = 60  # Failure counting window in seconds
    excluded_exceptions: tuple = ()  # Exceptions that don't count as failures


# Default configurations per channel
CIRCUIT_CONFIGS: Dict[str, CircuitBreakerConfig] = {
    "airbnb": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=60
    ),
    "booking_com": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=120  # Longer timeout for XML API
    ),
    "expedia": CircuitBreakerConfig(
        failure_threshold=10,  # Higher threshold due to higher rate limit
        success_threshold=3,
        timeout=60
    ),
    "fewo_direkt": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=60
    ),
    "google": CircuitBreakerConfig(
        failure_threshold=10,
        success_threshold=3,
        timeout=30  # Faster recovery
    ),
}


# =============================================================================
# EXCEPTIONS
# =============================================================================

class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, channel_type: str, retry_after: float):
        self.channel_type = channel_type
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker for {channel_type} is OPEN. "
            f"Retry after {retry_after:.2f}s"
        )


class CircuitBreakerHalfOpen(Exception):
    """Raised when circuit breaker is half-open and at max calls."""

    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        super().__init__(
            f"Circuit breaker for {channel_type} is HALF_OPEN and at max calls"
        )


# =============================================================================
# DISTRIBUTED CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """
    Distributed circuit breaker using Redis for state storage.

    State machine:
    ```
    CLOSED  --[failures >= threshold]--> OPEN
    OPEN    --[timeout elapsed]-------> HALF_OPEN
    HALF_OPEN --[success >= threshold]--> CLOSED
    HALF_OPEN --[failure]--------------> OPEN
    ```
    """

    def __init__(
        self,
        channel_type: str,
        config: CircuitBreakerConfig = None,
        redis_url: str = None,
        key_prefix: str = "circuit_breaker"
    ):
        """
        Initialize circuit breaker.

        Args:
            channel_type: The channel type (airbnb, booking_com, etc.)
            config: Circuit breaker configuration
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys
        """
        self.channel_type = channel_type
        self.config = config or CIRCUIT_CONFIGS.get(
            channel_type,
            CircuitBreakerConfig()
        )
        self.redis_url = redis_url or settings.REDIS_URL
        self.key_prefix = key_prefix
        self._redis: Optional[aioredis.Redis] = None

    async def get_redis(self) -> aioredis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()

    # =========================================================================
    # REDIS KEY HELPERS
    # =========================================================================

    def _state_key(self) -> str:
        return f"{self.key_prefix}:{self.channel_type}:state"

    def _failures_key(self) -> str:
        return f"{self.key_prefix}:{self.channel_type}:failures"

    def _successes_key(self) -> str:
        return f"{self.key_prefix}:{self.channel_type}:successes"

    def _opened_at_key(self) -> str:
        return f"{self.key_prefix}:{self.channel_type}:opened_at"

    def _half_open_calls_key(self) -> str:
        return f"{self.key_prefix}:{self.channel_type}:half_open_calls"

    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================

    async def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        redis = await self.get_redis()
        state_str = await redis.get(self._state_key())

        if state_str is None:
            return CircuitState.CLOSED

        state = CircuitState(state_str)

        # Check if we should transition from OPEN to HALF_OPEN
        if state == CircuitState.OPEN:
            opened_at = await redis.get(self._opened_at_key())
            if opened_at:
                elapsed = time.time() - float(opened_at)
                if elapsed >= self.config.timeout:
                    await self._transition_to(CircuitState.HALF_OPEN)
                    return CircuitState.HALF_OPEN

        return state

    async def _set_state(self, state: CircuitState) -> None:
        """Set circuit breaker state."""
        redis = await self.get_redis()
        old_state = await redis.get(self._state_key())

        await redis.set(self._state_key(), state.value)

        # Update metrics
        state_value = {"closed": 0, "open": 1, "half_open": 2}
        CIRCUIT_STATE.labels(channel_type=self.channel_type).set(
            state_value[state.value]
        )

        if old_state:
            CIRCUIT_TRANSITIONS.labels(
                channel_type=self.channel_type,
                from_state=old_state,
                to_state=state.value
            ).inc()

        logger.info(
            "Circuit breaker state changed",
            channel_type=self.channel_type,
            old_state=old_state,
            new_state=state.value
        )

    async def _transition_to(self, state: CircuitState) -> None:
        """Transition to a new state with appropriate cleanup."""
        redis = await self.get_redis()

        if state == CircuitState.CLOSED:
            # Reset all counters
            await redis.delete(
                self._failures_key(),
                self._successes_key(),
                self._opened_at_key(),
                self._half_open_calls_key()
            )

        elif state == CircuitState.OPEN:
            # Record when we opened
            await redis.set(self._opened_at_key(), time.time())
            await redis.delete(
                self._successes_key(),
                self._half_open_calls_key()
            )

        elif state == CircuitState.HALF_OPEN:
            # Reset success counter and half-open call count
            await redis.delete(self._successes_key())
            await redis.set(self._half_open_calls_key(), 0)

        await self._set_state(state)

    # =========================================================================
    # EXECUTION CONTROL
    # =========================================================================

    async def can_execute(self) -> bool:
        """
        Check if a request can be executed.

        Returns:
            True if request can proceed, False otherwise
        """
        state = await self.get_state()

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.OPEN:
            return False

        if state == CircuitState.HALF_OPEN:
            # Check if we're at max half-open calls
            redis = await self.get_redis()
            calls = int(await redis.get(self._half_open_calls_key()) or 0)
            if calls >= self.config.half_open_max_calls:
                return False

            # Increment half-open call count
            await redis.incr(self._half_open_calls_key())
            return True

        return False

    async def before_execute(self) -> None:
        """
        Check before executing a request.

        Raises:
            CircuitBreakerOpen: If circuit is open
            CircuitBreakerHalfOpen: If half-open and at max calls
        """
        state = await self.get_state()

        if state == CircuitState.OPEN:
            redis = await self.get_redis()
            opened_at = float(await redis.get(self._opened_at_key()) or 0)
            retry_after = self.config.timeout - (time.time() - opened_at)

            CIRCUIT_REJECTIONS.labels(channel_type=self.channel_type).inc()
            raise CircuitBreakerOpen(self.channel_type, max(0, retry_after))

        if state == CircuitState.HALF_OPEN:
            redis = await self.get_redis()
            calls = int(await redis.get(self._half_open_calls_key()) or 0)

            if calls >= self.config.half_open_max_calls:
                raise CircuitBreakerHalfOpen(self.channel_type)

            await redis.incr(self._half_open_calls_key())

    async def record_success(self) -> None:
        """Record a successful execution."""
        redis = await self.get_redis()
        state = await self.get_state()

        CIRCUIT_SUCCESSES.labels(channel_type=self.channel_type).inc()

        if state == CircuitState.HALF_OPEN:
            # Increment success counter
            successes = await redis.incr(self._successes_key())

            if successes >= self.config.success_threshold:
                # Enough successes, close the circuit
                await self._transition_to(CircuitState.CLOSED)
                logger.info(
                    "Circuit breaker closed after recovery",
                    channel_type=self.channel_type,
                    successes=successes
                )

    async def record_failure(self, error: Exception = None) -> None:
        """
        Record a failed execution.

        Args:
            error: The exception that caused the failure
        """
        # Check if this exception should be excluded
        if error and isinstance(error, self.config.excluded_exceptions):
            return

        redis = await self.get_redis()
        state = await self.get_state()

        error_type = type(error).__name__ if error else "unknown"
        CIRCUIT_FAILURES.labels(
            channel_type=self.channel_type,
            error_type=error_type
        ).inc()

        if state == CircuitState.CLOSED:
            # Add failure to sliding window
            now = time.time()
            window_start = now - self.config.window_size

            pipe = redis.pipeline()
            # Remove old failures
            pipe.zremrangebyscore(self._failures_key(), 0, window_start)
            # Add new failure
            pipe.zadd(self._failures_key(), {str(now): now})
            # Count failures in window
            pipe.zcard(self._failures_key())
            # Set TTL
            pipe.expire(self._failures_key(), self.config.window_size * 2)

            results = await pipe.execute()
            failure_count = results[2]

            if failure_count >= self.config.failure_threshold:
                # Too many failures, open the circuit
                await self._transition_to(CircuitState.OPEN)
                logger.warning(
                    "Circuit breaker opened due to failures",
                    channel_type=self.channel_type,
                    failures=failure_count
                )

        elif state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            await self._transition_to(CircuitState.OPEN)
            logger.warning(
                "Circuit breaker reopened after half-open failure",
                channel_type=self.channel_type
            )

    # =========================================================================
    # EXECUTION WRAPPER
    # =========================================================================

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of the function

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: If the function fails
        """
        await self.before_execute()

        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure(e)
            raise

    @asynccontextmanager
    async def context(self):
        """
        Context manager for circuit breaker protected code.

        Usage:
            async with circuit_breaker.context():
                await do_api_call()
        """
        await self.before_execute()
        try:
            yield
            await self.record_success()
        except Exception as e:
            await self.record_failure(e)
            raise

    # =========================================================================
    # ADMIN OPERATIONS
    # =========================================================================

    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        redis = await self.get_redis()
        await redis.delete(
            self._state_key(),
            self._failures_key(),
            self._successes_key(),
            self._opened_at_key(),
            self._half_open_calls_key()
        )

        CIRCUIT_STATE.labels(channel_type=self.channel_type).set(0)

        logger.info(
            "Circuit breaker reset",
            channel_type=self.channel_type
        )

    async def force_open(self, duration: int = None) -> None:
        """Force circuit breaker to open state."""
        await self._transition_to(CircuitState.OPEN)

        if duration:
            # Override the timeout
            redis = await self.get_redis()
            await redis.set(
                self._opened_at_key(),
                time.time() - self.config.timeout + duration
            )

    async def force_close(self) -> None:
        """Force circuit breaker to closed state."""
        await self._transition_to(CircuitState.CLOSED)

    async def get_status(self) -> Dict[str, Any]:
        """Get detailed circuit breaker status."""
        redis = await self.get_redis()
        state = await self.get_state()

        status = {
            "channel_type": self.channel_type,
            "state": state.value,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
                "window_size": self.config.window_size
            }
        }

        if state == CircuitState.CLOSED:
            # Get failure count
            failures = await redis.zcard(self._failures_key())
            status["failures_in_window"] = failures

        elif state == CircuitState.OPEN:
            opened_at = float(await redis.get(self._opened_at_key()) or 0)
            elapsed = time.time() - opened_at
            status["opened_at"] = opened_at
            status["elapsed_seconds"] = elapsed
            status["retry_after"] = max(0, self.config.timeout - elapsed)

        elif state == CircuitState.HALF_OPEN:
            successes = int(await redis.get(self._successes_key()) or 0)
            calls = int(await redis.get(self._half_open_calls_key()) or 0)
            status["successes"] = successes
            status["calls_in_half_open"] = calls
            status["remaining_calls"] = self.config.half_open_max_calls - calls

        return status


# =============================================================================
# CIRCUIT BREAKER MANAGER
# =============================================================================

class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(self, channel_type: str) -> CircuitBreaker:
        """Get or create circuit breaker for a channel."""
        if channel_type not in self._breakers:
            self._breakers[channel_type] = CircuitBreaker(
                channel_type=channel_type,
                redis_url=self.redis_url
            )
        return self._breakers[channel_type]

    async def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        statuses = {}
        for channel_type in CIRCUIT_CONFIGS.keys():
            breaker = self.get_breaker(channel_type)
            statuses[channel_type] = await breaker.get_status()
        return statuses

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for channel_type in CIRCUIT_CONFIGS.keys():
            breaker = self.get_breaker(channel_type)
            await breaker.reset()

    async def close_all(self) -> None:
        """Close all Redis connections."""
        for breaker in self._breakers.values():
            await breaker.close()


# =============================================================================
# DECORATOR
# =============================================================================

def circuit_breaker_protected(channel_type: str):
    """
    Decorator for circuit breaker protection.

    Usage:
        @circuit_breaker_protected("airbnb")
        async def call_airbnb_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = CircuitBreaker(channel_type=channel_type)

        async def wrapper(*args, **kwargs):
            return await breaker.execute(func, *args, **kwargs)

        return wrapper
    return decorator
