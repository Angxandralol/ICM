from fastapi.testclient import TestClient

from icm.business.models.configuration import ConfigUser
from icm.constants import RoleTypes


def test_get_assignments_statistics_returns_empty_for_a_user_with_no_history(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.get("/statistics/assignments/user", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_get_all_assignments_statistics_requires_view_global_permission(
    client: TestClient, auth_headers, set_permissions
):
    set_permissions(view_information_global=ConfigUser(root=True, admin=False, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/statistics/assignments/all", headers=headers, json={"usernames": []})

    assert response.status_code == 403


def test_get_all_assignments_statistics_allows_a_permitted_role(
    client: TestClient, auth_headers, set_permissions
):
    set_permissions(view_information_global=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.post("/statistics/assignments/all", headers=headers, json={"usernames": []})

    assert response.status_code == 200
    assert response.json() == []


def test_statistics_endpoints_require_authentication(client: TestClient):
    assert client.get("/statistics/assignments/user").status_code == 401
    assert client.post("/statistics/assignments/all", json={"usernames": []}).status_code == 401
