import pytest
import yaml

from craei.config import CONFIG_DIR, REQUIRED_PATH_KEYS, load_datasets, load_params


def test_load_params_all_have_tier_and_source():
    params = load_params()
    assert params
    for name, spec in params.items():
        assert "value" in spec, f"{name} missing value"
        assert "tier" in spec, f"{name} missing tier"
        assert spec["tier"] in (1, 2, 3), f"{name} has invalid tier"
        assert "source" in spec, f"{name} missing source"


def test_load_params_rejects_missing_field(tmp_path):
    bad = tmp_path / "params.yaml"
    bad.write_text("bad_param:\n  value: 1\n  tier: 1\n")
    with pytest.raises(ValueError):
        load_params(config_dir=tmp_path)


def test_load_datasets_has_required_keys():
    datasets = load_datasets()
    assert len(datasets["models"]) == 5
    assert len(datasets["scenarios"]) == 4
    assert len(datasets["variables"]) == 3


def test_paths_example_has_required_keys():
    paths = yaml.safe_load((CONFIG_DIR / "paths.example.yaml").read_text())
    assert set(REQUIRED_PATH_KEYS) <= paths.keys()


def test_load_paths_fails_without_local_file(tmp_path):
    from craei.config import load_paths

    with pytest.raises(FileNotFoundError):
        load_paths(config_dir=tmp_path)
