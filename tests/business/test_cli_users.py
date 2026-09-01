import pytest

from icm.access import UserQuery
from icm.business.cli.users import UserCLI
from icm.constants import RoleTypes, UserStatusTypes
from icm.data import Database


def _queued_answers(monkeypatch, *answers):
    """Make every `Prompt.ask(...)` call in `cli.users` return the next queued answer."""
    remaining = list(answers)

    def _ask(*args, **kwargs):
        return remaining.pop(0)

    monkeypatch.setattr("icm.business.cli.users.Prompt.ask", _ask)


def test_register_persists_the_user_on_success(database: Database, monkeypatch):
    _queued_answers(
        monkeypatch,
        "cli_new_user",  # username
        "a-password",  # password
        "First",  # name
        "Last",  # lastname
        RoleTypes.USER,  # role
        "y",  # confirm
    )

    with pytest.raises(SystemExit) as excinfo:
        UserCLI.register()

    assert excinfo.value.code == 0
    assert UserQuery().get("cli_new_user") is not None


def test_register_cancelled_at_confirmation_does_not_persist_anything(database: Database, monkeypatch):
    _queued_answers(
        monkeypatch,
        "cli_cancelled_user", "a-password", "First", "Last", RoleTypes.USER,
        "n",  # confirm: no
    )

    with pytest.raises(SystemExit) as excinfo:
        UserCLI.register()

    assert excinfo.value.code == 0
    assert UserQuery().get("cli_cancelled_user") is None


def test_register_rejects_an_empty_username(database: Database, monkeypatch):
    _queued_answers(monkeypatch, "")  # username

    with pytest.raises(SystemExit) as excinfo:
        UserCLI.register()

    assert excinfo.value.code == 1


def test_register_rejects_a_duplicate_username(database: Database, monkeypatch):
    from icm.business.controllers.user import UserController
    from icm.business.models.user import UserModel

    UserController.new_user(
        UserModel(
            username="cli_dup_user", password="pw", name="A", lastname="B",
            role=RoleTypes.USER, status=UserStatusTypes.ACTIVE, created_at=None, updated_at=None,
        )
    )
    _queued_answers(
        monkeypatch,
        "cli_dup_user", "a-password", "First", "Last", RoleTypes.USER, "y",
    )

    with pytest.raises(SystemExit) as excinfo:
        UserCLI.register()

    assert excinfo.value.code == 1


def test_restore_password_updates_the_password_on_success(database: Database, monkeypatch):
    from icm.business.controllers.user import UserController
    from icm.business.models.user import UserModel

    UserController.new_user(
        UserModel(
            username="cli_restore_user", password="old-password", name="A", lastname="B",
            role=RoleTypes.USER, status=UserStatusTypes.ACTIVE, created_at=None, updated_at=None,
        )
    )
    before = UserQuery().get("cli_restore_user").password
    _queued_answers(monkeypatch, "cli_restore_user")

    with pytest.raises(SystemExit) as excinfo:
        UserCLI.restore_password()

    assert excinfo.value.code == 0
    assert UserQuery().get("cli_restore_user").password != before


def test_restore_password_rejects_an_empty_username(database: Database, monkeypatch):
    _queued_answers(monkeypatch, "")

    with pytest.raises(SystemExit) as excinfo:
        UserCLI.restore_password()

    assert excinfo.value.code == 1


def test_restore_password_on_an_unknown_username_exits_with_error(database: Database, monkeypatch):
    _queued_answers(monkeypatch, "ghost_username")

    with pytest.raises(SystemExit) as excinfo:
        UserCLI.restore_password()

    assert excinfo.value.code == 1
