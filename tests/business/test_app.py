from fastapi.testclient import TestClient

from icm.business.api.app import app
from icm.constants import RoleTypes


def test_login_with_correct_credentials_returns_a_bearer_token(client: TestClient, make_user):
    make_user("login_ok", RoleTypes.USER)

    response = client.post("/token", data={"username": "login_ok", "password": "TestPassw0rd!"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_returns_401_with_detail_shape(client: TestClient, make_user):
    make_user("login_bad", RoleTypes.USER)

    response = client.post("/token", data={"username": "login_bad", "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {"detail": "User incorrect"}


def test_login_with_unknown_username_returns_401(client: TestClient):
    response = client.post("/token", data={"username": "ghost", "password": "anything"})
    assert response.status_code == 401


def test_business_error_handler_produces_a_plain_detail_body(client: TestClient, auth_headers):
    headers = auth_headers(RoleTypes.USER)

    response = client.post("/assignments/new", headers=headers, json=[])

    assert response.status_code == 403
    assert list(response.json().keys()) == ["detail"]


def test_openapi_schema_builds_and_every_route_has_its_expected_tag():
    schema = app.openapi()

    expected_tags = {
        "/user/info": "users",
        "/assignments/new": "assignments",
        "/changes": "changes",
        "/history/available": "history",
        "/statistics/assignments/user": "statistics",
        "/configuration": "configuration",
        "/token": "auth",
    }
    for path, expected_tag in expected_tags.items():
        operations = schema["paths"][path]
        first_operation = next(iter(operations.values()))
        assert expected_tag in first_operation["tags"]


def test_openapi_schema_documents_every_operation_with_a_description():
    schema = app.openapi()

    undocumented = [
        f"{method.upper()} {path}"
        for path, operations in schema["paths"].items()
        for method, operation in operations.items()
        if not operation.get("description") and not operation.get("summary")
    ]
    assert undocumented == []
