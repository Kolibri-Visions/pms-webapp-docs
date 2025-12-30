"""
Distributed Rate Limiter
========================

Redis-based distributed rate limiting for the Channel Manager.
Uses the sliding window algorithm to enforce per-platform rate limits.

Features:
- Platform-specific rate limits
- Per-connection rate tracking
- Sliding window for smooth rate limiting
- Metrics integration (Prometheus)
"""

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import redis.asyncio as aioredis
import structlog
from prometheus_client import Counter, Gauge, Histogram

from .config import settings

logger = structlog.get_logger(__name__)

# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

RATE_LIMIT_REQUESTS = Counter(
    "channel_rate_limit_requests_total",
    "Total rate limit check requests",
    ["channel_type", "result"]  # result: allowed, denied
)

RATE_LIMIT_CURRENT = Gauge(
    "channel_rate_limit_current_count",
    "Current request count in the sliding window",
    ["channel_type", "connection_id"]
)

RATE_LIMIT_WAIT_TIME = Histogram(
    "channel_rate_limit_wait_seconds",
    "Time spent waiting for rate limit",
    ["channel_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)


# =============================================================================
# RATE LIMIT CONFIGURATION
# =============================================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration for a channel."""
    max_requests: int
    window_seconds: int
    burst_limit: Optional[int] = None  # Optional burst allowance

    @property
    def requests_per_second(self) -> float:
        return self.max_requests / self.window_seconds


# Platform-specific rate limits
RATE_LIMITS: Dict[str, RateLimitConfig] = {
    "airbnb": RateLimitConfig(
        max_requests=10,
        window_seconds=1,
        burst_limit=15  # Allow small bursts
    ),
    "booking_com": RateLimitConfig(
        max_requests=20,
        window_seconds=60,  # 20 per minute (variable based on tier)
        burst_limit=30
    ),
    "expedia": RateLimitConfig(
        max_requests=50,
        window_seconds=1,
        burst_limit=75
    ),
    "fewo_direkt": RateLimitConfig(
        max_requests=30,
        window_seconds=1,
        burst_limit=45
    ),
    "google": RateLimitConfig(
        max_requests=100,
        window_seconds=1,
        burst_limit=150
    ),
}


# =============================================================================
# EXCEPTIONS
# =============================================================================

class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        channel_type: str,
        current_count: int,
        limit: int,
        retry_after: float
    ):
        self.channel_type = channel_type
        self.current_count = current_count
        self.limit = limit
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {channel_type}: "
            f"{current_count}/{limit} requests. Retry after {retry_after:.2f}s"
        )


# =============================================================================
# SLIDING WINDOW RATE LIMITER
# =============================================================================

class ChannelRateLimiter:
    """
    Distributed rate limiter using Redis sliding window algorithm.

    The sliding window algorithm:
    1. Maintains a sorted set of request timestamps
    2. Removes timestamps older than the window
    3. Counts remaining timestamps
    4. Allows request if count < limit

    This provides smooth rate limiting without the burst issues of
    fixed window algorithms.
    """

    def __init__(
        self,
        redis_url: str = None,
        key_prefix: str = "rate_limit"
    ):
        """
        Initialize the rate limiter.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for Redis keys
        """
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

    def _get_rate_limit_key(self, channel_type: str, connection_id: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"{self.key_prefix}:{channel_type}:{connection_id}"

    def _get_config(self, channel_type: str) -> RateLimitConfig:
        """Get rate limit configuration for a channel."""
        return RATE_LIMITS.get(
            channel_type,
            RateLimitConfig(max_requests=10, window_seconds=1)  # Default
        )

    async def acquire(
        self,
        channel_type: str,
        connection_id: str,
        weight: int = 1
    ) -> bool:
        """
        Try to acquire a rate limit slot.

        Args:
            channel_type: The channel type (airbnb, booking_com, etc.)
            connection_id: Unique connection identifier
            weight: Request weight (default 1, some operations may cost more)

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        config = self._get_config(channel_type)
        key = self._get_rate_limit_key(channel_type, connection_id)
        redis = await self.get_redis()

        now = time.time()
        window_start = now - config.window_seconds

        # Use Redis transaction for atomicity
        pipe = redis.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)

        # Count current entries
        pipe.zcard(key)

        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]

        # Check if we can proceed
        effective_limit = config.burst_limit or config.max_requests
        if current_count + weight > effective_limit:
            # Rate limit exceeded
            RATE_LIMIT_REQUESTS.labels(
                channel_type=channel_type,
                result="denied"
            ).inc()

            logger.warning(
                "Rate limit exceeded",
                channel_type=channel_type,
                connection_id=connection_id,
                current_count=current_count,
                limit=effective_limit
            )
            return False

        # Add current request (with weight)
        member = f"{now}:{weight}"
        await redis.zadd(key, {member: now})

        # Set TTL on the key (cleanup)
        await redis.expire(key, config.window_seconds * 2)

        # Update metrics
        RATE_LIMIT_REQUESTS.labels(
            channel_type=channel_type,
            result="allowed"
        ).inc()

        RATE_LIMIT_CURRENT.labels(
            channel_type=channel_type,
            connection_id=connection_id
        ).set(current_count + weight)

        return True

    async def acquire_or_raise(
        self,
        channel_type: str,
        connection_id: str,
        weight: int = 1
    ) -> None:
        """
        Acquire a rate limit slot or raise RateLimitExceeded.

        Args:
            channel_type: The channel type
            connection_id: Unique connection identifier
            weight: Request weight

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if not await self.acquire(channel_type, connection_id, weight):
            config = self._get_config(channel_type)
            current = await self.get_current_count(channel_type, connection_id)
            retry_after = await self.get_retry_after(channel_type, connection_id)

            raise RateLimitExceeded(
                channel_type=channel_type,
                current_count=current,
                limit=config.max_requests,
                retry_after=retry_after
            )

    async def acquire_with_wait(
        self,
        channel_type: str,
        connection_id: str,
        weight: int = 1,
        max_wait: float = 30.0
    ) -> bool:
        """
        Acquire a rate limit slot, waiting if necessary.

        Args:
            channel_type: The channel type
            connection_id: Unique connection identifier
            weight: Request weight
            max_wait: Maximum time to wait in seconds

        Returns:
            True if acquired, False if max_wait exceeded
        """
        start_time = time.time()

        while True:
            if await self.acquire(channel_type, connection_id, weight):
                wait_time = time.time() - start_time
                if wait_time > 0.01:  # Only record significant waits
                    RATE_LIMIT_WAIT_TIME.labels(
                        channel_type=channel_type
                    ).observe(wait_time)
                return True

            # Check if we've exceeded max wait time
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                logger.warning(
                    "Rate limit wait timeout",
                    channel_type=channel_type,
                    connection_id=connection_id,
                    elapsed=elapsed
                )
                return False

            # Calculate sleep time
            retry_after = await self.get_retry_after(channel_type, connection_id)
            sleep_time = min(retry_after, max_wait - elapsed, 1.0)

            await asyncio.sleep(sleep_time)

    async def get_current_count(
        self,
        channel_type: str,
        connection_id: str
    ) -> int:
        """Get current request count in the window."""
        config = self._get_config(channel_type)
        key = self._get_rate_limit_key(channel_type, connection_id)
        redis = await self.get_redis()

        now = time.time()
        window_start = now - config.window_seconds

        # Count requests in current window
        count = await redis.zcount(key, window_start, now)
        return count

    async def get_retry_after(
        self,
        channel_type: str,
        connection_id: str
    ) -> float:
        """
        Get the time to wait before retrying.

        Returns the time until the oldest request in the window expires.
        """
        config = self._get_config(channel_type)
        key = self._get_rate_limit_key(channel_type, connection_id)
        redis = await self.get_redis()

        # Get the oldest timestamp in the window
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if not oldest:
            return 0.0

        oldest_time = oldest[0][1]
        now = time.time()
        retry_after = (oldest_time + config.window_seconds) - now

        return max(0.0, retry_after)

    async def get_remaining(
        self,
        channel_type: str,
        connection_id: str
    ) -> int:
        """Get remaining requests allowed in the current window."""
        config = self._get_config(channel_type)
        current = await self.get_current_count(channel_type, connection_id)
        limit = config.burst_limit or config.max_requests
        return max(0, limit - current)

    async def reset(
        self,
        channel_type: str,
        connection_id: str
    ) -> None:
        """Reset rate limit for a connection (for testing/admin)."""
        key = self._get_rate_limit_key(channel_type, connection_id)
        redis = await self.get_redis()
        await redis.delete(key)

    @asynccontextmanager
    async def acquire_context(
        self,
        channel_type: str,
        connection_id: str,
        weight: int = 1
    ):
        """
        Context manager for rate limited operations.

        Usage:
            async with rate_limiter.acquire_context("airbnb", "conn123"):
                await do_api_call()
        """
        await self.acquire_or_raise(channel_type, connection_id, weight)
        try:
            yield
        finally:
            pass  # Could add cleanup logic here if needed


# =============================================================================
# TOKEN BUCKET RATE LIMITER (ALTERNATIVE)
# =============================================================================

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter as an alternative to sliding window.

    Token bucket algorithm:
    - Bucket fills with tokens at a fixed rate
    - Each request consumes one token
    - If bucket is empty, request is rejected
    - Allows bursts up to bucket capacity

    Better for APIs that allow occasional bursts.
    """

    def __init__(
        self,
        redis_url: str = None,
        key_prefix: str = "token_bucket"
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.key_prefix = key_prefix
        self._redis: Optional[aioredis.Redis] = None

    async def get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(self.redis_url)
        return self._redis

    async def acquire(
        self,
        channel_type: str,
        connection_id: str,
        tokens: int = 1
    ) -> bool:
        """
        Try to acquire tokens from the bucket.

        Uses a Lua script for atomic token bucket operations.
        """
        config = RATE_LIMITS.get(channel_type)
        if not config:
            return True

        key = f"{self.key_prefix}:{channel_type}:{connection_id}"
        redis = await self.get_redis()

        # Lua script for atomic token bucket
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])

        local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
        local current_tokens = tonumber(bucket[1]) or capacity
        local last_update = tonumber(bucket[2]) or now

        -- Calculate tokens to add since last update
        local elapsed = now - last_update
        local tokens_to_add = elapsed * refill_rate
        current_tokens = math.min(capacity, current_tokens + tokens_to_add)

        if current_tokens >= tokens_requested then
            current_tokens = current_tokens - tokens_requested
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', now)
            redis.call('EXPIRE', key, 3600)
            return 1
        else
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_update', now)
            redis.call('EXPIRE', key, 3600)
            return 0
        end
        """

        capacity = config.burst_limit or config.max_requests
        refill_rate = config.requests_per_second
        now = time.time()

        result = await redis.eval(
            lua_script,
            1,
            key,
            capacity,
            refill_rate,
            tokens,
            now
        )

        if result == 1:
            RATE_LIMIT_REQUESTS.labels(
                channel_type=channel_type,
                result="allowed"
            ).inc()
            return True
        else:
            RATE_LIMIT_REQUESTS.labels(
                channel_type=channel_type,
                result="denied"
            ).inc()
            return False


# =============================================================================
# ADAPTIVE RATE LIMITER
# =============================================================================

class AdaptiveRateLimiter(ChannelRateLimiter):
    """
    Adaptive rate limiter that adjusts limits based on API responses.

    Features:
    - Reduces rate on 429 responses
    - Gradually increases rate after successful requests
    - Respects Retry-After headers
    """

    async def record_success(
        self,
        channel_type: str,
        connection_id: str
    ) -> None:
        """Record a successful API call."""
        key = f"adaptive:{channel_type}:{connection_id}:success_count"
        redis = await self.get_redis()

        # Increment success counter
        count = await redis.incr(key)
        await redis.expire(key, 300)  # 5 minute window

        # After 100 successful requests, try increasing limit
        if count >= 100:
            await self._increase_limit(channel_type, connection_id)
            await redis.delete(key)

    async def record_rate_limit(
        self,
        channel_type: str,
        connection_id: str,
        retry_after: Optional[float] = None
    ) -> None:
        """Record a rate limit (429) response."""
        key = f"adaptive:{channel_type}:{connection_id}:rate_limit_count"
        redis = await self.get_redis()

        # Increment rate limit counter
        await redis.incr(key)
        await redis.expire(key, 300)

        # Immediately reduce limit
        await self._decrease_limit(channel_type, connection_id)

        # If retry_after provided, block until then
        if retry_after:
            block_key = f"adaptive:{channel_type}:{connection_id}:blocked_until"
            await redis.set(block_key, time.time() + retry_after, ex=int(retry_after) + 1)

    async def _increase_limit(
        self,
        channel_type: str,
        connection_id: str
    ) -> None:
        """Increase the effective rate limit."""
        key = f"adaptive:{channel_type}:{connection_id}:multiplier"
        redis = await self.get_redis()

        # Get current multiplier (default 1.0)
        multiplier = float(await redis.get(key) or 1.0)

        # Increase by 10%, max 1.5x
        new_multiplier = min(1.5, multiplier * 1.1)
        await redis.set(key, new_multiplier, ex=3600)

        logger.info(
            "Increased rate limit multiplier",
            channel_type=channel_type,
            connection_id=connection_id,
            multiplier=new_multiplier
        )

    async def _decrease_limit(
        self,
        channel_type: str,
        connection_id: str
    ) -> None:
        """Decrease the effective rate limit."""
        key = f"adaptive:{channel_type}:{connection_id}:multiplier"
        redis = await self.get_redis()

        # Get current multiplier
        multiplier = float(await redis.get(key) or 1.0)

        # Decrease by 25%, min 0.5x
        new_multiplier = max(0.5, multiplier * 0.75)
        await redis.set(key, new_multiplier, ex=3600)

        logger.warning(
            "Decreased rate limit multiplier",
            channel_type=channel_type,
            connection_id=connection_id,
            multiplier=new_multiplier
        )


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_rate_limiter(
    limiter_type: str = "sliding_window",
    redis_url: str = None
) -> ChannelRateLimiter:
    """
    Factory function to create rate limiters.

    Args:
        limiter_type: "sliding_window", "token_bucket", or "adaptive"
        redis_url: Redis connection URL

    Returns:
        Configured rate limiter instance
    """
    if limiter_type == "token_bucket":
        return TokenBucketRateLimiter(redis_url=redis_url)
    elif limiter_type == "adaptive":
        return AdaptiveRateLimiter(redis_url=redis_url)
    else:
        return ChannelRateLimiter(redis_url=redis_url)
