"""Redis cache database client for BuildSense.

This module implements the async Redis adapter, handling connection pooling,
IP rate-limiting checking, and global cumulative spend monitoring against budget caps.
"""

import os
from datetime import datetime, timezone
from typing import Optional
import redis.asyncio as aioredis


class RedisClient:
    """
    Cache client for Redis supporting rate-limiting and budget cap controls.

    Manages connection pools and provides atomic counters for tracking IP rates
    and daily global API spend constraints.
    """

    def __init__(self) -> None:
        """
        Initializes the Redis client and extracts settings from the environment.

        Arguments:
            None

        Returns:
            None
        """
        self.redis_url: Optional[str] = os.environ.get("REDIS_URL")
        self.client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """
        Initializes the async Redis connection client.

        Arguments:
            None

        Returns:
            None

        Raises:
            ValueError: If REDIS_URL environment variable is not defined.
        """
        if not self.redis_url:
            raise ValueError("REDIS_URL environment variable is not defined.")

        if not self.client:
            # Setup async Redis client with automatic connection pooling
            self.client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

    async def disconnect(self) -> None:
        """
        Closes the Redis connections and releases resources.

        Arguments:
            None

        Returns:
            None
        """
        if self.client:
            await self.client.close()
            self.client = None

    def _get_current_date_key(self) -> str:
        """
        Helper method to generate a date suffix for daily tracking keys.

        Arguments:
            None

        Returns:
            str: Date string in the format YYYY-MM-DD.
        """
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async def increment_global_spend(self, spend_amount_usd: float) -> float:
        """
        Increments the global cumulative daily spend and returns the new value.

        Arguments:
            spend_amount_usd: The cost in USD of the API execution step.

        Returns:
            float: The updated global spend in USD for today.
        """
        if not self.client:
            await self.connect()

        assert self.client is not None
        current_date_suffix = self._get_current_date_key()
        daily_spend_key = f"buildsense:global_spend:{current_date_suffix}"

        # Increment float value atomically
        updated_spend_str = await self.client.incrbyfloat(daily_spend_key, spend_amount_usd)
        
        # Set 36-hour expiry on new keys to ensure garbage collection
        await self.client.expire(daily_spend_key, 129600, nx=True)
        
        return float(updated_spend_str)

    async def get_global_spend(self) -> float:
        """
        Fetches the current global cumulative daily spend.

        Arguments:
            None

        Returns:
            float: Today's accumulated spend in USD.
        """
        if not self.client:
            await self.connect()

        assert self.client is not None
        current_date_suffix = self._get_current_date_key()
        daily_spend_key = f"buildsense:global_spend:{current_date_suffix}"

        spend_value = await self.client.get(daily_spend_key)
        return float(spend_value) if spend_value else 0.0

    async def has_exceeded_daily_spend_limit(self, max_daily_budget_usd: float = 10.00) -> bool:
        """
        Checks whether the global daily spend has exceeded the target budget cap.

        Arguments:
            max_daily_budget_usd: The global budget cap in USD.

        Returns:
            bool: True if spend limit has been exceeded, False otherwise.
        """
        current_spend = await self.get_global_spend()
        return current_spend >= max_daily_budget_usd

    async def check_ip_rate_limit(
        self, client_ip_address: str, max_allowed_runs: int = 3, time_window_seconds: int = 86400
    ) -> bool:
        """
        Increments and checks request counts for a specific IP.

        Arguments:
            client_ip_address: Target IP address of the incoming request.
            max_allowed_runs: Maximum runs allowed in the time window.
            time_window_seconds: Length of the rate-limiting window (default 24h).

        Returns:
            bool: True if request is allowed, False if limit has been exceeded.
        """
        if not self.client:
            await self.connect()

        assert self.client is not None
        current_date_suffix = self._get_current_date_key()
        ip_tracking_key = f"buildsense:rate_limit:{client_ip_address}:{current_date_suffix}"

        # Increment call count
        total_requests = await self.client.incr(ip_tracking_key)
        
        # Set key expiry on first creation
        if total_requests == 1:
            await self.client.expire(ip_tracking_key, time_window_seconds)

        return total_requests <= max_allowed_runs
