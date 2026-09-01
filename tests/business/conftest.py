"""Shared fixtures for the `business/` layer's test suite.

Controller tests run against the real Postgres database, same as
`tests/data/` and `tests/access/` (see the module docstring on the root
`tests/conftest.py`). Route tests additionally drive the real FastAPI app
through `TestClient`, because the things `api/` must guarantee (permission
dependencies, JWT auth, the exact shape of an error body) only exist once
the whole stack -- routes, dependencies, controllers, `access/` -- runs
together.
"""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from icm.access import ChangeQuery
from icm.business.api.app import app
from icm.business.controllers.config import ConfigController
from icm.business.controllers.user import UserController
from icm.business.models.configuration import NewConfigModel
from icm.business.models.user import UserModel
from icm.constants import UserStatusTypes
from icm.data import Database
from icm.utils import Configuration

TEST_PASSWORD = "TestPassw0rd!"


@pytest.fixture()
def client() -> TestClient:
    """A `TestClient` for the real FastAPI app."""
    return TestClient(app)


@pytest.fixture()
def make_user():
    """Factory: persist a fully-usable user (real hashed password) and return its username."""

    def _make(username: str, role: str, status: str = UserStatusTypes.ACTIVE) -> str:
        UserController.new_user(
            UserModel(
                username=username,
                password=TEST_PASSWORD,
                name="Test",
                lastname="User",
                role=role,
                status=status,
                created_at=None,
                updated_at=None,
            )
        )
        return username

    return _make


@pytest.fixture()
def auth_headers(client: TestClient, make_user):
    """Factory: persist a user with the given role and return its `Authorization` header."""

    def _headers(role: str, status: str = UserStatusTypes.ACTIVE, username: str = "auth_user") -> dict[str, str]:
        make_user(username, role, status)
        response = client.post("/token", data={"username": username, "password": TEST_PASSWORD})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _headers


@pytest.fixture(autouse=True)
def preserve_system_config():
    """Every test in this package starts and ends with the `system.json` already on disk.

    Several tests need deterministic permissions (`set_permissions`) regardless
    of whatever the developer's local `system.json` currently holds.
    """
    configuration = Configuration()
    original = configuration.system.model_copy(deep=True)
    yield
    configuration.save(
        can_assign=original.can_assign,
        can_receive_assignment=original.can_receive_assignment,
        view_information_global=original.view_information_global,
        notification_changes=original.notification_changes,
    )
    configuration.read_config_system()


@pytest.fixture()
def set_permissions():
    """Factory: overwrite `can_assign`/`can_receive_assignment`/`view_information_global`."""

    def _set(**overrides) -> None:
        current = Configuration().system
        fields = dict(
            can_assign=current.can_assign.model_dump(),
            can_receive_assignment=current.can_receive_assignment.model_dump(),
            view_information_global=current.view_information_global.model_dump(),
            notification_changes=current.notification_changes.model_dump(),
        )
        fields.update(overrides)
        ConfigController.new_config(NewConfigModel(**fields))

    return _set


@pytest.fixture()
def existing_change(database: Database, existing_interfaces: tuple[int, int]) -> tuple[int, int]:
    """Persist one unassigned change and return `(old_interface_id, new_interface_id)`."""
    old_id, new_id = existing_interfaces
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
    assert ChangeQuery().insert(pd.DataFrame([row])) is True
    return old_id, new_id
