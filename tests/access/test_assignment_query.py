from datetime import date, timedelta

import pandas as pd

from icm.access import AssignmentQuery, ReassignmentModel, UpdateAssignmentModel
from icm.constants import AssignmentStatusTypes
from icm.data import AssignmentSchema, Database, InterfaceSchema


def _new_interface_pair(session, ip: str) -> tuple[int, int]:
    old = InterfaceSchema(ip=ip, community="public", sysname=ip, ifIndex=1, consulted_at=date(2024, 1, 1))
    new = InterfaceSchema(ip=ip, community="public", sysname=ip, ifIndex=1, consulted_at=date(2024, 1, 2))
    session.add_all([old, new])
    session.flush()
    return old.id, new.id


def _assignments_df(old_id: int, new_id: int, username: str, assign_by: str, **overrides) -> pd.DataFrame:
    row = dict(
        old_interface_id=old_id,
        current_interface_id=new_id,
        username=username,
        assign_by=assign_by,
        type_status=AssignmentStatusTypes.PENDING,
    )
    row.update(overrides)
    return pd.DataFrame([row])


def _new_assignment(old_id: int, new_id: int, username: str, assign_by: str, **overrides) -> AssignmentSchema:
    fields = dict(
        old_interface_id=old_id,
        current_interface_id=new_id,
        username=username,
        assign_by=assign_by,
        type_status=AssignmentStatusTypes.PENDING,
    )
    fields.update(overrides)
    return AssignmentSchema(**fields)


def test_insert_persists_the_assignment(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    query = AssignmentQuery()
    assert query.insert(_assignments_df(old_id, new_id, existing_user, existing_user)) is True

    with database.session() as session:
        assignment = session.query(AssignmentSchema).one()
        assert assignment.username == existing_user
        assert assignment.type_status == AssignmentStatusTypes.PENDING


def test_reassing_moves_the_assignment_and_resets_status(
    database: Database,
    existing_interfaces: tuple[int, int],
    existing_user: str,
    another_existing_user: str,
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(
            _new_assignment(
                old_id,
                new_id,
                existing_user,
                existing_user,
                type_status=AssignmentStatusTypes.INSPECTED,
            )
        )

    query = AssignmentQuery()
    result = query.reassing(
        [
            ReassignmentModel(
                old_interface_id=old_id,
                current_interface_id=new_id,
                old_username=existing_user,
                new_username=another_existing_user,
                assign_by=another_existing_user,
            )
        ]
    )
    assert result is True

    with database.session() as session:
        assignment = session.query(AssignmentSchema).one()
        assert assignment.username == another_existing_user
        assert assignment.assign_by == another_existing_user
        assert assignment.type_status == AssignmentStatusTypes.PENDING
        assert assignment.updated_at is None


def test_reassing_batch_is_atomic(
    database: Database,
    existing_interfaces: tuple[int, int],
    existing_user: str,
    another_existing_user: str,
):
    """A batch with one item referencing a nonexistent user must roll back
    entirely, including otherwise-valid items in the same call."""
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_assignment(old_id, new_id, existing_user, existing_user))

    query = AssignmentQuery()
    result = query.reassing(
        [
            ReassignmentModel(
                old_interface_id=old_id,
                current_interface_id=new_id,
                old_username=existing_user,
                new_username="ghost",
                assign_by=another_existing_user,
            )
        ]
    )
    assert result is False

    with database.session() as session:
        assert session.query(AssignmentSchema).one().username == existing_user


def test_update_status_changes_status_and_sets_updated_at(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_assignment(old_id, new_id, existing_user, existing_user))

    query = AssignmentQuery()
    result = query.update_status(
        [
            UpdateAssignmentModel(
                old_interface_id=old_id,
                current_interface_id=new_id,
                username=existing_user,
                type_status=AssignmentStatusTypes.INSPECTED,
            )
        ]
    )
    assert result is True

    with database.session() as session:
        assignment = session.query(AssignmentSchema).one()
        assert assignment.type_status == AssignmentStatusTypes.INSPECTED
        assert assignment.updated_at == date.today()


def test_get_all_by_status_returns_only_matching_status(
    database: Database, existing_user: str
):
    query = AssignmentQuery()
    with database.session() as session:
        pending_ids = _new_interface_pair(session, "10.0.0.1")
        inspected_ids = _new_interface_pair(session, "10.0.0.2")
        session.add(_new_assignment(*pending_ids, existing_user, existing_user))
        session.add(
            _new_assignment(
                *inspected_ids,
                existing_user,
                existing_user,
                type_status=AssignmentStatusTypes.INSPECTED,
            )
        )

    result = query.get_all_by_status(AssignmentStatusTypes.PENDING)
    assert len(result) == 1
    assert result.iloc[0]["type_status"] == AssignmentStatusTypes.PENDING
    assert result.iloc[0]["username"] == existing_user
    assert result.iloc[0]["ip_old"] == "10.0.0.1"


def test_assigned_by_status_filters_by_username_and_status(
    database: Database, existing_user: str, another_existing_user: str
):
    query = AssignmentQuery()
    with database.session() as session:
        mine = _new_interface_pair(session, "10.0.0.1")
        theirs = _new_interface_pair(session, "10.0.0.2")
        session.add(_new_assignment(*mine, existing_user, existing_user))
        session.add(_new_assignment(*theirs, another_existing_user, another_existing_user))

    result = query.assigned_by_status(existing_user, AssignmentStatusTypes.PENDING)
    assert len(result) == 1
    assert result.iloc[0]["username"] == existing_user


def test_completed_by_month_excludes_pending_and_other_months(
    database: Database, existing_user: str
):
    query = AssignmentQuery()
    this_month = date.today().replace(day=1)
    other_month = (this_month - timedelta(days=32)).replace(day=1)

    with database.session() as session:
        pending_ids = _new_interface_pair(session, "10.0.0.1")
        inspected_this_month = _new_interface_pair(session, "10.0.0.2")
        inspected_other_month = _new_interface_pair(session, "10.0.0.3")
        session.add(_new_assignment(*pending_ids, existing_user, existing_user))
        session.add(
            _new_assignment(
                *inspected_this_month,
                existing_user,
                existing_user,
                type_status=AssignmentStatusTypes.INSPECTED,
                created_at=this_month,
            )
        )
        session.add(
            _new_assignment(
                *inspected_other_month,
                existing_user,
                existing_user,
                type_status=AssignmentStatusTypes.INSPECTED,
                created_at=other_month,
            )
        )

    result = query.completed_by_month(existing_user, this_month.strftime("%Y-%m"))
    assert len(result) == 1
    assert result.iloc[0]["ip_old"] == "10.0.0.2"


def test_date_available_to_consult_history_returns_distinct_months_desc(
    database: Database, existing_user: str
):
    query = AssignmentQuery()
    this_month = date.today().replace(day=1)
    other_month = (this_month - timedelta(days=32)).replace(day=1)

    with database.session() as session:
        ids_a = _new_interface_pair(session, "10.0.0.1")
        ids_b = _new_interface_pair(session, "10.0.0.2")
        session.add(_new_assignment(*ids_a, existing_user, existing_user, created_at=this_month))
        session.add(_new_assignment(*ids_b, existing_user, existing_user, created_at=other_month))

    months = query.date_available_to_consult_history()
    assert months == sorted(months, reverse=True)
    assert this_month.strftime("%Y-%m") in months
    assert other_month.strftime("%Y-%m") in months


def test_date_available_to_consult_history_empty_returns_empty_list(database: Database):
    assert AssignmentQuery().date_available_to_consult_history() == []


def test_get_statistics_counts_today_and_month_per_status(
    database: Database, existing_user: str
):
    today = date.today()
    other_month = (today.replace(day=1) - timedelta(days=32))

    with database.session() as session:
        pending_ids = _new_interface_pair(session, "10.0.0.1")
        inspected_ids = _new_interface_pair(session, "10.0.0.2")
        old_ids = _new_interface_pair(session, "10.0.0.3")
        session.add(_new_assignment(*pending_ids, existing_user, existing_user, created_at=today))
        session.add(
            _new_assignment(
                *inspected_ids,
                existing_user,
                existing_user,
                type_status=AssignmentStatusTypes.INSPECTED,
                created_at=today,
            )
        )
        session.add(
            _new_assignment(
                *old_ids,
                existing_user,
                existing_user,
                type_status=AssignmentStatusTypes.INSPECTED,
                created_at=other_month,
            )
        )

    result = AssignmentQuery().get_statistics([existing_user])
    assert len(result) == 1
    stats = result[0]
    assert stats.username == existing_user
    assert stats.total_pending_today == 1
    assert stats.total_pending_month == 1
    assert stats.total_inspected_today == 1
    assert stats.total_inspected_month == 1


def test_get_statistics_omits_users_with_no_assignments(
    database: Database, existing_user: str, another_existing_user: str
):
    with database.session() as session:
        ids = _new_interface_pair(session, "10.0.0.1")
        session.add(_new_assignment(*ids, existing_user, existing_user, created_at=date.today()))

    result = AssignmentQuery().get_statistics([existing_user, another_existing_user])
    assert {stats.username for stats in result} == {existing_user}
