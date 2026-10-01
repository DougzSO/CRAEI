"""COMANDO 18-D Action 1: is O08's Pearson III F_D gap a bug or a real estimator
property, tested against a known-answer synthetic ground truth?

For samples of size 30 drawn from a distribution with KNOWN parameters, the
population frequency of a standardized value <= -1.5, when standardized
with the TRUE parameters, is exactly `norm.cdf(-1.5)` = 6.68% by
construction (SPEI standardization maps the true distribution's quantiles
onto the standard normal). When standardized instead with parameters fit
from only the 30-sample draw, any systematic shift away from 6.68% is pure
small-sample estimator bias, computed analytically (no Monte Carlo
validation-set noise): the frequency a fitted-parameter threshold implies
under the TRUE distribution is `true_dist.cdf(fitted_dist.ppf(q, *fitted_params), *true_params)`,
`q = norm.cdf(-1.5)`.

Two true-generating families are used, each once matching PWM
log-logistic's own family (log-logistic, PWM "correctly specified") and
once matching Pearson III's own family (Pearson III, Pearson III
"correctly specified") -- isolating whether Pearson III's MLE has its own
small-sample tail bias even when its model is right, vs. only showing bias
when fitting log-logistic-generated data (model misspecification).
Read-only, no production code touched.
"""

import numpy as np
from scipy import stats

from craei.hazards import spei

THEORETICAL_FREQ = float(stats.norm.cdf(-1.5))
N = 30
NREP = 800
SEED = 7

LOGLOGISTIC_CONFIGS = [  # (c, loc, scale) -- c descending = skew increasing
    (30, 100, 80),
    (15, 100, 80),
    (8, 100, 80),
    (5, 100, 80),
    (3.5, 100, 80),
]
PEARSON3_CONFIGS = [  # (skew, loc, scale)
    (-2.0, 0, 1),
    (-1.0, 0, 1),
    (-0.5, 0, 1),
    (0.5, 0, 1),
    (1.0, 0, 1),
    (2.0, 0, 1),
]


def _true_freq(fitted_dist, fitted_params, true_dist, true_params):
    x_thresh = fitted_dist.ppf(THEORETICAL_FREQ, *fitted_params)
    return float(true_dist.cdf(x_thresh, *true_params))


def _run(true_dist, true_params, label: str, rng: np.random.Generator) -> None:
    pwm_freqs, p3_freqs = [], []
    pwm_signs = []
    for _ in range(NREP):
        x = true_dist.rvs(*true_params, size=N, random_state=rng)
        pwm_params, pwm_status = spei._fit_loglogistic_pwm(x)
        if pwm_status == "success":
            f = (pwm_params["shape"], pwm_params["loc"], pwm_params["scale"])
            pwm_freqs.append(_true_freq(stats.fisk, f, true_dist, true_params))

        p3_params, p3_status = spei._fit_pearson3_mle(x)
        if p3_status == "success":
            f = (p3_params["shape"], p3_params["loc"], p3_params["scale"])
            p3_freqs.append(_true_freq(stats.pearson3, f, true_dist, true_params))
            pwm_signs.append(np.sign(p3_params["shape"]))

    pwm_freqs = np.array(pwm_freqs)
    p3_freqs = np.array(p3_freqs)
    n_pwm, n_p3 = len(pwm_freqs), len(p3_freqs)
    pwm_bias = pwm_freqs.mean() - THEORETICAL_FREQ if n_pwm else float("nan")
    p3_bias = p3_freqs.mean() - THEORETICAL_FREQ if n_p3 else float("nan")
    sign_note = ""
    if pwm_signs:
        pos = sum(1 for s in pwm_signs if s > 0)
        neg = sum(1 for s in pwm_signs if s < 0)
        sign_note = f", pearson3 fitted skew sign: {pos} positive / {neg} negative"
    print(
        f"{label:32s} PWM: n_success={n_pwm:4d}/{NREP} mean_freq={pwm_freqs.mean()*100 if n_pwm else float('nan'):6.3f}% "
        f"bias={pwm_bias*100 if n_pwm else float('nan'):+6.3f}pp   |  "
        f"Pearson3: n_success={n_p3:4d}/{NREP} mean_freq={p3_freqs.mean()*100 if n_p3 else float('nan'):6.3f}% "
        f"bias={p3_bias*100 if n_p3 else float('nan'):+6.3f}pp{sign_note}"
    )


def main() -> None:
    print(f"Theoretical frequency (norm.cdf(-1.5)): {THEORETICAL_FREQ*100:.3f}%")
    print(f"N={N} per sample, {NREP} replicates per config\n")

    rng = np.random.default_rng(SEED)
    print("=== True generating family: log-logistic (PWM 'correctly specified') ===")
    for c, loc, scale in LOGLOGISTIC_CONFIGS:
        _run(stats.fisk, (c, loc, scale), f"fisk(c={c},loc={loc},scale={scale})", rng)

    print("\n=== True generating family: Pearson III (Pearson III 'correctly specified') ===")
    for skew, loc, scale in PEARSON3_CONFIGS:
        _run(stats.pearson3, (skew, loc, scale), f"pearson3(skew={skew},loc={loc},scale={scale})", rng)


if __name__ == "__main__":
    main()
