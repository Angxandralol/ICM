from datetime import date

from sqlalchemy import CheckConstraint, Date, String, func
from sqlalchemy.orm import Mapped, mapped_column

from icm.constants import RoleTypes, UserField, UserStatusTypes
from icm.data.base import Base
from icm.data.constants.database import TableNames


class UserSchema(Base):
    """ORM schema of the `users` table."""

    __tablename__ = TableNames.USERS
    __table_args__ = (
        CheckConstraint(
            f"{UserField.STATUS} IN ('{UserStatusTypes.ACTIVE}', "
            f"'{UserStatusTypes.INACTIVE}', '{UserStatusTypes.DELETED}')",
            name=f"{TableNames.USERS}_status",
        ),
        CheckConstraint(
            f"{UserField.ROLE} IN ('{RoleTypes.ADMIN}', '{RoleTypes.ROOT}', "
            f"'{RoleTypes.USER}', '{RoleTypes.SOPORT}')",
            name=f"{TableNames.USERS}_role",
        ),
    )

    username: Mapped[str] = mapped_column(String(20), primary_key=True)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    lastname: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[date | None] = mapped_column(Date, server_default=func.current_date())
    updated_at: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)
