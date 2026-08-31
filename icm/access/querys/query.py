from icm.data import Database


class Query:
    """Class to manage query."""
    database: Database

    def __init__(self):
        self.database = Database()