#!/bin/bash
# ============================================
# SyncContext - Inicialização do Banco de Dados
# ============================================
# Executa no container do Postgres existente para:
# 1. Instalar a extensão pgvector
# 2. Criar o database synccontext
# 3. Habilitar as extensões necessárias
#
# Uso:
#   docker exec -it $(docker ps -q -f name=postgres) bash
#   # Dentro do container:
#   apt-get update && apt-get install -y postgresql-17-pgvector
#   psql -U postgres -f /tmp/init-db.sql
#
# Ou direto do host:
#   docker cp deploy/init-db.sql $(docker ps -q -f name=postgres):/tmp/
#   docker exec $(docker ps -q -f name=postgres) bash -c "apt-get update && apt-get install -y postgresql-17-pgvector && psql -U postgres -f /tmp/init-db.sql"

set -e

POSTGRES_CONTAINER=$(docker ps -q -f name=postgres)

if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "Erro: Container do Postgres não encontrado"
    exit 1
fi

echo "==> Instalando pgvector no container Postgres..."
docker exec "$POSTGRES_CONTAINER" bash -c "apt-get update && apt-get install -y postgresql-17-pgvector"

echo "==> Criando database e extensões..."
docker cp "$(dirname "$0")/init-db.sql" "$POSTGRES_CONTAINER":/tmp/init-db.sql
docker exec "$POSTGRES_CONTAINER" psql -U postgres -f /tmp/init-db.sql

echo "==> Pronto! Database 'synccontext' criado com pgvector habilitado."
