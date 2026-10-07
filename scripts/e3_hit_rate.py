"""E3 hit rate (D146): ENA drought month (anomaly <= P20 of its calendar month) against the pipeline signal.

Signal: regional W5E5 SPEI-12 or SPI-12 <= drought threshold (-1.5). Main metric P(event | signal) with
lift over the realized event frequency; POD = P(signal | event); Heidke Skill Score. Lag 0 main, lags 1-6
supplementary (index at t-L, ENA at t). Block-12 bootstrap, 2,000 resamples, seed [23, 5, k]. Regions with
fewer than 10 signal months are 'not reportable' (count only). Reads e3_regional_series.csv written by
scripts/e3_ena_validation.py; writes e3_hit_rate.csv.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from craei.config import load_params, load_paths  # noqa: E402
from craei.exposure import hedge  # noqa: E402

GROUPS = ["SE/CO", "S", "NE", "N"]
INDICES = ["SPEI_12", "SPI_12"]
P_EVENT = 0.20
MIN_SIGNAL = 10
BLOCK, N_SIM = 12, 2000


def table_stats(s, e):
    s, e = np.asarray(s, bool), np.asarray(e, bool)
    a, b = int((s & e).sum()), int((s & ~e).sum())
    c, d = int((~s & e).sum()), int((~s & ~e).sum())
    n = a + b + c + d
    hit = a / (a + b) if a + b else np.nan
    pod = a / (a + c) if a + c else np.nan
    base = (a + c) / n
    den = (a + c) * (c + d) + (a + b) * (b + d)
    return {"hits": a, "false_alarms": b, "misses": c, "correct_neg": d,
            "P_event_given_signal": hit, "POD": pod, "base_rate": base,
            "lift": hit / base if base > 0 else np.nan,
            "HSS": 2 * (a * d - b * c) / den if den else np.nan}


def event_flags(anom):
    """ENA anomaly <= P20 of its calendar month, within the region (months 2000-01..2019-12 in order)."""
    anom = np.asarray(anom, float)
    ev = np.zeros(len(anom), bool)
    cal = np.arange(len(anom)) % 12
    for m in range(12):
        x = anom[cal == m]
        ev[cal == m] = x <= np.quantile(x, P_EVENT)
    return ev


def main():
    tab = Path(load_paths()["outputs_tables_dir"])
    thr = float(load_params()["drought_spei_threshold"]["value"])
    ser = pd.read_csv(tab / "e3_regional_series.csv", parse_dates=["month"])
    rows, k = [], 0
    for g in GROUPS:
        for name in INDICES:
            x = ser[(ser["group"] == g) & (ser["index"] == name)].sort_values("month")
            ev_all = event_flags(x["ena_anom"].to_numpy())
            idx = x["index_value"].to_numpy()
            for L in range(7):
                sig = (idx[: len(idx) - L] <= thr)
                ev = ev_all[L:]
                st = table_stats(sig, ev)
                n_sig = int(sig.sum())
                row = {"group": g, "index": name, "lag": L, "main": L == 0, "n": len(sig),
                       "n_signal": n_sig, "n_event": int(ev.sum()),
                       "reportable": n_sig >= MIN_SIGNAL, **st}
                if n_sig >= MIN_SIGNAL:
                    bi = hedge.mbb_indices(len(sig), BLOCK, N_SIM, np.random.default_rng([23, 5, k]))
                    boot = pd.DataFrame([table_stats(sig[i], ev[i]) for i in bi])
                    for m in ("P_event_given_signal", "lift", "POD", "HSS"):
                        row[m + "_lo"], row[m + "_hi"] = hedge.percentile_ci(boot[m])
                else:
                    for m in ("P_event_given_signal", "lift", "POD", "HSS"):
                        row[m] = np.nan
                        row[m + "_lo"] = row[m + "_hi"] = np.nan
                    row["lift"] = np.nan
                rows.append(row)
                k += 1
    out = pd.DataFrame(rows)
    out.to_csv(tab / "e3_hit_rate.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250)
    cols = ["group", "index", "n_signal", "n_event", "hits", "reportable", "P_event_given_signal",
            "P_event_given_signal_lo", "P_event_given_signal_hi", "lift", "lift_lo", "lift_hi", "POD", "HSS",
            "HSS_lo", "HSS_hi"]
    print(out[out["lag"] == 0][cols].round(3).to_string(index=False))
    print(out[(out["lag"] > 0) & (out["group"] == "SE/CO")][["index", "lag", "n_signal", "P_event_given_signal",
          "lift", "HSS"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
