"""Punto de entrada del ETL.

Valida las fuentes, prepara las capas de salida y ejecuta la ingesta a
staging, la limpieza a processed, el modelo estrella y las métricas de margen.
Antes de publicar corre las pruebas de calidad: si una prueba que bloquea
falla, ``data/published`` conserva la corrida anterior y el comando termina
con error.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from vina_vallehondo_bi.etl.margins import build_margin_tables, write_margin_tables
from vina_vallehondo_bi.etl.model import build_model, publish_model
from vina_vallehondo_bi.etl.processed import run_processing
from vina_vallehondo_bi.etl.quality import blocking_failures, run_checks, summarize_checks
from vina_vallehondo_bi.etl.staging import EXCHANGE_RATE_YEARS, run_ingestion, summarize


SOURCE_FILES = (
    "origen_vina.sqlite",
    "origen_costos_productos.csv",
    "origen_embarques.json",
)
OUTPUT_DIRECTORIES = (
    Path("data/staging"),
    Path("data/processed"),
    Path("data/published"),
)


def missing_sources(project_root: Path) -> list[Path]:
    """Devuelve las fuentes requeridas que no están disponibles."""
    return [project_root / name for name in SOURCE_FILES if not (project_root / name).is_file()]


def prepare_output_directories(project_root: Path, directories: Iterable[Path] = OUTPUT_DIRECTORIES) -> None:
    """Crea las carpetas de salida que utilizarán las etapas del ETL."""
    for directory in directories:
        (project_root / directory).mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingesta y limpia las fuentes de Viña Vallehondo.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Ruta de la raíz del proyecto (por defecto: directorio actual).",
    )
    parser.add_argument(
        "--anios-tipo-cambio",
        type=int,
        nargs="+",
        default=list(EXCHANGE_RATE_YEARS),
        metavar="AÑO",
        help=f"Años del dólar observado a descargar (por defecto: {' '.join(map(str, EXCHANGE_RATE_YEARS))}).",
    )
    parser.add_argument(
        "--omitir-tipo-cambio",
        action="store_true",
        help="No consulta la API de tipo de cambio; ingesta solo las fuentes locales.",
    )
    return parser.parse_args()


def write_run_report(project_root: Path, checks: pd.DataFrame, staging: dict[str, pd.DataFrame]) -> None:
    """Deja en published qué datos usó la corrida publicada, para el pie del prototipo."""
    rates = staging["stg_tipo_cambio"]
    fallback = rates.attrs.get("anios_respaldo", [])
    report = {
        "fecha_corrida": datetime.now().astimezone().isoformat(timespec="seconds"),
        "tipo_cambio": {
            "fuente": "respaldo" if fallback else "api",
            "anios_respaldo": fallback,
            "ultimo_dato": f"{rates['fecha'].max():%Y-%m-%d}",
        },
        "pruebas": {
            "total": len(checks),
            "en_verde": int(checks["resultado"].eq("ok").sum()),
            "avisos": int((checks["resultado"].eq("falla") & checks["si_falla"].eq("avisa")).sum()),
        },
    }
    path = project_root / "data/published/corrida.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    missing = missing_sources(project_root)
    if missing:
        names = ", ".join(path.name for path in missing)
        raise SystemExit(f"No se encontraron fuentes requeridas: {names}")

    prepare_output_directories(project_root)
    staging = run_ingestion(
        project_root,
        include_exchange_rate=not args.omitir_tipo_cambio,
        exchange_rate_years=args.anios_tipo_cambio,
    )
    print(summarize(staging))
    print()
    processed = run_processing(project_root, staging)
    print(summarize(processed))

    # El modelo y la métrica convierten a pesos: sin tipo de cambio solo se prueban las fuentes.
    model = metrics = None
    if not args.omitir_tipo_cambio:
        model = build_model(staging, processed)
        metrics = build_margin_tables(staging, processed)
    checks = run_checks(staging, processed, model, metrics)
    checks.to_csv(project_root / "data/published/calidad_ultima_corrida.csv", index=False)
    print()
    print(summarize_checks(checks))

    if not blocking_failures(checks).empty:
        print("Carga bloqueada: data/published conserva las tablas de la corrida anterior.")
        return 1
    if model is not None:
        publish_model(project_root, model)
        write_margin_tables(project_root, metrics)
        write_run_report(project_root, checks, staging)
        print()
        print(summarize({**model, **metrics}))
        print("Modelo y métricas de margen publicados en data/published.")
    print("Ingesta a staging y limpieza a processed listas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
