from fastapi.testclient import TestClient

from icm.business.models.configuration import ConfigUser
from icm.constants import RoleTypes


def test_get_changes_requires_assign_permission(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER)

    assert client.get("/changes", headers=headers).status_code == 403


def test_get_changes_returns_paginated_shape(
    client: TestClient, auth_headers, set_permissions, existing_change: tuple[int, int]
):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.get("/changes", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 100
    assert len(body["items"]) == 1


def test_get_changes_rejects_a_page_size_over_the_limit(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.ADMIN)

    response = client.get("/changes?page_size=10000", headers=headers)

    assert response.status_code == 422


def test_get_changes_requires_authentication(client: TestClient):
    assert client.get("/changes").status_code == 401
