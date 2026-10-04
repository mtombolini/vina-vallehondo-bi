from datetime import date

import pytest

from vina_vallehondo_bi.etl.parsers import parse_bool, parse_date, parse_discount, parse_integer, parse_number


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2025-03-25", date(2025, 3, 25)),
        ("25/03/2025", date(2025, 3, 25)),
        ("25-03-25", date(2025, 3, 25)),
        ("25-mar-2025", date(2025, 3, 25)),
        ("4-ene-2025", date(2025, 1, 4)),
        ("07/12/2025", date(2025, 12, 7)),
        ("31/02/2025", None),
        ("sin fecha", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_date(value, expected) -> None:
    assert parse_date(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("22.93", 22.93),
        ("44,47", 44.47),
        ("42.6", 42.6),
        ("38.100", 38100.0),
        ("$37.715", 37715.0),
        ("21175", 21175.0),
        ("3.651,62", 3651.62),
        ("$10.303.672", 10303672.0),
        ("-2.738,88", -2738.88),
        ("$-9.320.850", -9320850.0),
        ("13.734,00", 13734.0),
        ("9,0", 9.0),
        (125, 125.0),
        ("NULL", None),
        ("abc", None),
        (None, None),
    ],
)
def test_parse_number(value, expected) -> None:
    assert parse_number(value) == expected


@pytest.mark.parametrize("value, expected", [("49", 49), (49, 49), ("-33", -33), ("9,5", None), (None, None)])
def test_parse_integer(value, expected) -> None:
    assert parse_integer(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [("0", 0.0), ("0,08", 0.08), ("8", 0.08), ("8%", 0.08), ("0,10", 0.10), ("18", 0.18), (None, None)],
)
def test_parse_discount(value, expected) -> None:
    assert parse_discount(value) == pytest.approx(expected)


@pytest.mark.parametrize(
    "value, expected",
    [("SI", True), ("Sí", True), ("si", True), ("1", True), ("NO", False), ("0", False), ("quizás", None), ("", None)],
)
def test_parse_bool(value, expected) -> None:
    assert parse_bool(value) is expected
