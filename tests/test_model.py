import json
from pathlib import Path

import pandas as pd
import pytest

from vina_vallehondo_bi.etl.margins import TOTAL, build_margin_tables
from vina_vallehondo_bi.etl.model import FACT_COLUMNS, build_model
from vina_vallehondo_bi.etl.processed import run_processing
from vina_vallehondo_bi.etl.staging import run_ingestion

ROOT = Path(__file__).resolve().parents[1]


def cached_exchange_rate(year):
    return json.loads((ROOT / "data/staging" / f"tipo_cambio_{year}.json").read_text())


@pytest.fixture(scope="module")
def layers(tmp_path_factory):
    project = tmp_path_factory.mktemp("modelo")
    for name in ("origen_vina.sqlite", "origen_costos_productos.csv", "origen_embarques.json"):
        (project / name).symlink_to(ROOT / name)
    staging = run_ingestion(project, fetcher=cached_exchange_rate)
    processed = run_processing(project, staging)
    return staging, processed, build_model(staging, processed)


def test_star_schema_has_one_row_per_sale_and_unique_dimension_keys(layers):
    _, processed, model = layers
    fact = model["fact_venta"]
    assert fact.columns.tolist() == FACT_COLUMNS
    assert fact["venta_id"].is_unique and len(fact) == len(processed["ventas"]) == 13_830
    sizes = {name: len(model[name]) for name in ("dim_tiempo", "dim_mercado", "dim_cliente", "dim_producto")}
    assert sizes == {"dim_tiempo": 408, "dim_mercado": 11, "dim_cliente": 26, "dim_producto": 96}
    for dim, key in [("dim_tiempo", "fecha"), ("dim_mercado", "mercado_id"),
                     ("dim_cliente", "cliente_id"), ("dim_producto", "producto_anada_key")]:
        assert model[dim][key].is_unique
    assert fact["fecha"].isin(model["dim_tiempo"]["fecha"]).all()
    assert fact["fecha_embarque"].dropna().isin(model["dim_tiempo"]["fecha"]).all()
    assert fact["producto_anada_key"].isin(model["dim_producto"]["producto_anada_key"]).all()
    assert model["dim_mercado"][["hemisferio", "moneda_facturacion"]].notna().all().all()
    assert model["dim_producto"]["tipo"].notna().all()


def test_fact_measures_follow_finance_rules_and_match_published_metric(layers):
    staging, processed, model = layers
    fact = model["fact_venta"].merge(model["dim_mercado"], on="mercado_id")
    exports = fact.loc[fact["canal"].eq("Exportación")]
    margin = (exports["ingreso_neto_clp_fecha_venta"].sum() - exports["costo_total_clp"].sum()) / exports["litros"].sum()
    published = build_margin_tables(staging, processed)["margen_por_mercado"].query(
        "criterio == 'reglas_finanzas' and moneda == 'CLP' and fecha_conversion == 'factura' "
        "and base == 'disponible' and pais == @TOTAL"
    )["margen_por_litro"].iloc[0]
    assert margin == pytest.approx(published) == pytest.approx(2210.638078)

    # Las mermas restan litros e ingreso, pero no revierten costo.
    returns = fact.loc[fact["cajas"].lt(0)]
    assert len(returns) == 110 and returns["costo_total_clp"].eq(0).all() and returns["litros"].lt(0).all()
    # Chile factura en pesos: el ingreso en CLP es el monto original.
    national = fact.loc[fact["moneda_facturacion"].eq("CLP")]
    pd.testing.assert_series_equal(
        national["ingreso_neto_clp_fecha_venta"], national["ingreso_neto_moneda_original"], check_names=False
    )
    # El monto registrado se conserva y solo se divide en las ventas con cajas x10.
    sales = processed["ventas"].set_index("venta_id")
    source = staging["stg_ventas"].set_index("fila_origen")["monto_neto"]
    registered = sales["fila_origen"].map(source)
    expected = registered.mask(sales["ajuste_cajas"].eq("dividido_por_10"), registered / 10)
    indexed = model["fact_venta"].set_index("venta_id")["ingreso_neto_moneda_original"]
    pd.testing.assert_series_equal(indexed.sort_index(), expected.sort_index(), check_names=False, check_dtype=False)
    assert fact["ingreso_neto_clp_fecha_embarque"].notna().eq(fact["fecha_embarque"].notna()).all()
