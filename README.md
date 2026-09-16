# CRAEI

Climate Risk Assessment for Energy Infrastructure: asset-level exposure of
hydro and thermal power plants in Brazil, India and Portugal to heat, drought
and water-stress hazards under ISIMIP3b climate projections.

## Installation

```bash
conda env create -f environment.yml
conda activate craei
pip install -e .
cp config/paths.example.yaml config/paths.local.yaml  # fill in real paths
```

## Running the pipeline

Scripts run in numeric order, each a thin wrapper around `src/craei`:

```bash
python scripts/01_inventory.py
python scripts/02_acquire.py
...
python scripts/12_figures.py
```

## Methodology

The single source of truth for all definitions, thresholds and formulas is
[`docs/METHODS_SPEC.md`](docs/METHODS_SPEC.md). Decisions and known
limitations are tracked in [`docs/DECISIONS.md`](docs/DECISIONS.md) and
[`docs/LIMITATIONS.md`](docs/LIMITATIONS.md).

## Data sources

- ISIMIP3b bias-adjusted climate input data — Frieler, K. et al. (2021),
  ISIMIP3b scenario and forcing protocol; Lange, S. (2019), *Geoscientific
  Model Development*.
- Global Energy Monitor, Global Integrated Power Tracker.
- WRI Aqueduct 4.0 — Kuzma, S. et al. (2023).
- HydroBASINS / HydroSHEDS — Lehner, B. & Grill, G. (2013), *Hydrological
  Processes*.

Raw and processed data are not stored in this repository (see
`config/paths.local.yaml`).
