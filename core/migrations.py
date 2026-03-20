import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger("synccontext.migrations")

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Run all pending SQL migrations on startup with detailed logging."""
    async with pool.acquire() as conn:
        # 1. Ensure migrations tracking table exists
        logger.info("Checking migrations table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # 2. Check which migrations are already applied
        rows = await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
        applied = {row["version"] for row in rows}

        if applied:
            logger.info(f"Migrations already applied: {sorted(applied)}")
        else:
            logger.info("No migrations applied yet — fresh database")

        # 3. Discover and apply pending migrations
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not migration_files:
            logger.warning(f"No migration files found in {MIGRATIONS_DIR}")
            return

        pending = 0
        for migration_file in migration_files:
            version = int(migration_file.stem.split("_")[0])

            if version in applied:
                logger.info(f"  [skip] Migration {version:03d} ({migration_file.name}) — already applied")
                continue

            pending += 1
            logger.info(f"  [exec] Applying migration {version:03d}: {migration_file.name}...")

            sql = migration_file.read_text()

            # Execute each statement individually for better error reporting
            statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
            for i, stmt in enumerate(statements, 1):
                try:
                    await conn.execute(stmt)
                    # Log table/index creation
                    stmt_lower = stmt.lower()
                    if "create table" in stmt_lower:
                        table_name = _extract_name(stmt, "table")
                        logger.info(f"    Table created: {table_name}")
                    elif "create index" in stmt_lower:
                        index_name = _extract_name(stmt, "index")
                        logger.info(f"    Index created: {index_name}")
                    elif "create extension" in stmt_lower:
                        ext_name = _extract_name(stmt, "extension")
                        logger.info(f"    Extension enabled: {ext_name}")
                    elif "insert into schema_migrations" in stmt_lower:
                        logger.info(f"    Migration {version:03d} recorded")
                except asyncpg.exceptions.DuplicateTableError:
                    pass  # IF NOT EXISTS handled at SQL level
                except asyncpg.exceptions.DuplicateObjectError:
                    pass  # IF NOT EXISTS for indexes
                except Exception as e:
                    logger.error(f"    Error in statement {i}: {e}")
                    logger.error(f"    Statement: {stmt[:200]}...")
                    raise

            logger.info(f"  [done] Migration {version:03d} applied successfully")

        # 4. Summary
        if pending == 0:
            logger.info("All migrations up to date — no changes needed")
        else:
            logger.info(f"All {pending} migration(s) applied successfully")

        # 5. Verify final state
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        table_names = [r["tablename"] for r in tables]
        logger.info(f"Database tables: {', '.join(table_names)}")

        extensions = await conn.fetch("""
            SELECT extname, extversion FROM pg_extension
            WHERE extname IN ('uuid-ossp', 'vector')
        """)
        for ext in extensions:
            logger.info(f"Extension active: {ext['extname']} v{ext['extversion']}")

        logger.info("All data set — database ready")


def _extract_name(stmt: str, obj_type: str) -> str:
    """Extract object name from a CREATE statement for logging."""
    stmt_lower = stmt.lower()
    try:
        # Handle IF NOT EXISTS
        if "if not exists" in stmt_lower:
            after = stmt_lower.split("if not exists")[1].strip()
        else:
            after = stmt_lower.split(obj_type)[1].strip()

        # Get the first word/token (the name)
        name = after.split()[0].strip('"').strip("'").strip("(")
        return name
    except (IndexError, ValueError):
        return "unknown"
