import pandas as pd
from typing import List
from fastapi import status as http_status
from icm.access import (
    AssignmentQuery,
    ChangeQuery,
    UserQuery,
    ReassignmentModel,
    UpdateChangeModel,
    UpdateAssignmentModel as AccessUpdateAssignmentModel,
)
from icm.constants import AssignmentStatusTypes
from icm.utils import OperationData, Validate, log
from icm.constants.fields import ChangeField
from icm.business.exceptions import BusinessError
from icm.business.models.assignment import NewAssignmentModel, UpdateAssignmentModel


class AssignmentController:
    """Class to manage assignment controller."""

    @staticmethod
    def new_assignment(assignments: List[NewAssignmentModel]) -> None:
        """Insert a new assignment.

        Parameters
        ----------
        assignment : NewAssignmentModel
            Assignment to insert.
        """
        try:
            assignment_query = AssignmentQuery()
            data = pd.DataFrame([assignment.model_dump() for assignment in assignments])
            status_operation = assignment_query.insert(data=data)
            if not status_operation:
                raise Exception()
            changes: List[UpdateChangeModel] = []
            for assignment in assignments:
                changes.append(
                    UpdateChangeModel(
                        id_old=assignment.old_interface_id,
                        id_new=assignment.current_interface_id,
                        username=assignment.username,
                    )
                )
            change_query = ChangeQuery()
            status_operation = change_query.update_assign(data=changes)
            if not status_operation:
                raise Exception()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to insert a new assignment. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to insert a new assignment")

    @staticmethod
    def reassign(assignments: List[ReassignmentModel]) -> None:
        """Reassign assignments.

        Parameters
        ----------
        assignment : List[ReassignmentModel]
            Assignment to reassign.
        """
        try:
            query = AssignmentQuery()
            status_operation = query.reassing(data=assignments)
            if not status_operation:
                raise Exception()
            changes: List[UpdateChangeModel] = []
            for assignment in assignments:
                changes.append(
                    UpdateChangeModel(
                        id_old=assignment.old_interface_id,
                        id_new=assignment.current_interface_id,
                        username=assignment.new_username,
                    )
                )
            change_query = ChangeQuery()
            status_operation = change_query.update_assign(data=changes)
            if not status_operation:
                raise Exception()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to reassign assignments. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to reassign assignments")

    @staticmethod
    def automatic_assignment(assign_by: str, usernames: List[str]) -> None:
        """Automatic assignment."""
        try:
            if not usernames:
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "No users found")
            change_query = ChangeQuery()
            assign_query = AssignmentQuery()
            changes = change_query.get_all_unassigned()
            if not changes:
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "No change interfaces found")
            total_users = len(usernames)
            total_changes = len(changes)
            base = total_changes // total_users
            rest = total_changes % total_users
            new_assignments: List[NewAssignmentModel] = []
            start = 0
            for i, username in enumerate(usernames):
                count = base + (1 if i < rest else 0)
                for change in changes[start : start + count]:
                    new_assignments.append(
                        NewAssignmentModel(
                            old_interface_id=change[ChangeField.ID_OLD],
                            current_interface_id=change[ChangeField.ID_NEW],
                            username=username,
                            assign_by=assign_by,
                            type_status=AssignmentStatusTypes.PENDING,
                        )
                    )
                start += count
            data = pd.DataFrame([assignment.model_dump() for assignment in new_assignments])
            status_operation = assign_query.insert(data=data)
            if not status_operation:
                raise Exception()
            update_changes: List[UpdateChangeModel] = [
                UpdateChangeModel(
                    id_old=assignment.old_interface_id,
                    id_new=assignment.current_interface_id,
                    username=assignment.username,
                )
                for assignment in new_assignments
            ]
            status_operation = change_query.update_assign(data=update_changes)
            if not status_operation:
                raise Exception()
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to automatic assignment. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to automatic assignment")

    @staticmethod
    def update_status_assignment(
        assignments: List[UpdateAssignmentModel], username: str
    ) -> None:
        """Update assignments status.

        Parameters
        ----------
        assignment : List[UpdateAssignmentModel]
            Assignment to update status.
        """
        try:
            query = AssignmentQuery()
            list_assingments: List[AccessUpdateAssignmentModel] = []
            for assignment in assignments:
                list_assingments.append(
                    AccessUpdateAssignmentModel(
                        old_interface_id=assignment.old_interface_id,
                        current_interface_id=assignment.current_interface_id,
                        username=username,
                        type_status=assignment.type_status,
                    )
                )
            status_operation = query.update_status(data=list_assingments)
            if not status_operation:
                raise Exception()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to update assignments status. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update assignments status")

    @staticmethod
    def get_all_assignments_filter_by_status(status: str) -> List[dict]:
        """Get all assignments filter by a status.

        Parameters
        ----------
        status : str
            Status to get assignments.

        Returns
        -------
        List[dict]
            Assignments filtered by status.
        """
        try:
            query = AssignmentQuery()
            if not Validate.assignment_status(status=status):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid status")
            data = query.get_all_by_status(status=status)
            if data.empty:
                return []
            return OperationData.transform_to_json(data=data)
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to get assignments by status. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get assignments by status")

    @staticmethod
    def get_user_assignments_filter_by_status(username: str, status: str) -> List[dict]:
        """Get user assignments filter by a status.

        Parameters
        ----------
        username : str
            Username to get assignments.
        status : str
            Status to get assignments.

        Returns
        -------
        List[dict]
            Assignments of the user filtered by status.
        """
        try:
            if not Validate.assignment_status(status=status):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid status")
            user_query = UserQuery()
            if not user_query.get(username=username):
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "User not found")
            query = AssignmentQuery()
            data = query.assigned_by_status(username=username, status=status)
            if data.empty:
                return []
            return OperationData.transform_to_json(data=data)
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to get assignments by username and status. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get assignments by username and status")

    @staticmethod
    def get_user_assignments_completed_in_month(username: str, date: str) -> List[dict]:
        """Get user assignments completed in a month.

        Parameters
        ----------
        username : str
            Username to get assignments.
        date : str
            Month to get assignments (YYYY-MM).

        Returns
        -------
        List[dict]
            Assignments of the user completed in the given month.
        """
        try:
            if not Validate.month_date(date):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid date")
            user_query = UserQuery()
            if not user_query.get(username=username):
                raise BusinessError(http_status.HTTP_404_NOT_FOUND, "User not found")
            query = AssignmentQuery()
            data = query.completed_by_month(username=username, date=date)
            if data.empty:
                return []
            return OperationData.transform_to_json(data=data)
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to get assignments completed in month. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get assignments completed in month")

    @staticmethod
    def get_users_assignments_completed_in_month(usernames: List[str], date: str) -> List[dict]:
        """Get assignments completed in a month of all users.

        Parameters
        ----------
        usernames : List[str]
            Usernames to get assignments.
        date : str
            Month to get assignments (YYYY-MM).

        Returns
        -------
        List[dict]
            Assignments of all users completed in the given month.
        """
        try:
            response = []
            if not Validate.month_date(date):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid date")
            for username in usernames:
                user_query = UserQuery()
                if not user_query.get(username=username):
                    continue
                query = AssignmentQuery()
                data = query.completed_by_month(username=username, date=date)
                if data.empty:
                    continue
                data = OperationData.transform_to_json(data=data)
                if not response:
                    response = data
                else:
                    response = response + data
            return response
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Assignment controller error. Failed to get assignments completed in month. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get assignments completed in month")

    @staticmethod
    def get_date_available_to_consult_history() -> List[str]:
        """Get every distinct month with at least one assignment.

        Returns
        -------
        List[str]
            Months (YYYY-MM) available to consult, most recent first.
        """
        try:
            query = AssignmentQuery()
            return query.date_available_to_consult_history()
        except Exception as error:
            log.error(
                f"Assignment controller error. Failed to get date availables to consult history. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get date availables to consult history")

    @staticmethod
    def get_statistics_assignments(usernames: List[str]) -> List[dict]:
        """Get statistics of assignments.

        Parameters
        ----------
        usernames : List[str]
            Usernames to get statistics.

        Returns
        -------
        List[dict]
            Statistics of assignments by username.
        """
        try:
            query = AssignmentQuery()
            data = query.get_statistics(usernames=usernames)
            if not data:
                return []
            return OperationData.transform_to_json(data=data)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Assignment controller error. Failed to get statistics. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get statistics")
