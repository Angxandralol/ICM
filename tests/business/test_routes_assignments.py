from fastapi.testclient import TestClient

from icm.business.models.configuration import ConfigUser
from icm.constants import AssignmentStatusTypes, RoleTypes


def test_new_assignments_requires_assign_permission(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/assignments/new", headers=headers, json=[])

    assert response.status_code == 403


def test_new_assignments_persists_and_returns_201(
    client: TestClient, auth_headers, set_permissions, existing_change: tuple[int, int]
):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    old_id, new_id = existing_change
    headers = auth_headers(RoleTypes.ADMIN, username="assigner")

    response = client.post(
        "/assignments/new",
        headers=headers,
        json=[
            {
                "old_interface_id": old_id, "current_interface_id": new_id,
                "username": "assigner", "assign_by": "assigner", "type_status": AssignmentStatusTypes.PENDING,
            }
        ],
    )

    assert response.status_code == 201
    assert response.json() == {"message": "Assignments created successfully"}


def test_automatic_assignment_requires_assign_permission(client: TestClient, auth_headers, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/assignments/automatic", headers=headers, json={"usernames": []})

    assert response.status_code == 403


def test_automatic_assignment_with_no_unassigned_changes_returns_404(
    client: TestClient, auth_headers, set_permissions
):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=False, soport=False))
    headers = auth_headers(RoleTypes.ADMIN, username="auto_assigner")

    response = client.post("/assignments/automatic", headers=headers, json={"usernames": ["auto_assigner"]})

    assert response.status_code == 404


def test_update_assignments_status_only_requires_authentication(client: TestClient, auth_headers, set_permissions):
    """Unlike the other 3 endpoints in this router, updating status is a
    self-service action (marking one's own assigned work reviewed) -- no
    `can_assign` permission required, matching the original behaviour."""
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=False))
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/assignments/status", headers=headers, json=[])

    assert response.status_code == 200
    assert response.json() == {"message": "Assignments status updated successfully"}


def test_assignments_endpoints_require_authentication(client: TestClient):
    assert client.post("/assignments/new", json=[]).status_code == 401
    assert client.post("/assignments/reassign", json=[]).status_code == 401
    assert client.post("/assignments/automatic", json={"usernames": []}).status_code == 401
    assert client.post("/assignments/status", json=[]).status_code == 401
