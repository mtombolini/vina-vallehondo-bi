import json
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from vina_vallehondo_bi.etl.staging import (
    read_costs,
    read_exchange_rate,
    read_sales,
    read_shipments,
    run_ingestion,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def fake_fetcher(year: int) -> dict:
    return {
        "serie": [
            {"fecha": f"{year}-01-03T03:00:00.000Z", "valor": 999.84},
            {"fecha": f"{year}-01-02T03:00:00.000Z", "valor": 996.46},
        ]
    }


def failing_fetcher(year: int) -> dict:
    raise OSError("sin conexión")


def write_sources(root: Path) -> None:
    with sqlite3.connect(root / "origen_vina.sqlite") as connection:
        connection.execute(
            "CREATE TABLE ventas (venta_id INTEGER, fecha TEXT, cliente_id INTEGER, mercado_id INTEGER, "
            "producto_id INTEGER, moneda_id INTEGER, vendedor_id INTEGER, cajas TEXT, precio_unitario TEXT, "
            "descuento TEXT, monto_neto TEXT, anada TEXT, zona TEXT, mes TEXT)"
        )
        connection.executemany(
            "INSERT INTO ventas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "25-mar-2025", 8, 3, 2, 2, 2, "27", "44,01", "0,08", "1.093,15", "2022", "LatAm", "3"),
                (2, "24-09-25", 1, 1, 2, 1, 1, "-53", "$38.100", "5%", "$-1.918.335", "2022", "Nacional", "9"),
                (2, "fecha mala", 1, 1, 2, None, 1, "x", "?", "0", "", "2022", "Nacional", "9"),
            ],
        )
        for table in ("zonas", "mercados", "cepas", "monedas", "vendedores", "clientes"):
            connection.execute(f"CREATE TABLE {table} (id INTEGER, nombre TEXT)")
            connection.execute(f"INSERT INTO {table} VALUES (1, 'á')")

    (root / "origen_costos_productos.csv").write_bytes(
        "producto_id;producto;cepa;tier;formato;litros_por_caja;anada;costo_caja_clp;activo\n"
        "1;Carménère Varietal;CAR;Varietal;12x750;9,0;2021;13.734,00;Sí\n"
        "producto_id;producto;cepa;tier;formato;litros_por_caja;anada;costo_caja_clp;activo\n"
        "2;Merlot Reserva;merlot;Reserva;12x750;9,0;2024;NULL;1\n"
        "TOTAL;;;;;;;;\n".encode("cp1252")
    )
    (root / "origen_embarques.json").write_text(
        json.dumps(
            {
                "embarques": [
                    {
                        "embarque_id": "EMB-1",
                        "fecha_embarque": "21/01/2026",
                        "incoterm": "CIF",
                        "puerto_destino": "Shanghái",
                        "mercado_id": 9,
                        "lineas": [{"venta_id": 1, "cajas": "160"}, {"venta_id": 2, "cajas": 25}],
                    },
                    {
                        "embarque_id": "EMB-1",
                        "fecha_embarque": "2025-06-29",
                        "incoterm": "FOB",
                        "puerto_destino": "Vancouver",
                        "mercado_id": 5,
                        "lineas": [{"venta_id": 3, "cajas": 49}],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    write_sources(tmp_path)
    return tmp_path


def test_read_sales_types_columns_and_keeps_every_row(project: Path) -> None:
    sales = read_sales(project)

    assert len(sales) == 3
    assert sales.loc[0, "fecha"] == pd.Timestamp("2025-03-25")
    assert sales.loc[0, "precio_unitario"] == 44.01
    assert sales.loc[0, "descuento"] == pytest.approx(0.08)
    assert sales.loc[0, "monto_neto"] == 1093.15
    assert sales.loc[1, "cajas"] == -53
    assert sales.loc[1, "precio_unitario"] == 38100.0
    assert sales.loc[1, "descuento"] == pytest.approx(0.05)
    assert sales.loc[1, "monto_neto"] == -1918335.0
    assert sales.loc[2, ["fecha", "moneda_id", "cajas", "precio_unitario", "monto_neto"]].isna().all()


def test_read_costs_drops_repeated_headers_and_total(project: Path) -> None:
    costs = read_costs(project)

    assert costs["producto_id"].tolist() == [1, 2]
    assert costs["fila_origen"].tolist() == [2, 4]
    assert costs["producto"].tolist() == ["Carménère Varietal", "Merlot Reserva"]
    assert costs.loc[0, "costo_caja_clp"] == 13734.0
    assert pd.isna(costs.loc[1, "costo_caja_clp"])
    assert costs["litros_por_caja"].tolist() == [9.0, 9.0]
    assert costs["activo"].tolist() == [True, True]


def test_read_costs_counts_blank_lines_in_fila_origen(project: Path) -> None:
    path = project / "origen_costos_productos.csv"
    lines = path.read_bytes().split(b"\n")
    path.write_bytes(b"\n".join(lines[:2] + [b""] + lines[2:]))

    assert read_costs(project)["fila_origen"].tolist() == [2, 5]


def test_read_sales_nulls_dates_outside_pandas_range(project: Path) -> None:
    with sqlite3.connect(project / "origen_vina.sqlite") as connection:
        connection.execute("UPDATE ventas SET fecha = '1025-03-25' WHERE rowid = 1")

    sales = read_sales(project)

    assert pd.isna(sales.loc[0, "fecha"])
    assert sales.loc[1, "fecha"] == pd.Timestamp("2025-09-24")


def test_read_shipments_flattens_lines_and_keeps_repeated_ids(project: Path) -> None:
    shipments = read_shipments(project)

    assert shipments[["embarque_orden", "linea_orden"]].values.tolist() == [[1, 1], [1, 2], [2, 1]]
    assert shipments["embarque_id"].tolist() == ["EMB-1", "EMB-1", "EMB-1"]
    assert shipments["cajas"].tolist() == [160, 25, 49]
    assert shipments["fecha_embarque"].tolist() == [pd.Timestamp("2026-01-21")] * 2 + [pd.Timestamp("2025-06-29")]


def test_read_exchange_rate_sorts_series_and_caches_response(tmp_path: Path) -> None:
    rates = read_exchange_rate(tmp_path, years=(2025, 2026), fetcher=fake_fetcher)

    assert rates["fecha"].tolist() == [pd.Timestamp(day) for day in ("2025-01-02", "2025-01-03", "2026-01-02", "2026-01-03")]
    assert rates["dolar_observado"].tolist() == [996.46, 999.84, 996.46, 999.84]
    assert (tmp_path / "data/staging/tipo_cambio_2025.json").is_file()


def test_read_exchange_rate_falls_back_to_cache(tmp_path: Path) -> None:
    expected = read_exchange_rate(tmp_path, years=(2025,), fetcher=fake_fetcher)

    pd.testing.assert_frame_equal(read_exchange_rate(tmp_path, years=(2025,), fetcher=failing_fetcher), expected)


def test_read_exchange_rate_keeps_cache_when_response_has_no_series(tmp_path: Path) -> None:
    expected = read_exchange_rate(tmp_path, years=(2025,), fetcher=fake_fetcher)

    for payload in ({"error": "sin datos"}, {"serie": []}):
        pd.testing.assert_frame_equal(read_exchange_rate(tmp_path, years=(2025,), fetcher=lambda year: payload), expected)
    assert json.loads((tmp_path / "data/staging/tipo_cambio_2025.json").read_text(encoding="utf-8")) == fake_fetcher(2025)


def test_read_exchange_rate_fails_without_cache(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="2025"):
        read_exchange_rate(tmp_path, years=(2025,), fetcher=failing_fetcher)


def test_run_ingestion_writes_one_parquet_per_table(project: Path) -> None:
    tables = run_ingestion(project, fetcher=fake_fetcher)

    assert set(tables) == {
        "stg_ventas",
        "stg_zonas",
        "stg_mercados",
        "stg_cepas",
        "stg_monedas",
        "stg_vendedores",
        "stg_clientes",
        "stg_costos_productos",
        "stg_embarques",
        "stg_tipo_cambio",
    }
    for name, table in tables.items():
        stored = pd.read_parquet(project / "data/staging" / f"{name}.parquet")
        assert len(stored) == len(table)


def test_run_ingestion_can_skip_exchange_rate(project: Path) -> None:
    assert "stg_tipo_cambio" not in run_ingestion(project, include_exchange_rate=False, fetcher=failing_fetcher)


def test_original_sources_are_fully_typed() -> None:
    sales = read_sales(PROJECT_ROOT)
    costs = read_costs(PROJECT_ROOT)
    shipments = read_shipments(PROJECT_ROOT)

    assert len(sales) == 13968
    assert sales.drop(columns="moneda_id").notna().all().all()
    assert sales["moneda_id"].isna().sum() == 695
    assert sales["descuento"].between(0, 0.18).all()
    assert len(costs) == 81
    assert costs["costo_caja_clp"].isna().sum() == 1
    assert costs.drop(columns="costo_caja_clp").notna().all().all()
    assert len(shipments) == 10730
    assert shipments.notna().all().all()
