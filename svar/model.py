"""
SVAR model estimation — Layer 3.5.

Fits a reduced-form VAR, identifies structural shocks via Cholesky decomposition,
computes IRFs (24 periods) and FEVD (1, 6, 12, 24 months), and writes JSON results.

Cholesky ordering (most exogenous → most endogenous):
  1. m2_yoy_pct               — monetary policy (M2 private YoY)
  2. fx_mom_pct               — exchange rate shock
  3. emae_yoy_pct             — activity shock
  4. real_total_credit_yoy_pct— credit shock
  5. real_wage_yoy_pct        — wage shock
  6. cpi_mom_pct              — inflation (most endogenous)
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from utils import get_logger

log = get_logger("svar.model")

SVAR_DIR       = Path(__file__).parent.parent / "data" / "svar"
IRF_FILE       = SVAR_DIR / "irf_results.json"
FEVD_FILE      = SVAR_DIR / "fevd_results.json"
FORECAST_FILE  = SVAR_DIR / "forecast_results.json"

IRF_PERIODS       = 24
FEVD_HORIZONS     = [1, 6, 12, 24]
FORECAST_HORIZONS = [6, 12]
MAX_LAGS          = 6
BOOTSTRAP_REPS    = 200   # for CI; increase to 500 for publication quality

VAR_COLS = [
    "m2_yoy_pct",
    "fx_mom_pct",
    "emae_yoy_pct",
    "real_total_credit_yoy_pct",
    "real_wage_yoy_pct",
    "cpi_mom_pct",
]
VAR_LABELS = {
    "m2_yoy_pct":                  "M2 growth (monetary policy)",
    "fx_mom_pct":                  "FX shock",
    "emae_yoy_pct":                "Activity shock",
    "real_total_credit_yoy_pct":   "Credit shock",
    "real_wage_yoy_pct":           "Wage shock",
    "cpi_mom_pct":                 "Inflation",
}


def _select_max_lags(n_obs: int, n_vars: int) -> int:
    """Cap max lags so each equation retains ≥ 2×n_vars degrees of freedom."""
    max_safe = max(1, (n_obs - 2 * n_vars) // n_vars)
    return min(MAX_LAGS, max_safe)


def fit_model(df: pd.DataFrame) -> dict | None:
    """
    Fit reduced-form VAR, identify via Cholesky, compute IRF + FEVD.
    Returns summary dict and writes JSON files.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from statsmodels.tsa.vector_ar.var_model import VAR

    SVAR_DIR.mkdir(parents=True, exist_ok=True)

    # Ensure correct column ordering (Cholesky identification depends on order)
    cols_avail = [c for c in VAR_COLS if c in df.columns]
    if len(cols_avail) < 3:
        log.error("SVAR model: need at least 3 variables; got %d. Skipping.", len(cols_avail))
        return None

    data = df[cols_avail].dropna()
    n_obs, n_vars = data.shape
    log.info("SVAR model: fitting VAR on %d obs x %d vars", n_obs, n_vars)

    if n_obs < 30:
        log.error("SVAR model: only %d observations — too few to fit. Skipping.", n_obs)
        return None

    max_lags = _select_max_lags(n_obs, n_vars)
    log.info("SVAR model: AIC lag selection (max %d lags)...", max_lags)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model   = VAR(data.values)
        results = model.fit(maxlags=max_lags, ic="aic", verbose=False)

    lag_order = results.k_ar
    log.info("SVAR model: selected %d lags (AIC=%.2f)", lag_order, results.info_criteria["aic"])

    # --- Impulse response functions (orthogonalized = Cholesky) ---
    log.info("SVAR model: computing IRFs (%d periods)...", IRF_PERIODS)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        irf_analysis = results.irf(IRF_PERIODS)

    # orth_irfs shape: (periods+1, n_vars, n_vars) — orth_irfs[t, response, impulse]
    irfs = irf_analysis.orth_irfs

    # Bootstrap confidence intervals — manual residual bootstrap for correctness
    log.info("SVAR model: bootstrap CIs (%d replications)...", BOOTSTRAP_REPS)
    rng   = np.random.default_rng(42)
    resid = results.resid          # shape (T - p, n_vars)
    coefs = results.coefs          # shape (p, n_vars, n_vars)
    intercept = results.intercept  # shape (n_vars,)
    data_arr  = data.values        # shape (T, n_vars)

    boot_irfs: list[np.ndarray] = []
    for _ in range(BOOTSTRAP_REPS):
        idx        = rng.integers(0, len(resid), size=len(resid))
        boot_resid = resid[idx]

        # Reconstruct bootstrap time series from estimated coefficients + resampled residuals
        y = np.empty_like(data_arr)
        y[:lag_order] = data_arr[:lag_order]
        for t in range(lag_order, len(y)):
            y[t] = intercept.copy()
            for lag in range(lag_order):
                y[t] += coefs[lag] @ y[t - lag - 1]
            y[t] += boot_resid[t - lag_order]

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                b_res = VAR(y).fit(maxlags=lag_order, ic=None, verbose=False)
                boot_irfs.append(b_res.irf(IRF_PERIODS).orth_irfs)
        except Exception:
            continue

    if len(boot_irfs) >= 10:
        boot_arr  = np.array(boot_irfs)          # (reps, periods+1, n_vars, n_vars)
        irf_lower = np.percentile(boot_arr, 2.5,  axis=0)
        irf_upper = np.percentile(boot_arr, 97.5, axis=0)
        log.info("SVAR model: bootstrap CIs from %d replications.", len(boot_irfs))
    else:
        log.warning("SVAR model: too few bootstrap replications (%d) — CIs set to point estimate.", len(boot_irfs))
        irf_lower = irfs.copy()
        irf_upper = irfs.copy()

    # Build IRF JSON: for each impulse variable, IRF to CPI (and all responses)
    cpi_idx = cols_avail.index("cpi_mom_pct") if "cpi_mom_pct" in cols_avail else -1
    irf_json: dict = {
        "lag_order":      lag_order,
        "n_obs":          n_obs,
        "periods":        IRF_PERIODS,
        "variable_names": cols_avail,
        "variable_labels": {k: VAR_LABELS.get(k, k) for k in cols_avail},
        "shocks":         {},
    }

    for imp_idx, imp_col in enumerate(cols_avail):
        shock: dict = {}
        for resp_idx, resp_col in enumerate(cols_avail):
            shock[resp_col] = {
                "point":  [round(float(v), 6) for v in irfs[:, resp_idx, imp_idx]],
                "lower":  [round(float(v), 6) for v in irf_lower[:, resp_idx, imp_idx]],
                "upper":  [round(float(v), 6) for v in irf_upper[:, resp_idx, imp_idx]],
            }
        irf_json["shocks"][imp_col] = shock

    IRF_FILE.write_text(json.dumps(irf_json, indent=2))
    log.info("SVAR model: IRF results saved -> %s", IRF_FILE)

    # --- Forecast error variance decomposition ---
    log.info("SVAR model: computing FEVD...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fevd_analysis = results.fevd(max(FEVD_HORIZONS))

    # decomp shape: (periods, n_vars, n_vars) — decomp[t, equation, source]
    decomp = fevd_analysis.decomp

    fevd_json: dict = {
        "horizons":       FEVD_HORIZONS,
        "variable_names": cols_avail,
        "variable_labels": {k: VAR_LABELS.get(k, k) for k in cols_avail},
        "fevd":           {},
    }

    # decomp shape: (n_vars, periods, n_vars) — decomp[equation, horizon, source]
    for resp_idx, resp_col in enumerate(cols_avail):
        fevd_json["fevd"][resp_col] = {}
        for h in FEVD_HORIZONS:
            h_idx = min(h - 1, decomp.shape[1] - 1)
            row = decomp[resp_idx, h_idx, :]
            fevd_json["fevd"][resp_col][str(h)] = {
                src_col: round(float(row[src_idx]) * 100, 2)
                for src_idx, src_col in enumerate(cols_avail)
            }

    FEVD_FILE.write_text(json.dumps(fevd_json, indent=2))
    log.info("SVAR model: FEVD results saved -> %s", FEVD_FILE)

    # Log headline results
    if cpi_idx >= 0:
        log.info("SVAR model: FEVD of inflation at 12-month horizon:")
        fevd_12 = fevd_json["fevd"].get("cpi_mom_pct", {}).get("12", {})
        for src, share in sorted(fevd_12.items(), key=lambda x: -x[1]):
            log.info("  %-35s  %.1f%%", VAR_LABELS.get(src, src), share)

    # --- Forecasts ---
    max_horizon = max(FORECAST_HORIZONS)
    log.info("SVAR model: computing %d-month forecasts...", max_horizon)
    try:
        last_obs = data.values[-lag_order:]   # (p, n_vars) — conditioning observations
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fc_point = results.forecast(last_obs, steps=max_horizon)
            _, fc_lower, fc_upper = results.forecast_interval(
                last_obs, steps=max_horizon, alpha=0.05
            )

        # Historical tail to provide context in charts (last 24 months)
        hist_tail = min(24, len(data))
        history = {
            col: [round(float(v), 4) for v in data[col].values[-hist_tail:]]
            for col in cols_avail
        }
        history_dates = [d.strftime("%Y-%m") for d in data.index[-hist_tail:]]

        # Date index for forecast periods
        last_date   = data.index[-1]
        freq        = pd.tseries.frequencies.to_offset("MS")
        fc_dates    = [
            (last_date + freq * (i + 1)).strftime("%Y-%m")
            for i in range(max_horizon)
        ]

        forecast_json: dict = {
            "as_of_date":      last_date.strftime("%Y-%m"),
            "lag_order":       lag_order,
            "n_obs":           n_obs,
            "horizons":        FORECAST_HORIZONS,
            "variable_names":  cols_avail,
            "variable_labels": {k: VAR_LABELS.get(k, k) for k in cols_avail},
            "history_dates":   history_dates,
            "history":         history,
            "forecast_dates":  fc_dates,
            "forecasts":       {},
        }

        for i, col in enumerate(cols_avail):
            forecast_json["forecasts"][col] = {
                "point": [round(float(v), 4) for v in fc_point[:, i]],
                "lower": [round(float(v), 4) for v in fc_lower[:, i]],
                "upper": [round(float(v), 4) for v in fc_upper[:, i]],
            }

        FORECAST_FILE.write_text(json.dumps(forecast_json, indent=2))
        log.info("SVAR model: forecasts saved -> %s", FORECAST_FILE)

        # Log CPI forecast headline
        if cpi_idx >= 0:
            cpi_fc = forecast_json["forecasts"].get("cpi_mom_pct", {})
            for h in FORECAST_HORIZONS:
                pt = cpi_fc["point"][h - 1]
                lo = cpi_fc["lower"][h - 1]
                hi = cpi_fc["upper"][h - 1]
                log.info("SVAR model: CPI forecast +%dM  point=%.2f%%  95%% CI [%.2f%%, %.2f%%]",
                         h, pt, lo, hi)

    except Exception as exc:
        log.warning("SVAR model: forecast computation failed (%s).", exc)
        forecast_json = {}

    return {"irf": irf_json, "fevd": fevd_json, "forecast": forecast_json}
