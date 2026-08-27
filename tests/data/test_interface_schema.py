from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from icm.data import Database, InterfaceSchema


def _new_interface(**overrides) -> InterfaceSchema:
    fields = dict(
        ip="10.0.0.1",
        community="public",
        sysname="switch-1",
        ifIndex=1,
        ifName="eth1",
        ifDescr="ethernet1",
        ifAlias="eth1",
        ifHighSpeed=1000,
        ifOperStatus="up(1)",
        ifAdminStatus="up(1)",
        consulted_at=date(2024, 1, 1),
    )
    fields.update(overrides)
    return InterfaceSchema(**fields)


def test_create_interface_autoincrements_id(database: Database):
    with database.session() as session:
        interface = _new_interface()
        session.add(interface)
        session.flush()
        first_id = interface.id

    with database.session() as session:
        session.add(_new_interface(consulted_at=date(2024, 1, 2)))
        session.flush()

    with database.session() as session:
        second = session.get(InterfaceSchema, first_id + 1)
        assert second is not None
        assert second.consulted_at == date(2024, 1, 2)


def test_numeric_fields_round_trip_as_integers_not_strings(database: Database):
    with database.session() as session:
        session.add(_new_interface(ifIndex=42, ifHighSpeed=100000))

    with database.session() as session:
        interface = session.query(InterfaceSchema).one()
        assert interface.ifIndex == 42
        assert interface.ifHighSpeed == 100000
        assert isinstance(interface.ifIndex, int)
        assert isinstance(interface.ifHighSpeed, int)


def test_same_snapshot_cannot_be_inserted_twice_for_the_same_day(database: Database):
    with database.session() as session:
        session.add(_new_interface())

    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_interface())


def test_same_interface_can_repeat_on_a_different_day(database: Database):
    with database.session() as session:
        session.add(_new_interface(consulted_at=date(2024, 1, 1)))

    with database.session() as session:
        session.add(_new_interface(consulted_at=date(2024, 1, 2)))

    with database.session() as session:
        assert session.query(InterfaceSchema).count() == 2
