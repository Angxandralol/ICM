import pytest
from sqlalchemy.exc import IntegrityError

from icm.constants import RoleTypes, UserStatusTypes
from icm.data import AssignmentSchema, Database, UserSchema


def test_database_is_a_singleton(database: Database):
    assert Database() is database


def test_session_commits_on_success(database: Database):
    with database.session() as session:
        session.add(
            UserSchema(
                username="committed_user",
                password="hashed-password",
                name="Committed",
                lastname="User",
                status=UserStatusTypes.ACTIVE,
                role=RoleTypes.USER,
            )
        )

    with database.session() as session:
        assert session.get(UserSchema, "committed_user") is not None


def test_session_rolls_back_every_write_on_failure(
    database: Database, existing_interfaces: tuple[int, int]
):
    """Two related writes in one unit of work must live or die together.

    Mirrors the real scenario this fixed: creating an assignment together
    with marking its change as assigned must not leave one half committed
    if the other half fails.
    """
    old_id, new_id = existing_interfaces

    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(
                UserSchema(
                    username="rolled_back_user",
                    password="hashed-password",
                    name="Rolled",
                    lastname="Back",
                    status=UserStatusTypes.ACTIVE,
                    role=RoleTypes.USER,
                )
            )
            session.flush()
            session.add(
                AssignmentSchema(
                    old_interface_id=old_id,
                    current_interface_id=new_id,
                    username="rolled_back_user",
                    assign_by="rolled_back_user",
                    type_status="NOT_A_REAL_STATUS",
                )
            )

    with database.session() as session:
        assert session.get(UserSchema, "rolled_back_user") is None
        assert session.query(AssignmentSchema).count() == 0


def test_ensure_database_exists_is_idempotent(database: Database):
    assert database.ensure_database_exists() is True
    assert database.ensure_database_exists() is True


def test_initialize_is_idempotent_and_keeps_existing_data(database: Database):
    with database.session() as session:
        session.add(
            UserSchema(
                username="survivor",
                password="hashed-password",
                name="Survivor",
                lastname="User",
                status=UserStatusTypes.ACTIVE,
                role=RoleTypes.USER,
            )
        )

    assert database.initialize() is True

    with database.session() as session:
        assert session.get(UserSchema, "survivor") is not None
