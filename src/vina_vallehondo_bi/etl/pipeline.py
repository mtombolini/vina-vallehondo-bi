"""Punto de entrada del ETL.

Valida las fuentes, prepara las capas de salida y ejecuta la ingesta a
staging y la limpieza a processed. El modelo publicado se agregará por etapas,
una vez validado en los notebooks.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from vina_vallehondo_bi.etl.processed import run_processing
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


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    missing = missing_sources(project_root)
    if missing:
        names = ", ".join(path.name for path in missing)
        raise SystemExit(f"No se encontraron fuentes requeridas: {names}")

    prepare_output_directories(project_root)
    tables = run_ingestion(
        project_root,
        include_exchange_rate=not args.omitir_tipo_cambio,
        exchange_rate_years=args.anios_tipo_cambio,
    )
    print(summarize(tables))
    print()
    print(summarize(run_processing(project_root, tables)))
    print("Ingesta a staging y limpieza a processed listas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
