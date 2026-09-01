import pytest

from icm.business.controllers.user import UserController
from icm.business.exceptions import BusinessError
from icm.business.models.configuration import ConfigUser
from icm.business.models.user import UpdateUserModel, UserModel
from icm.constants import RoleTypes, UserStatusTypes
from icm.data import Database


def _new_user(username: str, **overrides) -> UserModel:
    fields = dict(
        username=username,
        password="plaintext-password",
        name="John",
        lastname="Doe",
        role=RoleTypes.USER,
        status=UserStatusTypes.ACTIVE,
        created_at=None,
        updated_at=None,
    )
    fields.update(overrides)
    return UserModel(**fields)


def test_new_user_hashes_the_password_before_persisting(database: Database):
    UserController.new_user(_new_user("new_hash_user", password="plaintext-password"))

    from icm.access import UserQuery

    stored = UserQuery().get("new_hash_user")
    assert stored.password != "plaintext-password"


def test_new_user_rejects_a_duplicate_username(database: Database):
    UserController.new_user(_new_user("dup_user"))

    with pytest.raises(BusinessError) as excinfo:
        UserController.new_user(_new_user("dup_user"))
    assert excinfo.value.status_code == 400


def test_new_user_rejects_an_invalid_role(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.new_user(_new_user("bad_role_user", role="NOT_A_ROLE"))
    assert excinfo.value.status_code == 400


def test_new_user_rejects_an_invalid_status(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.new_user(_new_user("bad_status_user", status="NOT_A_STATUS"))
    assert excinfo.value.status_code == 400


def test_update_user_changes_name_lastname_status_and_role(database: Database):
    UserController.new_user(_new_user("update_target"))

    UserController.update_user(
        UpdateUserModel(
            username="update_target",
            name="Renamed",
            lastname="Person",
            status=UserStatusTypes.INACTIVE,
            role=RoleTypes.ADMIN,
        )
    )

    updated = UserController.get_user("update_target")
    assert updated.name == "Renamed"
    assert updated.status == UserStatusTypes.INACTIVE
    assert updated.role == RoleTypes.ADMIN


def test_update_user_never_touches_the_password(database: Database):
    UserController.new_user(_new_user("password_untouched", password="original-password"))
    from icm.access import UserQuery

    original_hash = UserQuery().get("password_untouched").password

    UserController.update_user(
        UpdateUserModel(
            username="password_untouched",
            name="Same",
            lastname="Person",
            status=UserStatusTypes.ACTIVE,
            role=RoleTypes.USER,
        )
    )

    assert UserQuery().get("password_untouched").password == original_hash


def test_update_user_on_a_nonexistent_username_raises_404(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.update_user(
            UpdateUserModel(
                username="ghost", name="Ghost", lastname="User",
                status=UserStatusTypes.ACTIVE, role=RoleTypes.USER,
            )
        )
    assert excinfo.value.status_code == 404


def test_update_user_rejects_an_invalid_role(database: Database):
    UserController.new_user(_new_user("invalid_role_target"))

    with pytest.raises(BusinessError) as excinfo:
        UserController.update_user(
            UpdateUserModel(
                username="invalid_role_target", name="X", lastname="Y",
                status=UserStatusTypes.ACTIVE, role="NOT_A_ROLE",
            )
        )
    assert excinfo.value.status_code == 400


def test_update_password_changes_the_hash(database: Database):
    UserController.new_user(_new_user("pw_change_user", password="old-password"))
    from icm.access import UserQuery

    before = UserQuery().get("pw_change_user").password

    UserController.update_password("pw_change_user", "new-password")

    after = UserQuery().get("pw_change_user").password
    assert after != before


def test_update_password_on_a_nonexistent_username_raises_404(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.update_password("ghost", "new-password")
    assert excinfo.value.status_code == 404


def test_get_user_raises_404_when_missing(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.get_user("ghost")
    assert excinfo.value.status_code == 404


def test_get_user_logged_resolves_permissions_for_an_active_role(database: Database, set_permissions):
    set_permissions(can_assign=ConfigUser(root=False, admin=True, user=False, soport=False))
    UserController.new_user(_new_user("logged_admin", role=RoleTypes.ADMIN))

    logged = UserController.get_user_logged("logged_admin")

    assert logged.can_assign is True
    assert logged.username == "logged_admin"


def test_get_user_logged_denies_every_permission_for_an_inactive_user(database: Database, set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=True, user=True, soport=True))
    UserController.new_user(_new_user("logged_inactive", role=RoleTypes.USER, status=UserStatusTypes.INACTIVE))

    logged = UserController.get_user_logged("logged_inactive")

    assert logged.can_assign is False
    assert logged.can_receive_assignment is False
    assert logged.view_information_global is False


def test_get_user_logged_raises_404_when_missing(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.get_user_logged("ghost")
    assert excinfo.value.status_code == 404


def test_get_all_users_includes_deleted(database: Database):
    UserController.new_user(_new_user("all_active", status=UserStatusTypes.ACTIVE))
    UserController.new_user(_new_user("all_deleted", status=UserStatusTypes.DELETED))

    usernames = {user.username for user in UserController.get_all_users()}
    assert usernames == {"all_active", "all_deleted"}


def test_get_users_excludes_deleted(database: Database):
    UserController.new_user(_new_user("visible_active", status=UserStatusTypes.ACTIVE))
    UserController.new_user(_new_user("visible_deleted", status=UserStatusTypes.DELETED))

    usernames = {user.username for user in UserController.get_users()}
    assert usernames == {"visible_active"}


def test_get_deleted_users_only_returns_deleted(database: Database):
    UserController.new_user(_new_user("del_active", status=UserStatusTypes.ACTIVE))
    UserController.new_user(_new_user("del_deleted", status=UserStatusTypes.DELETED))

    usernames = {user.username for user in UserController.get_deleted_users()}
    assert usernames == {"del_deleted"}


def test_get_users_by_category_filters_status_and_role_together(database: Database):
    UserController.new_user(_new_user("cat_active_admin", role=RoleTypes.ADMIN, status=UserStatusTypes.ACTIVE))
    UserController.new_user(_new_user("cat_active_user", role=RoleTypes.USER, status=UserStatusTypes.ACTIVE))
    UserController.new_user(_new_user("cat_inactive_admin", role=RoleTypes.ADMIN, status=UserStatusTypes.INACTIVE))

    result = UserController.get_users_by_category(UserStatusTypes.ACTIVE, RoleTypes.ADMIN)
    assert [user.username for user in result] == ["cat_active_admin"]


def test_get_users_by_category_rejects_an_invalid_status(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.get_users_by_category("NOT_A_STATUS", RoleTypes.ADMIN)
    assert excinfo.value.status_code == 400


def test_get_users_by_category_rejects_an_invalid_role(database: Database):
    with pytest.raises(BusinessError) as excinfo:
        UserController.get_users_by_category(UserStatusTypes.ACTIVE, "NOT_A_ROLE")
    assert excinfo.value.status_code == 400
