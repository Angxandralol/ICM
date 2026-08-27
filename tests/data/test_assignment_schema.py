import pytest
from sqlalchemy.exc import IntegrityError

from icm.constants import AssignmentStatusTypes
from icm.data import AssignmentSchema, Database


def _new_assignment(old_id: int, new_id: int, username: str, assign_by: str, **overrides):
    fields = dict(
        old_interface_id=old_id,
        current_interface_id=new_id,
        username=username,
        assign_by=assign_by,
        type_status=AssignmentStatusTypes.PENDING,
    )
    fields.update(overrides)
    return AssignmentSchema(**fields)


def test_create_assignment_autoincrements_id_and_persists_fields(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        assignment = _new_assignment(old_id, new_id, existing_user, existing_user)
        session.add(assignment)
        session.flush()
        assignment_id = assignment.id

    with database.session() as session:
        assignment = session.get(AssignmentSchema, assignment_id)
        assert assignment.old_interface_id == old_id
        assert assignment.current_interface_id == new_id
        assert assignment.username == existing_user
        assert assignment.type_status == AssignmentStatusTypes.PENDING
        assert assignment.created_at is not None


def test_relationships_resolve_interfaces_and_users(
    database: Database,
    existing_interfaces: tuple[int, int],
    existing_user: str,
    another_existing_user: str,
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_assignment(old_id, new_id, existing_user, another_existing_user))

    with database.session() as session:
        assignment = session.query(AssignmentSchema).one()
        assert assignment.old_interface.id == old_id
        assert assignment.current_interface.id == new_id
        assert assignment.user.username == existing_user
        assert assignment.assigned_by_user.username == another_existing_user


@pytest.mark.parametrize(
    "status",
    [
        AssignmentStatusTypes.PENDING,
        AssignmentStatusTypes.INSPECTED,
        AssignmentStatusTypes.REDISCOVERED,
        AssignmentStatusTypes.EQUIPMENT_DOWN,
    ],
)
def test_type_status_check_constraint_accepts_every_valid_value(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str, status: str
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_assignment(old_id, new_id, existing_user, existing_user, type_status=status))

    with database.session() as session:
        assert session.query(AssignmentSchema).one().type_status == status


def test_type_status_check_constraint_rejects_invalid_value(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(
                _new_assignment(
                    old_id, new_id, existing_user, existing_user, type_status="NOT_A_REAL_STATUS"
                )
            )


def test_same_change_cannot_be_assigned_to_two_users_at_once(
    database: Database,
    existing_interfaces: tuple[int, int],
    existing_user: str,
    another_existing_user: str,
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_assignment(old_id, new_id, existing_user, existing_user))

    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_assignment(old_id, new_id, another_existing_user, existing_user))


def test_username_must_reference_an_existing_user(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_assignment(old_id, new_id, "ghost", existing_user))


def test_assign_by_must_reference_an_existing_user(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_assignment(old_id, new_id, existing_user, "ghost"))
