from typing import Annotated
from fastapi import Depends, status as http_status
from icm.constants import RoleTypes
from icm.business.controllers.config import ConfigController
from icm.business.controllers.security import SecurityController
from icm.business.exceptions import BusinessError
from icm.business.models.user import UserModel


CurrentUser = Annotated[UserModel, Depends(SecurityController.get_current_user)]


def require_assign_permission(user: CurrentUser) -> UserModel:
    """Require a role with permission to assign work / manage administrative resources."""
    if not ConfigController.can_assign_permission(role=user.role):
        raise BusinessError(http_status.HTTP_403_FORBIDDEN, "User not authorized to perform this action")
    return user


def require_view_global_permission(user: CurrentUser) -> UserModel:
    """Require a role with permission to view global (all-users) information."""
    if not ConfigController.can_view_information_global_permission(role=user.role):
        raise BusinessError(http_status.HTTP_403_FORBIDDEN, "User not authorized to view global information")
    return user


def require_root_role(user: CurrentUser) -> UserModel:
    """Require the root role."""
    if user.role != RoleTypes.ROOT:
        raise BusinessError(http_status.HTTP_403_FORBIDDEN, "User not authorized")
    return user


AssignPermissionUser = Annotated[UserModel, Depends(require_assign_permission)]
ViewGlobalPermissionUser = Annotated[UserModel, Depends(require_view_global_permission)]
RootUser = Annotated[UserModel, Depends(require_root_role)]
