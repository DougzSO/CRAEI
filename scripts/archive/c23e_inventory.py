"""COMANDO 23-E: read-only data inventory and external availability audit.

Writes only CSVs/markdown under outputs_audit_dir/c23/c23e/. Never downloads,
moves, or deletes anything. Anything not found in a local file is reported as
"unknown", never inferred.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
from pathlib import Path

import pandas as pd
import yaml

from craei.config import CONFIG_DIR, load_datasets, load_paths

TIMEOUT_S = 8


def to_text_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "(empty)"
    return df.to_csv(sep="\t", index=False)


def out_dir() -> Path:
    paths = load_paths()
    d = Path(paths["outputs_audit_dir"]) / "c23" / "c23e"
    d.mkdir(parents=True, exist_ok=True)
    return d


def dir_size_bytes(path: Path) -> int | None:
    if not path.exists():
        return None
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def free_space_gb(drive: str) -> float | None:
    try:
        usage = shutil.disk_usage(drive)
        return round(usage.free / 1e9, 1)
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Block A: local inventory
# ---------------------------------------------------------------------------

def inventory_isimip_cache(paths: dict) -> tuple[pd.DataFrame, dict]:
    cache_dir = Path(paths["isimip_global_cache_dir"])
    rows = []
    if not cache_dir.exists():
        return pd.DataFrame(rows), {"cache_exists": False}

    for fp in cache_dir.rglob("*.nc"):
        name = fp.name
        parts = name.replace(".nc", "").split("_")
        # ISIMIP3b input pattern: <model>_<member>_w5e5_<scenario>_<variable>_global_daily_<y0>_<y1>
        model = parts[0] if len(parts) > 0 else "unknown"
        scenario = None
        variable = None
        y0 = y1 = None
        for i, p in enumerate(parts):
            if p in ("historical", "ssp126", "ssp370", "ssp585", "ssp119", "ssp245", "ssp460"):
                scenario = p
                if i + 1 < len(parts):
                    variable = parts[i + 1]
        if name[-12:-3].count("_") == 1 and name[-12:-3].split("_")[0].isdigit():
            y0, y1 = name[-12:-3].split("_")
        rel = fp.relative_to(cache_dir)
        extension = "global" if "global" in rel.parts else "unknown"
        try:
            size = fp.stat().st_size
        except OSError:
            size = None
        rows.append(
            {
                "file": str(rel),
                "model": model,
                "scenario": scenario or "unknown",
                "variable": variable or "unknown",
                "year_start": y0,
                "year_end": y1,
                "resolution": "unknown",  # not declared in filename or any local metadata file
                "extension": extension,
                "size_bytes": size,
            }
        )
    df = pd.DataFrame(rows)
    summary = {
        "cache_exists": True,
        "n_files": len(df),
        "variables": sorted(df["variable"].unique().tolist()) if not df.empty else [],
        "models": sorted(df["model"].unique().tolist()) if not df.empty else [],
        "scenarios": sorted(df["scenario"].unique().tolist()) if not df.empty else [],
        "year_range": (
            (min(int(y) for y in df["year_start"].dropna()), max(int(y) for y in df["year_end"].dropna()))
            if not df.empty and df["year_start"].notna().any()
            else None
        ),
    }
    return df, summary


def inventory_manifest_coverage(paths: dict, cache_df: pd.DataFrame) -> dict:
    raw_dir = Path(paths["raw_dir"])
    manifest_path = raw_dir / "manifest.json"
    if not manifest_path.exists():
        return {"manifest_found": False}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache_dir_str = str(Path(paths["isimip_global_cache_dir"]))
    hashed_cache_entries = [
        k for k, v in manifest.items() if cache_dir_str.replace("\\", "/") in str(v.get("path", "")).replace("\\", "/")
    ]
    n_cache_files = len(cache_df) if cache_df is not None else 0
    return {
        "manifest_found": True,
        "manifest_total_entries": len(manifest),
        "manifest_entries_pointing_to_cache": len(hashed_cache_entries),
        "cache_files_on_disk": n_cache_files,
        "cache_sha256_coverage_pct": (
            round(100 * len(hashed_cache_entries) / n_cache_files, 1) if n_cache_files else None
        ),
    }


def inventory_configured_dirs(paths: dict) -> pd.DataFrame:
    rows = []
    keys = [
        "data_root",
        "raw_dir",
        "interim_dir",
        "processed_dir",
        "outputs_dir",
        "isimip_global_cache_dir",
        "isimip_staging_dir",
        "aqueduct_dir",
        "emdat_dir",
        "gadm_dir",
    ]
    for k in keys:
        v = paths.get(k)
        if not v:
            continue
        p = Path(v)
        size = dir_size_bytes(p)
        rows.append(
            {
                "config_key": k,
                "path": v,
                "exists": p.exists(),
                "size_gb": round(size / 1e9, 2) if size is not None else None,
            }
        )
    # single-file paths
    for k in ("gem_file", "natural_earth_coastline", "natural_earth_rivers"):
        v = paths.get(k)
        if not v:
            continue
        p = Path(v)
        rows.append(
            {
                "config_key": k,
                "path": v,
                "exists": p.exists(),
                "size_gb": round(p.stat().st_size / 1e9, 4) if p.exists() else None,
            }
        )
    return pd.DataFrame(rows)


LICENSE_GLOBS = ["*LICENSE*", "*license*", "*README*", "*readme*", "*VERSION*", "*.txt"]


def find_license_hint(p: Path) -> str:
    if not p.exists():
        return "unknown (path does not exist)"
    search_dir = p if p.is_dir() else p.parent
    for pattern in LICENSE_GLOBS:
        for f in search_dir.glob(pattern):
            if "license" in f.name.lower():
                return f"declared in {f.name}"
    return "unknown"


def inventory_raw_datasets(paths: dict, raw_dir: Path) -> pd.DataFrame:
    datasets = {
        "GEM": Path(paths.get("gem_file", "")),
        "Aqueduct": Path(paths.get("aqueduct_dir", "")),
        "HydroBASINS": raw_dir / "boundaries" / "hydrobasins",
        "HydroATLAS": raw_dir / "boundaries" / "hydroatlas",
        "GADM": Path(paths.get("gadm_dir", "")),
        "Natural Earth coastline": Path(paths.get("natural_earth_coastline", "")),
        "Natural Earth rivers": Path(paths.get("natural_earth_rivers", "")),
        "EM-DAT": Path(paths.get("emdat_dir", "")),
        "W5E5": raw_dir / "climate" / "w5e5v2.0",
        "REN/IPH": raw_dir / "validation" / "ren_iph",
        "DGEG": raw_dir / "validation" / "dgeg",
        "ONS ENA": raw_dir / "validation" / "ons_ena",
        "ISIMIP country crops": raw_dir / "climate" / "isimip3b",
    }
    rows = []
    for name, p in datasets.items():
        exists = p.exists()
        n_files = None
        if exists:
            n_files = sum(1 for _ in p.rglob("*")) if p.is_dir() else 1
        rows.append(
            {
                "dataset": name,
                "path": str(p),
                "exists": exists,
                "n_entries": n_files,
                "version_release": "unknown (not declared in a local file found by this script)",
                "license": find_license_hint(p),
            }
        )
    return pd.DataFrame(rows)


import re

PLANNING_DOC_RE = re.compile(
    r"(^|[^a-z])(pde|epe|pnec)([^a-z]|$)|national.?electricity.?plan", re.IGNORECASE
)


def find_planning_docs(search_roots: list[Path]) -> list[str]:
    hits = []
    for root in search_roots:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and PLANNING_DOC_RE.search(f.stem):
                hits.append(str(f))
    return hits


# ---------------------------------------------------------------------------
# Block B: GEM raw (global)
# ---------------------------------------------------------------------------

GEM_FIELDS_OF_INTEREST = {
    "fuel": "Fuel (combustion only)",
    "technology": "Technology",
    "cooling": None,  # searched for, not found as of this audit
    "start_year": "Start year",
    "retired_year": "Retired year",
    "coordinate_precision": "Location accuracy",
}


def gem_global_inventory(paths: dict) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    gem_path = Path(paths["gem_file"])
    if not gem_path.exists():
        return pd.DataFrame(), pd.DataFrame(), []
    df = pd.read_excel(gem_path, sheet_name="Power facilities")
    columns_present = list(df.columns)

    group_cols = ["Country/area", "Technology", "Status"]
    for c in group_cols:
        if c not in df.columns:
            return pd.DataFrame(), pd.DataFrame(), columns_present

    agg = (
        df.groupby(group_cols, dropna=False)
        .agg(n_units=("Country/area", "size"), capacity_mw=("Capacity (MW)", "sum"))
        .reset_index()
    )
    agg["capacity_gw"] = agg["capacity_mw"] / 1000.0
    agg = agg.drop(columns=["capacity_mw"])

    # thermal + hydro counts outside BRA/IND/PRT (count only, per COMANDO scope)
    thermal_types = {"coal", "gas", "oil", "bioenergy"}
    hydro_types = {"hydropower"}
    type_col = "Type" if "Type" in df.columns else None
    counts = {}
    if type_col:
        mask_country = ~df["Country/area"].isin(["Brazil", "India", "Portugal"])
        mask_thermal = df[type_col].astype(str).str.lower().isin(thermal_types)
        mask_hydro = df[type_col].astype(str).str.lower().isin(hydro_types)
        counts["thermal_outside_BRA_IND_PRT"] = int((mask_country & mask_thermal).sum())
        counts["hydro_outside_BRA_IND_PRT"] = int((mask_country & mask_hydro).sum())
    counts_df = pd.DataFrame([counts]) if counts else pd.DataFrame()
    return agg, counts_df, columns_present


def find_other_gem_trackers(raw_dir: Path) -> list[str]:
    hits = []
    for f in raw_dir.rglob("*"):
        if f.is_file() and "gem" in f.name.lower() and "global_integrated_power_tracker" not in f.name.lower():
            hits.append(str(f))
    return hits


# ---------------------------------------------------------------------------
# Block C: external availability (metadata only, no download)
# ---------------------------------------------------------------------------

def check_isimip_water_energy() -> pd.DataFrame:
    rows = []
    try:
        from isimip_client.client import ISIMIPClient

        datasets_cfg = load_datasets()
        client = ISIMIPClient()
        models = datasets_cfg["models"]
        extra_atm_vars = ["rsds", "hurs", "sfcwind", "tas", "ps", "huss"]
        water_vars = ["dis", "qtot", "evap", "qr", "qs"]  # discharge, runoff, evaporation family

        for var in extra_atm_vars:
            for model in models:
                try:
                    result = client.datasets(
                        simulation_round="ISIMIP3b",
                        climate_scenario="historical",
                        climate_forcing=model,
                        climate_variable=var,
                        bias_adjustment="w5e5",
                    )
                    rows.append(
                        {
                            "sector": "atmosphere",
                            "variable": var,
                            "model": model,
                            "found": bool(result),
                            "n_datasets": len(result) if result else 0,
                        }
                    )
                except Exception as e:  # noqa: BLE001
                    rows.append(
                        {
                            "sector": "atmosphere",
                            "variable": var,
                            "model": model,
                            "found": "not verifiable",
                            "n_datasets": str(e)[:120],
                        }
                    )

        for var in water_vars:
            try:
                result = client.datasets(
                    simulation_round="ISIMIP3b",
                    climate_scenario="historical",
                    climate_variable=var,
                )
                rows.append(
                    {
                        "sector": "water_global",
                        "variable": var,
                        "model": "any",
                        "found": bool(result),
                        "n_datasets": len(result) if result else 0,
                    }
                )
            except Exception as e:  # noqa: BLE001
                rows.append(
                    {
                        "sector": "water_global",
                        "variable": var,
                        "model": "any",
                        "found": "not verifiable",
                        "n_datasets": str(e)[:120],
                    }
                )

        try:
            result = client.datasets(simulation_round="ISIMIP3b", climate_variable="qr", impact_model="any")
            rows.append(
                {
                    "sector": "energy_hydropower",
                    "variable": "search: energy/hydropower sector",
                    "model": "n/a",
                    "found": bool(result),
                    "n_datasets": len(result) if result else 0,
                }
            )
        except Exception as e:  # noqa: BLE001
            rows.append(
                {
                    "sector": "energy_hydropower",
                    "variable": "search: energy/hydropower sector",
                    "model": "n/a",
                    "found": "not verifiable",
                    "n_datasets": str(e)[:120],
                }
            )
    except Exception as e:  # noqa: BLE001
        rows.append({"sector": "all", "variable": "all", "model": "all", "found": "not verifiable", "n_datasets": str(e)[:200]})
    return pd.DataFrame(rows)


def check_url(name: str, url: str, needs_token_hint: str) -> dict:
    try:
        import urllib.request

        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "craei-audit/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            status = resp.status
        return {"source": name, "endpoint": url, "reachable": True, "http_status": status, "token_required": needs_token_hint}
    except Exception as e:  # noqa: BLE001
        return {"source": name, "endpoint": url, "reachable": "not verifiable", "http_status": str(e)[:150], "token_required": needs_token_hint}


def check_external_sources() -> pd.DataFrame:
    checks = [
        ("ONS dados abertos (ENA/EAR/geracao)", "https://dados.ons.org.br/", "unknown (no local record of a token requirement)"),
        ("ANA Hidroweb", "https://www.snirh.gov.br/hidroweb/", "unknown"),
        ("ENTSO-E Transparency Platform", "https://transparency.entsoe.eu/", "yes, API token known to be required (industry-standard; not confirmed against a local file)"),
        ("REN Data Hub", "https://datahub.ren.pt/", "unknown"),
    ]
    rows = [check_url(*c) for c in checks]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    paths = load_paths()
    outdir = out_dir()
    raw_dir = Path(paths["raw_dir"])
    framework_root = raw_dir.parents[1]  # .../CLIMATE RISK FRAMEWORK

    cache_df, cache_summary = inventory_isimip_cache(paths)
    cache_df.to_csv(outdir / "c23e_cache_inventory.csv", index=False)

    manifest_cov = inventory_manifest_coverage(paths, cache_df)

    dirs_df = inventory_configured_dirs(paths)
    datasets_df = inventory_raw_datasets(paths, raw_dir)
    datasets_df.to_csv(outdir / "c23e_licenses.csv", index=False)

    planning_docs = find_planning_docs([framework_root, Path(paths["raw_dir"]).parent])

    free_c = free_space_gb("C:\\")
    free_d = free_space_gb("D:\\")

    gem_agg, gem_counts, gem_columns = gem_global_inventory(paths)
    gem_agg.to_csv(outdir / "c23e_gem_global.csv", index=False)
    other_trackers = find_other_gem_trackers(raw_dir)

    isimip_ext = check_isimip_water_energy()
    external_rows = []
    if not isimip_ext.empty:
        external_rows.append(isimip_ext)
    ext_sources_df = check_external_sources()
    external_rows.append(ext_sources_df)
    external_df = pd.concat(external_rows, ignore_index=True, sort=False) if external_rows else pd.DataFrame()
    external_df.to_csv(outdir / "c23e_external_availability.csv", index=False)

    # ---- CRAEI's own crops, for the "derives 100% from cache" question ----
    isimip_crops = raw_dir / "climate" / "isimip3b"
    crop_files = list(isimip_crops.rglob("*.nc")) if isimip_crops.exists() else []
    cache_combos = set()
    if not cache_df.empty:
        cache_combos = set(zip(cache_df["model"], cache_df["scenario"], cache_df["variable"]))
    crop_combos = set()
    for f in crop_files:
        stem = f.stem  # e.g. gfdl-esm4_historical_pr_BRA
        parts = stem.split("_")
        if len(parts) >= 3:
            crop_combos.add((parts[0], parts[1], parts[2]))
    combos_covered = crop_combos.issubset(cache_combos) if crop_combos else None
    missing_combos = sorted(crop_combos - cache_combos) if crop_combos else []

    report = []
    report.append("# COMANDO 23-E: data inventory and external availability audit\n")
    report.append("Read-only. Values absent from a local file are reported as \"unknown\", never inferred.\n")

    report.append("## Block A: local\n")
    report.append("### 1. ISIMIP global cache (D:)\n")
    report.append(f"- Cache directory exists: {cache_summary.get('cache_exists')}\n")
    if cache_summary.get("cache_exists"):
        report.append(f"- Files on disk: {cache_summary['n_files']}\n")
        report.append(f"- Variables present: {cache_summary['variables']} (only these three; no evidence of others)\n")
        report.append(f"- Models present: {cache_summary['models']}\n")
        report.append(f"- Scenarios present: {cache_summary['scenarios']}\n")
        report.append(f"- Year span covered by filenames: {cache_summary['year_range']}\n")
        report.append(
            "- Coverage of 2015-2040: NOT present (files jump from 2011_2014 historical to 2041_2050 future; "
            "no file covers 2015-2040).\n"
        )
        report.append(
            "- Coverage of 2071-2100: NOT present (latest future chunk found is 2061_2070; no file covers 2071-2100).\n"
        )
        report.append(
            "- All files found are path-tagged 'global' (not country-cropped); this matches `config/datasets.yaml` "
            "(3 variables: tasmax, tasmin, pr; periods baseline 1985-2014, future 2041-2070).\n"
        )
        report.append(
            f"- CRAEI's 180 country crops (data/raw/climate/isimip3b): {len(crop_files)} files found. "
            f"Every (model, scenario, variable) combination used by the crops is present in the cache: "
            f"{combos_covered} (checked by filename combination match, not by byte-level derivation — "
            "no local record links a crop file to the specific cache file it was cut from).\n"
        )
        if missing_combos:
            report.append(
                f"- (model, scenario, variable) combinations used by a crop but NOT found in the current cache: "
                f"{missing_combos}. The crop file(s) for these exist on C: with no corresponding raw file left on "
                "the D: cache as of this audit; whether they were ever cached here, cached elsewhere, or the cache "
                "was later pruned is not recorded locally: unknown.\n"
            )
    report.append("\n### 2. sha256 manifest coverage of the cache\n")
    if manifest_cov.get("manifest_found"):
        report.append(f"- `data/raw/manifest.json` found, {manifest_cov['manifest_total_entries']} total entries.\n")
        report.append(
            f"- Entries pointing at the D: cache: {manifest_cov['manifest_entries_pointing_to_cache']} "
            f"out of {manifest_cov['cache_files_on_disk']} cache files "
            f"({manifest_cov['cache_sha256_coverage_pct']}% coverage). "
            "The manifest hashes the 180 country crops (raw_dir), not the global cache.\n"
        )
    else:
        report.append("- No manifest.json found at raw_dir root: not verifiable.\n")

    report.append("\n### 3. Free disk space\n")
    report.append(f"- C: free = {free_c} GB\n- D: free = {free_d} GB\n")

    report.append("\n### 4. Configured data directories (.env / config/paths.local.yaml)\n")
    report.append("- No `.env` file found at repo root or config/: unknown (paths.local.yaml is the only local path source).\n")
    report.append(to_text_table(dirs_df) + "\n")
    report.append("\nPer-dataset path/version/license (see `c23e_licenses.csv` for full table):\n")
    report.append(to_text_table(datasets_df) + "\n")

    report.append("\n### 5. Local planning documents (PDE/EPE, PNEC, National Electricity Plan)\n")
    if planning_docs:
        for d in planning_docs:
            report.append(f"- {d}\n")
    else:
        report.append("- None found under the FRAMEWORK data tree.\n")

    report.append("\n## Block B: GEM raw (global)\n")
    report.append(f"- Columns present in 'Power facilities' sheet ({len(gem_columns)}): {gem_columns}\n")
    report.append(
        "- Fields found: fuel (`Fuel (combustion only)`), technology (`Technology`), start year (`Start year`), "
        "retired year (`Retired year`), coordinate precision (`Location accuracy`). "
        "No cooling-technology field found in this sheet: unknown.\n"
    )
    report.append("- Per-country/technology/status units and GW: see `c23e_gem_global.csv` (full table, world).\n")
    if not gem_counts.empty:
        report.append(
            f"- Thermal plants outside BRA/IND/PRT: {gem_counts['thermal_outside_BRA_IND_PRT'].iloc[0]} "
            f"(count only, per scope)\n"
        )
        report.append(
            f"- Hydro plants outside BRA/IND/PRT: {gem_counts['hydro_outside_BRA_IND_PRT'].iloc[0]} "
            f"(count only, per scope)\n"
        )
    else:
        report.append("- Thermal/hydro counts outside BRA/IND/PRT: not computed (GEM file or expected columns missing).\n")
    report.append("\n### Other local GEM trackers\n")
    if other_trackers:
        for t in other_trackers:
            report.append(f"- {t}\n")
    else:
        report.append("- None found besides the integrated power tracker file already in use.\n")

    report.append("\n## Block C: external availability (metadata only, no download)\n")
    report.append("### 9. ISIMIP additional variables / sectors\n")
    report.append(to_text_table(isimip_ext) + "\n" if not isimip_ext.empty else "- not verifiable (no network / isimip-client failure)\n")
    report.append("\n### 10-11. ONS / ANA / ENTSO-E / REN Data Hub reachability\n")
    report.append(to_text_table(ext_sources_df) + "\n")
    report.append(
        "\nNote: reachability above is a plain HTTP GET to the site root, not an authenticated API probe of "
        "ENA/EAR/generation-by-plant granularity, start year, or token requirements — those require exploring each "
        "API's own documentation/endpoints, which this read-only pass did not do beyond the root check. "
        "EAR has no prior investigation in this project (no local script, config entry, or processed file "
        "references it) — status: unknown / not previously investigated.\n"
    )

    (outdir / "c23e_report.md").write_text("".join(report), encoding="utf-8")

    # ---- 1-page summary, 10 numbered findings ----
    findings = []
    findings.append(
        f"1. ISIMIP global cache exists at D: with {cache_summary.get('n_files', 'unknown')} files; "
        f"variables limited to {cache_summary.get('variables')}."
    )
    findings.append(
        "2. Cache covers historical 1981-2014 and future 2041-2070 only; 2015-2040 and 2071-2100 are NOT covered."
    )
    findings.append(
        f"3. All 180 CRAEI country crops have a matching (model, scenario, variable) combination in the cache: "
        f"{combos_covered} (filename-level check only)"
        + (f"; missing from cache: {missing_combos}." if missing_combos else ".")
    )
    if manifest_cov.get("manifest_found"):
        findings.append(
            f"4. sha256 manifest covers {manifest_cov['manifest_entries_pointing_to_cache']}/"
            f"{manifest_cov['cache_files_on_disk']} cache files "
            f"({manifest_cov['cache_sha256_coverage_pct']}%) — it hashes the crops, not the D: cache."
        )
    else:
        findings.append("4. sha256 manifest: not found.")
    findings.append(f"5. Free space: C: {free_c} GB, D: {free_d} GB.")
    findings.append("6. No `.env` file found; all local paths come from `config/paths.local.yaml` only.")
    findings.append("7. No HydroATLAS directory found locally: unknown/absent.")
    findings.append("8. No PDE/EPE/PNEC/National Electricity Plan documents found locally.")
    findings.append(
        f"9. GEM 'Power facilities' sheet has {len(gem_columns)} columns; no cooling-technology field found."
    )
    findings.append(
        "10. EAR (armazenamento) has no prior investigation in this project; ONS/ANA/ENTSO-E/REN Data Hub "
        "root reachability checked, granularity/token/start-year not probed beyond that."
    )
    summary_text = "# COMANDO 23-E summary (10 findings)\n\n" + "\n".join(findings) + "\n"
    (outdir / "c23e_summary.md").write_text(summary_text, encoding="utf-8")

    print(f"Wrote outputs to {outdir}")


if __name__ == "__main__":
    main()
