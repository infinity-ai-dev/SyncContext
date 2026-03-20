#!/bin/bash
# ============================================
# SyncContext - Preparação do Postgres 16
# ============================================
# Executar UMA VEZ antes do primeiro deploy.
# O container do SyncContext cria as tabelas automaticamente.
#
# Uso (via SSH na VPS):
#   bash init-db.sh

set -e

POSTGRES_CONTAINER=$(docker ps -q -f name=postgres)

if [ -z "$POSTGRES_CONTAINER" ]; then
    echo "Erro: Container do Postgres não encontrado"
    echo "Verifique com: docker ps -f name=postgres"
    exit 1
fi

echo ""
echo "========================================="
echo " SyncContext - Preparando Postgres 16"
echo "========================================="
echo ""

# 1. Instalar pgvector (para Postgres 16)
echo "[1/3] Instalando pgvector..."
docker exec "$POSTGRES_CONTAINER" bash -c \
    "apt-get update -qq && apt-get install -y -qq postgresql-16-pgvector > /dev/null 2>&1"
echo "  pgvector instalado"

# 2. Criar database
echo "[2/3] Criando database synccontext..."
docker exec "$POSTGRES_CONTAINER" psql -U postgres -tc \
    "SELECT 1 FROM pg_database WHERE datname = 'synccontext'" | grep -q 1 \
    && echo "  Database já existe" \
    || docker exec "$POSTGRES_CONTAINER" psql -U postgres -c "CREATE DATABASE synccontext" \
    && echo "  Database criado"

# 3. Habilitar extensões
echo "[3/3] Habilitando extensões..."
docker exec "$POSTGRES_CONTAINER" psql -U postgres -d synccontext -c '
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
'
echo "  Extensões habilitadas"

# Verificar
echo ""
echo "========================================="
echo " Verificação"
echo "========================================="
docker exec "$POSTGRES_CONTAINER" psql -U postgres -d synccontext -c \
    "SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector');"

echo ""
echo "Pronto! Agora faça o deploy da stack no Portainer."
echo "As tabelas serão criadas automaticamente pelo container."
echo ""
