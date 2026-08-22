"""Unit and integration tests for PostgreSQL and Redis database clients.

Tests mock active pool environments and verify input validation limits,
session isolation guardrails, and budget calculation outputs.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.db.postgres import PostgresClient
from app.db.redis import RedisClient


@pytest.mark.asyncio
async def test_postgres_client_initialization() -> None:
    """
    Verifies that the PostgresClient loads database credentials.

    Arguments:
        None

    Returns:
        None
    """
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
        postgres_client = PostgresClient()
        assert postgres_client.database_url == "postgresql://user:pass@host:5432/db"


@pytest.mark.asyncio
async def test_postgres_client_missing_url_raises_error() -> None:
    """
    Verifies that PostgresClient connection raises error if DATABASE_URL is missing.

    Arguments:
        None

    Returns:
        None
    """
    with patch.dict("os.environ", {}, clear=True):
        postgres_client = PostgresClient()
        postgres_client.database_url = None
        with pytest.raises(ValueError, match="DATABASE_URL environment variable is not defined."):
            await postgres_client.connect()


@pytest.mark.asyncio
async def test_postgres_client_enforces_session_id_on_add() -> None:
    """
    Verifies that add_session_memory raises ValueError for empty session_id.

    Arguments:
        None

    Returns:
        None
    """
    postgres_client = PostgresClient()
    postgres_client.database_url = "postgresql://mock:mock@localhost:5432/mock"
    postgres_client.pool = MagicMock()

    with pytest.raises(ValueError, match="session_id must be provided to add session memory."):
        await postgres_client.add_session_memory(
            session_id="  ",
            content="Mock content text",
            embedding=[0.1, 0.2, 0.3],
        )


@pytest.mark.asyncio
async def test_postgres_client_enforces_session_id_on_search() -> None:
    """
    Verifies that search_session_memory raises ValueError for empty session_id.

    Arguments:
        None

    Returns:
        None
    """
    postgres_client = PostgresClient()
    postgres_client.database_url = "postgresql://mock:mock@localhost:5432/mock"
    postgres_client.pool = MagicMock()

    with pytest.raises(ValueError, match="session_id must be provided to search session memory."):
        await postgres_client.search_session_memory(
            session_id="",
            query_embedding=[0.1, 0.2, 0.3],
        )


@pytest.mark.asyncio
async def test_redis_client_initialization() -> None:
    """
    Verifies that the RedisClient loads connection credentials.

    Arguments:
        None

    Returns:
        None
    """
    with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379/0"}):
        redis_client = RedisClient()
        assert redis_client.redis_url == "redis://localhost:6379/0"


@pytest.mark.asyncio
async def test_redis_client_missing_url_raises_error() -> None:
    """
    Verifies that RedisClient connection raises error if REDIS_URL is missing.

    Arguments:
        None

    Returns:
        None
    """
    with patch.dict("os.environ", {}, clear=True):
        redis_client = RedisClient()
        redis_client.redis_url = None
        with pytest.raises(ValueError, match="REDIS_URL environment variable is not defined."):
            await redis_client.connect()


@pytest.mark.asyncio
async def test_redis_client_increment_global_spend() -> None:
    """
    Verifies that increment_global_spend interacts with Redis and converts values.

    Arguments:
        None

    Returns:
        None
    """
    redis_client = RedisClient()
    redis_client.redis_url = "redis://mock"
    redis_client.client = AsyncMock()
    
    # Mock redis incrbyfloat response
    redis_client.client.incrbyfloat.return_value = "0.75"

    updated_spend_total = await redis_client.increment_global_spend(0.15)
    
    assert updated_spend_total == 0.75
    redis_client.client.incrbyfloat.assert_called_once()
    redis_client.client.expire.assert_called_once()


@pytest.mark.asyncio
async def test_redis_client_check_ip_rate_limit() -> None:
    """
    Verifies that check_ip_rate_limit correctly flags limit overruns.

    Arguments:
        None

    Returns:
        None
    """
    redis_client = RedisClient()
    redis_client.redis_url = "redis://mock"
    redis_client.client = AsyncMock()

    # First request: total is 1 (allowed)
    redis_client.client.incr.return_value = 1
    allowed = await redis_client.check_ip_rate_limit("127.0.0.1", max_allowed_runs=3)
    assert allowed is True
    redis_client.client.expire.assert_called_once()

    # Fourth request: total is 4 (exceeded)
    redis_client.client.incr.return_value = 4
    allowed = await redis_client.check_ip_rate_limit("127.0.0.1", max_allowed_runs=3)
    assert allowed is False


@pytest.mark.asyncio
async def test_postgres_client_cross_project_memory_mock() -> None:
    """
    Verifies that search_session_memory retrieves facts across projects sharing a company_id.
    """
    postgres_client = PostgresClient()
    postgres_client.is_mock = True
    
    postgres_client.mock_store["projects"] = {
        "proj_1": {"id": "proj_1", "company_id": "comp_1"},
        "proj_2": {"id": "proj_2", "company_id": "comp_1"},
        "proj_3": {"id": "proj_3", "company_id": "other_comp"}
    }
    
    postgres_client.mock_store["session_memory"] = [
        {"id": 1, "project_id": "proj_1", "content": "Company is in Seattle", "embedding": [0.1], "metadata": {}},
        {"id": 2, "project_id": "proj_3", "content": "Other company fact", "embedding": [0.2], "metadata": {}}
    ]
    
    # Search from proj_2 should retrieve proj_1's memory because of shared comp_1
    results = await postgres_client.search_session_memory(session_id="proj_2", query_embedding=[0.1])
    
    assert len(results) == 1
    assert results[0]["content"] == "Company is in Seattle"
