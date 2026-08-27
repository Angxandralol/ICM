from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from icm.constants import AssignmentField, AssignmentStatusTypes, InterfaceField, UserField
from icm.data.base import Base
from icm.data.constants.database import TableNames


class AssignmentSchema(Base):
    """ORM schema of the `assignments` table.

    Tracks who has to review one specific detected change (a pair of
    `interfaces` rows) and its follow-up status. Unlike `changes`, this
    table is never truncated: it is the historical log used for statistics.
    `(old_interface_id, current_interface_id)` identifies that single
    detected change for its whole lifetime, so it is kept unique to prevent
    the same change from ever being assigned to two users at once.
    """

    __tablename__ = TableNames.ASSIGNMENTS
    __table_args__ = (
        CheckConstraint(
            f"{AssignmentField.TYPE_STATUS} IN ("
            f"'{AssignmentStatusTypes.PENDING}', '{AssignmentStatusTypes.INSPECTED}', "
            f"'{AssignmentStatusTypes.REDISCOVERED}', '{AssignmentStatusTypes.EQUIPMENT_DOWN}')",
            name=f"{TableNames.ASSIGNMENTS}_status",
        ),
        UniqueConstraint(
            AssignmentField.OLD_INTERFACE_ID,
            AssignmentField.CURRENT_INTERFACE_ID,
            name=f"{TableNames.ASSIGNMENTS}_change_unique",
        ),
        Index(
            f"ix_{TableNames.ASSIGNMENTS}_{AssignmentField.USERNAME}_status",
            AssignmentField.USERNAME,
            AssignmentField.TYPE_STATUS,
        ),
        Index(
            f"ix_{TableNames.ASSIGNMENTS}_{AssignmentField.USERNAME}_created",
            AssignmentField.USERNAME,
            AssignmentField.CREATED_AT,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    old_interface_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{TableNames.INTERFACES}.{InterfaceField.ID}"), nullable=False
    )
    current_interface_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{TableNames.INTERFACES}.{InterfaceField.ID}"), nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(100), ForeignKey(f"{TableNames.USERS}.{UserField.USERNAME}"), nullable=False
    )
    assign_by: Mapped[str] = mapped_column(
        String(100), ForeignKey(f"{TableNames.USERS}.{UserField.USERNAME}"), nullable=False
    )
    type_status: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[date | None] = mapped_column(
        Date, server_default=func.current_date(), index=True
    )
    updated_at: Mapped[date | None] = mapped_column(Date, nullable=True, default=None)

    old_interface: Mapped["InterfaceSchema"] = relationship(
        "InterfaceSchema", foreign_keys=[old_interface_id]
    )
    current_interface: Mapped["InterfaceSchema"] = relationship(
        "InterfaceSchema", foreign_keys=[current_interface_id]
    )
    user: Mapped["UserSchema"] = relationship("UserSchema", foreign_keys=[username])
    assigned_by_user: Mapped["UserSchema"] = relationship(
        "UserSchema", foreign_keys=[assign_by]
    )
