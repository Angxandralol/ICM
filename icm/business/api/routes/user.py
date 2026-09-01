from fastapi import APIRouter
from icm.business.api.dependencies import AssignPermissionUser, CurrentUser
from icm.business.constants.tags import ApiTags
from icm.business.controllers.user import UserController
from icm.business.models.response import MessageResponse
from icm.business.models.user import UserLoggedModel, UserPublicModel, UpdatePasswordModel, UpdateUserModel


router = APIRouter(prefix="/user", tags=[ApiTags.USERS])


@router.get("/info", response_model=UserLoggedModel)
def get_user(user: CurrentUser):
    """Get user logged."""
    return UserController.get_user_logged(username=user.username)


@router.get("/all", response_model=list[UserPublicModel])
def get_users(user: AssignPermissionUser):
    """Get all users active."""
    return UserController.get_users()


@router.put("/info", response_model=MessageResponse)
def update_user(new_user: UpdateUserModel, user: AssignPermissionUser):
    """Update user."""
    UserController.update_user(update_user=new_user)
    return MessageResponse(message="User updated successfully")


@router.patch("/info/password", response_model=MessageResponse)
def update_password(request: UpdatePasswordModel, user: CurrentUser):
    """Update password of the logged-in user."""
    UserController.update_password(username=user.username, password=request.password)
    return MessageResponse(message="Password updated successfully")
