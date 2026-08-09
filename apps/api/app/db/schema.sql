-- SQL Schema migration for BuildSense PostgreSQL database.
-- Installs the pgvector extension and creates namespaces for global knowledge, session memory, and session state.

-- Enable the vector extension to support vector similarity operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Global Knowledge Table (Shared, read-only benchmark data)
CREATE TABLE IF NOT EXISTS global_knowledge (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for global knowledge vector similarity searches (using cosine distance)
CREATE INDEX IF NOT EXISTS global_knowledge_embedding_hnsw_idx 
ON global_knowledge USING hnsw (embedding vector_cosine_ops);

-- Session Memory Table (Session-isolated vector storage)
CREATE TABLE IF NOT EXISTS session_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- B-Tree Index on session_id to guarantee fast lookup and strict session isolation
CREATE INDEX IF NOT EXISTS session_memory_session_id_idx ON session_memory (session_id);

-- Index for session memory vector similarity searches (using cosine distance)
CREATE INDEX IF NOT EXISTS session_memory_embedding_hnsw_idx 
ON session_memory USING hnsw (embedding vector_cosine_ops);

-- Session State Table (Stateless session persistence)
CREATE TABLE IF NOT EXISTS session_state (
    session_id VARCHAR(255) PRIMARY KEY,
    state_data JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
