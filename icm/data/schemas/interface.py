from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from icm.constants import InterfaceField
from icm.data.base import Base
from icm.data.constants.database import TableNames


class InterfaceSchema(Base):
    """ORM schema of the `interfaces` table.

    Each row is a daily snapshot of a single interface of a single device.
    A new consult never updates a row in place: it always inserts a fresh
    one, so the same physical interface accumulates one row per day.
    """

    __tablename__ = TableNames.INTERFACES
    __table_args__ = (
        UniqueConstraint(
            InterfaceField.IP,
            InterfaceField.COMMUNITY,
            InterfaceField.SYSNAME,
            InterfaceField.IFINDEX,
            InterfaceField.CONSULTED_AT,
            name=f"{TableNames.INTERFACES}_unique",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(15), nullable=False)
    community: Mapped[str] = mapped_column(String, nullable=False)
    sysname: Mapped[str] = mapped_column(String, nullable=False)
    ifIndex: Mapped[int] = mapped_column(Integer, nullable=False)
    ifName: Mapped[str | None] = mapped_column(String, nullable=True)
    ifDescr: Mapped[str | None] = mapped_column(String, nullable=True)
    ifAlias: Mapped[str | None] = mapped_column(String, nullable=True)
    ifHighSpeed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ifOperStatus: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ifAdminStatus: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consulted_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
