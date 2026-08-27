"""Shared fixtures for the whole test suite.

Tests run against a real Postgres database instead of mocking
`psycopg2`/SQLAlchemy: most of what this layer must guarantee (constraints,
foreign keys, uniqueness) only exists in the real database engine, so a mock
would give false confidence (see REFACTOR.md).

They reuse the database already configured in `.env` (`URI_POSTGRES`)
instead of creating a dedicated one, since the app's own database role is
not granted `CREATEDB`. Running this suite drops and recreates every table
in that database — never point `.env` at one that holds data you care about.
"""

import pytest
from sqlalchemy import text

from icm.data import Base, Database
from icm.utils import Configuration


@pytest.fixture(scope="session")
def database() -> Database:
    """The single `Database` instance for the whole test session."""
    db = Database(uri=Configuration().uri_postgres)
    if not (db.ensure_database_exists() and db.drop() and db.initialize()):
        pytest.skip("Could not reset the test database — is Postgres reachable?")
    return db


@pytest.fixture(autouse=True)
def clean_tables(database: Database) -> None:
    """Every test starts from empty tables with identity counters reset."""
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with database.session() as session:
        session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
