from sqlalchemy import inspect, text

from app.core.database import engine


def run_migrations() -> None:
    """Apply lightweight schema migrations for columns added after initial deploy."""
    migrations = [
        ("activities", "include_in_weekly", "BOOLEAN DEFAULT TRUE"),
        ("attachments", "include_in_weekly", "BOOLEAN DEFAULT TRUE"),
        ("users", "sector", "VARCHAR(20) DEFAULT 'CSI'"),
        ("users", "employee_id", "VARCHAR(50) UNIQUE NOT NULL DEFAULT ''"),
    ]

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.begin() as conn:
        for table, column, col_type in migrations:
            if table not in existing_tables:
                continue
            columns = {c["name"] for c in inspector.get_columns(table)}
            if column not in columns:
                if column == "employee_id":
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(50)"))
                    conn.execute(text(f"UPDATE {table} SET {column} = id WHERE {column} IS NULL"))
                    conn.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT unique_employee_id UNIQUE ({column})"))
                else:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))

        if "weekly_reports" in existing_tables:
            template_column = next(
                (
                    column
                    for column in inspector.get_columns("weekly_reports")
                    if column["name"] == "template_id"
                ),
                None,
            )
            # DROP NOT NULL só existe no Postgres — não roda no SQLite (QA-018).
            if (
                template_column
                and not template_column["nullable"]
                and engine.dialect.name == "postgresql"
            ):
                conn.execute(
                    text(
                        "ALTER TABLE weekly_reports "
                        "ALTER COLUMN template_id DROP NOT NULL"
                    )
                )

        # Índices que entraram no modelo depois da tabela existir; create_all
        # não altera tabela existente, então criamos idempotente aqui (QA-008).
        index_ddl = {
            "weekly_reports": [
                ("ix_weekly_reports_user_id", "user_id"),
                ("ix_weekly_reports_week_number", "week_number"),
                ("ix_weekly_reports_status", "status"),
                ("ix_weekly_reports_user_year_week", "user_id, year, week_number"),
                ("ix_weekly_reports_created_at_desc", "created_at"),
            ],
        }
        for table, indexes in index_ddl.items():
            if table not in existing_tables:
                continue
            for name, cols in indexes:
                try:
                    conn.execute(
                        text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})")
                    )
                except Exception:
                    pass  # índice já existe / dialeto sem IF NOT EXISTS — ignora
