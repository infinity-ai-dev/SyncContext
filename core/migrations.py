import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger("synccontext.migrations")

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Run SQL migrations idempotently."""
    async with pool.acquire() as conn:
        # Ensure schema_migrations table exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Get applied versions
        rows = await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
        applied = {row["version"] for row in rows}

        # Find and apply pending migrations
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for migration_file in migration_files:
            version = int(migration_file.stem.split("_")[0])
            if version in applied:
                continue

            logger.info(f"Applying migration {migration_file.name}...")
            sql = migration_file.read_text()
            await conn.execute(sql)
            logger.info(f"Migration {migration_file.name} applied successfully")
