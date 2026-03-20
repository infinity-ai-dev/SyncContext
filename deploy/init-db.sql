-- ============================================
-- SyncContext - Inicialização do Banco de Dados
-- ============================================
-- Executar no Postgres existente antes do primeiro deploy

-- 1. Criar database dedicado
SELECT 'CREATE DATABASE synccontext'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'synccontext')\gexec

-- 2. Conectar no database synccontext e habilitar extensões
\c synccontext

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 3. Verificar que pgvector está funcionando
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
