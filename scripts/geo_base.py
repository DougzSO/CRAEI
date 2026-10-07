"""O26: fetch Natural Earth (public domain) via cartopy and keep Brazil layers.

Also builds the article map layers from GADM 4.1 (Phase 9): `brazil_admin0_gadm` and `brazil_admin1_gadm` in
`gadm_brazil.gpkg`, simplified at 0.01 degree, state postal code from HASC_1. GADM is not redistributable:
the gpkg stays outside any public archive (see docs/OPEN_ITEMS.md).
"""

from datetime import date
from pathlib import Path

import geopandas as gpd
import shapely
from cartopy.io import shapereader

from craei.config import load_paths


def fetch(name):
    path = shapereader.natural_earth(resolution="10m", category="cultural", name=name)
    return gpd.read_file(path), path


def pick(gdf, col):
    low = {c.lower(): c for c in gdf.columns}
    return low[col.lower()]


GADM_TOLERANCE = 0.01  # degrees


def build_gadm(out):
    """GADM 4.1 country and state layers, lightly simplified; states keep their shared borders."""
    src = Path(load_paths()["gadm_bra_dir"])
    a0 = gpd.read_file(src / "gadm41_BRA_0_mainland.shp")
    a1 = gpd.read_file(src / "gadm41_BRA_1_mainland.shp")
    assert len(a0) == 1 and len(a1) == 27, (len(a0), len(a1))
    a0["geometry"] = a0.geometry.simplify(GADM_TOLERANCE, preserve_topology=True)
    simp = shapely.coverage_simplify(a1.geometry.to_numpy(), GADM_TOLERANCE)
    a1 = a1.assign(geometry=gpd.GeoSeries(simp, index=a1.index, crs=a1.crs))
    a1["postal"] = a1["HASC_1"].str[-2:]
    a1 = a1[["GID_1", "NAME_1", "postal", "geometry"]]
    assert a1["postal"].nunique() == 27 and a1.geometry.is_valid.all() and a0.geometry.is_valid.all()
    gpkg = out / "gadm_brazil.gpkg"
    a0.to_file(gpkg, layer="brazil_admin0_gadm", driver="GPKG")
    a1.to_file(gpkg, layer="brazil_admin1_gadm", driver="GPKG")
    note = "\n".join([
        "GADM 4.1 Brazil, mainland (gadm41_BRA_0_mainland, gadm41_BRA_1_mainland), simplified "
        + str(GADM_TOLERANCE) + " degree on " + str(date.today()) + ".",
        "GADM licence: free for academic and non-commercial use, redistribution not allowed (gadm.org/license).",
        "Do not include this file in any public archive; cite and obtain from gadm.org.", ""])
    (out / "SOURCE_GADM.txt").write_text(note, encoding="utf-8")
    print("gadm admin0 / admin1:", len(a0), len(a1), "| written:", gpkg)


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
    build_gadm(out)


if __name__ == "__main__":
    main()