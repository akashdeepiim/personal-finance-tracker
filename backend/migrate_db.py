"""Small, dialect-aware migration for installations created before schema versioning."""

from sqlalchemy import inspect, text

from database import engine
from models import Base


def _columns(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def migrate_database() -> None:
    Base.metadata.create_all(bind=engine)
    statements = {
        "transactions": {
            "original_amount": "NUMERIC(18, 2) NOT NULL DEFAULT 0",
            "currency": "VARCHAR NOT NULL DEFAULT 'USD'",
            "subcategory": "VARCHAR",
            "transaction_type": "VARCHAR NOT NULL DEFAULT 'debit'",
        },
        "statements": {
            "currency": "VARCHAR NOT NULL DEFAULT 'USD'",
            "file_hash": "VARCHAR(64)",
        },
        "analyses": {"total_income": "NUMERIC(18, 2) NOT NULL DEFAULT 0"},
    }

    with engine.begin() as connection:
        tables = set(inspect(engine).get_table_names())
        for table, additions in statements.items():
            if table not in tables:
                continue
            existing = _columns(table)
            for name, definition in additions.items():
                if name not in existing:
                    connection.execute(
                        text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')
                    )
        if engine.dialect.name == "postgresql":
            for table, column in (
                ("transactions", "amount"),
                ("transactions", "original_amount"),
                ("analyses", "total_spending"),
                ("analyses", "total_income"),
            ):
                connection.execute(
                    text(
                        f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
                        f'TYPE NUMERIC(18, 2) USING ROUND("{column}"::numeric, 2)'
                    )
                )
        connection.execute(
            text(
                "UPDATE transactions SET original_amount = amount "
                "WHERE original_amount IS NULL OR original_amount = 0"
            )
        )
        connection.execute(
            text(
                "DELETE FROM analyses WHERE id NOT IN "
                "(SELECT MAX(id) FROM analyses GROUP BY year, month)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_year_month "
                "ON analyses (year, month)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_statement_account_hash "
                "ON statements (account_type, file_hash)"
            )
        )


if __name__ == "__main__":
    migrate_database()
