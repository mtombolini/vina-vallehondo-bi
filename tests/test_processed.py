from pathlib import Path

import pandas as pd
import pytest

from vina_vallehondo_bi.etl.processed import (
    clean_costs,
    clean_customers,
    clean_exchange_rate,
    clean_markets,
    clean_sales,
    clean_shipments,
    run_processing,
)
from vina_vallehondo_bi.etl.staging import read_costs, read_dimensions, read_sales, read_shipments


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sales_frame(rows: list[dict]) -> pd.DataFrame:
    base = {
        "cliente_id": 9,
        "mercado_id": 4,
        "producto_id": 1,
        "moneda_id": 2,
        "vendedor_id": 3,
        "descuento": 0.0,
        "anada": 2023,
        "zona_origen": "Norteamérica",
        "mes_origen": 1,
    }
    frame = pd.DataFrame([{**base, "fila_origen": index, **row} for index, row in enumerate(rows, start=1)])
    frame["fecha"] = pd.to_datetime(frame["fecha"])
    integers = ["fila_origen", "venta_id", "cliente_id", "mercado_id", "producto_id", "moneda_id", "vendedor_id", "cajas", "anada", "mes_origen"]
    return frame.astype({column: "Int64" for column in integers})


def test_clean_sales_applies_each_rule() -> None:
    sales = sales_frame(
        [
            {"venta_id": 1, "fecha": "2025-01-02", "cajas": 100, "precio_unitario": 20.0, "monto_neto": 2000.0},
            {"venta_id": 2, "fecha": "2025-01-03", "cajas": 1200, "precio_unitario": 20.0, "monto_neto": 2000.0},
            {"venta_id": 3, "fecha": "2025-01-03", "cajas": 1500, "precio_unitario": 20.0, "monto_neto": 30000.0},
            {"venta_id": 4, "fecha": "2026-03-12", "cajas": 50, "precio_unitario": 20.0, "descuento": 0.1, "monto_neto": 1000.0},
            {"venta_id": 5, "fecha": "2025-01-05", "cajas": -10, "precio_unitario": 20.0, "monto_neto": -200.0, "moneda_id": None},
            {"venta_id": 1, "fecha": "2025-01-02", "cajas": 100, "precio_unitario": 20.0, "monto_neto": 2300.0},
        ]
    )

    clean = clean_sales(sales).set_index("venta_id")

    assert clean.index.tolist() == [1, 2, 3, 4, 5]
    assert clean["cajas"].tolist() == [100, 100, 150, 50, -10]
    assert clean["monto_neto"].tolist() == [2000.0, 2000.0, 3000.0, 900.0, -200.0]
    assert clean["ajuste_cajas"].tolist() == ["ninguno", "botellas_a_cajas", "dividido_por_10", "ninguno", "ninguno"]
    assert clean["monto_recalculado"].tolist() == [False, False, False, True, False]
    assert clean.loc[4, "fecha"] == pd.Timestamp("2025-01-03")
    assert clean["fecha_imputada"].tolist() == [False, False, False, True, False]
    assert clean.loc[5, "moneda_id"] == 2
    assert clean["moneda_imputada"].tolist() == [False, False, False, False, True]
    assert clean["es_devolucion"].tolist() == [False, False, False, False, True]


def test_clean_markets_resolves_missing_zone_from_sales() -> None:
    zones = pd.DataFrame({"zona_id": [5], "zona": ["Asia"]})
    markets = pd.DataFrame({"mercado_id": [9, 11], "pais": ["China", "Corea del Sur"], "zona_id": [5, 8], "canal": ["Exportación"] * 2})
    sales = pd.DataFrame({"mercado_id": [11, 11, 11], "zona_origen": ["Asia", "Asia", "Europa"]})

    clean = clean_markets(markets, zones, sales)

    assert clean["zona"].tolist() == ["Asia", "Asia"]
    assert clean["zona_id"].tolist() == [5, 5]


def test_clean_customers_normalizes_rut() -> None:
    customers = pd.DataFrame({"cliente_id": [1, 2, 3], "rut": ["680591970", "66539946-k", "78.998.487 - 5"]})

    assert clean_customers(customers)["rut"].tolist() == ["68059197-0", "66539946-K", "78998487-5"]


def test_clean_costs_unifies_variety_and_fills_missing_costs() -> None:
    varieties = pd.DataFrame({"cepa": ["Cabernet Sauvignon", "Sauvignon Blanc"]})
    costs = pd.DataFrame(
        {
            "fila_origen": [2, 3, 4],
            "producto_id": [1, 1, 2],
            "producto": ["Cabernet Sauvignon Reserva", "Cabernet Sauvignon Reserva", "Sauvignon Blanc Reserva"],
            "cepa": ["CS", "Cab Sauv", "SB"],
            "tier": ["Reserva"] * 3,
            "formato": ["12x750"] * 3,
            "litros_por_caja": [9.0] * 3,
            "anada": [2023, 2024, 2023],
            "costo_caja_clp": [20394.0, 19800.0, None],
            "activo": [True, True, True],
        }
    )

    clean = clean_costs(costs, varieties)

    assert clean[["producto_id", "anada"]].values.tolist() == [[1, 2023], [1, 2024], [2, 2023], [2, 2024]]
    assert clean["cepa"].tolist() == ["Cabernet Sauvignon"] * 2 + ["Sauvignon Blanc"] * 2
    assert clean["costo_caja_clp"].tolist() == [20394.0, 19800.0, 20394.0, 19800.0]
    assert clean["costo_imputado"].tolist() == [False, False, True, True]


def test_clean_shipments_flags_reliable_dates_and_drops_unknown_sales() -> None:
    sales = pd.DataFrame({"venta_id": [1, 2, 3], "fecha": pd.to_datetime(["2025-05-01"] * 3), "mercado_id": [5, 11, 5]})
    shipments = pd.DataFrame(
        {
            "embarque_orden": [1, 1, 2, 3],
            "linea_orden": [1, 2, 1, 1],
            "embarque_id": ["EMB-1", "EMB-1", "EMB-2", "EMB-3"],
            "fecha_embarque": pd.to_datetime(["2025-06-01", "2025-06-01", "2025-04-01", "2025-06-01"]),
            "mercado_id": [5, 5, 5, 5],
            "venta_id": [1, 2, 3, 999],
            "cajas": [10, 20, 30, 40],
        }
    )

    clean = clean_shipments(shipments, sales)

    assert clean["venta_id"].tolist() == [1, 2, 3]
    assert clean["dias_desde_venta"].tolist() == [31, 31, -30]
    assert clean["fecha_embarque_confiable"].tolist() == [True, False, False]


def test_clean_exchange_rate_fills_days_without_publication() -> None:
    rates = pd.DataFrame(
        {"fecha": pd.to_datetime(["2024-12-30", "2025-01-02", "2025-01-03"]), "dolar_observado": [992.12, 996.46, 999.84]}
    )

    clean = clean_exchange_rate(rates)

    assert clean["fecha"].tolist() == [pd.Timestamp(day) for day in ("2025-01-01", "2025-01-02", "2025-01-03")]
    assert clean["dolar_observado"].tolist() == [992.12, 996.46, 999.84]
    assert clean["publicado"].tolist() == [False, True, True]


def test_original_sources_are_consistent_after_cleaning(tmp_path: Path) -> None:
    staging = {
        "stg_ventas": read_sales(PROJECT_ROOT),
        **read_dimensions(PROJECT_ROOT),
        "stg_costos_productos": read_costs(PROJECT_ROOT),
        "stg_embarques": read_shipments(PROJECT_ROOT),
    }

    tables = run_processing(tmp_path, staging)
    sales, costs, shipments = tables["ventas"], tables["costos_productos"], tables["embarques"]

    assert "tipo_cambio" not in tables
    assert (tmp_path / "data/processed/ventas.parquet").is_file()
    assert len(sales) == 13830 and sales["venta_id"].is_unique
    assert sales.notna().all().all()
    assert sales["fecha"].dt.year.eq(2025).all()
    assert sales.sort_values("venta_id")["fecha"].is_monotonic_increasing
    assert sales["cajas"].abs().max() <= 220
    expected = sales["cajas"].astype("float64") * sales["precio_unitario"] * (1 - sales["descuento"])
    assert (sales["monto_neto"] / expected).between(0.995, 1.005).all()
    assert tables["mercados"]["zona"].notna().all()
    with_cost = sales.merge(costs, on=["producto_id", "anada"], how="left")
    assert with_cost["costo_caja_clp"].notna().all()
    assert shipments["venta_id"].isin(sales["venta_id"]).all()
    with_sale = shipments.merge(sales[["venta_id", "cajas"]], on="venta_id", suffixes=("", "_venta"))
    assert (with_sale["cajas"] == with_sale["cajas_venta"].abs()).all()
    assert shipments["fecha_embarque_confiable"].sum() == 3064


def test_clean_sales_tolerates_values_staging_could_not_parse() -> None:
    sales = sales_frame(
        [
            {"venta_id": 1, "fecha": "2025-01-02", "cajas": None, "precio_unitario": 20.0, "monto_neto": 2000.0},
            {"venta_id": 2, "fecha": "2025-01-03", "cajas": 10, "precio_unitario": 20.0, "monto_neto": None},
        ]
    )

    clean = clean_sales(sales).set_index("venta_id")

    assert pd.isna(clean.loc[1, "cajas"])
    assert clean["ajuste_cajas"].tolist() == ["ninguno", "ninguno"]
    assert clean["es_devolucion"].tolist() == [False, False]
    assert clean.loc[2, "monto_neto"] == 200.0
    assert clean["monto_recalculado"].tolist() == [False, True]


def test_clean_exchange_rate_keeps_january_first_without_previous_year() -> None:
    rates = pd.DataFrame({"fecha": pd.to_datetime(["2025-01-02"]), "dolar_observado": [996.46]})

    clean = clean_exchange_rate(rates)

    assert clean["fecha"].tolist() == [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-02")]
    assert pd.isna(clean.loc[0, "dolar_observado"])
