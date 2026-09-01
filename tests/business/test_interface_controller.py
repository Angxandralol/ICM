from datetime import date, timedelta

import pandas as pd
import pytest

from icm.business.constants.header import HEADER_CONSULT_SNMP
from icm.business.controllers.interface import InterfaceController
from icm.business.exceptions import BusinessError
from icm.data import Database, InterfaceSchema


def _interfaces_dataframe(consulted_at: str, ip: str = "10.0.0.1") -> pd.DataFrame:
    row = {
        "ip": ip, "community": "public", "sysname": "switch-1", "ifIndex": 1,
        "ifName": "eth0", "ifDescr": "d", "ifAlias": "a", "ifHighSpeed": 1000,
        "ifOperStatus": "up", "ifAdminStatus": "up", "consulted_at": consulted_at,
    }
    return pd.DataFrame([row])[HEADER_CONSULT_SNMP]


def test_new_interfaces_rejects_a_dataframe_with_the_wrong_header(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        InterfaceController.new_interfaces(pd.DataFrame([{"unexpected": "column"}]))
    assert excinfo.value.status_code == 400


def test_new_interfaces_persists_the_rows(database: Database):
    InterfaceController.new_interfaces(_interfaces_dataframe("2024-01-01"))

    with database.session() as session:
        assert session.query(InterfaceSchema).count() == 1


def test_reload_interfaces_by_date_consult_rejects_an_invalid_date(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        InterfaceController.reload_interfaces_by_date_consult("not-a-date", _interfaces_dataframe("2024-01-01"))
    assert excinfo.value.status_code == 400


def test_reload_interfaces_by_date_consult_rejects_a_dataframe_spanning_multiple_dates(database: Database):
    mixed = pd.concat([_interfaces_dataframe("2024-01-01"), _interfaces_dataframe("2024-01-02")], ignore_index=True)

    with pytest.raises(BusinessError) as excinfo:
        InterfaceController.reload_interfaces_by_date_consult("2024-01-01", mixed)
    assert excinfo.value.status_code == 400


def test_reload_interfaces_by_date_consult_replaces_that_days_rows(database: Database):
    InterfaceController.new_interfaces(_interfaces_dataframe("2024-01-01", ip="10.0.0.1"))
    InterfaceController.new_interfaces(_interfaces_dataframe("2024-01-02", ip="10.0.0.1"))

    InterfaceController.reload_interfaces_by_date_consult("2024-01-01", _interfaces_dataframe("2024-01-01", ip="10.0.0.9"))

    with database.session() as session:
        remaining = session.query(InterfaceSchema).filter_by(consulted_at=date(2024, 1, 1)).all()
        assert len(remaining) == 1
        assert remaining[0].ip == "10.0.0.9"
        assert session.query(InterfaceSchema).filter_by(consulted_at=date(2024, 1, 2)).count() == 1


def test_delete_interfaces_by_date_consult_rejects_an_invalid_date(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        InterfaceController.delete_interfaces_by_date_consult("not-a-date")
    assert excinfo.value.status_code == 400


def test_delete_interfaces_by_date_consult_removes_only_that_date(database: Database):
    InterfaceController.new_interfaces(_interfaces_dataframe("2024-01-01"))
    InterfaceController.new_interfaces(_interfaces_dataframe("2024-01-02"))

    InterfaceController.delete_interfaces_by_date_consult("2024-01-01")

    with database.session() as session:
        assert session.query(InterfaceSchema).filter_by(consulted_at=date(2024, 1, 1)).count() == 0
        assert session.query(InterfaceSchema).filter_by(consulted_at=date(2024, 1, 2)).count() == 1


def test_get_interfaces_by_date_consult_rejects_an_invalid_date(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        InterfaceController.get_interfaces_by_date_consult("not-a-date")
    assert excinfo.value.status_code == 400


def test_get_interfaces_by_date_consult_returns_empty_list_when_none_found(database: Database):
    assert InterfaceController.get_interfaces_by_date_consult("2024-01-01") == []


def test_get_interfaces_by_date_consult_returns_the_rows(database: Database):
    InterfaceController.new_interfaces(_interfaces_dataframe("2024-01-01"))

    result = InterfaceController.get_interfaces_by_date_consult("2024-01-01")

    assert len(result) == 1
    assert result[0]["ip"] == "10.0.0.1"


def test_get_interfaces_with_changes_empty_when_nothing_to_compare(database: Database):
    result = InterfaceController.get_interfaces_with_changes()
    assert result.empty


def test_get_interfaces_with_changes_detects_a_real_change(database: Database):
    day_before_yesterday = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    old_row = {
        "ip": "10.0.0.1", "community": "public", "sysname": "switch-1", "ifIndex": 1,
        "ifName": "eth0", "ifDescr": "d", "ifAlias": "a", "ifHighSpeed": 1000,
        "ifOperStatus": "up", "ifAdminStatus": "up", "consulted_at": day_before_yesterday,
    }
    new_row = dict(old_row, ifName="eth0-renamed", consulted_at=yesterday)
    InterfaceController.new_interfaces(pd.DataFrame([old_row])[HEADER_CONSULT_SNMP])
    InterfaceController.new_interfaces(pd.DataFrame([new_row])[HEADER_CONSULT_SNMP])

    result = InterfaceController.get_interfaces_with_changes()

    assert len(result) == 1
    assert result.iloc[0]["ifName_old"] == "eth0"
    assert result.iloc[0]["ifName_new"] == "eth0-renamed"
