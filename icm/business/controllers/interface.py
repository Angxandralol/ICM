from typing import Tuple, List
from datetime import datetime, timedelta
from pandas import DataFrame
from icm.access import InterfaceQuery
from icm.constants import InterfaceField
from icm.utils import OperationData, HEADER_RESPONSE_INTERFACES_CHANGES, Validate, log
from icm.business.constants.header import HEADER_CONSULT_SNMP, HEADER_RESPONSE_INTERFACES
from icm.business.libs.code import ResponseCode


class InterfaceController:
    """Class to manage interface controller."""

    @staticmethod
    def new_interfaces(interfaces: DataFrame) -> ResponseCode:
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
                return ResponseCode(status=400, message="Invalid header of data interfaces to insert")
            status_operation = query.insert(data=interfaces)
            if not status_operation: raise Exception()
            return ResponseCode(status=201)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to insert a new interfaces. {error}")
            return ResponseCode(status=500)
        
    @staticmethod
    def reload_interfaces_by_date_consult(date: str, interfaces: DataFrame) -> ResponseCode:
        """Delete all interfaces by a given date, then re-insert them with their new values.
        
        Parameters
        ----------
        date : str
            Date to reload interfaces. Format YYYY-MM-DD.
        interfaces : DataFrame
            Data of interfaces to reload.

        Returns
        -------
        ResponseCode
            Response code.
        """
        try:
            query = InterfaceQuery()
            if not Validate.date(date=date):
                return ResponseCode(status=400, message="Invalid date")
            dates_date = interfaces[InterfaceField.CONSULTED_AT].unique()
            if len(dates_date) > 1:
                return ResponseCode(status=400, message=f"The dataframe has more than one date ({date}) to reload in the database")
            status_operation = query.delete_by_date_consult(date=date)
            if not status_operation:
                return ResponseCode(status=500, message=f"Failed to delete interfaces to reload {date}")
            status_operation = query.insert(data=interfaces)
            if not status_operation:
                return ResponseCode(status=500, message=f"Failed to reload interfaces of {date}")
            return ResponseCode(status=200)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to reload interfaces by date. {error}")
            return ResponseCode(status=500)
        
    @staticmethod
    def delete_interfaces_by_date_consult(date: str) -> ResponseCode:
        """Delete interfaces by date.
        
        Parameters
        ----------
        date : str
            Date to delete interfaces. Format YYYY-MM-DD.

        Returns
        -------
        ResponseCode
            Response code.
        """
        try:
            query = InterfaceQuery()
            if not Validate.date(date=date):
                return ResponseCode(status=400, message="Invalid date")
            status_operation = query.delete_by_date_consult(date=date)
            if not status_operation:
                return ResponseCode(status=500, message="Failed to delete interfaces")
            return ResponseCode(status=200)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to delete interfaces by date. {error}")
            return ResponseCode(status=500)
        
    @staticmethod
    def get_interfaces_by_date_consult(date: str) -> Tuple[ResponseCode, List[dict]]:
        """Get all interfaces by date.
        
        Parameters
        ----------
        date : str
            Date to get interfaces. Format YYYY-MM-DD.

        Returns
        -------
        Tuple[ResponseCode, DataFrame]
            Response code and dataframe.
        """
        try:
            query = InterfaceQuery()
            if not Validate.date(date=date):
                return ResponseCode(status=400, message="Invalid date"), DataFrame(columns=HEADER_RESPONSE_INTERFACES)
            data = query.get_by_date_consult(date=date)
            if not data:
                return ResponseCode(status=200), DataFrame(columns=HEADER_RESPONSE_INTERFACES)
            data = OperationData.transform_to_json(data=data)
            return ResponseCode(status=200), data
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to get interfaces by date. {error}")
            return ResponseCode(status=500), DataFrame(columns=HEADER_RESPONSE_INTERFACES)
        
    @staticmethod
    def get_interfaces_with_changes() -> Tuple[ResponseCode, DataFrame]:
        """Get interfaces with changes.
        
        Returns
        -------
        Tuple[ResponseCode, DataFrame]
            Response code and dataframe.
        """
        try:
            query = InterfaceQuery()
            date_new = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            date_old = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            data_old = query.get_by_date_consult(date=date_old)
            data_new = query.get_by_date_consult(date=date_new)
            if not data_old or not data_new:
                return ResponseCode(status=200), DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            data = OperationData.compare(old_data=data_old, new_data=data_new)
            if not data:
                return ResponseCode(status=200), DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)
            return ResponseCode(status=200), data
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface controller error. Failed to get interfaces changes. {error}")
            return ResponseCode(status=500), DataFrame(columns=HEADER_RESPONSE_INTERFACES_CHANGES)