from fastapi.testclient import TestClient

from icm.constants import AssignmentStatusTypes, RoleTypes


def test_get_assignments_returns_an_empty_list_when_none_exist(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/history/assignments", headers=headers, json={"status": AssignmentStatusTypes.PENDING})

    assert response.status_code == 200
    assert response.json() == []


def test_get_assignments_rejects_an_invalid_status(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/history/assignments", headers=headers, json={"status": "NOT_A_STATUS"})

    assert response.status_code == 400


def test_get_user_history_rejects_an_invalid_date(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.get("/history/user?date=not-a-date", headers=headers)

    assert response.status_code == 400


def test_get_all_history_skips_unknown_usernames(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/history/all", headers=headers, json={"date": "2024-01", "usernames": ["ghost"]})

    assert response.status_code == 200
    assert response.json() == []


def test_get_date_available_to_consult_history_returns_a_list(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.get("/history/available", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_history_endpoints_require_authentication(client: TestClient):
    assert client.post("/history/assignments", json={"status": "PENDING"}).status_code == 401
    assert client.get("/history/user?date=2024-01").status_code == 401
    assert client.post("/history/all", json={"date": "2024-01", "usernames": []}).status_code == 401
    assert client.get("/history/available").status_code == 401
