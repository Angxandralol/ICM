"""Pure-function tests for `dataframe_to_rows` — no database needed."""

import pandas as pd

from icm.access.utils.frame import dataframe_to_rows


def test_dataframe_to_rows_preserves_regular_values():
    df = pd.DataFrame([{"ip": "10.0.0.1", "ifIndex": 1}])
    assert dataframe_to_rows(df) == [{"ip": "10.0.0.1", "ifIndex": 1}]


def test_dataframe_to_rows_converts_nan_to_none():
    df = pd.DataFrame([{"ifAlias": "eth0", "ifName": None}])
    rows = dataframe_to_rows(df)
    assert rows == [{"ifAlias": "eth0", "ifName": None}]


def test_dataframe_to_rows_handles_multiple_rows_independently():
    df = pd.DataFrame(
        [
            {"ifAlias": "a", "ifHighSpeed": 1000},
            {"ifAlias": None, "ifHighSpeed": None},
        ]
    )
    rows = dataframe_to_rows(df)
    assert rows == [
        {"ifAlias": "a", "ifHighSpeed": 1000},
        {"ifAlias": None, "ifHighSpeed": None},
    ]
