-- ============================================
-- SyncContext - Preparação do Postgres
-- ============================================
-- Só precisa rodar UMA VEZ antes do primeiro deploy.
-- As tabelas são criadas automaticamente pelo container.
--
-- Uso:
--   docker exec <container_postgres> psql -U postgres -f /tmp/init-db.sql

-- 1. Criar database
SELECT 'CREATE DATABASE synccontext'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'synccontext')\gexec

-- 2. Habilitar extensões (pgvector precisa estar instalado no Postgres)
\c synccontext

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 3. Verificar
\echo ''
\echo 'Database synccontext criado com sucesso!'
\echo 'Extensões habilitadas:'
SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector');
\echo ''
\echo 'As tabelas serão criadas automaticamente na primeira execução do container.'
