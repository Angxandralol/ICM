from datetime import date
from typing import List
from icm.access.querys.query import Query
from icm.access.utils.adapter import AdapterUser
from icm.access.models.user import UserModel
from icm.constants import UserStatusTypes
from icm.data import UserSchema
from icm.utils import log


class UserQuery(Query):
    """Class to manage user query."""

    def __init__(self):
        super().__init__()

    def insert(self, new_user: UserModel) -> bool:
        """Insert user in database.

        Parameters
        ----------
        new_user : UserModel
            User to insert.

        Returns
        -------
        bool
            True if the user was inserted successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                session.add(
                    UserSchema(
                        username=new_user.username.lower(),
                        password=new_user.password,
                        name=new_user.name.capitalize(),
                        lastname=new_user.lastname.capitalize(),
                        status=new_user.status.upper(),
                        role=new_user.role.upper(),
                    )
                )
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User query error. Failed to insert user. {error}")
            return False
        else:
            return True

    def update(self, user: UserModel) -> bool:
        """Update user in database. Without password.

        Parameters
        ----------
        user : UserModel
            User to update.

        Returns
        -------
        bool
            True if the user was updated successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                row = session.get(UserSchema, user.username)
                if row is None:
                    return False
                row.name = user.name.capitalize()
                row.lastname = user.lastname.capitalize()
                row.status = user.status.upper()
                row.role = user.role.upper()
                row.updated_at = date.today()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User query error. Failed to update user. {error}")
            return False
        else:
            return True

    def update_password(self, username: str, password: str) -> bool:
        """Update password in database.

        Parameters
        ----------
        username : str
            Username to update password.
        password : str
            Password to update.

        Returns
        -------
        bool
            True if the password was updated successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                row = session.get(UserSchema, username)
                if row is None:
                    return False
                row.password = password
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User query error. Failed to update password. {error}")
            return False
        else:
            return True

    def delete(self, usernames: List[str]) -> bool:
        """Delete users.

        Parameters
        ----------
        usernames : List[str]
            Usernames to delete.

        Returns
        -------
        bool
            True if the users were deleted successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                session.query(UserSchema).filter(
                    UserSchema.username.in_(usernames)
                ).delete(synchronize_session=False)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User query error. Failed to delete users. {error}")
            return False
        else:
            return True

    def get(self, username: str) -> UserModel | None:
        """Get a user.

        Parameters
        ----------
        username : str
            Username to get user.

        Returns
        -------
        UserModel
            User.
        """
        try:
            with self.database.session() as session:
                row = session.get(UserSchema, username)
                if row is None:
                    return None
                user = AdapterUser.response([row])
                return user[0] if user else None
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User service error. Failed to get user by username. {error}")
            return None

    def get_all(self) -> List[UserModel]:
        """Get all users."""
        try:
            with self.database.session() as session:
                rows = session.query(UserSchema).all()
                return AdapterUser.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User service error. Failed to get users. {error}")
            return []

    def get_users(self) -> List[UserModel]:
        """Get users without deleted."""
        try:
            with self.database.session() as session:
                rows = (
                    session.query(UserSchema)
                    .filter(UserSchema.status != UserStatusTypes.DELETED)
                    .all()
                )
                return AdapterUser.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User service error. Failed to get users. {error}")
            return []

    def get_deleted(self) -> List[UserModel]:
        """Get deleted users."""
        try:
            with self.database.session() as session:
                rows = (
                    session.query(UserSchema)
                    .filter(UserSchema.status == UserStatusTypes.DELETED)
                    .all()
                )
                return AdapterUser.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User service error. Failed to get users. {error}")
            return []

    def get_users_by_category(self, status: str, role: str) -> List[UserModel]:
        """Get users by a category. The category is a status with a role.

        Parameters
        ----------
        status : str
            Status to get users. The status can be ACTIVE, INACTIVE or DELETED.
        role : str
            Role to get users. The role can be ADMIN, ROOT, USER or SOPORT.

        Returns
        -------
        List[UserModel]
            Users matching the status and role.
        """
        try:
            with self.database.session() as session:
                rows = (
                    session.query(UserSchema)
                    .filter(UserSchema.status == status, UserSchema.role == role)
                    .all()
                )
                return AdapterUser.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"User service error. Failed to get users. {error}")
            return []
