import pytest

from icm.business.api.dependencies import (
    require_assign_permission,
    require_root_role,
    require_view_global_permission,
)
from icm.business.exceptions import BusinessError
from icm.business.models.configuration import ConfigUser
from icm.business.models.user import UserModel
from icm.constants import RoleTypes, UserStatusTypes


def _user(role: str) -> UserModel:
    return UserModel(
        username="dep_user", password="hashed", name="Dep", lastname="User",
        role=role, status=UserStatusTypes.ACTIVE, created_at=None, updated_at=None,
    )


def test_require_assign_permission_allows_a_permitted_role(set_permissions):
    set_permissions(can_assign=ConfigUser(root=False, admin=True, user=False, soport=False))

    user = _user(RoleTypes.ADMIN)
    assert require_assign_permission(user) is user


def test_require_assign_permission_rejects_a_role_without_permission(set_permissions):
    set_permissions(can_assign=ConfigUser(root=False, admin=False, user=False, soport=False))

    with pytest.raises(BusinessError) as excinfo:
        require_assign_permission(_user(RoleTypes.ADMIN))
    assert excinfo.value.status_code == 403


def test_require_view_global_permission_allows_a_permitted_role(set_permissions):
    set_permissions(view_information_global=ConfigUser(root=False, admin=False, user=True, soport=False))

    user = _user(RoleTypes.USER)
    assert require_view_global_permission(user) is user


def test_require_view_global_permission_rejects_a_role_without_permission(set_permissions):
    set_permissions(view_information_global=ConfigUser(root=False, admin=False, user=False, soport=False))

    with pytest.raises(BusinessError) as excinfo:
        require_view_global_permission(_user(RoleTypes.USER))
    assert excinfo.value.status_code == 403


def test_require_root_role_allows_root():
    user = _user(RoleTypes.ROOT)
    assert require_root_role(user) is user


def test_require_root_role_rejects_every_other_role():
    with pytest.raises(BusinessError) as excinfo:
        require_root_role(_user(RoleTypes.ADMIN))
    assert excinfo.value.status_code == 403
