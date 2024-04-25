#
# Copyright (c) 2012-2024 Snowflake Computing Inc. All rights reserved.
#

import modin.pandas as pd
import numpy as np
import pandas as native_pd
import pytest

import snowflake.snowpark.modin.plugin  # noqa: F401
from tests.integ.conftest import running_on_public_ci
from tests.integ.modin.sql_counter import sql_count_checker
from tests.integ.modin.utils import eval_snowpark_pandas_result


@pytest.fixture(scope="function")
def test_dropna_df():
    return native_pd.DataFrame(
        {
            "name": ["Alfred", "Batman", "Catwoman"],
            "toy": [np.nan, "Batmobile", "Bullwhip"],
            "born": [pd.NaT, pd.Timestamp("1940-04-25"), pd.NaT],
        }
    )


@sql_count_checker(query_count=5)
def test_basic_arguments(test_dropna_df):
    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(),
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(how="any"),
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(how="all"),
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(subset=["toy"]),
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(thresh=1),
    )


@sql_count_checker(query_count=1)
def test_df_with_index(test_dropna_df):
    test_dropna_df = test_dropna_df.set_index(["toy"])
    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(),
    )


@sql_count_checker(query_count=1)
def test_how_all_with_subset(test_dropna_df):
    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(how="all", subset=["name", "toy"]),
    )


@pytest.mark.xfail(
    reason="SNOW-1336091: Snowpark pandas cannot run in sprocs until modin 0.28.1 is available in conda",
    strict=True,
    raises=RuntimeError,
)
@pytest.mark.skipif(running_on_public_ci(), reason="slow fallback test")
@sql_count_checker(query_count=8, fallback_count=1, sproc_count=1)
def test_axis_1_fallback(test_dropna_df):
    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(axis="columns"),
    )


@sql_count_checker(query_count=1)
def test_dropna_negative(test_dropna_df):
    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(axis=[]),
        expect_exception=True,
        expect_exception_type=TypeError,
        expect_exception_match="supplying multiple axes to axis is no longer supported",
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(how="invalid"),
        expect_exception=True,
        expect_exception_type=ValueError,
        expect_exception_match="invalid how option",
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(how="any", thresh=1),
        expect_exception=True,
        expect_exception_type=TypeError,
        expect_exception_match="You cannot set both the how and thresh arguments at the same time",
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(subset=["invalid"]),
        expect_exception=True,
        expect_exception_type=KeyError,
        expect_exception_match="['invalid']",
    )

    eval_snowpark_pandas_result(
        pd.DataFrame(test_dropna_df),
        test_dropna_df,
        lambda df: df.dropna(subset=["invalid"], axis=1),
        expect_exception=True,
        expect_exception_type=KeyError,
        expect_exception_match="['invalid']",
    )


@pytest.mark.parametrize(
    "df",
    [
        native_pd.DataFrame(
            {
                "name": ["Alfred", "Batman", "Catwoman"],
                "toy": [np.nan, "Batmobile", "Bullwhip"],
                "born": [pd.NaT, pd.Timestamp("1940-04-25"), pd.NaT],
            }
        ),
    ],
)
@sql_count_checker(query_count=1, join_count=4, union_count=1)
def test_dropna_iloc(df):
    # Check that dropna() generates a new index correctly for iloc.
    # 1 join for iloc, 2 joins generated by to_pandas methods during eval.
    eval_snowpark_pandas_result(
        pd.DataFrame(df).dropna(),
        df.dropna(),
        lambda _df: _df.iloc[0],
    )


TEST_DATA_FOR_SORTING_DF = [
    native_pd.DataFrame(
        {
            "col0": ["snooze", "zzzzz", ". z . . .z ."],
            "echo": ["echo 2", "echo 1", "foxtrot"],
            "not an echo": ["99. .32. 467. . .", ".1 .3 3 5.", "2.5 . 3.7"],
        }
    ),
    native_pd.DataFrame(
        {
            22 / 7: [1, np.nan, -2, 3, np.nan, None],
            "col0": [4, np.nan, 5, 6, np.nan, np.nan],
        }
    ),
    native_pd.DataFrame(
        {
            "col0": [None, "a", "b", "c", None, "d", "e"],
            "B": [None, None, "e", "d", "c", "b", "a"],
        }
    ),
]


@pytest.mark.parametrize("df", TEST_DATA_FOR_SORTING_DF)
@sql_count_checker(query_count=1)
def test_dropna_sort_values(df):
    # Test data that does not start with a row_position_column due to sorting.
    eval_snowpark_pandas_result(
        pd.DataFrame(df).sort_values(by="col0"),
        df.sort_values(by="col0"),
        lambda _df: _df.dropna(),
    )