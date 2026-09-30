"""COMANDO 18-F Action 4: synthetic tail-bias check at the temporal variants'
sample sizes (n=90, 150, 360), same known-answer methodology as COMANDO
18-D/18-E (`audit_pearson3_bias_synthetic.py`, `audit_pool_size_synthetic_bias.py`).
"""

import numpy as np
from scipy import stats

from craei.hazards import spei

THEORETICAL_FREQ = float(stats.norm.cdf(-1.5))
NREP = 800
SEED = 23

CONFIGS = [(30, 100, 80), (15, 100, 80), (8, 100, 80), (5, 100, 80), (3.5, 100, 80)]
SAMPLE_SIZES = {
    "n=30 (original per-series)": 30,
    "n=90 (window k=1)": 90,
    "n=150 (window k=2)": 150,
    "n=360 (single per-series, variant b)": 360,
}


def _true_freq(fitted_params, true_dist, true_params):
    x_thresh = stats.fisk.ppf(THEORETICAL_FREQ, *fitted_params)
    return float(true_dist.cdf(x_thresh, *true_params))


def _run(true_params, n, rng):
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


def main():
    print(f"Theoretical frequency: {THEORETICAL_FREQ*100:.3f}%; {NREP} replicates per (config, N)\n")
    rng = np.random.default_rng(SEED)
    for label, n in SAMPLE_SIZES.items():
        print(f"--- {label} ---")
        for c, loc, scale in CONFIGS:
            bias, n_success = _run((c, loc, scale), n, rng)
            print(f"  fisk(c={c}): n_success={n_success}/{NREP} bias={bias*100:+.4f}pp")
        print()


if __name__ == "__main__":
    main()
