from datetime import date

import pandas as pd
import pytest

from icm.access import AssignmentQuery, ChangeQuery, ReassignmentModel
from icm.business.controllers.assignment import AssignmentController
from icm.business.controllers.user import UserController
from icm.business.exceptions import BusinessError
from icm.business.models.assignment import NewAssignmentModel, UpdateAssignmentModel
from icm.business.models.user import UserModel
from icm.constants import AssignmentStatusTypes, RoleTypes, UserStatusTypes
from icm.data import AssignmentSchema, Database, InterfaceSchema


def _persist_user(username: str) -> str:
    UserController.new_user(
        UserModel(
            username=username, password="password", name="Test", lastname="User",
            role=RoleTypes.USER, status=UserStatusTypes.ACTIVE, created_at=None, updated_at=None,
        )
    )
    return username


def _persist_unassigned_change(database: Database, ip: str) -> tuple[int, int]:
    with database.session() as session:
        old = InterfaceSchema(ip=ip, community="public", sysname=ip, ifIndex=1, consulted_at=date(2024, 1, 1))
        new = InterfaceSchema(ip=ip, community="public", sysname=ip, ifIndex=1, consulted_at=date(2024, 1, 2))
        session.add_all([old, new])
        session.flush()
        old_id, new_id = old.id, new.id
    row = dict(
        id_old=old_id, ip_old=ip, community_old="public", sysname_old=ip, ifIndex_old=1,
        ifName_old="eth0", ifDescr_old="d", ifAlias_old="a", ifHighSpeed_old=1000,
        ifOperStatus_old="up", ifAdminStatus_old="up",
        id_new=new_id, ip_new=ip, community_new="public", sysname_new=ip, ifIndex_new=1,
        ifName_new="eth0", ifDescr_new="d", ifAlias_new="a", ifHighSpeed_new=1000,
        ifOperStatus_new="up", ifAdminStatus_new="up", assigned=None,
    )
    assert ChangeQuery().insert(pd.DataFrame([row])) is True
    return old_id, new_id


def test_new_assignment_persists_the_assignment_and_marks_the_change_assigned(
    database: Database, existing_change: tuple[int, int]
):
    old_id, new_id = existing_change
    _persist_user("assignee")

    AssignmentController.new_assignment(
        [
            NewAssignmentModel(
                old_interface_id=old_id, current_interface_id=new_id,
                username="assignee", assign_by="assignee", type_status=AssignmentStatusTypes.PENDING,
            )
        ]
    )

    from icm.data import ChangeSchema

    with database.session() as session:
        assert session.query(AssignmentSchema).count() == 1
        assert session.get(ChangeSchema, (old_id, new_id)).assigned == "assignee"


def test_reassign_moves_the_assignment_and_resets_status(
    database: Database, existing_change: tuple[int, int]
):
    old_id, new_id = existing_change
    _persist_user("original_owner")
    _persist_user("new_owner")
    AssignmentController.new_assignment(
        [
            NewAssignmentModel(
                old_interface_id=old_id, current_interface_id=new_id,
                username="original_owner", assign_by="original_owner", type_status=AssignmentStatusTypes.PENDING,
            )
        ]
    )
    AssignmentController.update_status_assignment(
        [UpdateAssignmentModel(old_interface_id=old_id, current_interface_id=new_id, type_status=AssignmentStatusTypes.INSPECTED)],
        username="original_owner",
    )

    AssignmentController.reassign(
        [
            ReassignmentModel(
                old_interface_id=old_id, current_interface_id=new_id,
                old_username="original_owner", new_username="new_owner", assign_by="new_owner",
            )
        ]
    )

    from icm.data import ChangeSchema

    with database.session() as session:
        assignment = session.query(AssignmentSchema).one()
        assert assignment.username == "new_owner"
        assert assignment.type_status == AssignmentStatusTypes.PENDING
        assert session.get(ChangeSchema, (old_id, new_id)).assigned == "new_owner"


def test_automatic_assignment_distributes_unassigned_changes_evenly(database: Database):
    changes = [_persist_unassigned_change(database, f"10.0.0.{i}") for i in range(1, 4)]
    _persist_user("auto_user_a")
    _persist_user("auto_user_b")

    AssignmentController.automatic_assignment(assign_by="auto_user_a", usernames=["auto_user_a", "auto_user_b"])

    with database.session() as session:
        assignments = session.query(AssignmentSchema).all()
        assert len(assignments) == 3
        counts = {}
        for assignment in assignments:
            counts[assignment.username] = counts.get(assignment.username, 0) + 1
        assert sorted(counts.values()) == [1, 2]


def test_automatic_assignment_with_no_usernames_raises_404(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        AssignmentController.automatic_assignment(assign_by="someone", usernames=[])
    assert excinfo.value.status_code == 404


def test_automatic_assignment_with_no_unassigned_changes_raises_404(database: Database):
    _persist_user("no_changes_user")
    with pytest.raises(BusinessError) as excinfo:
        AssignmentController.automatic_assignment(assign_by="no_changes_user", usernames=["no_changes_user"])
    assert excinfo.value.status_code == 404


def test_update_status_assignment_changes_the_status(
    database: Database, existing_change: tuple[int, int]
):
    old_id, new_id = existing_change
    _persist_user("status_owner")
    AssignmentController.new_assignment(
        [
            NewAssignmentModel(
                old_interface_id=old_id, current_interface_id=new_id,
                username="status_owner", assign_by="status_owner", type_status=AssignmentStatusTypes.PENDING,
            )
        ]
    )

    AssignmentController.update_status_assignment(
        [UpdateAssignmentModel(old_interface_id=old_id, current_interface_id=new_id, type_status=AssignmentStatusTypes.REDISCOVERED)],
        username="status_owner",
    )

    with database.session() as session:
        assert session.query(AssignmentSchema).one().type_status == AssignmentStatusTypes.REDISCOVERED


def test_get_all_assignments_filter_by_status_rejects_an_invalid_status(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        AssignmentController.get_all_assignments_filter_by_status("NOT_A_STATUS")
    assert excinfo.value.status_code == 400


def test_get_all_assignments_filter_by_status_returns_matching_rows(
    database: Database, existing_change: tuple[int, int]
):
    old_id, new_id = existing_change
    _persist_user("filter_owner")
    AssignmentController.new_assignment(
        [
            NewAssignmentModel(
                old_interface_id=old_id, current_interface_id=new_id,
                username="filter_owner", assign_by="filter_owner", type_status=AssignmentStatusTypes.PENDING,
            )
        ]
    )

    result = AssignmentController.get_all_assignments_filter_by_status(AssignmentStatusTypes.PENDING)
    assert len(result) == 1
    assert result[0]["username"] == "filter_owner"


def test_get_user_assignments_filter_by_status_rejects_an_invalid_status(database: Database):
    _persist_user("known_user")
    with pytest.raises(BusinessError) as excinfo:
        AssignmentController.get_user_assignments_filter_by_status("known_user", "NOT_A_STATUS")
    assert excinfo.value.status_code == 400


def test_get_user_assignments_filter_by_status_rejects_an_unknown_username(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        AssignmentController.get_user_assignments_filter_by_status("ghost", AssignmentStatusTypes.PENDING)
    assert excinfo.value.status_code == 404


def test_get_user_assignments_completed_in_month_rejects_an_invalid_date(database: Database):
    _persist_user("month_user")
    with pytest.raises(BusinessError) as excinfo:
        AssignmentController.get_user_assignments_completed_in_month("month_user", "not-a-month")
    assert excinfo.value.status_code == 400


def test_get_users_assignments_completed_in_month_skips_unknown_usernames(database: Database):
    result = AssignmentController.get_users_assignments_completed_in_month(["ghost"], "2024-01")
    assert result == []


def test_get_date_available_to_consult_history_returns_a_list(database: Database):
    assert AssignmentController.get_date_available_to_consult_history() == []


def test_get_statistics_assignments_returns_empty_list_for_unknown_usernames(database: Database):
    assert AssignmentController.get_statistics_assignments(["ghost"]) == []
