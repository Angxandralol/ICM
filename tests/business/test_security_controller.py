import pytest

from icm.business.controllers.security import SecurityController
from icm.business.controllers.user import UserController
from icm.business.exceptions import BusinessError
from icm.business.models.user import UserModel
from icm.constants import RoleTypes, UserStatusTypes
from icm.data import Database
from icm.utils import Configuration


def _persist_user(username: str, password: str) -> None:
    UserController.new_user(
        UserModel(
            username=username,
            password=password,
            name="Security",
            lastname="Test",
            role=RoleTypes.USER,
            status=UserStatusTypes.ACTIVE,
            created_at=None,
            updated_at=None,
        )
    )


def test_create_password_hash_is_not_the_plaintext_and_verifies_back(database: Database):
    security = SecurityController()
    hashed = security.create_password_hash("my-secret")

    assert hashed != "my-secret"
    assert security._verify_password("my-secret", hashed) is True
    assert security._verify_password("wrong-password", hashed) is False


def test_authenticate_user_with_correct_password_returns_the_user(database: Database):
    _persist_user("sec_auth_ok", "correct-password")

    user = SecurityController().authenticate_user("sec_auth_ok", "correct-password")

    assert user is not None
    assert user.username == "sec_auth_ok"


def test_authenticate_user_with_wrong_password_returns_none(database: Database):
    _persist_user("sec_auth_bad", "correct-password")

    assert SecurityController().authenticate_user("sec_auth_bad", "wrong-password") is None


def test_authenticate_user_unknown_username_returns_none(database: Database):
    assert SecurityController().authenticate_user("ghost", "anything") is None


def test_create_access_token_round_trips_through_get_current_user(database: Database):
    _persist_user("sec_token_user", "password")

    token = SecurityController().create_access_token(data={"sub": "sec_token_user"})
    user = SecurityController.get_current_user(token)

    assert user.username == "sec_token_user"


def test_get_current_user_rejects_a_malformed_token():
    with pytest.raises(BusinessError) as excinfo:
        SecurityController.get_current_user("not-a-real-jwt")
    assert excinfo.value.status_code == 401


def test_get_current_user_rejects_a_token_for_a_deleted_or_missing_user(database: Database):
    security = SecurityController()
    token = security.create_access_token(data={"sub": "never_existed"})

    with pytest.raises(BusinessError) as excinfo:
        SecurityController.get_current_user(token)
    assert excinfo.value.status_code == 401


def test_get_current_user_rejects_a_token_signed_with_a_different_key(database: Database):
    import jwt as pyjwt

    forged = pyjwt.encode({"sub": "sec_token_user"}, "a-completely-different-secret-key-value", algorithm="HS256")

    with pytest.raises(BusinessError) as excinfo:
        SecurityController.get_current_user(forged)
    assert excinfo.value.status_code == 401


def test_weak_secret_key_is_rejected_at_construction(monkeypatch):
    monkeypatch.setattr(Configuration(), "key", "too-short")

    with pytest.raises(BusinessError) as excinfo:
        SecurityController()
    assert excinfo.value.status_code == 500
