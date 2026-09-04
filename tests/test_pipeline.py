from pathlib import Path

from vina_vallehondo_bi.etl.pipeline import OUTPUT_DIRECTORIES, missing_sources, prepare_output_directories


def test_missing_sources_reports_all_expected_files(tmp_path: Path) -> None:
    assert [path.name for path in missing_sources(tmp_path)] == [
        "origen_vina.sqlite",
        "origen_costos_productos.csv",
        "origen_embarques.json",
    ]


def test_prepare_output_directories_creates_all_layers(tmp_path: Path) -> None:
    prepare_output_directories(tmp_path)

    assert all((tmp_path / directory).is_dir() for directory in OUTPUT_DIRECTORIES)
