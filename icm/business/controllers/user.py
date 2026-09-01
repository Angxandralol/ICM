from typing import List
from fastapi import status as http_status
from icm.access import UserQuery
from icm.constants import UserStatusTypes
from icm.utils import Validate, log
from icm.business.exceptions import BusinessError
from icm.business.controllers.config import ConfigController
from icm.business.controllers.security import SecurityController
from icm.business.models.user import UserModel, UserLoggedModel, UpdateUserModel


class UserController:
    """Class to manage user controller."""

    @staticmethod
    def new_user(new_user: UserModel) -> None:
        """Insert a new user.

        Parameters
        ----------
        new_user : UserModel
            User to insert.
        """
        try:
            query = UserQuery()
            if query.get(username=new_user.username):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid username")
            if not Validate.role(role=new_user.role):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid role")
            if not Validate.status(status=new_user.status):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid status")
            security = SecurityController()
            hashed_password = security.create_password_hash(password=new_user.password)
            new_user.password = hashed_password
            status_operation = query.insert(new_user=new_user)
            if not status_operation:
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Failed to insert user")
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to insert a new user. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to insert a new user")

    @staticmethod
    def update_user(update_user: UpdateUserModel) -> None:
        """Update a user.

        Parameters
        ----------
        user : UserModel
            User to update.
        """
        try:
            query = UserQuery()
            if not query.get(username=update_user.username):
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "User not found to update")
            if not Validate.role(role=update_user.role):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid role")
            if not Validate.status(status=update_user.status):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid status")
            user = UserModel(
                username=update_user.username,
                password="",
                name=update_user.name,
                lastname=update_user.lastname,
                status=update_user.status,
                role=update_user.role,
                created_at=None,
                updated_at=None
            )
            status_operation = query.update(user=user)
            if not status_operation:
                raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update user")
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to update a user. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update a user")

    @staticmethod
    def update_password(username: str, password: str) -> None:
        """Update password of a user.

        Parameters
        ----------
        username : str
            Username to update password.
        password : str
            Password to update.
        """
        try:
            query = UserQuery()
            if not query.get(username=username):
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "User not found to update")
            security = SecurityController()
            hashed_password = security.create_password_hash(password=password)
            status_operation = query.update_password(username=username, password=hashed_password)
            if not status_operation:
                raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update password")
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to update password. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update password")

    @staticmethod
    def get_user(username: str) -> UserModel:
        """Get a user.

        Parameters
        ----------
        username : str
            Username to get user.

        Returns
        -------
        UserModel
            User found.
        """
        try:
            query = UserQuery()
            user = query.get(username=username)
            if not user:
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "User not found")
            return user
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to get a user. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get a user")

    @staticmethod
    def get_user_logged(username: str) -> UserLoggedModel:
        """Get user logged.

        Parameters
        ----------
        username : str
            Username to get user logged.

        Returns
        -------
        UserLoggedModel
            User logged, with its permissions resolved.
        """
        try:
            query = UserQuery()
            user = query.get(username=username)
            if not user:
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "User not found")
            config = ConfigController.get_config()
            if user.status == UserStatusTypes.ACTIVE:
                role_key = user.role.lower()
                can_assign = getattr(config.can_assign, role_key, False)
                can_receive_assignment = getattr(config.can_receive_assignment, role_key, False)
                view_information_global = getattr(config.view_information_global, role_key, False)
            else:
                can_assign = False
                can_receive_assignment = False
                view_information_global = False
            return UserLoggedModel(
                username=user.username,
                name=user.name,
                lastname=user.lastname,
                status=user.status,
                role=user.role,
                can_assign=can_assign,
                can_receive_assignment=can_receive_assignment,
                view_information_global=view_information_global
            )
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to get a user logged. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get a user logged")

    @staticmethod
    def get_all_users() -> List[UserModel]:
        """Get all users.

        Returns
        -------
        List[UserModel]
            All users, including deleted ones.
        """
        try:
            query = UserQuery()
            return query.get_all() or []
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to get all users. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get all users")

    @staticmethod
    def get_users() -> List[UserModel]:
        """Get users without deleted."""
        try:
            query = UserQuery()
            return query.get_users() or []
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to get users. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get users")

    @staticmethod
    def get_deleted_users() -> List[UserModel]:
        """Get deleted users."""
        try:
            query = UserQuery()
            return query.get_deleted() or []
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to get users. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get deleted users")

    @staticmethod
    def get_users_by_category(status: str, role: str) -> List[UserModel]:
        """Get users by a category.

        Parameters
        ----------
        status : str
            Status to get users. The status can be ACTIVE, INACTIVE or DELETED.
        role : str
            Role to get users. The role can be ADMIN, ROOT, USER or SOPORT.

        Returns
        -------
        List[UserModel]
            Users matching the given status and role.
        """
        try:
            query = UserQuery()
            if not Validate.status(status=status):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid status")
            if not Validate.role(role=role):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid role")
            return query.get_users_by_category(status=status, role=role) or []
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User controller error. Failed to get users by category. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get users by category")
