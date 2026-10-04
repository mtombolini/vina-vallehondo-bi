"""Conversión de los valores de texto de las fuentes a tipos nativos.

Cada función recibe el valor tal como viene en la fuente y devuelve ``None``
cuando no puede interpretarlo, de modo que la ingesta nunca descarta filas.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, Optional


MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}
NULL_TOKENS = {"", "null", "none", "nan", "n/a", "na", "-"}
TRUE_TOKENS = {"si", "sí", "s", "1", "true", "x"}
FALSE_TOKENS = {"no", "n", "0", "false"}

_ISO_DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_SLASH_DATE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_SHORT_YEAR_DATE = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{2})")
_MONTH_NAME_DATE = re.compile(r"(\d{1,2})-([a-zñ]{3})-(\d{4})")
_THOUSANDS_ONLY = re.compile(r"-?[1-9]\d{0,2}(\.\d{3})+")


def _clean(value: Any) -> Optional[str]:
    if value is None or value != value:  # None o NaN
        return None
    text = str(value).strip()
    return None if text.lower() in NULL_TOKENS else text


def parse_date(value: Any) -> Optional[date]:
    """Interpreta los formatos de fecha presentes en ventas y embarques.

    Admite ``2025-03-25``, ``25/03/2025``, ``25-03-25`` y ``25-mar-2025``. Los
    formatos numéricos se leen siempre como día-mes-año.
    """
    text = _clean(value)
    if text is None:
        return None
    text = text.lower()
    try:
        match = _ISO_DATE.fullmatch(text)
        if match:
            return date(int(match[1]), int(match[2]), int(match[3]))
        match = _SLASH_DATE.fullmatch(text)
        if match:
            return date(int(match[3]), int(match[2]), int(match[1]))
        match = _SHORT_YEAR_DATE.fullmatch(text)
        if match:
            return date(2000 + int(match[3]), int(match[2]), int(match[1]))
        match = _MONTH_NAME_DATE.fullmatch(text)
        if match and match[2] in MONTHS:
            return date(int(match[3]), MONTHS[match[2]], int(match[1]))
    except ValueError:
        return None
    return None


def parse_number(value: Any) -> Optional[float]:
    """Interpreta números con separadores de miles y decimales mezclados.

    Si hay coma, la coma es el decimal y los puntos son miles (``3.651,62``).
    Sin coma, los puntos son miles solo cuando todos los grupos tienen tres
    dígitos (``38.100``, ``10.303.672``); en otro caso el punto es decimal
    (``22.93``, ``0.125``). Se ignoran ``$``, ``%`` y espacios. Los valores que
    ya son numéricos se devuelven sin reinterpretar sus separadores.
    """
    text = _clean(value)
    if text is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return number if math.isfinite(number) else None
    text = re.sub(r"[$%\s]", "", text)
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif _THOUSANDS_ONLY.fullmatch(text):
        text = text.replace(".", "")
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_integer(value: Any) -> Optional[int]:
    """Interpreta un entero que puede venir como número o como texto."""
    number = parse_number(value)
    if number is None or number != int(number):
        return None
    return int(number)


def parse_discount(value: Any) -> Optional[float]:
    """Devuelve el descuento como fracción entre 0 y 1.

    La fuente mezcla fracciones (``0,08``) con porcentajes (``8`` y ``8%``):
    todo valor con ``%`` o mayor o igual a 1 se trata como porcentaje.
    """
    number = parse_number(value)
    if number is None:
        return None
    if "%" in str(value) or abs(number) >= 1:
        return number / 100
    return number


def parse_bool(value: Any) -> Optional[bool]:
    """Interpreta indicadores como ``SI``, ``Sí``, ``si``, ``1`` o ``NO``."""
    text = _clean(value)
    if text is None:
        return None
    text = text.lower()
    if text in TRUE_TOKENS:
        return True
    if text in FALSE_TOKENS:
        return False
    return None
