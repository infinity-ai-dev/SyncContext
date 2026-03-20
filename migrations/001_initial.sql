-- SyncContext: Initial Schema
-- Requires: PostgreSQL 15+ with pgvector extension

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Memories table (authoritative metadata store)
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_token VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(255),
    tags TEXT[] DEFAULT '{}',
    file_path VARCHAR(1024),
    memory_type VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_memories_project_token ON memories(project_token);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(project_token, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_author ON memories(project_token, author);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(project_token, memory_type);

-- Migrations tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES (1) ON CONFLICT DO NOTHING;
