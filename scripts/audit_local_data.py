"""COMANDO 07: audit real fields of GEM, Aqueduct, EM-DAT and GADM.

Lists columns and unique values only; does not map strings to classes.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from craei.config import load_paths

COUNTRIES = ("Brazil", "India", "Portugal")


def audit_gem(gem_file: Path) -> None:
    print("\n=== GEM Global Integrated Power Tracker ===")
    xl = pd.ExcelFile(gem_file)
    print(f"Sheets: {xl.sheet_names}")
    for sheet in xl.sheet_names:
        df = xl.parse(sheet, nrows=5)
        print(f"\n-- sheet '{sheet}' -- columns ({len(df.columns)}):")
        print(list(df.columns))

    # Use the sheet that looks like the main unit-level table.
    main_sheet = "Power facilities" if "Power facilities" in xl.sheet_names else xl.sheet_names[0]
    df = xl.parse(main_sheet)
    print(f"\nUsing sheet '{main_sheet}' for detailed audit, {len(df)} rows.")
    print(f"Columns: {list(df.columns)}")

    for col in ("Status", "Type", "Technology", "Fuel (combustion only)", "Country/area"):
        if col in df.columns:
            print(f"\nUnique values of '{col}' ({df[col].nunique()}):")
            print(sorted(df[col].dropna().unique().tolist()))

    country_col = "Country/area" if "Country/area" in df.columns else None
    if country_col:
        for status_like in ("Status", "Type", "Technology", "Fuel (combustion only)"):
            if status_like in df.columns:
                print(f"\nUnique '{status_like}' per country:")
                for country in COUNTRIES:
                    sub = df[df[country_col].str.contains(country, case=False, na=False)]
                    print(f"  {country}: {sorted(sub[status_like].dropna().unique().tolist())}")

    lat_col = next((c for c in df.columns if c.lower() in ("latitude", "lat")), None)
    lon_col = next((c for c in df.columns if c.lower() in ("longitude", "lon")), None)
    cap_col = next((c for c in df.columns if "capacity" in c.lower()), None)
    if lat_col and lon_col:
        missing_coords = df[df[lat_col].isna() | df[lon_col].isna()]
        print(f"\nRows without coordinates: {len(missing_coords)} / {len(df)}")
    if cap_col:
        missing_cap = df[df[cap_col].isna()]
        print(f"Rows without capacity ('{cap_col}'): {len(missing_cap)} / {len(df)}")

    if country_col:
        print("\nRow counts per country (GEM):")
        for country in COUNTRIES:
            n = df[country_col].str.contains(country, case=False, na=False).sum()
            print(f"  {country}: {n}")
        print(f"  Total rows in sheet: {len(df)}")


def audit_aqueduct(aqueduct_dir: Path) -> None:
    print("\n=== WRI Aqueduct ===")
    for country in COUNTRIES:
        country_dir = aqueduct_dir / country
        if not country_dir.exists():
            print(f"{country}: directory not found ({country_dir})")
            continue
        files = sorted(country_dir.glob("*"))
        print(f"\n{country}: files found: {[f.name for f in files]}")
        for f in files:
            if f.suffix.lower() != ".csv":
                continue
            df = pd.read_csv(f, nrows=5)
            print(f"  '{f.name}' columns ({len(df.columns)}): {list(df.columns)}")
            full = pd.read_csv(f)
            print(f"  '{f.name}' row count: {len(full)}")
            bws_cols = [c for c in full.columns if "bws" in c.lower()]
            print(f"  bws-related columns: {bws_cols}")
            if bws_cols:
                for c in bws_cols:
                    sample = sorted(full[c].dropna().unique().tolist())[:20]
                    print(f"    unique values in '{c}' (sample): {sample}")
            ws_cols = [c for c in full.columns if "_ws_" in c.lower()]
            print(f"  '_ws_' (water stress) columns: {ws_cols}")
            if ws_cols:
                for c in ws_cols[:4]:
                    sample = sorted(full[c].dropna().unique().tolist())[:20]
                    print(f"    unique values in '{c}' (sample): {sample}")


def audit_emdat(emdat_dir: Path) -> None:
    print("\n=== EM-DAT ===")
    for country in COUNTRIES:
        f = emdat_dir / f"emdat_{country}.csv"
        if not f.exists():
            print(f"{country}: file not found ({f})")
            continue
        df = pd.read_csv(f)
        print(f"\n{country}: '{f.name}' rows: {len(df)}, columns ({len(df.columns)}):")
        print(list(df.columns))
        if "Start Year" in df.columns:
            print(f"  Year coverage: {df['Start Year'].min()}-{df['Start Year'].max()}")
        if "Disaster Type" in df.columns:
            types = sorted(df["Disaster Type"].dropna().unique().tolist())
            print(f"  Unique Disaster Type: {types}")


def audit_gadm(gadm_dir: Path) -> None:
    print("\n=== GADM ===")
    iso_map = {"Brazil": "BRA", "India": "IND", "Portugal": "PRT"}
    for country, iso in iso_map.items():
        f = gadm_dir / f"gadm41_{iso}.gpkg"
        if not f.exists():
            print(f"{country}: file not found ({f})")
            continue
        import fiona

        layers = fiona.listlayers(f)
        print(f"\n{country}: '{f.name}' layers: {layers}")
        for layer in layers:
            gdf = gpd.read_file(f, layer=layer, rows=5)
            print(f"  layer '{layer}' columns ({len(gdf.columns)}): {list(gdf.columns)}")
        # Row count and coverage for the finest available admin layer.
        finest = layers[-1]
        gdf_full = gpd.read_file(f, layer=finest)
        print(f"  layer '{finest}' feature count: {len(gdf_full)}")


def main() -> None:
    paths = load_paths()
    gem_file = Path(paths["gem_file"])
    aqueduct_dir = Path(paths["aqueduct_dir"])
    emdat_dir = Path(paths["emdat_dir"])
    gadm_dir = Path(paths["gadm_dir"])

    audit_gem(gem_file)
    audit_aqueduct(aqueduct_dir)
    audit_emdat(emdat_dir)
    audit_gadm(gadm_dir)


if __name__ == "__main__":
    main()
