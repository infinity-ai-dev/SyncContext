-- SyncContext Migration 001: Initial Schema
-- Extensions + Projects + Memories tables

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    embedding_provider VARCHAR(50) DEFAULT 'gemini',
    embedding_dimension INT DEFAULT 768,
    is_active BOOLEAN DEFAULT true,
    max_memories INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_token ON projects(token);
CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active);

-- Memories table
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    project_token VARCHAR(255) NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    author VARCHAR(255),
    tags TEXT[] DEFAULT '{}',
    file_path VARCHAR(1024),
    memory_type VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_project_id ON memories(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_project_token ON memories(project_token);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_author ON memories(project_id, author);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(project_id, memory_type);

-- Track this migration
INSERT INTO schema_migrations (version) VALUES (1) ON CONFLICT DO NOTHING;
