from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from icm.data.base import Base
from icm.utils import Configuration, log

_DRIVER_NAME = "postgresql+psycopg2"
_MAINTENANCE_DATABASE = "postgres"


class Database:
    """Owns the single SQLAlchemy engine of the process.

    Design pattern: Singleton (one engine/pool per process, mirroring
    `icm.utils.config.Configuration`) plus Unit of Work (`session()`), so a
    controller can group several related writes in one transaction instead
    of each query opening and closing its own connection.
    """

    _instance: "Database | None" = None
    _engine: Engine
    _session_factory: sessionmaker

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, uri: str | None = None):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._uri = uri or Configuration().uri_postgres
        self._engine = create_engine(self._as_driver_url(self._uri), pool_pre_ping=True)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @staticmethod
    def _as_driver_url(uri: str) -> str:
        return (
            make_url(uri)
            .set(drivername=_DRIVER_NAME)
            .render_as_string(hide_password=False)
        )

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def ensure_database_exists(self) -> bool:
        """Create the target database if it doesn't exist yet.

        Meant to run once, from the `icm database --start` CLI flow. It must
        not run on every connection: creating a database requires connecting
        to Postgres' own maintenance database (`postgres`) first, which is
        wasted work on every request.
        """
        url = make_url(self._as_driver_url(self._uri))
        target_db = url.database
        maintenance_engine = create_engine(
            url.set(database=_MAINTENANCE_DATABASE), isolation_level="AUTOCOMMIT"
        )
        try:
            with maintenance_engine.connect() as connection:
                exists = (
                    connection.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :name"),
                        {"name": target_db},
                    ).scalar()
                    is not None
                )
                if not exists:
                    connection.execute(
                        text(f"CREATE DATABASE {self._quote_identifier(target_db)}")
                    )
                    log.info(f"Database '{target_db}' created successfully.")
            return True
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"PostgreSQL database error. Failed to ensure database exists. {error}"
            )
            return False
        finally:
            maintenance_engine.dispose()

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Unit of work: commits on success, rolls back on error, always closes.

        Use this to group every write that must succeed or fail together,
        e.g. inserting an assignment and marking its change as assigned.
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def initialize(self) -> bool:
        """Create every table declared in the ORM schemas."""
        try:
            Base.metadata.create_all(self._engine)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"PostgreSQL database error. Failed to migrate database. {error}")
            return False
        else:
            log.info("Migration database successfully.")
            return True

    def drop(self) -> bool:
        """Drop every table declared in the ORM schemas."""
        try:
            Base.metadata.drop_all(self._engine)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"PostgreSQL database error. Failed to rollback database. {error}"
            )
            return False
        else:
            log.info("Rollback database successfully.")
            return True
