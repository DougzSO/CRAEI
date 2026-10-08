"""Country definitions (config/countries/<ISO>.yaml) for main.py and the country-specific scripts.

`load_country` resolves an ISO code or an alias (case-insensitive) to its definition and refuses countries that
are not implemented, so a run never starts partially. `iso()` is the country of the current run: the
environment variable CRAEI_COUNTRY set by main.py, BRA when a script is run on its own.
"""

import os
from pathlib import Path

import yaml

from craei.config import CONFIG_DIR

DEFAULT_COUNTRY = "BRA"


class CountryNotImplemented(Exception):
    """Raised for a known country whose pipeline is not implemented (PRT, IND)."""


def _definitions(config_dir: Path = CONFIG_DIR) -> list[dict]:
    out = []
    for p in sorted((Path(config_dir) / "countries").glob("*.yaml")):
        with open(p, encoding="utf-8") as fh:
            out.append(yaml.safe_load(fh))
    return out


def load_country(name: str, config_dir: Path = CONFIG_DIR) -> dict:
    """Definition of the country called `name` (ISO or alias); error if unknown or not implemented."""
    key = str(name).strip().lower()
    for d in _definitions(config_dir):
        if key in {str(a).lower() for a in [d["iso"], d["name"], *d.get("aliases", [])]}:
            if not d.get("implemented", False):
                raise CountryNotImplemented(f"país não implementado: {d['iso']}")
            return d
    known = ", ".join(sorted(d["iso"] for d in _definitions(config_dir)))
    raise ValueError(f"unknown country {name!r}; known: {known}")


def iso() -> str:
    """ISO code of the current run's country (CRAEI_COUNTRY, default BRA)."""
    return load_country(os.environ.get("CRAEI_COUNTRY", DEFAULT_COUNTRY))["iso"]


def current() -> dict:
    """Definition of the current run's country."""
    return load_country(os.environ.get("CRAEI_COUNTRY", DEFAULT_COUNTRY))
