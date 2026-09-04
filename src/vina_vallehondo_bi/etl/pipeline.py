"""Punto de entrada del ETL.

Este scaffolding valida las fuentes y prepara las capas de salida. Las
transformaciones se agregarán por etapas, una vez validadas en los notebooks.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


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
    parser = argparse.ArgumentParser(description="Prepara el entorno de salida para el ETL de Viña Vallehondo.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Ruta de la raíz del proyecto (por defecto: directorio actual).",
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
    print("Scaffolding ETL listo. No se ejecutaron transformaciones.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
