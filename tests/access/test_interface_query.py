from datetime import date

import pandas as pd

from icm.access import InterfaceQuery
from icm.data import Database, InterfaceSchema


def _interfaces_df(**overrides) -> pd.DataFrame:
    row = dict(
        ip="10.0.0.1",
        community="public",
        sysname="switch-1",
        ifIndex=1,
        ifName="eth0",
        ifDescr="ethernet0",
        ifAlias="eth0-alias",
        ifHighSpeed=1000,
        ifOperStatus="up",
        ifAdminStatus="up",
        consulted_at=date(2024, 1, 1),
    )
    row.update(overrides)
    return pd.DataFrame([row])


def test_insert_persists_every_field(database: Database):
    query = InterfaceQuery()
    assert query.insert(_interfaces_df()) is True

    with database.session() as session:
        interface = session.query(InterfaceSchema).one()
        assert interface.ip == "10.0.0.1"
        assert interface.ifIndex == 1
        assert interface.ifHighSpeed == 1000
        assert interface.consulted_at == date(2024, 1, 1)


def test_insert_accepts_a_plain_string_date(database: Database):
    """`business/updater` always sends `consulted_at` as a "YYYY-MM-DD" string,
    never a `date` object — Postgres must cast it on insert."""
    query = InterfaceQuery()
    assert query.insert(_interfaces_df(consulted_at="2024-01-01")) is True

    with database.session() as session:
        assert session.query(InterfaceSchema).one().consulted_at == date(2024, 1, 1)


def test_insert_converts_missing_optional_fields_to_null(database: Database):
    query = InterfaceQuery()
    df = _interfaces_df(ifName=None, ifAlias=None, ifHighSpeed=None)
    assert query.insert(df) is True

    with database.session() as session:
        interface = session.query(InterfaceSchema).one()
        assert interface.ifName is None
        assert interface.ifAlias is None
        assert interface.ifHighSpeed is None


def test_insert_preserves_separator_characters_in_text_fields(database: Database):
    """Regression test: the old `cursor.copy_from(sep=";")` corrupted any SNMP
    value containing a literal `;`. The ORM insert must not."""
    query = InterfaceQuery()
    assert query.insert(_interfaces_df(ifAlias="uplink; core; primary")) is True

    with database.session() as session:
        assert session.query(InterfaceSchema).one().ifAlias == "uplink; core; primary"


def test_insert_accepts_multiple_rows_in_one_call(database: Database):
    query = InterfaceQuery()
    df = pd.concat(
        [
            _interfaces_df(ifIndex=1),
            _interfaces_df(ifIndex=2),
        ],
        ignore_index=True,
    )
    assert query.insert(df) is True

    with database.session() as session:
        assert session.query(InterfaceSchema).count() == 2


def test_delete_by_date_consult_only_removes_that_date(database: Database):
    query = InterfaceQuery()
    query.insert(_interfaces_df(consulted_at=date(2024, 1, 1)))
    query.insert(_interfaces_df(consulted_at=date(2024, 1, 2)))

    assert query.delete_by_date_consult("2024-01-01") is True

    with database.session() as session:
        remaining = session.query(InterfaceSchema).all()
        assert len(remaining) == 1
        assert remaining[0].consulted_at == date(2024, 1, 2)


def test_get_by_date_consult_returns_only_matching_rows(database: Database):
    query = InterfaceQuery()
    query.insert(_interfaces_df(consulted_at=date(2024, 1, 1), ifIndex=1))
    query.insert(_interfaces_df(consulted_at=date(2024, 1, 2), ifIndex=2))

    result = query.get_by_date_consult("2024-01-01")
    assert len(result) == 1
    assert result.iloc[0]["ifIndex"] == 1
    assert result.iloc[0]["consulted_at"] == "2024-01-01"


def test_get_by_date_consult_with_no_matches_returns_empty_dataframe(database: Database):
    result = InterfaceQuery().get_by_date_consult("2099-01-01")
    assert result.empty
