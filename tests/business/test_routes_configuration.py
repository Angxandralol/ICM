from fastapi.testclient import TestClient

from icm.business.models.configuration import ConfigUser
from icm.constants import RoleTypes


def test_get_configuration_requires_assign_permission(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER)

    assert client.get("/configuration", headers=headers).status_code == 403


def test_get_configuration_returns_the_current_config(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.get("/configuration", headers=headers)

    assert response.status_code == 200
    assert response.json()["can_assign"]["admin"] is True


def test_new_configuration_requires_root(client: TestClient, auth_headers, set_permissions):
    """Being an admin with `can_assign` is not enough to change the config -- only `root` can."""
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.post(
        "/configuration/new",
        headers=headers,
        json={
            "can_assign": {"root": True, "admin": True, "user": False, "soport": False},
            "can_receive_assignment": {"root": False, "admin": True, "user": True, "soport": False},
            "view_information_global": {"root": True, "admin": True, "user": False, "soport": True},
            "notification_changes": {
                "ifName": True, "ifDescr": True, "ifAlias": True,
                "ifHighSpeed": True, "ifOperStatus": False, "ifAdminStatus": False,
            },
        },
    )

    assert response.status_code == 403


def test_new_configuration_as_root_is_applied(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.ROOT)

    payload = {
        "can_assign": {"root": True, "admin": False, "user": False, "soport": True},
        "can_receive_assignment": {"root": False, "admin": True, "user": True, "soport": False},
        "view_information_global": {"root": True, "admin": True, "user": False, "soport": True},
        "notification_changes": {
            "ifName": True, "ifDescr": True, "ifAlias": True,
            "ifHighSpeed": True, "ifOperStatus": False, "ifAdminStatus": False,
        },
    }
    response = client.post("/configuration/new", headers=headers, json=payload)
    assert response.status_code == 200

    updated = client.get("/configuration", headers=headers).json()
    assert updated["can_assign"] == payload["can_assign"]


def test_configuration_endpoints_require_authentication(client: TestClient):
    assert client.get("/configuration").status_code == 401
    assert client.post("/configuration/new", json={}).status_code == 401
