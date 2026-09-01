from typing import List
from datetime import datetime, timedelta
from pandas import DataFrame
from fastapi import status as http_status
from icm.access import InterfaceQuery
from icm.constants import InterfaceField
from icm.utils import OperationData, HEADER_RESPONSE_INTERFACES_CHANGES, Validate, log
from icm.business.constants.header import HEADER_CONSULT_SNMP
from icm.business.exceptions import BusinessError


class InterfaceController:
    """Class to manage interface controller."""

    @staticmethod
    def new_interfaces(interfaces: DataFrame) -> None:
        """Insert a new interface.

        Parameters
        ----------
        interfaces : DataFrame
            Interfaces to insert.
        """
        try:
            query = InterfaceQuery()
            header_data = interfaces.columns.tolist()
            if not header_data == HEADER_CONSULT_SNMP:
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid header of data interfaces to insert")
            status_operation = query.insert(data=interfaces)
            if not status_operation:
                raise Exception()
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to insert a new interfaces. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to insert a new interfaces")

    @staticmethod
    def reload_interfaces_by_date_consult(date: str, interfaces: DataFrame) -> None:
        """Delete all interfaces by a given date, then re-insert them with their new values.

        Parameters
        ----------
        date : str
            Date to reload interfaces. Format YYYY-MM-DD.
        interfaces : DataFrame
            Data of interfaces to reload.
        """
        try:
            query = InterfaceQuery()
            if not Validate.date(date=date):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid date")
            dates_date = interfaces[InterfaceField.CONSULTED_AT].unique()
            if len(dates_date) > 1:
                raise BusinessError(
                    http_status.HTTP_400_BAD_REQUEST,
                    f"The dataframe has more than one date ({date}) to reload in the database",
                )
            status_operation = query.delete_by_date_consult(date=date)
            if not status_operation:
                raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to delete interfaces to reload {date}")
            status_operation = query.insert(data=interfaces)
            if not status_operation:
                raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to reload interfaces of {date}")
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to reload interfaces by date. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to reload interfaces by date")

    @staticmethod
    def delete_interfaces_by_date_consult(date: str) -> None:
        """Delete interfaces by date.

        Parameters
        ----------
        date : str
            Date to delete interfaces. Format YYYY-MM-DD.
        """
        try:
            query = InterfaceQuery()
            if not Validate.date(date=date):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid date")
            status_operation = query.delete_by_date_consult(date=date)
            if not status_operation:
                raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete interfaces")
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to delete interfaces by date. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete interfaces by date")

    @staticmethod
    def get_interfaces_by_date_consult(date: str) -> List[dict]:
        """Get all interfaces by date.

        Parameters
        ----------
        date : str
            Date to get interfaces. Format YYYY-MM-DD.

        Returns
        -------
        List[dict]
            Interfaces consulted on the given date.
        """
        try:
            query = InterfaceQuery()
            if not Validate.date(date=date):
                raise BusinessError(http_status.HTTP_400_BAD_REQUEST, "Invalid date")
            data = query.get_by_date_consult(date=date)
            if data.empty:
                return []
            return OperationData.transform_to_json(data=data)
        except BusinessError:
            raise
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to get interfaces by date. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get interfaces by date")

    @staticmethod
    def get_interfaces_with_changes() -> DataFrame:
        """Get interfaces with changes.

        Returns
        -------
        DataFrame
            Interfaces with changes detected between the last two consult dates.
        """
        try:
            query = InterfaceQuery()
            date_new = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            date_old = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            data_old = query.get_by_date_consult(date=date_old)
            data_new = query.get_by_date_consult(date=date_new)
            if data_old.empty or data_new.empty:
                return DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            data = OperationData.compare(old_data=data_old, new_data=data_new)
            if data.empty:
                return DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            return data
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to get interfaces changes. {error}")
            raise BusinessError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to get interfaces with changes")
