import pandas as pd
import pytest

from icm.business.controllers.change import ChangeController
from icm.business.exceptions import BusinessError
from icm.data import ChangeSchema, Database
from icm.utils import HEADER_RESPONSE_INTERFACES_CHANGES


def _changes_dataframe(old_id: int, new_id: int) -> pd.DataFrame:
    row = {
        "id_old": old_id, "ip_old": "10.0.0.1", "community_old": "public", "sysname_old": "switch-1",
        "ifIndex_old": 1, "ifName_old": "eth0", "ifDescr_old": "d", "ifAlias_old": "a",
        "ifHighSpeed_old": 1000, "ifOperStatus_old": "up", "ifAdminStatus_old": "up",
        "id_new": new_id, "ip_new": "10.0.0.1", "community_new": "public", "sysname_new": "switch-1",
        "ifIndex_new": 1, "ifName_new": "eth0-renamed", "ifDescr_new": "d", "ifAlias_new": "a",
        "ifHighSpeed_new": 1000, "ifOperStatus_new": "up", "ifAdminStatus_new": "up",
    }
    return pd.DataFrame([row])[HEADER_RESPONSE_INTERFACES_CHANGES]


def test_new_interfaces_rejects_a_dataframe_with_the_wrong_header(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        ChangeController.new_interfaces(pd.DataFrame([{"unexpected": "column"}]))
    assert excinfo.value.status_code == 400


def test_new_interfaces_replaces_the_whole_changes_table(
    database: Database, existing_interfaces: tuple[int, int]
):
    old_id, new_id = existing_interfaces
    ChangeController.new_interfaces(_changes_dataframe(old_id, new_id))

    with database.session() as session:
        change = session.get(ChangeSchema, (old_id, new_id))
        assert change is not None
        assert change.assigned is None
        assert session.query(ChangeSchema).count() == 1


def test_new_interfaces_is_a_full_replace_not_an_append(
    database: Database, existing_change: tuple[int, int], existing_interfaces: tuple[int, int]
):
    # `existing_change` already left one row in `changes`; a second call must
    # replace it, not add to it (this is what makes the daily updater run safe
    # to re-run).
    old_id, new_id = existing_interfaces
    ChangeController.new_interfaces(_changes_dataframe(old_id, new_id))

    with database.session() as session:
        assert session.query(ChangeSchema).count() == 1


def test_get_interfaces_with_changes_paginates(
    database: Database, existing_change: tuple[int, int]
):
    result = ChangeController.get_interfaces_with_changes(page=1, page_size=10)

    assert result.total == 1
    assert result.page == 1
    assert result.page_size == 10
    assert result.total_pages == 1
    assert len(result.items) == 1


def test_get_interfaces_with_changes_empty_table_has_zero_pages(database: Database):
    result = ChangeController.get_interfaces_with_changes()
    assert result.total == 0
    assert result.total_pages == 0
    assert result.items == []


def test_update_assignment_sets_the_assignee(
    database: Database, existing_change: tuple[int, int]
):
    from icm.access import UpdateChangeModel
    from icm.business.controllers.user import UserController
    from icm.business.models.user import UserModel
    from icm.constants import RoleTypes, UserStatusTypes

    old_id, new_id = existing_change
    UserController.new_user(
        UserModel(
            username="change_assignee", password="pw", name="A", lastname="B",
            role=RoleTypes.USER, status=UserStatusTypes.ACTIVE, created_at=None, updated_at=None,
        )
    )

    ChangeController.update_assignment(
        [UpdateChangeModel(id_old=old_id, id_new=new_id, username="change_assignee")]
    )

    with database.session() as session:
        assert session.get(ChangeSchema, (old_id, new_id)).assigned == "change_assignee"


def test_delete_changes_empties_the_table(database: Database, existing_change: tuple[int, int]):
    assert ChangeController.delete_changes() is True

    with database.session() as session:
        assert session.query(ChangeSchema).count() == 0
