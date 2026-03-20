-- ============================================
-- SyncContext - Inicialização Completa do Banco
-- ============================================
-- Executar no Postgres da VPS antes do primeiro deploy
--
-- Uso:
--   1. Copiar para o container: docker cp deploy/init-db.sql <container_postgres>:/tmp/
--   2. Executar: docker exec <container_postgres> psql -U postgres -f /tmp/init-db.sql

-- ============================================
-- 1. Criar database dedicado
-- ============================================
SELECT 'CREATE DATABASE synccontext'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'synccontext')\gexec

\c synccontext

-- ============================================
-- 2. Extensões necessárias
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Verificar pgvector
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE EXCEPTION 'pgvector extension not installed. Run: apt-get install postgresql-17-pgvector';
    END IF;
END $$;

-- ============================================
-- 3. Tabela de Projetos (tokens)
-- ============================================
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    embedding_provider VARCHAR(50) DEFAULT 'gemini',
    embedding_dimension INT DEFAULT 768,
    is_active BOOLEAN DEFAULT true,
    max_memories INT,  -- NULL = ilimitado
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_token ON projects(token);
CREATE INDEX IF NOT EXISTS idx_projects_active ON projects(is_active);

-- ============================================
-- 4. Tabela de Memórias
-- ============================================
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_author ON memories(project_id, author);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(project_id, memory_type);

-- ============================================
-- 5. Controle de Migrações
-- ============================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES (1) ON CONFLICT DO NOTHING;
INSERT INTO schema_migrations (version) VALUES (2) ON CONFLICT DO NOTHING;

-- ============================================
-- Resultado
-- ============================================
\echo ''
\echo '========================================='
\echo ' SyncContext database criado com sucesso!'
\echo '========================================='
\echo ''

SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector');

\echo ''
\echo 'Tabelas criadas:'
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
