from typing import Tuple, List
from math import ceil
from pandas import DataFrame
from icm.access import ChangeQuery, UpdateChangeModel
from icm.utils import HEADER_RESPONSE_INTERFACES_CHANGES, log
from icm.business.libs.code import ResponseCode
from icm.constants.fields import ChangeField


class ChangeController:
    """Class to manage change controller."""

    @staticmethod
    def new_interfaces(data: DataFrame) -> ResponseCode:
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
                return ResponseCode(
                    status=400,
                    message="Invalid header of data interfaces with changes to insert",
                )
            data[ChangeField.ASSIGNED] = None
            status_operation = ChangeController.delete_changes()
            if not status_operation:
                raise Exception()
            status_operation = query.insert(data=data)
            if not status_operation:
                raise Exception()
            return ResponseCode(status=201)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Change controller error. Failed to insert a new interfaces with changes. {error}"
            )
            return ResponseCode(status=500)

    @staticmethod
    def get_interfaces_with_changes(
        page: int = 1, page_size: int = 100
    ) -> Tuple[ResponseCode, dict]:
        """Get interfaces with changes (paginated).

        Returns
        -------
        Tuple[ResponseCode, dict]
            Response code and paginated result with metadata.
        """
        try:
            query = ChangeQuery()
            data, total = query.get_all(page=page, page_size=page_size)
            return ResponseCode(status=200), {
                "items": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": ceil(total / page_size),
            }
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Change controller error. Failed to get interfaces with changes. {error}"
            )
            return ResponseCode(status=500), {}

    @staticmethod
    def update_assignment(changes: List[UpdateChangeModel]) -> ResponseCode:
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
            return ResponseCode(status=200)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Change controller error. Failed to update assignment of changes. {error}"
            )
            return ResponseCode(status=500)

    @staticmethod
    def delete_changes() -> bool:
        """Delete changes.

        Returns
        -------
        ResponseCode
            Response code.
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
