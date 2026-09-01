from typing import List
from math import ceil
from pandas import DataFrame
from fastapi import status as http_status
from icm.access import ChangeQuery, UpdateChangeModel
from icm.utils import HEADER_RESPONSE_INTERFACES_CHANGES, log
from icm.business.exceptions import BusinessError
from icm.business.models.change import PaginatedChanges
from icm.constants.fields import ChangeField


class ChangeController:
    """Class to manage change controller."""

    @staticmethod
    def new_interfaces(data: DataFrame) -> None:
        """Insert a new interface.

        Parameters
        ----------
        data : DataFrame
            Data with information of interfaces with their changes.
        """
        try:
            query = ChangeQuery()
            header_data = data.columns.tolist()
            if not header_data == HEADER_RESPONSE_INTERFACES_CHANGES:
                raise BusinessError(
                    http_status.HTTP_400_BAD_REQUEST,
                    "Invalid header of data interfaces with changes to insert",
                )
            data[ChangeField.ASSIGNED] = None
            status_operation = ChangeController.delete_changes()
            if not status_operation:
                raise Exception()
            status_operation = query.insert(data=data)
            if not status_operation:
                raise Exception()
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Change controller error. Failed to insert a new interfaces with changes. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to insert a new interfaces with changes")

    @staticmethod
    def get_interfaces_with_changes(page: int = 1, page_size: int = 100) -> PaginatedChanges:
        """Get interfaces with changes (paginated).

        Returns
        -------
        PaginatedChanges
            Paginated result with metadata.
        """
        try:
            query = ChangeQuery()
            data, total = query.get_all(page=page, page_size=page_size)
            return PaginatedChanges(
                items=data,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=ceil(total / page_size),
            )
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Change controller error. Failed to get interfaces with changes. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get interfaces with changes")

    @staticmethod
    def update_assignment(changes: List[UpdateChangeModel]) -> None:
        """Update assignment of changes.

        Parameters
        ----------
        changes : List[UpdateChangeModel]
            Data to update.
        """
        try:
            query = ChangeQuery()
            status_operation = query.update_assign(data=changes)
            if not status_operation:
                raise Exception()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Change controller error. Failed to update assignment of changes. {error}"
            )
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update assignment of changes")

    @staticmethod
    def delete_changes() -> bool:
        """Delete changes.

        Returns
        -------
        bool
            True if the changes were deleted successfully, False otherwise.
        """
        try:
            query = ChangeQuery()
            status_operation = query.delete_changes()
            if not status_operation:
                raise Exception()
            return True
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Change controller error. Failed to delete changes. {error}")
            return False
