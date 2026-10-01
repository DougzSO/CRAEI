"""COMANDO 18-E Action 6: does the pool's much larger sample size actually
remove the small-sample tail bias COMANDO 18-D measured at n=30?

Same known-answer methodology as `audit_pearson3_bias_synthetic.py`: draw N
samples from a log-logistic distribution with known parameters, fit PWM,
and compute the analytic frequency a value <= -1.5 would have under the
TRUE distribution when standardized with the FITTED (from N samples)
parameters -- any shift from `norm.cdf(-1.5)` = 6.68% is small-sample bias.
Only PWM is tested (production no longer uses Pearson III, D52); N is set
to this project's real measured pool sizes (`scripts/08_spei.py`'s run),
not just n=30 for comparison.
"""

import numpy as np
from scipy import stats

from craei.hazards import spei

THEORETICAL_FREQ = float(stats.norm.cdf(-1.5))
NREP = 800
SEED = 19

CONFIGS = [  # (c, loc, scale)
    (30, 100, 80),
    (15, 100, 80),
    (8, 100, 80),
    (5, 100, 80),
    (3.5, 100, 80),
]

# Real pool sizes measured by scripts/08_spei.py's production run (this
# command); N=30 included for direct comparison against COMANDO 18-D.
POOL_SIZES = {
    "n=30 (per-series, COMANDO 18-D)": 30,
    "N=1,800 (smallest real pool: PRT run-of-river/thermal)": 1800,
    "N=23,700 (median-ish real pool: BRA hydro reservoir)": 23700,
    "N=51,150 (largest real pool: BRA thermal water-dependent)": 51150,
}


def _true_freq(fitted_params, true_dist, true_params):
    x_thresh = stats.fisk.ppf(THEORETICAL_FREQ, *fitted_params)
    return float(true_dist.cdf(x_thresh, *true_params))


def _run(true_params, n: int, rng: np.random.Generator) -> tuple[float, int]:
    freqs = []
    for _ in range(NREP):
        x = stats.fisk.rvs(*true_params, size=n, random_state=rng)
        params, status = spei._fit_loglogistic_pwm(x)
        if status == "success":
            f = (params["shape"], params["loc"], params["scale"])
            freqs.append(_true_freq(f, stats.fisk, true_params))
    freqs = np.array(freqs)
    bias = freqs.mean() - THEORETICAL_FREQ if len(freqs) else float("nan")
    return bias, len(freqs)


def main(pool_sizes: dict) -> None:
    print(f"Theoretical frequency (norm.cdf(-1.5)): {THEORETICAL_FREQ*100:.3f}%")
    print(f"{NREP} replicates per (config, N)\n")

    rng = np.random.default_rng(SEED)
    for label, n in pool_sizes.items():
        print(f"--- N={n} ({label}) ---")
        for c, loc, scale in CONFIGS:
            bias, n_success = _run((c, loc, scale), n, rng)
            print(
                f"  fisk(c={c},loc={loc},scale={scale}): n_success={n_success}/{NREP} "
                f"bias={bias*100:+.4f}pp"
            )
        print()


if __name__ == "__main__":
    main(POOL_SIZES)
