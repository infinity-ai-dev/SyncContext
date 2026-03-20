-- SyncContext: Multi-project support
-- Adds projects table and links memories/vectors via project_id FK

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    embedding_provider VARCHAR(50) DEFAULT 'gemini',
    embedding_dimension INT DEFAULT 768,
    is_active BOOLEAN DEFAULT true,
    max_memories INT,  -- NULL = unlimited
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_token ON projects(token);
CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active);

-- Migrate: add project_id FK to memories (keep project_token for backward compat)
ALTER TABLE memories ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_memories_project_id ON memories(project_id);

-- Migrate: add project_id to memory_vectors
ALTER TABLE memory_vectors ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_memory_vectors_project_id ON memory_vectors(project_id);

INSERT INTO schema_migrations (version) VALUES (2) ON CONFLICT DO NOTHING;
