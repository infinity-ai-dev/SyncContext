-- ============================================
-- SyncContext - Preparação do Postgres 16
-- ============================================
-- Executar UMA VEZ antes do primeiro deploy.
-- As tabelas são criadas automaticamente pelo container.
--
-- Uso:
--   docker exec <container_postgres> psql -U postgres -f /tmp/init-db.sql

-- 1. Criar database
SELECT 'CREATE DATABASE synccontext'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'synccontext')\gexec

-- 2. Habilitar extensões (pgvector precisa estar instalado: apt install postgresql-16-pgvector)
\c synccontext

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 3. Verificar
\echo ''
\echo 'Database synccontext pronto!'
SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector');
\echo ''
\echo 'As tabelas serao criadas automaticamente pelo container do SyncContext.'
