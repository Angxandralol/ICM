"""Fixtures for `data/` schema tests: rows other tests can depend on."""

from datetime import date

import pytest

from icm.constants import RoleTypes, UserStatusTypes
from icm.data import Database, InterfaceSchema, UserSchema


@pytest.fixture()
def existing_user(database: Database) -> str:
    """Persist one user and return its username."""
    username = "fixture_user"
    with database.session() as session:
        session.add(
            UserSchema(
                username=username,
                password="hashed-password",
                name="Fixture",
                lastname="User",
                status=UserStatusTypes.ACTIVE,
                role=RoleTypes.USER,
            )
        )
    return username


@pytest.fixture()
def another_existing_user(database: Database) -> str:
    """Persist a second, distinct user and return its username."""
    username = "another_fixture_user"
    with database.session() as session:
        session.add(
            UserSchema(
                username=username,
                password="hashed-password",
                name="Another",
                lastname="User",
                status=UserStatusTypes.ACTIVE,
                role=RoleTypes.USER,
            )
        )
    return username


@pytest.fixture()
def existing_interfaces(database: Database) -> tuple[int, int]:
    """Persist two daily snapshots of the same interface, return their ids."""
    with database.session() as session:
        old = InterfaceSchema(
            ip="10.0.0.1",
            community="public",
            sysname="switch-1",
            ifIndex=1,
            consulted_at=date(2024, 1, 1),
        )
        new = InterfaceSchema(
            ip="10.0.0.1",
            community="public",
            sysname="switch-1",
            ifIndex=1,
            consulted_at=date(2024, 1, 2),
        )
        session.add_all([old, new])
        session.flush()
        return old.id, new.id
