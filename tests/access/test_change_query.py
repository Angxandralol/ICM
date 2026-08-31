from datetime import date

import pandas as pd

from icm.access import ChangeQuery, UpdateChangeModel
from icm.data import ChangeSchema, Database, InterfaceSchema


def _new_interface_pair(session, ip: str) -> tuple[int, int]:
    old = InterfaceSchema(ip=ip, community="public", sysname=ip, ifIndex=1, consulted_at=date(2024, 1, 1))
    new = InterfaceSchema(ip=ip, community="public", sysname=ip, ifIndex=1, consulted_at=date(2024, 1, 2))
    session.add_all([old, new])
    session.flush()
    return old.id, new.id


def _changes_df(old_id: int, new_id: int, **overrides) -> pd.DataFrame:
    row = dict(
        id_old=old_id,
        ip_old="10.0.0.1",
        community_old="public",
        sysname_old="switch-1",
        ifIndex_old=1,
        ifName_old="eth0",
        ifDescr_old="d",
        ifAlias_old="a",
        ifHighSpeed_old=1000,
        ifOperStatus_old="up",
        ifAdminStatus_old="up",
        id_new=new_id,
        ip_new="10.0.0.1",
        community_new="public",
        sysname_new="switch-1",
        ifIndex_new=1,
        ifName_new="eth0-renamed",
        ifDescr_new="d",
        ifAlias_new="a",
        ifHighSpeed_new=1000,
        ifOperStatus_new="up",
        ifAdminStatus_new="up",
        assigned=None,
    )
    row.update(overrides)
    return pd.DataFrame([row])


def test_insert_persists_both_sides_of_the_change(
    database: Database, existing_interfaces: tuple[int, int]
):
    old_id, new_id = existing_interfaces
    query = ChangeQuery()
    assert query.insert(_changes_df(old_id, new_id)) is True

    with database.session() as session:
        change = session.get(ChangeSchema, (old_id, new_id))
        assert change.ifName_old == "eth0"
        assert change.ifName_new == "eth0-renamed"
        assert change.assigned is None


def test_get_all_paginates_and_orders_by_id_old_descending(database: Database):
    query = ChangeQuery()
    for ip in ("10.0.0.1", "10.0.0.2", "10.0.0.3"):
        with database.session() as session:
            old_id, new_id = _new_interface_pair(session, ip)
        query.insert(_changes_df(old_id, new_id))

    first_page, total = query.get_all(page=1, page_size=2)
    second_page, total_again = query.get_all(page=2, page_size=2)

    assert total == 3
    assert total_again == 3
    assert len(first_page) == 2
    assert len(second_page) == 1
    assert [row["id_old"] for row in first_page] == sorted(
        [row["id_old"] for row in first_page], reverse=True
    )


def test_get_all_reports_null_assignee_as_none(
    database: Database, existing_interfaces: tuple[int, int]
):
    old_id, new_id = existing_interfaces
    query = ChangeQuery()
    query.insert(_changes_df(old_id, new_id))

    items, _ = query.get_all()
    assert items[0]["username"] is None
    assert items[0]["name"] is None
    assert items[0]["lastname"] is None


def test_get_all_includes_assignee_details_when_assigned(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    query = ChangeQuery()
    query.insert(_changes_df(old_id, new_id, assigned=existing_user))

    items, _ = query.get_all()
    assert items[0]["username"] == existing_user
    assert items[0]["name"] == "Fixture"


def test_get_all_unassigned_excludes_assigned_changes(
    database: Database, existing_user: str
):
    query = ChangeQuery()
    with database.session() as session:
        old1, new1 = _new_interface_pair(session, "10.0.0.1")
        old2, new2 = _new_interface_pair(session, "10.0.0.2")

    query.insert(_changes_df(old1, new1, assigned=None))
    query.insert(_changes_df(old2, new2, assigned=existing_user))

    result = query.get_all_unassigned()
    ids = {(row["id_old"], row["id_new"]) for row in result}
    assert ids == {(old1, new1)}


def test_update_assign_sets_the_assignee(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    query = ChangeQuery()
    query.insert(_changes_df(old_id, new_id))

    updated = query.update_assign(
        [UpdateChangeModel(id_old=old_id, id_new=new_id, username=existing_user)]
    )
    assert updated is True

    with database.session() as session:
        assert session.get(ChangeSchema, (old_id, new_id)).assigned == existing_user


def test_update_assign_batch_is_atomic(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    """If any item in the batch fails, none of the batch's writes survive.

    The second item references a nonexistent username, violating the FK on
    `changes.assigned`. The whole batch must roll back, including the first,
    otherwise-valid item.
    """
    old_id, new_id = existing_interfaces
    query = ChangeQuery()
    query.insert(_changes_df(old_id, new_id))

    result = query.update_assign(
        [
            UpdateChangeModel(id_old=old_id, id_new=new_id, username=existing_user),
            UpdateChangeModel(id_old=old_id, id_new=new_id, username="ghost"),
        ]
    )
    assert result is False

    with database.session() as session:
        assert session.get(ChangeSchema, (old_id, new_id)).assigned is None


def test_delete_changes_removes_every_row(
    database: Database, existing_interfaces: tuple[int, int]
):
    old_id, new_id = existing_interfaces
    query = ChangeQuery()
    query.insert(_changes_df(old_id, new_id))

    assert query.delete_changes() is True

    with database.session() as session:
        assert session.query(ChangeSchema).count() == 0
