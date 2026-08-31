import pandas as pd


def dataframe_to_rows(data: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to a list of row dicts ready for a bulk ORM insert.

    Parameters
    ----------
    data : pd.DataFrame
        Data to convert. Column names must match the target ORM schema's
        attribute names.

    Returns
    -------
    list[dict]
        One dict per row, with pandas' `NaN`/`NaT` normalized to `None` so
        optional columns insert as SQL `NULL` instead of the literal string
        "nan".
    """
    return data.astype(object).where(pd.notnull(data), None).to_dict(orient="records")
