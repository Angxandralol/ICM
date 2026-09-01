from fastapi.testclient import TestClient

from icm.business.models.configuration import ConfigUser
from icm.constants import RoleTypes, UserStatusTypes


def test_get_user_info_requires_authentication(client: TestClient):
    assert client.get("/user/info").status_code == 401


def test_get_user_info_returns_the_logged_in_user(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER, username="whoami")

    response = client.get("/user/info", headers=headers)

    assert response.status_code == 200
    assert response.json()["username"] == "whoami"


def test_get_all_users_requires_assign_permission(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER)

    assert client.get("/user/all", headers=headers).status_code == 403


def test_get_all_users_never_leaks_the_password_field(client: TestClient, auth_headers, make_user, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    make_user("visible_user", RoleTypes.USER)
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.get("/user/all", headers=headers)

    assert response.status_code == 200
    assert all("password" not in user for user in response.json())


def test_put_user_info_without_permission_is_forbidden_even_when_editing_self(
    client: TestClient, auth_headers, set_permissions
):
    """Regression test for the privilege-escalation bug: a role without
    `can_assign` must not be able to edit any account through this endpoint,
    including its own -- not even to change its own role.
    """
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER, username="self_edit_attempt")

    response = client.put(
        "/user/info",
        headers=headers,
        json={
            "username": "self_edit_attempt",
            "name": "Hacked",
            "lastname": "Hacked",
            "status": UserStatusTypes.ACTIVE,
            "role": RoleTypes.ROOT,
        },
    )

    assert response.status_code == 403


def test_put_user_info_with_permission_updates_the_target_account(
    client: TestClient, auth_headers, make_user, set_permissions
):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    make_user("edit_target", RoleTypes.USER)
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.put(
        "/user/info",
        headers=headers,
        json={
            "username": "edit_target",
            "name": "Renamed",
            "lastname": "Person",
            "status": UserStatusTypes.ACTIVE,
            "role": RoleTypes.ADMIN,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User updated successfully"}


def test_put_user_info_on_unknown_username_returns_404(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.put(
        "/user/info",
        headers=headers,
        json={"username": "ghost", "name": "G", "lastname": "H", "status": UserStatusTypes.ACTIVE, "role": RoleTypes.USER},
    )

    assert response.status_code == 404


def test_update_password_accepts_the_password_in_the_body(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.patch("/user/info/password", headers=headers, json={"password": "a-new-password"})

    assert response.status_code == 200


def test_update_password_rejects_the_legacy_query_string_style(client: TestClient, auth_headers):
    """Regression test: the password must never be accepted as `?new_password=`."""
    headers = auth_headers(RoleTypes.USER)

    response = client.patch("/user/info/password?new_password=leaked-in-the-url", headers=headers)

    assert response.status_code == 422


def test_update_password_requires_authentication(client: TestClient):
    response = client.patch("/user/info/password", json={"password": "anything"})
    assert response.status_code == 401
