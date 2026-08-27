from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from icm.constants import RoleTypes, UserStatusTypes
from icm.data import Database, UserSchema


def _new_user(**overrides) -> UserSchema:
    fields = dict(
        username="user_a",
        password="hashed-password",
        name="User",
        lastname="A",
        status=UserStatusTypes.ACTIVE,
        role=RoleTypes.USER,
    )
    fields.update(overrides)
    return UserSchema(**fields)


def test_create_user_round_trips_expected_columns(database: Database):
    with database.session() as session:
        session.add(_new_user())

    with database.session() as session:
        user = session.get(UserSchema, "user_a")
        assert user.name == "User"
        assert user.lastname == "A"
        assert user.status == UserStatusTypes.ACTIVE
        assert user.role == RoleTypes.USER
        assert user.created_at == date.today()
        assert user.updated_at is None


def test_username_is_the_primary_key(database: Database):
    with database.session() as session:
        session.add(_new_user())

    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_user(password="another-hash"))


@pytest.mark.parametrize(
    "status",
    [UserStatusTypes.ACTIVE, UserStatusTypes.INACTIVE, UserStatusTypes.DELETED],
)
def test_status_check_constraint_accepts_every_valid_value(database: Database, status: str):
    with database.session() as session:
        session.add(_new_user(status=status))

    with database.session() as session:
        assert session.get(UserSchema, "user_a").status == status


def test_status_check_constraint_rejects_invalid_value(database: Database):
    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_user(status="NOT_A_REAL_STATUS"))


def test_role_check_constraint_rejects_invalid_value(database: Database):
    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_user(role="NOT_A_REAL_ROLE"))


def test_no_users_by_default(database: Database):
    with database.session() as session:
        assert session.execute(select(UserSchema)).scalars().all() == []
