-- SQL Schema migration for BuildSense PostgreSQL database.
-- Supports multi-tenancy, Supabase Auth integration, pgvector RAG, and execution graph caching.

-- Enable the vector extension to support vector similarity operations
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Users Table (Synchronized with Supabase Auth users)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1.5 Companies Table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(255) NOT NULL,
    industry_vertical VARCHAR(255),
    core_tools TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast company lookup
CREATE INDEX IF NOT EXISTS companies_user_id_idx ON companies (user_id);

-- 2. Projects Table (Multi-tenant container for sessions)
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    mode VARCHAR(50) NOT NULL, -- SUGGESTER, EVALUATOR, OPTIMIZER
    motivation VARCHAR(50) NOT NULL, -- REVENUE, EDUCATION
    user_persona VARCHAR(100) NOT NULL, -- Small Business Operator, Student, Solo Founder, Enterprise PM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migration statement to ensure existing databases get the company_id column
ALTER TABLE projects ADD COLUMN IF NOT EXISTS company_id UUID REFERENCES companies(id) ON DELETE SET NULL;

-- Migration statement to ensure companies have industry_vertical column
ALTER TABLE companies ADD COLUMN IF NOT EXISTS industry_vertical VARCHAR(255);
UPDATE companies SET industry_vertical = industry WHERE industry_vertical IS NULL;

-- Index for fast tenant lookup
CREATE INDEX IF NOT EXISTS projects_user_id_idx ON projects (user_id);

-- 3. Chat Messages Table (Persistent Conversation Threads)
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- system, user, assistant, tool
    content TEXT NOT NULL,
    name VARCHAR(255),
    tool_call_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS chat_messages_project_id_idx ON chat_messages (project_id);

-- 4. Graph Nodes Table (React Flow Components)
CREATE TABLE IF NOT EXISTS graph_nodes (
    id VARCHAR(255) NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    position_x DOUBLE PRECISION NOT NULL,
    position_y DOUBLE PRECISION NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, project_id)
);

CREATE INDEX IF NOT EXISTS graph_nodes_project_id_idx ON graph_nodes (project_id);

-- 5. Graph Edges Table (React Flow Connectors)
CREATE TABLE IF NOT EXISTS graph_edges (
    id VARCHAR(255) NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source VARCHAR(255) NOT NULL,
    target VARCHAR(255) NOT NULL,
    label VARCHAR(255),
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, project_id)
);

CREATE INDEX IF NOT EXISTS graph_edges_project_id_idx ON graph_edges (project_id);

-- 6. Global Knowledge Table (Shared, read-only benchmark data)
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

-- 7. Session Memory Table (Project-isolated vector storage)
CREATE TABLE IF NOT EXISTS session_memory (
    id SERIAL PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    session_id VARCHAR(255), -- legacy compatibility support
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index on project_id to guarantee fast lookup and strict session isolation
CREATE INDEX IF NOT EXISTS session_memory_project_id_idx ON session_memory (project_id);

-- Index for session memory vector similarity searches (using cosine distance)
CREATE INDEX IF NOT EXISTS session_memory_embedding_hnsw_idx 
ON session_memory USING hnsw (embedding vector_cosine_ops);

-- 8. Session State Table (Stateless session persistence, legacy endpoint support)
CREATE TABLE IF NOT EXISTS session_state (
    session_id VARCHAR(255) PRIMARY KEY,
    state_data JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enable Row Level Security (RLS) on Postgres tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_memory ENABLE ROW LEVEL SECURITY;

-- Setup Row Level Security policies based on Supabase auth.uid() function
-- Note: When database calls are executed via service-role context, RLS is bypassed.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'user_self_read_write'
    ) THEN
        CREATE POLICY user_self_read_write ON users 
            FOR ALL USING (auth.uid() = id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'companies_tenant_isolation'
    ) THEN
        CREATE POLICY companies_tenant_isolation ON companies 
            FOR ALL USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'project_tenant_isolation'
    ) THEN
        CREATE POLICY project_tenant_isolation ON projects 
            FOR ALL USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'chat_messages_tenant_isolation'
    ) THEN
        CREATE POLICY chat_messages_tenant_isolation ON chat_messages 
            FOR ALL USING (
                EXISTS (
                    SELECT 1 FROM projects 
                    WHERE projects.id = chat_messages.project_id AND projects.user_id = auth.uid()
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'graph_nodes_tenant_isolation'
    ) THEN
        CREATE POLICY graph_nodes_tenant_isolation ON graph_nodes 
            FOR ALL USING (
                EXISTS (
                    SELECT 1 FROM projects 
                    WHERE projects.id = graph_nodes.project_id AND projects.user_id = auth.uid()
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'graph_edges_tenant_isolation'
    ) THEN
        CREATE POLICY graph_edges_tenant_isolation ON graph_edges 
            FOR ALL USING (
                EXISTS (
                    SELECT 1 FROM projects 
                    WHERE projects.id = graph_edges.project_id AND projects.user_id = auth.uid()
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'session_memory_tenant_isolation'
    ) THEN
        CREATE POLICY session_memory_tenant_isolation ON session_memory 
            FOR ALL USING (
                EXISTS (
                    SELECT 1 FROM projects 
                    WHERE projects.id = session_memory.project_id AND projects.user_id = auth.uid()
                )
            );
    END IF;
END
$$;
