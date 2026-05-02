"""
SVAR model estimation — Layer 3.5.

Fits a reduced-form VAR, identifies structural shocks via Cholesky decomposition,
computes IRFs (24 periods) and FEVD (1, 6, 12, 24 months), and writes JSON results.

Cholesky ordering (most exogenous → most endogenous):
  1. fx_mom_pct               — exchange rate shock
  2. emae_yoy_pct             — activity shock
  3. real_total_credit_yoy_pct— credit shock
  4. real_wage_yoy_pct        — wage shock
  5. cpi_mom_pct              — inflation (most endogenous)
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from utils import get_logger

log = get_logger("svar.model")

SVAR_DIR  = Path(__file__).parent.parent / "data" / "svar"
IRF_FILE  = SVAR_DIR / "irf_results.json"
FEVD_FILE = SVAR_DIR / "fevd_results.json"

IRF_PERIODS   = 24
FEVD_HORIZONS = [1, 6, 12, 24]
MAX_LAGS      = 6
BOOTSTRAP_REPS = 200   # for CI; increase to 500 for publication quality

VAR_COLS = [
    "fx_mom_pct",
    "emae_yoy_pct",
    "real_total_credit_yoy_pct",
    "real_wage_yoy_pct",
    "cpi_mom_pct",
]
VAR_LABELS = {
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

    # irfs shape: (periods+1, n_vars, n_vars) — irfs[t, impulse, response]
    irfs = irf_analysis.irfs  # orthogonalized by default

    # Bootstrap confidence intervals
    log.info("SVAR model: bootstrap CIs (%d replications)...", BOOTSTRAP_REPS)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ci = irf_analysis.errband_mc(
                orth=True, repl=BOOTSTRAP_REPS, signif=0.05, seed=42
            )
        # ci is a tuple (lower, upper), each shape (periods+1, n_vars, n_vars)
        irf_lower, irf_upper = ci
    except Exception as exc:
        log.warning("SVAR model: bootstrap CI failed (%s) — using ±2 asymptotic stderr.", exc)
        try:
            se = np.sqrt(np.abs(irf_analysis.cov()[:, :, :]))
            se = se.reshape(IRF_PERIODS + 1, n_vars, n_vars)
        except Exception:
            se = np.zeros_like(irfs)
        irf_lower = irfs - 2 * se
        irf_upper = irfs + 2 * se

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
                "point":  [round(float(v), 6) for v in irfs[:, imp_idx, resp_idx]],
                "lower":  [round(float(v), 6) for v in irf_lower[:, imp_idx, resp_idx]],
                "upper":  [round(float(v), 6) for v in irf_upper[:, imp_idx, resp_idx]],
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

    return {"irf": irf_json, "fevd": fevd_json}
