import decimal

import numpy as np
from numpy import iinfo
import pytest

import pandas as pd
from pandas import DataFrame, Index, Series, to_numeric
import pandas._testing as tm


@pytest.fixture(params=[None, "ignore", "raise", "coerce"])
def errors(request):
    return request.param


@pytest.fixture(params=[True, False])
def signed(request):
    return request.param


@pytest.fixture(params=[lambda x: x, str], ids=["identity", "str"])
def transform(request):
    return request.param


@pytest.fixture(params=[47393996303418497800, 100000000000000000000])
def large_val(request):
    return request.param


@pytest.fixture(params=[True, False])
def multiple_elts(request):
    return request.param


@pytest.fixture(
    params=[
        (lambda x: Index(x, name="idx"), tm.assert_index_equal),
        (lambda x: Series(x, name="ser"), tm.assert_series_equal),
        (lambda x: np.array(Index(x).values), tm.assert_numpy_array_equal),
    ]
)
def transform_assert_equal(request):
    return request.param


@pytest.mark.parametrize(
    "input_kwargs,result_kwargs",
    [
        (dict(), dict(dtype=np.int64)),
        (dict(errors="coerce", downcast="integer"), dict(dtype=np.int8)),
    ],
)
def test_empty(input_kwargs, result_kwargs):
    # see gh-16302
    ser = Series([], dtype=object)
    result = to_numeric(ser, **input_kwargs)

    expected = Series([], **result_kwargs)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize("last_val", ["7", 7])
def test_series(last_val):
    ser = Series(["1", "-3.14", last_val])
    result = to_numeric(ser)

    expected = Series([1, -3.14, 7])
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "data",
    [
        [1, 3, 4, 5],
        [1.0, 3.0, 4.0, 5.0],
        # Bool is regarded as numeric.
        [True, False, True, True],
    ],
)
def test_series_numeric(data):
    ser = Series(data, index=list("ABCD"), name="EFG")

    result = to_numeric(ser)
    tm.assert_series_equal(result, ser)


@pytest.mark.parametrize(
    "data,msg",
    [
        ([1, -3.14, "apple"], 'Unable to parse string "apple" at position 2'),
        (
            ["orange", 1, -3.14, "apple"],
            'Unable to parse string "orange" at position 0',
        ),
    ],
)
def test_error(data, msg):
    ser = Series(data)

    with pytest.raises(ValueError, match=msg):
        to_numeric(ser, errors="raise")


@pytest.mark.parametrize(
    "errors,exp_data", [("ignore", [1, -3.14, "apple"]), ("coerce", [1, -3.14, np.nan])]
)
def test_ignore_error(errors, exp_data):
    ser = Series([1, -3.14, "apple"])
    result = to_numeric(ser, errors=errors)

    expected = Series(exp_data)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "errors,exp",
    [
        ("raise", 'Unable to parse string "apple" at position 2'),
        ("ignore", [True, False, "apple"]),
        # Coerces to float.
        ("coerce", [1.0, 0.0, np.nan]),
    ],
)
def test_bool_handling(errors, exp):
    ser = Series([True, False, "apple"])

    if isinstance(exp, str):
        with pytest.raises(ValueError, match=exp):
            to_numeric(ser, errors=errors)
    else:
        result = to_numeric(ser, errors=errors)
        expected = Series(exp)

        tm.assert_series_equal(result, expected)


def test_list():
    ser = ["1", "-3.14", "7"]
    res = to_numeric(ser)

    expected = np.array([1, -3.14, 7])
    tm.assert_numpy_array_equal(res, expected)


@pytest.mark.parametrize(
    "data,arr_kwargs",
    [
        ([1, 3, 4, 5], dict(dtype=np.int64)),
        ([1.0, 3.0, 4.0, 5.0], dict()),
        # Boolean is regarded as numeric.
        ([True, False, True, True], dict()),
    ],
)
def test_list_numeric(data, arr_kwargs):
    result = to_numeric(data)
    expected = np.array(data, **arr_kwargs)
    tm.assert_numpy_array_equal(result, expected)


@pytest.mark.parametrize("kwargs", [dict(dtype="O"), dict()])
def test_numeric(kwargs):
    data = [1, -3.14, 7]

    ser = Series(data, **kwargs)
    result = to_numeric(ser)

    expected = Series(data)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "columns",
    [
        # One column.
        "a",
        # Multiple columns.
        ["a", "b"],
    ],
)
def test_numeric_df_columns(columns):
    # see gh-14827
    df = DataFrame(
        dict(
            a=[1.2, decimal.Decimal(3.14), decimal.Decimal("infinity"), "0.1"],
            b=[1.0, 2.0, 3.0, 4.0],
        )
    )

    expected = DataFrame(dict(a=[1.2, 3.14, np.inf, 0.1], b=[1.0, 2.0, 3.0, 4.0]))

    df_copy = df.copy()
    df_copy[columns] = df_copy[columns].apply(to_numeric)

    tm.assert_frame_equal(df_copy, expected)


@pytest.mark.parametrize(
    "data,exp_data",
    [
        (
            [[decimal.Decimal(3.14), 1.0], decimal.Decimal(1.6), 0.1],
            [[3.14, 1.0], 1.6, 0.1],
        ),
        ([np.array([decimal.Decimal(3.14), 1.0]), 0.1], [[3.14, 1.0], 0.1]),
    ],
)
def test_numeric_embedded_arr_likes(data, exp_data):
    # Test to_numeric with embedded lists and arrays
    df = DataFrame(dict(a=data))
    df["a"] = df["a"].apply(to_numeric)

    expected = DataFrame(dict(a=exp_data))
    tm.assert_frame_equal(df, expected)


def test_all_nan():
    ser = Series(["a", "b", "c"])
    result = to_numeric(ser, errors="coerce")

    expected = Series([np.nan, np.nan, np.nan])
    tm.assert_series_equal(result, expected)


def test_type_check(errors):
    # see gh-11776
    df = DataFrame({"a": [1, -3.14, 7], "b": ["4", "5", "6"]})
    kwargs = dict(errors=errors) if errors is not None else dict()
    error_ctx = pytest.raises(TypeError, match="1-d array")

    with error_ctx:
        to_numeric(df, **kwargs)


@pytest.mark.parametrize("val", [1, 1.1, 20001])
def test_scalar(val, signed, transform):
    val = -val if signed else val
    assert to_numeric(transform(val)) == float(val)


def test_really_large_scalar(large_val, signed, transform, errors):
    # see gh-24910
    kwargs = dict(errors=errors) if errors is not None else dict()
    val = -large_val if signed else large_val

    val = transform(val)
    val_is_string = isinstance(val, str)

    if val_is_string and errors in (None, "raise"):
        msg = "Integer out of range. at position 0"
        with pytest.raises(ValueError, match=msg):
            to_numeric(val, **kwargs)
    else:
        expected = float(val) if (errors == "coerce" and val_is_string) else val
        tm.assert_almost_equal(to_numeric(val, **kwargs), expected)


def test_really_large_in_arr(large_val, signed, transform, multiple_elts, errors):
    # see gh-24910
    kwargs = dict(errors=errors) if errors is not None else dict()
    val = -large_val if signed else large_val
    val = transform(val)

    extra_elt = "string"
    arr = [val] + multiple_elts * [extra_elt]

    val_is_string = isinstance(val, str)
    coercing = errors == "coerce"

    if errors in (None, "raise") and (val_is_string or multiple_elts):
        if val_is_string:
            msg = "Integer out of range. at position 0"
        else:
            msg = 'Unable to parse string "string" at position 1'

        with pytest.raises(ValueError, match=msg):
            to_numeric(arr, **kwargs)
    else:
        result = to_numeric(arr, **kwargs)

        exp_val = float(val) if (coercing and val_is_string) else val
        expected = [exp_val]

        if multiple_elts:
            if coercing:
                expected.append(np.nan)
                exp_dtype = float
            else:
                expected.append(extra_elt)
                exp_dtype = object
        else:
            exp_dtype = float if isinstance(exp_val, (int, float)) else object

        tm.assert_almost_equal(result, np.array(expected, dtype=exp_dtype))


def test_really_large_in_arr_consistent(large_val, signed, multiple_elts, errors):
    # see gh-24910
    #
    # Even if we discover that we have to hold float, does not mean
    # we should be lenient on subsequent elements that fail to be integer.
    kwargs = dict(errors=errors) if errors is not None else dict()
    arr = [str(-large_val if signed else large_val)]

    if multiple_elts:
        arr.insert(0, large_val)

    if errors in (None, "raise"):
        index = int(multiple_elts)
        msg = f"Integer out of range. at position {index}"

        with pytest.raises(ValueError, match=msg):
            to_numeric(arr, **kwargs)
    else:
        result = to_numeric(arr, **kwargs)

        if errors == "coerce":
            expected = [float(i) for i in arr]
            exp_dtype = float
        else:
            expected = arr
            exp_dtype = object

        tm.assert_almost_equal(result, np.array(expected, dtype=exp_dtype))


@pytest.mark.parametrize(
    "errors,checker",
    [
        ("raise", 'Unable to parse string "fail" at position 0'),
        ("ignore", lambda x: x == "fail"),
        ("coerce", lambda x: np.isnan(x)),
    ],
)
def test_scalar_fail(errors, checker):
    scalar = "fail"

    if isinstance(checker, str):
        with pytest.raises(ValueError, match=checker):
            to_numeric(scalar, errors=errors)
    else:
        assert checker(to_numeric(scalar, errors=errors))


@pytest.mark.parametrize("data", [[1, 2, 3], [1.0, np.nan, 3, np.nan]])
def test_numeric_dtypes(data, transform_assert_equal):
    transform, assert_equal = transform_assert_equal
    data = transform(data)

    result = to_numeric(data)
    assert_equal(result, data)


@pytest.mark.parametrize(
    "data,exp",
    [
        (["1", "2", "3"], np.array([1, 2, 3], dtype="int64")),
        (["1.5", "2.7", "3.4"], np.array([1.5, 2.7, 3.4])),
    ],
)
def test_str(data, exp, transform_assert_equal):
    transform, assert_equal = transform_assert_equal
    result = to_numeric(transform(data))

    expected = transform(exp)
    assert_equal(result, expected)


def test_datetime_like(tz_naive_fixture, transform_assert_equal):
    transform, assert_equal = transform_assert_equal
    idx = pd.date_range("20130101", periods=3, tz=tz_naive_fixture)

    result = to_numeric(transform(idx))
    expected = transform(idx.asi8)
    assert_equal(result, expected)


def test_timedelta(transform_assert_equal):
    transform, assert_equal = transform_assert_equal
    idx = pd.timedelta_range("1 days", periods=3, freq="D")

    result = to_numeric(transform(idx))
    expected = transform(idx.asi8)
    assert_equal(result, expected)


def test_period(transform_assert_equal):
    transform, assert_equal = transform_assert_equal

    idx = pd.period_range("2011-01", periods=3, freq="M", name="")
    inp = transform(idx)

    if isinstance(inp, Index):
        result = to_numeric(inp)
        expected = transform(idx.asi8)
        assert_equal(result, expected)
    else:
        # TODO: PeriodDtype, so support it in to_numeric.
        pytest.skip("Missing PeriodDtype support in to_numeric")


@pytest.mark.parametrize(
    "errors,expected",
    [
        ("raise", "Invalid object type at position 0"),
        ("ignore", Series([[10.0, 2], 1.0, "apple"])),
        ("coerce", Series([np.nan, 1.0, np.nan])),
    ],
)
def test_non_hashable(errors, expected):
    # see gh-13324
    ser = Series([[10.0, 2], 1.0, "apple"])

    if isinstance(expected, str):
        with pytest.raises(TypeError, match=expected):
            to_numeric(ser, errors=errors)
    else:
        result = to_numeric(ser, errors=errors)
        tm.assert_series_equal(result, expected)


def test_downcast_invalid_cast():
    # see gh-13352
    data = ["1", 2, 3]
    invalid_downcast = "unsigned-integer"
    msg = "invalid downcasting method provided"

    with pytest.raises(ValueError, match=msg):
        to_numeric(data, downcast=invalid_downcast)


def test_errors_invalid_value():
    # see gh-26466
    data = ["1", 2, 3]
    invalid_error_value = "invalid"
    msg = "invalid error value specified"

    with pytest.raises(ValueError, match=msg):
        to_numeric(data, errors=invalid_error_value)


@pytest.mark.parametrize(
    "data",
    [
        ["1", 2, 3],
        [1, 2, 3],
        np.array(["1970-01-02", "1970-01-03", "1970-01-04"], dtype="datetime64[D]"),
    ],
)
@pytest.mark.parametrize(
    "kwargs,exp_dtype",
    [
        # Basic function tests.
        (dict(), np.int64),
        (dict(downcast=None), np.int64),
        # Support below np.float32 is rare and far between.
        (dict(downcast="float"), np.dtype(np.float32).char),
        # Basic dtype support.
        (dict(downcast="unsigned"), np.dtype(np.typecodes["UnsignedInteger"][0])),
    ],
)
def test_downcast_basic(data, kwargs, exp_dtype):
    # see gh-13352
    result = to_numeric(data, **kwargs)
    expected = np.array([1, 2, 3], dtype=exp_dtype)
    tm.assert_numpy_array_equal(result, expected)


@pytest.mark.parametrize("signed_downcast", ["integer", "signed"])
@pytest.mark.parametrize(
    "data",
    [
        ["1", 2, 3],
        [1, 2, 3],
        np.array(["1970-01-02", "1970-01-03", "1970-01-04"], dtype="datetime64[D]"),
    ],
)
def test_signed_downcast(data, signed_downcast):
    # see gh-13352
    smallest_int_dtype = np.dtype(np.typecodes["Integer"][0])
    expected = np.array([1, 2, 3], dtype=smallest_int_dtype)

    res = to_numeric(data, downcast=signed_downcast)
    tm.assert_numpy_array_equal(res, expected)


def test_ignore_downcast_invalid_data():
    # If we can't successfully cast the given
    # data to a numeric dtype, do not bother
    # with the downcast parameter.
    data = ["foo", 2, 3]
    expected = np.array(data, dtype=object)

    res = to_numeric(data, errors="ignore", downcast="unsigned")
    tm.assert_numpy_array_equal(res, expected)


def test_ignore_downcast_neg_to_unsigned():
    # Cannot cast to an unsigned integer
    # because we have a negative number.
    data = ["-1", 2, 3]
    expected = np.array([-1, 2, 3], dtype=np.int64)

    res = to_numeric(data, downcast="unsigned")
    tm.assert_numpy_array_equal(res, expected)


@pytest.mark.parametrize("downcast", ["integer", "signed", "unsigned"])
@pytest.mark.parametrize(
    "data,expected",
    [
        (["1.1", 2, 3], np.array([1.1, 2, 3], dtype=np.float64)),
        (
            [10000.0, 20000, 3000, 40000.36, 50000, 50000.00],
            np.array(
                [10000.0, 20000, 3000, 40000.36, 50000, 50000.00], dtype=np.float64
            ),
        ),
    ],
)
def test_ignore_downcast_cannot_convert_float(data, expected, downcast):
    # Cannot cast to an integer (signed or unsigned)
    # because we have a float number.
    res = to_numeric(data, downcast=downcast)
    tm.assert_numpy_array_equal(res, expected)


@pytest.mark.parametrize(
    "downcast,expected_dtype",
    [("integer", np.int16), ("signed", np.int16), ("unsigned", np.uint16)],
)
def test_downcast_not8bit(downcast, expected_dtype):
    # the smallest integer dtype need not be np.(u)int8
    data = ["256", 257, 258]

    expected = np.array([256, 257, 258], dtype=expected_dtype)
    res = to_numeric(data, downcast=downcast)
    tm.assert_numpy_array_equal(res, expected)


@pytest.mark.parametrize(
    "dtype,downcast,min_max",
    [
        ("int8", "integer", [iinfo(np.int8).min, iinfo(np.int8).max]),
        ("int16", "integer", [iinfo(np.int16).min, iinfo(np.int16).max]),
        ("int32", "integer", [iinfo(np.int32).min, iinfo(np.int32).max]),
        ("int64", "integer", [iinfo(np.int64).min, iinfo(np.int64).max]),
        ("uint8", "unsigned", [iinfo(np.uint8).min, iinfo(np.uint8).max]),
        ("uint16", "unsigned", [iinfo(np.uint16).min, iinfo(np.uint16).max]),
        ("uint32", "unsigned", [iinfo(np.uint32).min, iinfo(np.uint32).max]),
        ("uint64", "unsigned", [iinfo(np.uint64).min, iinfo(np.uint64).max]),
        ("int16", "integer", [iinfo(np.int8).min, iinfo(np.int8).max + 1]),
        ("int32", "integer", [iinfo(np.int16).min, iinfo(np.int16).max + 1]),
        ("int64", "integer", [iinfo(np.int32).min, iinfo(np.int32).max + 1]),
        ("int16", "integer", [iinfo(np.int8).min - 1, iinfo(np.int16).max]),
        ("int32", "integer", [iinfo(np.int16).min - 1, iinfo(np.int32).max]),
        ("int64", "integer", [iinfo(np.int32).min - 1, iinfo(np.int64).max]),
        ("uint16", "unsigned", [iinfo(np.uint8).min, iinfo(np.uint8).max + 1]),
        ("uint32", "unsigned", [iinfo(np.uint16).min, iinfo(np.uint16).max + 1]),
        ("uint64", "unsigned", [iinfo(np.uint32).min, iinfo(np.uint32).max + 1]),
    ],
)
def test_downcast_limits(dtype, downcast, min_max):
    # see gh-14404: test the limits of each downcast.
    series = to_numeric(Series(min_max), downcast=downcast)
    assert series.dtype == dtype


@pytest.mark.parametrize(
    "ser,expected",
    [
        (
            pd.Series([0, 9223372036854775808]),
            pd.Series([0, 9223372036854775808], dtype=np.uint64),
        )
    ],
)
def test_downcast_uint64(ser, expected):
    # see gh-14422:
    # BUG: to_numeric doesn't work uint64 numbers

    result = pd.to_numeric(ser, downcast="unsigned")

    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "data,exp_data",
    [
        (
            [200, 300, "", "NaN", 30000000000000000000],
            [200, 300, np.nan, np.nan, 30000000000000000000],
        ),
        (
            ["12345678901234567890", "1234567890", "ITEM"],
            [12345678901234567890, 1234567890, np.nan],
        ),
    ],
)
def test_coerce_uint64_conflict(data, exp_data):
    # see gh-17007 and gh-17125
    #
    # Still returns float despite the uint64-nan conflict,
    # which would normally force the casting to object.
    result = to_numeric(Series(data), errors="coerce")
    expected = Series(exp_data, dtype=float)
    tm.assert_series_equal(result, expected)


@pytest.mark.parametrize(
    "errors,exp",
    [
        ("ignore", Series(["12345678901234567890", "1234567890", "ITEM"])),
        ("raise", "Unable to parse string"),
    ],
)
def test_non_coerce_uint64_conflict(errors, exp):
    # see gh-17007 and gh-17125
    #
    # For completeness.
    ser = Series(["12345678901234567890", "1234567890", "ITEM"])

    if isinstance(exp, str):
        with pytest.raises(ValueError, match=exp):
            to_numeric(ser, errors=errors)
    else:
        result = to_numeric(ser, errors=errors)
        tm.assert_series_equal(result, ser)


@pytest.mark.parametrize("dc1", ["integer", "float", "unsigned"])
@pytest.mark.parametrize("dc2", ["integer", "float", "unsigned"])
def test_downcast_empty(dc1, dc2):
    # GH32493

    tm.assert_numpy_array_equal(
        pd.to_numeric([], downcast=dc1),
        pd.to_numeric([], downcast=dc2),
        check_dtype=False,
    )


def test_failure_to_convert_uint64_string_to_NaN():
    # GH 32394
    result = to_numeric("uint64", errors="coerce")
    assert np.isnan(result)

    ser = Series([32, 64, np.nan])
    result = to_numeric(pd.Series(["32", "64", "uint64"]), errors="coerce")
    tm.assert_series_equal(result, ser)


def test_set_levels_with_changed_multiindex():
    # GH33420
    np.random.seed(seed=0)
    arrays = [
        ["bar", "bar", "baz", "baz", "foo", "foo", "qux", "qux"],
        ["one", "one", "one", "one", "one", "one", "one", "one"],
        ["three", "four", "three", "four", "three", "four", "three", "four"],
    ]
    ran_array = np.random.rand(8, 4)
    test_df = pd.DataFrame(ran_array, index=arrays)
    test_df.index.set_levels([3, 4], level=2, inplace=True)
    correct_df = pd.DataFrame(ran_array, index=arrays)
    correct_df.index = pd.MultiIndex.from_arrays(
        [
            test_df.index.get_level_values(0),
            test_df.index.get_level_values(1),
            np.tile([3, 4], 4),
        ]
    )
    tm.assert_equal(test_df, correct_df)
