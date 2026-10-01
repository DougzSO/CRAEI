"""O26: fetch Natural Earth (public domain) via cartopy and keep Brazil layers."""

from datetime import date
from pathlib import Path

import geopandas as gpd
from cartopy.io import shapereader

from craei.config import load_paths


def fetch(name):
    path = shapereader.natural_earth(resolution="10m", category="cultural", name=name)
    return gpd.read_file(path), path


def pick(gdf, col):
    low = {c.lower(): c for c in gdf.columns}
    return low[col.lower()]


def main():
    out = Path(load_paths()["processed_dir"]).parent / "external" / "geo"
    out.mkdir(parents=True, exist_ok=True)
    ctry, p0 = fetch("admin_0_countries")
    adm1, p1 = fetch("admin_1_states_provinces")
    bra = ctry[ctry[pick(ctry, "ADM0_A3")] == "BRA"]
    sam = ctry[ctry[pick(ctry, "CONTINENT")] == "South America"]
    bra1 = adm1[adm1[pick(adm1, "adm0_a3")] == "BRA"]
    gpkg = out / "natural_earth_brazil.gpkg"
    bra.to_file(gpkg, layer="brazil_admin0", driver="GPKG")
    sam.to_file(gpkg, layer="southamerica_admin0", driver="GPKG")
    bra1.to_file(gpkg, layer="brazil_admin1", driver="GPKG")
    note = (
        "Natural Earth 10m cultural: admin_0_countries, admin_1_states_provinces.\n"
        "Fetched via cartopy on " + str(date.today()) + ". Terms: public domain\n"
        "(naturalearthdata.com/about/terms-of-use). Source files: " + str(p0)
        + " ; " + str(p1) + "\n"
    )
    (out / "SOURCE.txt").write_text(note, encoding="utf-8")
    print("brazil admin0:", len(bra), "| south america admin0:", len(sam),
          "| brazil admin1:", len(bra1))
    print("crs:", bra.crs, "| bounds:", [round(v, 2) for v in bra.total_bounds])
    print("states sample:", sorted(bra1[pick(bra1, "name")])[:5])
    print("written:", gpkg)


if __name__ == "__main__":
    main()