import pandas as pd
from pandas import DataFrame
from sqlalchemy import insert
from icm.data import InterfaceSchema
from icm.utils import log
from icm.access.querys.query import Query
from icm.access.utils.adapter import AdapterInterface
from icm.access.utils.frame import dataframe_to_rows


class InterfaceQuery(Query):
    """Class to manage interface query."""

    def __init__(self):
        super().__init__()

    def insert(self, data: pd.DataFrame) -> bool:
        """Insert interfaces in database.

        Parameters
        ----------
        data : pd.DataFrame
            Interfaces to insert. Columns must match `InterfaceSchema`'s
            attribute names.

        Returns
        -------
        bool
            True if the data was inserted successfully, False otherwise.
        """
        try:
            rows = dataframe_to_rows(data)
            with self.database.session() as session:
                session.execute(insert(InterfaceSchema), rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Interface query error. Failed to insert interfaces. {error}")
            return False
        else:
            return True

    def delete_by_date_consult(self, date: str) -> bool:
        """Delete interfaces by date.

        Parameters
        ----------
        date : str
            Date to delete interfaces.

        Returns
        -------
        bool
            True if the data was deleted successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                session.query(InterfaceSchema).filter_by(consulted_at=date).delete()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Interface query error. Failed to delete interfaces by date. {error}"
            )
            return False
        else:
            return True

    def get_by_date_consult(self, date: str) -> DataFrame:
        """Get interfaces by date.

        Parameters
        ----------
        date : str
            Date to get interfaces.

        Returns
        -------
        DataFrame
            Interfaces consulted on that date.
        """
        try:
            with self.database.session() as session:
                rows = (
                    session.query(InterfaceSchema)
                    .filter_by(consulted_at=date)
                    .all()
                )
                return AdapterInterface.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(
                f"Interface query error. Failed to get interfaces by date. {error}"
            )
            return pd.DataFrame()
