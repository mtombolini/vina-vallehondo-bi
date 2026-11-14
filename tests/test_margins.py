import json
from pathlib import Path

import pandas as pd
import pytest

from vina_vallehondo_bi.etl.margins import TOTAL, publish_margin_tables
from vina_vallehondo_bi.etl.processed import run_processing
from vina_vallehondo_bi.etl.staging import run_ingestion

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def published(tmp_path_factory):
    project = tmp_path_factory.mktemp("margin")
    for name in ("origen_vina.sqlite", "origen_costos_productos.csv", "origen_embarques.json"):
        (project / name).symlink_to(ROOT / name)

    def cached_exchange_rate(year):
        return json.loads((ROOT / "data/staging" / f"tipo_cambio_{year}.json").read_text())

    staging = run_ingestion(project, fetcher=cached_exchange_rate)
    processed = run_processing(project, staging)
    tables = publish_margin_tables(project, staging, processed)
    first_csvs = {p.name: p.read_bytes() for p in (project / "data/published").glob("*.csv")}
    publish_margin_tables(project, staging, processed)
    assert set(first_csvs) == {f"{name}.csv" for name in tables}
    assert first_csvs == {p.name: p.read_bytes() for p in (project / "data/published").glob("*.csv")}
    return tables


def test_reproduces_e1_and_isolates_finance_adjustments(published):
    audit = published["sensibilidad_reglas_margen"].set_index(["criterio", "pais"])
    total = audit.xs(TOTAL, level="pais")
    br = audit.xs("Brasil", level="pais")
    assert total["margen_por_litro"].round(2).to_dict() == {
        "e1": 2201.93, "solo_monto_facturado": 2230.24,
        "solo_sin_reversa": 2182.32, "reglas_finanzas": 2210.64,
    }
    assert br["margen_por_litro"].round(2).to_dict() == {
        "e1": 1705.27, "solo_monto_facturado": 1730.27,
        "solo_sin_reversa": 1693.61, "reglas_finanzas": 1718.61,
    }
    assert br["ranking"].eq(10).all()
    assert total.loc["reglas_finanzas", "costo_producto"] - total.loc["e1", "costo_producto"] == 222_719_760
    assert br.loc["reglas_finanzas", "mediana_margen_por_litro"] == pytest.approx(2289.02344)
    flags = published["descuadres_monto_exportacion"]
    assert len(flags) == 527 and flags["venta_id"].is_unique
    scaled = flags.loc[flags["ajuste_cajas"].eq("dividido_por_10")]
    assert not scaled.empty
    assert (scaled["neto_facturado_usd"] == scaled["neto_fuente_usd"] / 10).all()


def test_dashboard_uses_same_universe_for_date_sensitivity(published):
    data = published["margen_por_mercado"]
    keys = ["criterio", "moneda", "fecha_conversion", "base", "pais"]
    assert not data.duplicated(keys).any()
    assert len(data) == 132
    comparable = data.loc[data["base"].eq("comparable")]
    for field in ["ventas_con_margen", "litros_con_margen", "cobertura_litros_pct"]:
        wide = comparable.pivot(index=["criterio", "moneda", "pais"], columns="fecha_conversion", values=field)
        assert wide["factura"].equals(wide["embarque"])
    assert (data["margen_por_caja"] - data["margen_por_litro"] * 9).abs().max() < 1e-8
    assert (data["crecimiento_litros_pct"] - data["crecimiento_cajas_pct"]).abs().max() < 1e-8
    indexed = data.set_index(keys).sort_index()
    official = indexed.loc["reglas_finanzas", "CLP", "factura", "disponible"]
    comparable_clp = indexed.loc["reglas_finanzas", "CLP", "embarque", "comparable"]
    assert official.loc[TOTAL, "cobertura_litros_pct"] == pytest.approx(100)
    assert comparable_clp.loc[TOTAL, "cobertura_litros_pct"] == pytest.approx(28.38686)
    assert official.loc["México", "ranking"] == 2
    assert official.loc["Reino Unido", "ranking"] == 3
    assert comparable_clp.loc["Brasil", "ranking"] == 10
    assert data.query("moneda == 'USD'")["margen_por_litro"].between(1, 3).all()


def test_business_case_and_monthly_series_reconcile(published):
    business = published["caso_descuento_brasil"].set_index("criterio")
    assert business.loc["e1", "descuento_extra_clp"] == pytest.approx(783_826_600, abs=100)
    br = business.loc["reglas_finanzas"]
    assert br["un_punto_descuento_clp"] == pytest.approx(70_617_137.74)
    assert br["perdida_volumen_equilibrio_pct"] == pytest.approx(23.3818, abs=1e-4)
    mix = published["escenarios_mezcla"]
    assert len(mix) == 4
    assert mix["variacion_margen_clp"].tolist() == pytest.approx(
        (mix["litros_reasignados"] * (mix["margen_destino_clp_litro"] - mix["margen_origen_clp_litro"])).tolist()
    )
    monthly = published["serie_mensual_mercado"].groupby("pais")["margen_total"].sum()
    official = published["margen_por_mercado"].query(
        "criterio == 'reglas_finanzas' and moneda == 'CLP' and fecha_conversion == 'factura' and base == 'disponible'"
    ).set_index("pais")["margen_total"].drop(TOTAL)
    pd.testing.assert_series_equal(monthly.sort_index(), official.sort_index())
