-- ============================================
-- SyncContext - Gerenciamento de Projetos
-- ============================================
-- Executar no Postgres da VPS:
--   docker exec <container_postgres> psql -U postgres -d synccontext -f /tmp/manage-projects.sql
--
-- Ou abrir um shell interativo:
--   docker exec -it <container_postgres> psql -U postgres -d synccontext

-- ============================================
-- CRIAR UM NOVO PROJETO
-- ============================================
-- Substitua 'Nome do Projeto' e 'Descrição' pelos valores desejados
-- O token é gerado automaticamente com prefixo sc_

-- Exemplo: Criar projeto para o time de frontend
INSERT INTO projects (name, token, description, embedding_provider, embedding_dimension)
VALUES (
    'Frontend Team',                                    -- nome do projeto
    'sc_' || encode(gen_random_bytes(32), 'hex'),       -- token auto-gerado
    'Memórias compartilhadas do time de frontend',      -- descrição
    'gemini',                                           -- provider de embedding
    768                                                 -- dimensão dos vetores
)
RETURNING id, name, token, created_at;

-- ============================================
-- CRIAR PROJETO COM TOKEN ESPECÍFICO
-- ============================================
-- Use isso quando quiser definir o token manualmente

-- INSERT INTO projects (name, token, description)
-- VALUES (
--     'Meu Projeto',
--     'sc_meu_token_customizado_aqui',
--     'Descrição do projeto'
-- )
-- RETURNING id, name, token;

-- ============================================
-- LISTAR TODOS OS PROJETOS
-- ============================================
SELECT
    id,
    name,
    token,
    description,
    is_active,
    embedding_provider,
    (SELECT COUNT(*) FROM memories m WHERE m.project_id = p.id) AS total_memories,
    created_at
FROM projects p
ORDER BY created_at DESC;

-- ============================================
-- DESATIVAR UM PROJETO (soft delete)
-- ============================================
-- UPDATE projects SET is_active = false, updated_at = NOW()
-- WHERE id = 'UUID-DO-PROJETO-AQUI';

-- ============================================
-- REATIVAR UM PROJETO
-- ============================================
-- UPDATE projects SET is_active = true, updated_at = NOW()
-- WHERE id = 'UUID-DO-PROJETO-AQUI';

-- ============================================
-- DELETAR UM PROJETO E TODAS AS MEMÓRIAS
-- ============================================
-- CUIDADO: Isso apaga tudo do projeto (CASCADE)!
-- DELETE FROM projects WHERE id = 'UUID-DO-PROJETO-AQUI';

-- ============================================
-- VER MEMÓRIAS DE UM PROJETO ESPECÍFICO
-- ============================================
-- SELECT id, content, author, tags, memory_type, created_at
-- FROM memories
-- WHERE project_id = 'UUID-DO-PROJETO-AQUI'
-- ORDER BY created_at DESC
-- LIMIT 20;

-- ============================================
-- CONTAR MEMÓRIAS POR PROJETO
-- ============================================
SELECT
    p.name,
    p.token,
    COUNT(m.id) AS total_memories,
    COUNT(DISTINCT m.author) AS contributors
FROM projects p
LEFT JOIN memories m ON m.project_id = p.id
GROUP BY p.id, p.name, p.token
ORDER BY total_memories DESC;
