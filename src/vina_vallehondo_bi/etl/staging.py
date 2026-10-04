"""Ingesta de las fuentes originales a la capa ``data/staging``.

Cada fuente se lee completa y se tipa (fechas, números, booleanos) sin aplicar
reglas de negocio: no se eliminan duplicados, no se imputan valores y no se
corrigen inconsistencias. Lo que no se puede interpretar queda nulo y se
informa en el resumen de la ingesta.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd

from vina_vallehondo_bi.etl.parsers import (
    parse_bool,
    parse_date,
    parse_discount,
    parse_integer,
    parse_number,
)


STAGING_DIRECTORY = Path("data/staging")
SALES_DATABASE = "origen_vina.sqlite"
COSTS_FILE = "origen_costos_productos.csv"
SHIPMENTS_FILE = "origen_embarques.json"
DIMENSION_TABLES = ("zonas", "mercados", "cepas", "monedas", "vendedores", "clientes")
EXCHANGE_RATE_URL = "https://mindicador.cl/api/dolar/{year}"
# Los embarques de ventas de fines de 2025 se extienden hasta inicios de 2026.
EXCHANGE_RATE_YEARS = (2025, 2026)

Fetcher = Callable[[int], dict]


def _integers(values: Iterable[Any]) -> pd.Series:
    return pd.Series([parse_integer(value) for value in values], dtype="Int64")


def _numbers(values: Iterable[Any]) -> pd.Series:
    return pd.Series([parse_number(value) for value in values], dtype="float64")


def _dates(values: Iterable[Any]) -> pd.Series:
    return pd.to_datetime(pd.Series([parse_date(value) for value in values], dtype="object"))


def read_sales(project_root: Path) -> pd.DataFrame:
    """Lee la tabla ``ventas`` y tipa sus columnas de texto.

    ``zona`` y ``mes`` se conservan como ``zona_origen`` y ``mes_origen`` porque
    no siempre coinciden con el mercado ni con la fecha de la venta.
    """
    with sqlite3.connect(project_root / SALES_DATABASE) as connection:
        raw = pd.read_sql_query("SELECT rowid AS fila_origen, * FROM ventas ORDER BY rowid", connection)

    return pd.DataFrame(
        {
            "fila_origen": _integers(raw["fila_origen"]),
            "venta_id": _integers(raw["venta_id"]),
            "fecha": _dates(raw["fecha"]),
            "cliente_id": _integers(raw["cliente_id"]),
            "mercado_id": _integers(raw["mercado_id"]),
            "producto_id": _integers(raw["producto_id"]),
            "moneda_id": _integers(raw["moneda_id"]),
            "vendedor_id": _integers(raw["vendedor_id"]),
            "cajas": _integers(raw["cajas"]),
            "precio_unitario": _numbers(raw["precio_unitario"]),
            "descuento": pd.Series([parse_discount(value) for value in raw["descuento"]], dtype="float64"),
            "monto_neto": _numbers(raw["monto_neto"]),
            "anada": _integers(raw["anada"]),
            "zona_origen": raw["zona"].str.strip(),
            "mes_origen": _integers(raw["mes"]),
        }
    )


def read_dimensions(project_root: Path) -> dict[str, pd.DataFrame]:
    """Lee las tablas de dimensiones de la base comercial sin modificarlas."""
    with sqlite3.connect(project_root / SALES_DATABASE) as connection:
        return {
            f"stg_{table}": pd.read_sql_query(f"SELECT * FROM {table}", connection)
            for table in DIMENSION_TABLES
        }


def read_costs(project_root: Path) -> pd.DataFrame:
    """Lee los costos por producto y añada.

    Descarta las líneas que no son registros (encabezados repetidos y la fila
    ``TOTAL``). ``cepa`` se conserva tal como viene, con sus distintas grafías.
    """
    raw = pd.read_csv(
        project_root / COSTS_FILE,
        sep=";",
        encoding="cp1252",
        dtype=str,
        keep_default_na=False,
    )
    raw.insert(0, "fila_origen", raw.index + 2)  # línea del archivo, con el encabezado en la 1
    raw = raw[raw["producto_id"].str.strip().str.fullmatch(r"\d+")].reset_index(drop=True)

    return pd.DataFrame(
        {
            "fila_origen": _integers(raw["fila_origen"]),
            "producto_id": _integers(raw["producto_id"]),
            "producto": raw["producto"].str.strip(),
            "cepa": raw["cepa"].str.strip(),
            "tier": raw["tier"].str.strip(),
            "formato": raw["formato"].str.strip(),
            "litros_por_caja": _numbers(raw["litros_por_caja"]),
            "anada": _integers(raw["anada"]),
            "costo_caja_clp": _numbers(raw["costo_caja_clp"]),
            "activo": pd.Series([parse_bool(value) for value in raw["activo"]], dtype="boolean"),
        }
    )


def read_shipments(project_root: Path) -> pd.DataFrame:
    """Lee los embarques y los aplana a una fila por línea de embarque.

    ``embarque_id`` se repite en la fuente, por lo que ``embarque_orden`` (la
    posición del embarque en el archivo) es el identificador confiable.
    """
    with open(project_root / SHIPMENTS_FILE, encoding="utf-8") as file:
        shipments = json.load(file)["embarques"]

    rows = []
    for shipment_order, shipment in enumerate(shipments, start=1):
        for line_order, line in enumerate(shipment.get("lineas") or [], start=1):
            rows.append(
                {
                    "embarque_orden": shipment_order,
                    "linea_orden": line_order,
                    "embarque_id": shipment.get("embarque_id"),
                    "fecha_embarque": shipment.get("fecha_embarque"),
                    "incoterm": shipment.get("incoterm"),
                    "puerto_destino": shipment.get("puerto_destino"),
                    "mercado_id": shipment.get("mercado_id"),
                    "venta_id": line.get("venta_id"),
                    "cajas": line.get("cajas"),
                }
            )
    raw = pd.DataFrame(rows)

    return pd.DataFrame(
        {
            "embarque_orden": _integers(raw["embarque_orden"]),
            "linea_orden": _integers(raw["linea_orden"]),
            "embarque_id": raw["embarque_id"].str.strip(),
            "fecha_embarque": _dates(raw["fecha_embarque"]),
            "incoterm": raw["incoterm"].str.strip().str.upper(),
            "puerto_destino": raw["puerto_destino"].str.strip(),
            "mercado_id": _integers(raw["mercado_id"]),
            "venta_id": _integers(raw["venta_id"]),
            "cajas": _integers(raw["cajas"]),
        }
    )


def fetch_exchange_rate(year: int) -> dict:
    """Descarga el dólar observado de un año desde Mindicador."""
    request = urllib.request.Request(
        EXCHANGE_RATE_URL.format(year=year),
        headers={"User-Agent": "vina-vallehondo-bi"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def read_exchange_rate(
    project_root: Path,
    years: Iterable[int] = EXCHANGE_RATE_YEARS,
    fetcher: Fetcher = fetch_exchange_rate,
) -> pd.DataFrame:
    """Obtiene el dólar observado diario de los años indicados.

    Guarda la respuesta de la API en staging y la reutiliza si una ejecución
    posterior no logra conectarse. La serie solo trae días hábiles.
    """
    staging = project_root / STAGING_DIRECTORY
    staging.mkdir(parents=True, exist_ok=True)

    rows = []
    for year in years:
        cache = staging / f"tipo_cambio_{year}.json"
        try:
            payload = fetcher(year)
            cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except (OSError, ValueError) as error:
            if not cache.is_file():
                raise RuntimeError(
                    f"No se pudo descargar el tipo de cambio de {year} y no hay una copia previa en {cache}."
                ) from error
            print(f"Aviso: no se pudo descargar el tipo de cambio de {year}; se usa la copia en {cache.name}.")
            payload = json.loads(cache.read_text(encoding="utf-8"))
        # La API entrega la medianoche de Chile en UTC, por lo que el día es el de la marca de tiempo.
        rows.extend((entry["fecha"][:10], entry["valor"]) for entry in payload.get("serie", []))

    frame = pd.DataFrame(rows, columns=["fecha", "dolar_observado"])
    frame["fecha"] = pd.to_datetime(frame["fecha"])
    frame["dolar_observado"] = frame["dolar_observado"].astype("float64")
    return frame.drop_duplicates("fecha").sort_values("fecha").reset_index(drop=True)


def run_ingestion(
    project_root: Path,
    include_exchange_rate: bool = True,
    exchange_rate_years: Iterable[int] = EXCHANGE_RATE_YEARS,
    fetcher: Fetcher = fetch_exchange_rate,
) -> dict[str, pd.DataFrame]:
    """Lee todas las fuentes y escribe una tabla Parquet por cada una en staging."""
    tables = {
        "stg_ventas": read_sales(project_root),
        **read_dimensions(project_root),
        "stg_costos_productos": read_costs(project_root),
        "stg_embarques": read_shipments(project_root),
    }
    if include_exchange_rate:
        tables["stg_tipo_cambio"] = read_exchange_rate(project_root, exchange_rate_years, fetcher)

    staging = project_root / STAGING_DIRECTORY
    staging.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_parquet(staging / f"{name}.parquet", index=False)
    return tables


def summarize(tables: dict[str, pd.DataFrame]) -> str:
    """Resume filas y nulos por tabla para revisar el resultado de la ingesta."""
    lines = []
    for name, table in tables.items():
        nulls = table.isna().sum()
        detail = ", ".join(f"{column}={count}" for column, count in nulls[nulls > 0].items())
        lines.append(f"{name}: {len(table)} filas" + (f" (nulos: {detail})" if detail else ""))
    return "\n".join(lines)
