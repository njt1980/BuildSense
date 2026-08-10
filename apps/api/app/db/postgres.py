"""PostgreSQL database client with pgvector support.

This module implements the async database adapter for PostgreSQL, handling
connection pooling, table initialization, session state persistence,
multi-tenant project data, chat message history, visual DAG graphs, and
dual-namespace vector searches.
"""

import os
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple, cast
import asyncpg
from app.models.state import SessionState, Message


class PostgresClient:
    """
    Database client for PostgreSQL supporting pgvector similarity operations
    and multi-tenant SaaS project separation.
    """

    def __init__(self) -> None:
        """
        Initializes the database client and fetches connection details.
        """
        import os
        from app.core.config import settings
        self.database_url: Optional[str] = os.environ.get("DATABASE_URL") or settings.database_url
        self.pool: Any = None
        self.is_mock: bool = False
        
        # In-memory mock store for offline/local testing
        self.mock_store: Dict[str, Any] = {
            "users": {},
            "companies": {},
            "projects": {},
            "chat_messages": {},
            "graph_nodes": {},
            "graph_edges": {},
            "session_state": {},
            "session_memory": [],
            "global_knowledge": []
        }

    async def connect(self) -> None:
        """
        Establishes the database connection pool.

        Raises:
            ValueError: If DATABASE_URL is not set.
        """
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is not defined.")

        if not self.pool:
            try:
                # Attempt to connect to real PostgreSQL database pool
                self.pool = await asyncpg.create_pool(
                    dsn=self.database_url,
                    min_size=1,
                    max_size=10,
                )
                self.is_mock = False
            except Exception as e:
                # Graceful fallback to local in-memory Mock mode if offline
                print(f"Warning: PostgreSQL server offline ({e}). Running in Mock database mode.")
                self.is_mock = True

    async def disconnect(self) -> None:
        """
        Closes the database connection pool.
        """
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def init_db(self, schema_filepath: str) -> None:
        """
        Loads schema definitions from SQL file and initializes tables.
        """
        await self.connect()

        if self.is_mock:
            print("Mock database initialized.")
            return

        assert self.pool is not None
        with open(schema_filepath, "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()

        async with self.pool.acquire() as connection:
            # Run schema SQL script to set up tables and vector extension
            await connection.execute(schema_sql)

    # --- Legacy Session State Methods (maintained for compatibility) ---

    async def save_session_state(self, state: SessionState) -> None:
        """
        Saves or updates a serialized SessionState model inside the database.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            self.mock_store["session_state"][state.session_id] = state.model_dump_json()
            return

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
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            state_data_str = self.mock_store["session_state"].get(session_id)
            if not state_data_str:
                return None
            return SessionState.model_validate_json(state_data_str)

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

    # --- Companies Layer Methods ---

    async def create_company(
        self,
        user_id: str,
        name: str,
        industry: str,
        core_tools: str
    ) -> str:
        """
        Creates a new company record associated with the user and returns its UUID.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        company_id = str(uuid.uuid4())
        if self.is_mock:
            self.mock_store["companies"][company_id] = {
                "id": company_id,
                "user_id": user_id,
                "name": name,
                "industry": industry,
                "core_tools": core_tools
            }
            return company_id

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO companies (id, user_id, name, industry, core_tools)
                VALUES ($1, $2, $3, $4, $5);
                """,
                uuid.UUID(company_id),
                uuid.UUID(user_id),
                name,
                industry,
                core_tools
            )
        return company_id

    async def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves company details dictionary for a given UUID.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            return cast(Optional[Dict[str, Any]], self.mock_store["companies"].get(company_id))

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT id, user_id, name, industry, core_tools FROM companies WHERE id = $1;
                """,
                uuid.UUID(company_id)
            )
            if not row:
                return None
            return {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "name": row["name"],
                "industry": row["industry"],
                "core_tools": row["core_tools"]
            }

    async def get_user_companies(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Lists all companies belonging to a specific authenticated user.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            return [
                v for v in self.mock_store["companies"].values()
                if v["user_id"] == user_id
            ]

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT id, user_id, name, industry, core_tools FROM companies WHERE user_id = $1 ORDER BY created_at DESC;
                """,
                uuid.UUID(user_id)
            )
            return [
                {
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "name": row["name"],
                    "industry": row["industry"],
                    "core_tools": row["core_tools"]
                }
                for row in rows
            ]

    # --- Multi-Tenant SaaS Methods ---

    async def create_user_if_not_exists(self, user_id: str, email: str) -> None:
        """
        Saves Supabase authenticated user metadata locally for RLS joins.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            self.mock_store["users"][user_id] = {
                "id": user_id,
                "email": email
            }
            return

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO users (id, email)
                VALUES ($1, $2)
                ON CONFLICT (id) DO UPDATE SET email = $2;
                """,
                uuid.UUID(user_id),
                email,
            )

    async def create_project(
        self,
        user_id: str,
        title: str,
        description: str,
        mode: str,
        motivation: str,
        user_persona: str,
        company_id: Optional[str] = None
    ) -> str:
        """
        Creates a new project record and returns its UUID.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        project_id = str(uuid.uuid4())
        if self.is_mock:
            self.mock_store["projects"][project_id] = {
                "id": project_id,
                "user_id": user_id,
                "title": title,
                "description": description,
                "mode": mode,
                "motivation": motivation,
                "user_persona": user_persona,
                "company_id": company_id
            }
            return project_id

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO projects (id, user_id, title, description, mode, motivation, user_persona, company_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                """,
                uuid.UUID(project_id),
                uuid.UUID(user_id),
                title,
                description,
                mode,
                motivation,
                user_persona,
                uuid.UUID(company_id) if company_id else None
            )
        return project_id

    async def update_project_mode_and_title(
        self,
        project_id: str,
        mode: str,
        title: str
    ) -> None:
        """
        Updates the mode and title of an existing project.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            if project_id in self.mock_store["projects"]:
                self.mock_store["projects"][project_id]["mode"] = mode
                self.mock_store["projects"][project_id]["title"] = title
            return

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE projects 
                SET mode = $1, title = $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $3;
                """,
                mode,
                title,
                uuid.UUID(project_id)
            )

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the project details dictionary for a given project UUID.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            return cast(Optional[Dict[str, Any]], self.mock_store["projects"].get(project_id))

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT id, user_id, title, description, mode, motivation, user_persona, created_at, updated_at, company_id
                FROM projects WHERE id = $1;
                """,
                uuid.UUID(project_id),
            )
            if not row:
                return None
            return {
                "id": str(row["id"]),
                "user_id": str(row["user_id"]),
                "title": row["title"],
                "description": row["description"],
                "mode": row["mode"],
                "motivation": row["motivation"],
                "user_persona": row["user_persona"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "company_id": str(row["company_id"]) if row["company_id"] else None,
            }

    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Lists all project summaries belonging to a specific authenticated user.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            return [
                v for v in self.mock_store["projects"].values()
                if v["user_id"] == user_id
            ]

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT id, user_id, title, description, mode, motivation, user_persona, created_at, company_id
                FROM projects WHERE user_id = $1 ORDER BY created_at DESC;
                """,
                uuid.UUID(user_id),
            )
            return [
                {
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "title": row["title"],
                    "description": row["description"],
                    "mode": row["mode"],
                    "motivation": row["motivation"],
                    "user_persona": row["user_persona"],
                    "company_id": str(row["company_id"]) if row["company_id"] else None,
                }
                for row in rows
            ]

    async def delete_project(self, project_id: str) -> None:
        """
        Deletes a project workspace and cascades dependencies.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            self.mock_store["projects"].pop(project_id, None)
            self.mock_store["chat_messages"].pop(project_id, None)
            self.mock_store["graph_nodes"].pop(project_id, None)
            self.mock_store["graph_edges"].pop(project_id, None)
            return

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            await connection.execute(
                "DELETE FROM projects WHERE id = $1;",
                uuid.UUID(project_id),
            )

    # --- Chat Message Storage ---

    async def get_chat_messages(self, project_id: str) -> List[Message]:
        """
        Fetches conversation history associated with a project thread.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            return cast(List[Message], self.mock_store["chat_messages"].get(project_id, []))

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT role, content, name, tool_call_id
                FROM chat_messages WHERE project_id = $1 ORDER BY created_at ASC;
                """,
                uuid.UUID(project_id),
            )
            return [
                Message(
                    role=row["role"],
                    content=row["content"],
                    name=row["name"],
                    tool_call_id=row["tool_call_id"]
                )
                for row in rows
            ]

    async def save_chat_messages(self, project_id: str, messages: List[Message]) -> None:
        """
        Persists a series of conversation messages associated with a project thread.
        Does a clean rewrite to maintain chronological alignment.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            self.mock_store["chat_messages"][project_id] = messages
            return

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                # Delete existing messages for clean rewrite
                await connection.execute(
                    "DELETE FROM chat_messages WHERE project_id = $1;",
                    uuid.UUID(project_id)
                )
                
                # Batch insert updated list
                for msg in messages:
                    await connection.execute(
                        """
                        INSERT INTO chat_messages (project_id, role, content, name, tool_call_id)
                        VALUES ($1, $2, $3, $4, $5);
                        """,
                        uuid.UUID(project_id),
                        msg.role,
                        msg.content,
                        msg.name,
                        msg.tool_call_id
                    )

    # --- React Flow Graph Node/Edge Storage ---

    async def get_graph(self, project_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Retrieves serialized React Flow nodes and edges associated with a project workspace.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            nodes = self.mock_store["graph_nodes"].get(project_id, [])
            edges = self.mock_store["graph_edges"].get(project_id, [])
            return nodes, edges

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            node_rows = await connection.fetch(
                """
                SELECT id, type, position_x, position_y, data
                FROM graph_nodes WHERE project_id = $1;
                """,
                uuid.UUID(project_id)
            )
            edge_rows = await connection.fetch(
                """
                SELECT id, source, target, label, data
                FROM graph_edges WHERE project_id = $1;
                """,
                uuid.UUID(project_id)
            )
            
            nodes = [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "position": {"x": row["position_x"], "y": row["position_y"]},
                    "data": json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
                }
                for row in node_rows
            ]
            edges = [
                {
                    "id": row["id"],
                    "source": row["source"],
                    "target": row["target"],
                    "label": row["label"],
                    "data": json.loads(row["data"]) if row["data"] and isinstance(row["data"], str) else row["data"]
                }
                for row in edge_rows
            ]
            
            return nodes, edges

    async def save_graph(
        self,
        project_id: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> None:
        """
        Saves React Flow nodes and edges representing the workspace workflow visual DAG.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            self.mock_store["graph_nodes"][project_id] = nodes
            self.mock_store["graph_edges"][project_id] = edges
            return

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                # Delete existing graph
                await connection.execute("DELETE FROM graph_nodes WHERE project_id = $1;", uuid.UUID(project_id))
                await connection.execute("DELETE FROM graph_edges WHERE project_id = $1;", uuid.UUID(project_id))
                
                # Insert Nodes
                for n in nodes:
                    pos = n.get("position", {"x": 0.0, "y": 0.0})
                    node_data = json.dumps(n.get("data", {}))
                    await connection.execute(
                        """
                        INSERT INTO graph_nodes (id, project_id, type, position_x, position_y, data)
                        VALUES ($1, $2, $3, $4, $5, $6);
                        """,
                        n["id"],
                        uuid.UUID(project_id),
                        n.get("type", "default"),
                        float(pos.get("x", 0.0)),
                        float(pos.get("y", 0.0)),
                        node_data
                    )
                
                # Insert Edges
                for e in edges:
                    edge_data = json.dumps(e.get("data", {})) if e.get("data") else None
                    await connection.execute(
                        """
                        INSERT INTO graph_edges (id, project_id, source, target, label, data)
                        VALUES ($1, $2, $3, $4, $5, $6);
                        """,
                        e["id"],
                        uuid.UUID(project_id),
                        e["source"],
                        e["target"],
                        e.get("label"),
                        edge_data
                    )

    # --- Vector RAG pgvector Methods ---

    async def add_global_knowledge(
        self, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Inserts new content and vector embedding into the global knowledge database.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            record_id = len(self.mock_store["global_knowledge"]) + 1
            self.mock_store["global_knowledge"].append({
                "id": record_id,
                "content": content,
                "embedding": embedding,
                "metadata": metadata
            })
            return record_id

        assert self.pool is not None
        metadata_json = json.dumps(metadata) if metadata else None
        
        async with self.pool.acquire() as connection:
            record_id = await connection.fetchval(
                """
                INSERT INTO global_knowledge (content, embedding, metadata)
                VALUES ($1, $2, $3)
                RETURNING id;
                """,
                content,
                embedding,
                metadata_json,
            )
            return int(record_id)

    async def search_global_knowledge(
        self, query_embedding: List[float], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search (cosine distance) on global knowledge.
        """
        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            # Simple mock score ordering (simulated distance)
            return [
                {
                    "id": item["id"],
                    "content": item["content"],
                    "metadata": item["metadata"] or {},
                    "distance": 0.1
                }
                for item in self.mock_store["global_knowledge"][:limit]
            ]

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
        Inserts new content and vector embedding isolated by a session/project ID.

        Raises:
            ValueError: If session_id is empty or missing.
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id must be provided to add session memory.")

        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            record_id = len(self.mock_store["session_memory"]) + 1
            self.mock_store["session_memory"].append({
                "id": record_id,
                "project_id": session_id,
                "content": content,
                "embedding": embedding,
                "metadata": metadata
            })
            return record_id

        assert self.pool is not None
        metadata_json = json.dumps(metadata) if metadata else None

        async with self.pool.acquire() as connection:
            record_id = await connection.fetchval(
                """
                INSERT INTO session_memory (project_id, content, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id;
                """,
                uuid.UUID(session_id),
                content,
                embedding,
                metadata_json,
            )
            return int(record_id)

    async def search_session_memory(
        self, session_id: str, query_embedding: List[float], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs vector similarity search strictly isolated to a session/project ID.

        Raises:
            ValueError: If session_id is empty or missing.
        """
        if not session_id or not session_id.strip():
            raise ValueError("session_id must be provided to search session memory.")

        try:
            await self.connect()
        except ValueError:
            self.is_mock = True

        if self.is_mock:
            return [
                {
                    "id": item["id"],
                    "content": item["content"],
                    "metadata": item["metadata"] or {},
                    "distance": 0.15
                }
                for item in self.mock_store["session_memory"]
                if item["project_id"] == session_id
            ][:limit]

        assert self.pool is not None
        async with self.pool.acquire() as connection:
            records = await connection.fetch(
                """
                SELECT id, content, metadata, (embedding <=> $1) as distance
                FROM session_memory
                WHERE project_id = $2
                ORDER BY distance ASC
                LIMIT $3;
                """,
                query_embedding,
                uuid.UUID(session_id),
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
