from core.migrations import MIGRATIONS_DIR, _split_sql_statements


def test_split_sql_statements_preserves_commented_create_table_statement():
    sql = (MIGRATIONS_DIR / "001_initial.sql").read_text()

    statements = _split_sql_statements(sql)

    projects_table_index = next(
        i for i, stmt in enumerate(statements) if stmt.startswith("CREATE TABLE IF NOT EXISTS projects")
    )
    projects_token_index = next(
        i for i, stmt in enumerate(statements) if stmt.startswith("CREATE INDEX IF NOT EXISTS idx_projects_token")
    )

    assert projects_table_index < projects_token_index


def test_split_sql_statements_ignores_comment_only_lines():
    statements = _split_sql_statements("""
        -- comment before statement
        CREATE TABLE demo (id INT);

        -- comment before another statement
        CREATE INDEX idx_demo_id ON demo(id);
    """)

    assert statements == [
        "CREATE TABLE demo (id INT)",
        "CREATE INDEX idx_demo_id ON demo(id)",
    ]
