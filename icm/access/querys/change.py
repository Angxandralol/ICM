import pandas as pd
from sqlalchemy import insert, update
from sqlalchemy.orm import joinedload
from icm.data import ChangeSchema
from icm.utils import log
from icm.access.models.changes import UpdateChangeModel
from icm.access.querys.query import Query
from icm.access.utils.adapter import AdapterChange
from icm.access.utils.frame import dataframe_to_rows


class ChangeQuery(Query):
    """Class to manage change query."""

    def __init__(self):
        super().__init__()

    def insert(self, data: pd.DataFrame) -> bool:
        """Insert changes in database.

        Parameters
        ----------
        data : pd.DataFrame
            Changes to insert. Columns must match `ChangeSchema`'s attribute
            names.

        Returns
        -------
        bool
            True if the data was inserted successfully, False otherwise.
        """
        try:
            rows = dataframe_to_rows(data)
            with self.database.session() as session:
                session.execute(insert(ChangeSchema), rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Change query error. Failed to insert changes. {error}")
            return False
        else:
            return True

    def get_all(self, page: int = 1, page_size: int = 100) -> tuple[list[dict], int]:
        """Get all changes, paginated.

        Parameters
        ----------
        page : int
            Page to retrieve, starting at 1.
        page_size : int
            Amount of changes per page.

        Returns
        -------
        tuple[list[dict], int]
            Changes of the requested page and the total amount of changes.
        """
        try:
            with self.database.session() as session:
                total = session.query(ChangeSchema).count()
                offset = (page - 1) * page_size
                rows = (
                    session.query(ChangeSchema)
                    .options(joinedload(ChangeSchema.assigned_user))
                    .order_by(ChangeSchema.id_old.desc())
                    .limit(page_size)
                    .offset(offset)
                    .all()
                )
                return AdapterChange.response(rows), total
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Change query error. Failed to get all changes. {error}")
            return ([], 0)

    def get_all_unassigned(self) -> list[dict]:
        """Get all changes without an assigned user.

        Returns
        -------
        list[dict]
            List of changes without an assigned user.
        """
        try:
            with self.database.session() as session:
                rows = (
                    session.query(ChangeSchema)
                    .options(joinedload(ChangeSchema.assigned_user))
                    .filter(ChangeSchema.assigned.is_(None))
                    .order_by(ChangeSchema.id_old.asc())
                    .all()
                )
                return AdapterChange.response(rows)
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Change query error. Failed to get unassigned changes. {error}")
            return []

    def update_assign(self, data: list[UpdateChangeModel]) -> bool:
        """Update assignment of changes.

        Parameters
        ----------
        data : List[UpdateChangeModel]
            Data to update.

        Returns
        -------
        bool
            True if the data was updated successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                for change in data:
                    session.execute(
                        update(ChangeSchema)
                        .where(
                            ChangeSchema.id_old == change.id_old,
                            ChangeSchema.id_new == change.id_new,
                        )
                        .values(assigned=change.username)
                    )
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Change query error. Failed to update changes. {error}")
            return False
        else:
            return True

    def delete_changes(self) -> bool:
        """Delete changes in database.

        Returns
        -------
        bool
            True if the data was deleted successfully, False otherwise.
        """
        try:
            with self.database.session() as session:
                session.query(ChangeSchema).delete()
        except Exception as error:
            error = str(error).strip().capitalize()
            log.error(f"Change query error. Failed to delete changes. {error}")
            return False
        else:
            return True
