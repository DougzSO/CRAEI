"""Load and validate YAML configuration for CRAEI."""

from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

REQUIRED_PATH_KEYS = (
    "data_root",
    "raw_dir",
    "interim_dir",
    "processed_dir",
    "outputs_dir",
)

REQUIRED_DATASET_KEYS = (
    "models",
    "scenarios",
    "variables",
    "periods",
    "bboxes",
)


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_params(config_dir: Path = CONFIG_DIR) -> dict:
    params = _load_yaml(config_dir / "params.yaml")
    for name, spec in params.items():
        missing = {"value", "tier", "source"} - spec.keys()
        if missing:
            raise ValueError(f"params.yaml: '{name}' is missing {sorted(missing)}")
    return params


def load_datasets(config_dir: Path = CONFIG_DIR) -> dict:
    datasets = _load_yaml(config_dir / "datasets.yaml")
    missing = set(REQUIRED_DATASET_KEYS) - datasets.keys()
    if missing:
        raise ValueError(f"datasets.yaml: missing keys {sorted(missing)}")
    return datasets


def load_paths(config_dir: Path = CONFIG_DIR) -> dict:
    local_path = config_dir / "paths.local.yaml"
    if not local_path.exists():
        raise FileNotFoundError(
            f"{local_path} not found. Copy config/paths.example.yaml to "
            "config/paths.local.yaml and fill in real paths."
        )
    paths = _load_yaml(local_path)
    missing = set(REQUIRED_PATH_KEYS) - paths.keys()
    if missing:
        raise ValueError(f"paths.local.yaml: missing keys {sorted(missing)}")
    return paths
