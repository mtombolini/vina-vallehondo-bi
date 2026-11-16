import json
from pathlib import Path

import pytest

from vina_vallehondo_bi.etl import pipeline
from vina_vallehondo_bi.etl.margins import build_margin_tables
from vina_vallehondo_bi.etl.model import build_model
from vina_vallehondo_bi.etl.processed import run_processing
from vina_vallehondo_bi.etl.quality import BLOCK, WARN, blocking_failures, run_checks
from vina_vallehondo_bi.etl.staging import read_exchange_rate, run_ingestion

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("origen_vina.sqlite", "origen_costos_productos.csv", "origen_embarques.json")


def cached_exchange_rate(year):
    return json.loads((ROOT / "data/staging" / f"tipo_cambio_{year}.json").read_text())


def project_with_sources(path: Path) -> Path:
    for name in SOURCES:
        (path / name).symlink_to(ROOT / name)
    return path


@pytest.fixture(scope="module")
def layers(tmp_path_factory):
    project = project_with_sources(tmp_path_factory.mktemp("calidad"))
    staging = run_ingestion(project, fetcher=cached_exchange_rate)
    processed = run_processing(project, staging)
    return staging, processed, build_model(staging, processed), build_margin_tables(staging, processed)


def test_real_sources_pass_every_blocking_check(layers):
    checks = run_checks(*layers).set_index("prueba")
    assert len(checks) == 13
    assert blocking_failures(checks.reset_index()).empty
    assert checks["si_falla"].value_counts().to_dict() == {BLOCK: 11, WARN: 2}
    # Las 15 líneas de embarque sin venta se informan, pero no detienen la carga.
    assert checks.loc["Fuente JSON de embarques", "resultado"] == "falla"
    assert checks.loc["Fuente JSON de embarques", "detalle"].startswith("15 de 10.730")
    assert checks.loc["API mindicador.cl: origen", "resultado"] == "ok"
    assert checks.loc["Métrica cuadra con el modelo", "resultado"] == "ok"


def test_broken_model_or_rates_block_the_load(layers):
    staging, processed, model, metrics = layers
    duplicated = {**model, "fact_venta": model["fact_venta"].pipe(lambda f: f.assign(
        venta_id=f["venta_id"].where(f.index != 1, f["venta_id"].iloc[0])))}
    orphan = {**model, "dim_cliente": model["dim_cliente"].iloc[1:]}
    bad_rates = {**staging, "stg_tipo_cambio": staging["stg_tipo_cambio"].assign(dolar_observado=lambda t: t["dolar_observado"] * 100)}
    cases = [
        (run_checks(staging, processed, duplicated, metrics), "Unicidad de la clave del hecho"),
        (run_checks(staging, processed, orphan, metrics), "Claves sin huérfanos"),
        (run_checks(bad_rates, processed, model, metrics), "API mindicador.cl: rango"),
    ]
    for checks, failed in cases:
        assert blocking_failures(checks)["prueba"].tolist() == [failed]


def test_exchange_rate_fallback_is_recorded_and_warned(tmp_path):
    (tmp_path / "data/staging").mkdir(parents=True)
    (tmp_path / "data/staging/tipo_cambio_2025.json").write_text(json.dumps(cached_exchange_rate(2025)))

    def offline(year):
        raise OSError("sin conexión")

    rates = read_exchange_rate(tmp_path, [2025], offline)
    assert rates.attrs["anios_respaldo"] == [2025]
    assert read_exchange_rate(tmp_path, [2025], cached_exchange_rate).attrs["anios_respaldo"] == []


def test_pipeline_publishes_only_when_blocking_checks_pass(tmp_path, monkeypatch):
    project = project_with_sources(tmp_path)
    ingest = pipeline.run_ingestion
    monkeypatch.setattr(pipeline, "run_ingestion", lambda root, **kw: ingest(root, fetcher=cached_exchange_rate, **kw))
    monkeypatch.setattr("sys.argv", ["pipeline", "--project-root", str(project)])

    assert pipeline.main() == 0
    published = project / "data/published"
    assert {"fact_venta.parquet", "dim_producto.parquet", "margen_por_mercado.csv", "corrida.json"} <= {
        p.name for p in published.iterdir()
    }
    report = json.loads((published / "corrida.json").read_text())
    assert report["tipo_cambio"]["fuente"] == "api" and report["pruebas"]["total"] == 13

    def failing(*args):
        checks = run_checks(*args)
        checks.loc[checks["prueba"].eq("Unicidad de la clave del hecho"), "resultado"] = "falla"
        return checks

    monkeypatch.setattr(pipeline, "run_checks", failing)
    (published / "margen_por_mercado.csv").write_bytes(b"corrida anterior")
    assert pipeline.main() == 1
    assert (published / "margen_por_mercado.csv").read_bytes() == b"corrida anterior"
    assert "falla" in (published / "calidad_ultima_corrida.csv").read_text()


def test_empty_exchange_rate_blocks_instead_of_crashing(layers):
    staging, processed, _, _ = layers
    empty = {**staging, "stg_tipo_cambio": staging["stg_tipo_cambio"].iloc[0:0]}
    checks = run_checks(empty, processed)
    assert blocking_failures(checks)["prueba"].tolist() == ["API mindicador.cl: rango"]
    assert checks.loc[checks["prueba"].eq("API mindicador.cl: origen"), "detalle"].iloc[0].endswith("sin datos.")


def test_pipeline_reports_build_errors_as_blocking_checks(tmp_path, monkeypatch):
    project = project_with_sources(tmp_path)
    ingest = pipeline.run_ingestion
    monkeypatch.setattr(pipeline, "run_ingestion", lambda root, **kw: ingest(root, fetcher=cached_exchange_rate, **kw))
    monkeypatch.setattr("sys.argv", ["pipeline", "--project-root", str(project)])

    def broken(*args):
        raise ValueError("Hay ventas sin cajas o equivalencia a litros.")

    monkeypatch.setattr(pipeline, "build_model", broken)
    assert pipeline.main() == 1
    published = project / "data/published"
    report = (published / "calidad_ultima_corrida.csv").read_text()
    assert "Construcción del modelo y la métrica" in report and "sin cajas" in report
    assert not (published / "fact_venta.parquet").exists() and not (published / "corrida.json").exists()

    # Sin tipo de cambio no se escribe nada en published.
    (published / "calidad_ultima_corrida.csv").unlink()
    monkeypatch.setattr("sys.argv", ["pipeline", "--project-root", str(project), "--omitir-tipo-cambio"])
    assert pipeline.main() == 0
    assert not any(published.iterdir())


def test_check_details_use_chilean_number_format(layers):
    detail = run_checks(*layers).set_index("prueba").loc["Métrica cuadra con el modelo", "detalle"]
    assert detail == "fact_venta 2.210,64 y métrica 2.210,64 CLP/L; diferencia 0,0000."
