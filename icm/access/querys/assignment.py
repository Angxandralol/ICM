import pandas as pd
from datetime import date
from typing import List
from sqlalchemy import and_, case, desc, func, insert, select, update
from sqlalchemy.orm import joinedload
from icm.constants import AssignmentStatusTypes, StatisticsField
from icm.data import AssignmentSchema, UserSchema
from icm.utils import log
from icm.access.models.assignment import ReassignmentModel, UpdateAssignmentModel, StatisticsModel
from icm.access.querys.query import Query
from icm.access.utils.adapter import AdapterAssignment
from icm.access.utils.frame import dataframe_to_rows


class AssignmentQuery(Query):
    """Class to manage assignment query."""

    def __init__(self):
        super().__init__()

    def insert(self, data: pd.DataFrame) -> bool:
        """Insert assignments in database.

        Parameters
        ----------
        data : pd.DataFrame
            Assignments to insert. Columns must match `AssignmentSchema`'s
            attribute names.

        Returns
        -------
        bool
            True if the data was inserted successfully, False otherwise.
        """
        try:
            rows = dataframe_to_rows(data)
            with self.database.session() as session:
                session.execute(insert(AssignmentSchema), rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment query error. Failed to insert assignment. {error}")
            return False
        else:
            return True

    def reassing(self, data: List[ReassignmentModel]) -> bool:
        """Reassing assignments in database.

        Parameters
        ----------
        data : List[ReassignmentModel]
            Data to reassign.

        Returns
        -------
        bool
            True if the data was updated successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                for assignment in data:
                    session.execute(
                        update(AssignmentSchema)
                        .where(
                            AssignmentSchema.old_interface_id == assignment.old_interface_id,
                            AssignmentSchema.current_interface_id == assignment.current_interface_id,
                            AssignmentSchema.username == assignment.old_username,
                        )
                        .values(
                            username=assignment.new_username,
                            assign_by=assignment.assign_by.lower(),
                            type_status=AssignmentStatusTypes.PENDING,
                            created_at=func.current_date(),
                            updated_at=None,
                        )
                    )
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment query error. Failed to insert assignment. {error}")
            return False
        else:
            return True

    def update_status(self, data: List[UpdateAssignmentModel]) -> bool:
        """Update assignments in database.

        Parameters
        ----------
        data : List[UpdateAssignmentModel]
            Data to update.

        Returns
        -------
        bool
            True if the data was updated successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                for assignment in data:
                    session.execute(
                        update(AssignmentSchema)
                        .where(
                            AssignmentSchema.old_interface_id == assignment.old_interface_id,
                            AssignmentSchema.current_interface_id == assignment.current_interface_id,
                            AssignmentSchema.username == assignment.username,
                        )
                        .values(
                            type_status=assignment.type_status,
                            updated_at=func.current_date(),
                        )
                    )
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment query error. Failed to update assignment. {error}")
            return False
        else:
            return True

    def get_all_by_status(self, status: str) -> pd.DataFrame:
        """Get all assignments by status.

        Parameters
        ----------
        status : str
            Status to get assignments.

        Returns
        -------
        DataFrame
            DataFrame with all assignments.
        """
        try:
            with self.database.session() as session:
                rows = (
                    session.query(AssignmentSchema)
                    .options(
                        joinedload(AssignmentSchema.old_interface),
                        joinedload(AssignmentSchema.current_interface),
                        joinedload(AssignmentSchema.user),
                    )
                    .filter(AssignmentSchema.type_status == status)
                    .all()
                )
                return AdapterAssignment.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment query error. Failed to get assignments by status. {error}")
            return pd.DataFrame()

    def assigned_by_status(self, username: str, status: str) -> pd.DataFrame:
        """Get all assignments of a user by status.

        Parameters
        ----------
        username : str
            Username to get assignments.
        status : str
            Status to get assignments.

        Returns
        -------
        pd.DataFrame
            DataFrame with all assignments.
        """
        try:
            with self.database.session() as session:
                rows = (
                    session.query(AssignmentSchema)
                    .options(
                        joinedload(AssignmentSchema.old_interface),
                        joinedload(AssignmentSchema.current_interface),
                        joinedload(AssignmentSchema.user),
                    )
                    .filter(
                        AssignmentSchema.username == username,
                        AssignmentSchema.type_status == status,
                    )
                    .all()
                )
                return AdapterAssignment.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment query error. Failed to get assignments by username and status. {error}"
            )
            return pd.DataFrame()

    def completed_by_month(self, username: str, date: int) -> pd.DataFrame:
        """Get all assignments completed of a user by filter month.

        Parameters
        ----------
        username : str
            Username to get assignments.
        date : int
            Month to get assignments (YYYY-MM).

        Returns
        -------
        pd.DataFrame
            DataFrame with all assignments.
        """
        try:
            with self.database.session() as session:
                rows = (
                    session.query(AssignmentSchema)
                    .options(
                        joinedload(AssignmentSchema.old_interface),
                        joinedload(AssignmentSchema.current_interface),
                        joinedload(AssignmentSchema.user),
                    )
                    .filter(
                        AssignmentSchema.username == username,
                        AssignmentSchema.type_status != AssignmentStatusTypes.PENDING,
                        func.to_char(AssignmentSchema.created_at, "YYYY-MM") == date,
                    )
                    .all()
                )
                return AdapterAssignment.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment query error. Failed to get assignments by username and month. {error}"
            )
            return pd.DataFrame()

    def date_available_to_consult_history(self) -> List[str]:
        """Get every distinct month with at least one assignment.

        Returns
        -------
        List[str]
            Months (YYYY-MM) available to consult, most recent first.
        """
        try:
            stmt = (
                select(func.to_char(AssignmentSchema.created_at, "YYYY-MM").label("unique_date"))
                .distinct()
                .order_by(desc("unique_date"))
            )
            with self.database.session() as session:
                return [row.unique_date for row in session.execute(stmt)]
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment query error. Failed to get available dates to consult history. {error}"
            )
            return []

    def get_statistics(self, usernames: List[str]) -> List[StatisticsModel]:
        """Get statistics of assignments by a list of usernames.

        Parameters
        ----------
        usernames : List[str]
            Usernames to get statistics.

        Returns
        -------
        List[StatisticsModel]
            Statistics of assignments by username.
        """
        try:
            today = date.today()
            same_month = func.extract("month", AssignmentSchema.created_at) == func.extract(
                "month", func.current_date()
            )

            def count_of(status: str, period):
                return func.count(case((and_(AssignmentSchema.type_status == status, period), 1)))

            stmt = (
                select(
                    count_of(AssignmentStatusTypes.PENDING, AssignmentSchema.created_at == today).label(
                        StatisticsField.TOTAL_PENDING_TODAY
                    ),
                    count_of(AssignmentStatusTypes.INSPECTED, AssignmentSchema.created_at == today).label(
                        StatisticsField.TOTAL_INSPECTED_TODAY
                    ),
                    count_of(AssignmentStatusTypes.REDISCOVERED, AssignmentSchema.created_at == today).label(
                        StatisticsField.TOTAL_REDISCOVERED_TODAY
                    ),
                    count_of(AssignmentStatusTypes.PENDING, same_month).label(
                        StatisticsField.TOTAL_PENDING_MONTH
                    ),
                    count_of(AssignmentStatusTypes.INSPECTED, same_month).label(
                        StatisticsField.TOTAL_INSPECTED_MONTH
                    ),
                    count_of(AssignmentStatusTypes.REDISCOVERED, same_month).label(
                        StatisticsField.TOTAL_REDISCOVERED_MONTH
                    ),
                    UserSchema.username.label(StatisticsField.USERNAME),
                    UserSchema.name.label(StatisticsField.NAME),
                    UserSchema.lastname.label(StatisticsField.LASTNAME),
                )
                .select_from(AssignmentSchema)
                .join(UserSchema, UserSchema.username == AssignmentSchema.username)
                .where(AssignmentSchema.username.in_(usernames))
                .group_by(UserSchema.username, UserSchema.name, UserSchema.lastname)
            )
            with self.database.session() as session:
                rows = session.execute(stmt).mappings().all()
                return AdapterAssignment.response_statistics(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment query error. Failed to get statistics. {error}")
            return []
