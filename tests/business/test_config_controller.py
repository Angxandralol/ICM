from icm.business.controllers.config import ConfigController
from icm.business.models.configuration import ConfigUser
from icm.constants import RoleTypes


def test_get_config_returns_a_populated_model():
    config = ConfigController.get_config()

    assert config.can_assign is not None
    assert config.can_receive_assignment is not None
    assert config.view_information_global is not None
    assert config.notification_changes is not None


def test_new_config_is_reflected_immediately_by_get_config(set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=True))

    config = ConfigController.get_config()

    assert config.can_assign.root is True
    assert config.can_assign.admin is False
    assert config.can_assign.soport is True


def test_can_assign_permission_reads_the_role_specific_flag(set_permissions):
    set_permissions(can_assign=ConfigUser(root=True, admin=False, user=False, soport=False))

    assert ConfigController.can_assign_permission(RoleTypes.ROOT) is True
    assert ConfigController.can_assign_permission(RoleTypes.ADMIN) is False
    assert ConfigController.can_assign_permission(RoleTypes.USER) is False
    assert ConfigController.can_assign_permission(RoleTypes.SOPORT) is False


def test_can_assign_permission_returns_false_for_an_unknown_role():
    assert ConfigController.can_assign_permission("NOT_A_ROLE") is False


def test_can_view_information_global_permission_reads_the_role_specific_flag(set_permissions):
    set_permissions(
        view_information_global=ConfigUser(root=False, admin=False, user=True, soport=False)
    )

    assert ConfigController.can_view_information_global_permission(RoleTypes.USER) is True
    assert ConfigController.can_view_information_global_permission(RoleTypes.ADMIN) is False


def test_can_view_information_global_permission_returns_false_for_an_unknown_role():
    assert ConfigController.can_view_information_global_permission("NOT_A_ROLE") is False
