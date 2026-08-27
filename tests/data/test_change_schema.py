import pytest
from sqlalchemy.exc import IntegrityError

from icm.data import ChangeSchema, Database


def _new_change(old_id: int, new_id: int, **overrides) -> ChangeSchema:
    fields = dict(
        id_old=old_id,
        ip_old="10.0.0.1",
        community_old="public",
        sysname_old="switch-1",
        ifIndex_old=1,
        id_new=new_id,
        ip_new="10.0.0.1",
        community_new="public",
        sysname_new="switch-1",
        ifIndex_new=1,
    )
    fields.update(overrides)
    return ChangeSchema(**fields)


def test_change_relationships_resolve_to_its_two_interfaces(
    database: Database, existing_interfaces: tuple[int, int]
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_change(old_id, new_id))

    with database.session() as session:
        change = session.get(ChangeSchema, (old_id, new_id))
        assert change.old_interface.id == old_id
        assert change.new_interface.id == new_id


def test_assigned_defaults_to_none_and_its_relationship_is_none(
    database: Database, existing_interfaces: tuple[int, int]
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_change(old_id, new_id))

    with database.session() as session:
        change = session.get(ChangeSchema, (old_id, new_id))
        assert change.assigned is None
        assert change.assigned_user is None


def test_assigned_user_relationship_resolves_once_assigned(
    database: Database, existing_interfaces: tuple[int, int], existing_user: str
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_change(old_id, new_id, assigned=existing_user))

    with database.session() as session:
        change = session.get(ChangeSchema, (old_id, new_id))
        assert change.assigned_user.username == existing_user


def test_id_old_and_id_new_together_are_the_primary_key(
    database: Database, existing_interfaces: tuple[int, int]
):
    old_id, new_id = existing_interfaces
    with database.session() as session:
        session.add(_new_change(old_id, new_id))

    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_change(old_id, new_id))


def test_change_requires_existing_interface_ids(database: Database):
    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(_new_change(old_id=999_999, new_id=999_998))
