"""PostgreSQL database client with pgvector support.

This module implements the async database adapter for PostgreSQL, handling
connection pooling, table initialization, session state persistence, and
dual-namespace vector searches (global_knowledge and session_memory).
"""

import os
import json
from typing import Any, Dict, List, Optional
import asyncpg
from app.models.state import SessionState


class PostgresClient:
    """
    Database client for PostgreSQL supporting pgvector similarity operations.

    Enforces strict namespace isolation for session-specific RAG queries
    and provides unified connection pool lifecycle methods.
    """

    def __init__(self) -> None:
        """
        Initializes the database client and fetches connection details.

        Arguments:
            None

        Returns:
            None
        """
        # Fetch the database connection string from environment or global settings fallback
        import os
        from app.core.config import settings
        self.database_url: Optional[str] = os.environ.get("DATABASE_URL") or settings.database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """
        Establishes the database connection pool.

        Arguments:
            None

        Returns:
            None

        Raises:
            ValueError: If DATABASE_URL is not set in the environment.
        """
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is not defined.")

        if not self.pool:
            # Create connection pool using asyncpg
            self.pool = await asyncpg.create_pool(
                dsn=self.database_url,
                min_size=1,
                max_size=10,
            )

    async def disconnect(self) -> None:
        """
        Closes the database connection pool.

        Arguments:
            None

        Returns:
            None
        """
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def init_db(self, schema_filepath: str) -> None:
        """
        Loads schema definitions from SQL file and initializes tables.

        Arguments:
            schema_filepath: The local path to the schema.sql file.

        Returns:
            None
        """
        if not self.pool:
            await self.connect()

        assert self.pool is not None
        with open(schema_filepath, "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()

        async with self.pool.acquire() as connection:
            # Run schema SQL script to set up tables and vector extension
            await connection.execute(schema_sql)

    async def save_session_state(self, state: SessionState) -> None:
        """
        Saves or updates a serialized SessionState model inside the database.

        Arguments:
            state: The SessionState model instance to save.

        Returns:
            None
        """
        if not self.pool:
            await self.connect()

        assert self.pool is not None
        state_json_str = state.model_dump_json()

        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO session_state (session_id, state_data)
                VALUES ($1, $2)
                ON CONFLICT (session_id) DO UPDATE
                SET state_data = $2, updated_at = CURRENT_TIMESTAMP;
                """,
                state.session_id,
                state_json_str,
            )

    async def get_session_state(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieves and deserializes the SessionState model for a given ID.

        Arguments:
            session_id: Unique UUID string representing the target session.

        Returns:
            Optional[SessionState]: The parsed SessionState if found, else None.
        """
        if not self.pool:
            await self.connect()

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            state_data_str = await connection.fetchval(
                """
                SELECT state_data FROM session_state WHERE session_id = $1;
                """,
                session_id,
            )
            if not state_data_str:
                return None
            return SessionState.model_validate_json(state_data_str)

    async def add_global_knowledge(
        self, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Inserts new content and vector embedding into the global knowledge database.

        Arguments:
            content: Raw text content to store.
            embedding: Normalized list of floats representing the text vector.
            metadata: Optional dictionary containing extra attributes.

        Returns:
            int: The primary key ID of the inserted record.
        """
        if not self.pool:
            await self.connect()

        assert self.pool is not None
        metadata_json = json.dumps(metadata) if metadata else None
        
        async with self.pool.acquire() as connection:
            record_id: int = await connection.fetchval(
                """
                INSERT INTO global_knowledge (content, embedding, metadata)
                VALUES ($1, $2, $3)
                RETURNING id;
                """,
                content,
                embedding,
                metadata_json,
            )
            return record_id

    async def search_global_knowledge(
        self, query_embedding: List[float], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search (cosine distance) on global knowledge.

        Arguments:
            query_embedding: Target vector for similarity lookup.
            limit: Maximum count of results to return.

        Returns:
            List[Dict[str, Any]]: List of matching records.
        """
        if not self.pool:
            await self.connect()

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            records = await connection.fetch(
                """
                SELECT id, content, metadata, (embedding <=> $1) as distance
                FROM global_knowledge
                ORDER BY distance ASC
                LIMIT $2;
                """,
                query_embedding,
                limit,
            )
            return [
                {
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "distance": float(row["distance"]),
                }
                for row in records
            ]

    async def add_session_memory(
        self, session_id: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Inserts new content and vector embedding isolated by a session ID.

        Arguments:
            session_id: Target session identifier to partition content.
            content: Raw text content to store.
            embedding: Normalized list of floats representing the text vector.
            metadata: Optional dictionary containing extra attributes.

        Returns:
            int: The primary key ID of the inserted record.

        Raises:
            ValueError: If session_id is empty or missing.
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id must be provided to add session memory.")

        if not self.pool:
            await self.connect()

        assert self.pool is not None
        metadata_json = json.dumps(metadata) if metadata else None

        async with self.pool.acquire() as connection:
            record_id: int = await connection.fetchval(
                """
                INSERT INTO session_memory (session_id, content, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id;
                """,
                session_id,
                content,
                embedding,
                metadata_json,
            )
            return record_id

    async def search_session_memory(
        self, session_id: str, query_embedding: List[float], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search strictly isolated to a session ID.

        Arguments:
            session_id: Target session identifier to filter searches.
            query_embedding: Target vector for similarity lookup.
            limit: Maximum count of results to return.

        Returns:
            List[Dict[str, Any]]: List of matching records isolated to the session.

        Raises:
            ValueError: If session_id is empty or missing.
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id must be provided to search session memory.")

        if not self.pool:
            await self.connect()

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            # Enforce strict session namespace isolation filtering on session_id
            records = await connection.fetch(
                """
                SELECT id, content, metadata, (embedding <=> $1) as distance
                FROM session_memory
                WHERE session_id = $2
                ORDER BY distance ASC
                LIMIT $3;
                """,
                query_embedding,
                session_id,
                limit,
            )
            return [
                {
                    "id": row["id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "distance": float(row["distance"]),
                }
                for row in records
            ]


# Instantiate global PostgresClient instance
postgres_client = PostgresClient()
